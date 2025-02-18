##### main.py #####
"""
API Endpoints

Features:
- Async request handling (async DB & scraper calls)
- Redis caching (via fastapi-cache)
- Rate limiting placeholders
- Comprehensive error handling
"""

import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from typing import List, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert

from database import get_db, engine, Base
from models import Company, Founder, CompanyFounder
from schemas import CompanySearchResponse, FounderSearchResponse
from config import settings
from serp_scraper import DCPScraper

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager for startup/shutdown:
    - Initialize Redis cache
    - Create DB tables (if dev environment)
    - Dispose connections on shutdown
    """
    redis = aioredis.from_url(settings.REDIS_URL)
    FastAPICache.init(RedisBackend(redis), prefix="dcp-cache")

    if settings.ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
    await redis.close()


app = FastAPI(
    title="DCP AI Scouting Platform",
    version="1.0.0",
    lifespan=lifespan,
    responses={
        404: {"description": "Not Found"},
        429: {"description": "Too Many Requests"},
        500: {"description": "Internal Server Error"},
    }
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/companies/{company_name}", response_model=CompanySearchResponse)
@cache(expire=300)
async def get_company(
    company_name: str,
    db: AsyncSession = Depends(get_db)
) -> CompanySearchResponse:
    """
    Retrieve company info from DB or scrape if not found.
    """

    # 1) Look for company in DB
    result = await db.execute(
        select(Company)
        .options(selectinload(Company.founders))
        .where(func.lower(Company.name) == func.lower(company_name))
    )
    company_obj = result.scalars().first()

    if company_obj:
        return CompanySearchResponse(
            name=company_obj.name,
            domain=company_obj.domain,
            duke_affiliation=False,  # Placeholder
            founders=[f.full_name for f in company_obj.founders]
        )

    # 2) If not found, scrape from SERP
    scraper = DCPScraper()
    try:
        serp_results = await scraper.search_company(company_name)
        if not serp_results:
            raise HTTPException(status_code=404, detail="No data found for this company.")

        # Insert new Company record
        stmt = insert(Company).values(
            name=company_name,
            normalized_name=company_name.lower()
        ).on_conflict_do_nothing()

        await db.execute(stmt)
        await db.commit()

        # Fetch the newly inserted company
        result = await db.execute(
            select(Company).where(func.lower(Company.name) == func.lower(company_name))
        )
        new_company = result.scalars().first()

        if not new_company:
            raise HTTPException(status_code=500, detail="Failed to retrieve the newly inserted company.")

        # Parse & Insert Founders
        for item in serp_results:
            raw_title = item.get("name") or ""
            founder_name = " ".join(raw_title.split()[:2]) if raw_title else "Unknown"

            # Check if founder exists
            foundr_res = await db.execute(
                select(Founder).where(Founder.full_name.ilike(founder_name))
            )
            foundr_obj = foundr_res.scalars().first()

            if not foundr_obj:
                foundr_obj = Founder(
                    full_name=founder_name,
                    normalized_name=founder_name.lower()
                )
                db.add(foundr_obj)
                await db.commit()
                await db.refresh(foundr_obj)

            # Link Founder & Company if not already linked
            link_res = await db.execute(
                select(CompanyFounder).where(
                    (CompanyFounder.company_id == new_company.id)
                    & (CompanyFounder.founder_id == foundr_obj.id)
                )
            )
            if not link_res.scalars().first():
                db.add(CompanyFounder(
                    company_id=new_company.id,
                    founder_id=foundr_obj.id,
                    role="Founder"
                ))
                await db.commit()

        return CompanySearchResponse(
            name=new_company.name,
            domain=new_company.domain,
            duke_affiliation=False,  # Placeholder
            founders=[f.full_name for f in new_company.founders]
        )
    finally:
        await scraper.close()


@app.get("/founders/{founder_name}", response_model=FounderSearchResponse)
@cache(expire=300)
async def get_founder(
    founder_name: str,
    db: AsyncSession = Depends(get_db)
) -> FounderSearchResponse:
    """
    Retrieve founder info from DB or scrape if not found.
    """

    # Step 1: Check if Founder Exists in DB -
    result = await db.execute(
        select(Founder)
        .options(selectinload(Founder.companies))  # Load associated companies
        .where(Founder.full_name.ilike(f"%{founder_name}%"))  
    )
    found: Optional[Founder] = result.scalars().first()

    if found:
        return FounderSearchResponse(
            name=found.full_name,
            duke_affiliation=False,  # Placeholder
            companies=[c.name for c in found.companies]
        )

    # Step 2: Founder Not Found in DB → Search via SERP API
    scraper = DCPScraper()
    try:
        serp_results = await scraper.search_founder(founder_name)
        if not serp_results:
            raise HTTPException(status_code=404, detail="Founder not found in SERP API")

        # Step 3: Insert the new founder into DB
        new_founder = Founder(
            full_name=founder_name.strip(),  # Strip spaces to avoid duplicate issues
            normalized_name=founder_name.lower().strip()
        )
        db.add(new_founder)
        await db.commit()
        await db.refresh(new_founder)

        # Step 4: Attempt to link founder to companies found via SERP
        for item in serp_results:
            company_name = item.get("snippet", "").strip()
            if not company_name:
                continue  # Skip invalid company names
            
            # Step 4.1: Check if company exists
            comp_res = await db.execute(
                select(Company).where(Company.name.ilike(f"%{company_name}%"))
            )
            company_obj = comp_res.scalars().first()

            # Step 4.2: Insert new company if it doesn’t exist
            if not company_obj:
                company_obj = Company(
                    name=company_name,
                    normalized_name=company_name.lower()
                )
                db.add(company_obj)
                await db.commit()
                await db.refresh(company_obj)

            # Step 4.3: Ensure founder-company link exists
            link_res = await db.execute(
                select(CompanyFounder).where(
                    (CompanyFounder.company_id == company_obj.id)
                    & (CompanyFounder.founder_id == new_founder.id)
                )
            )
            if not link_res.scalars().first():
                db.add(CompanyFounder(
                    company_id=company_obj.id,
                    founder_id=new_founder.id,
                    role="Founder"
                ))
                await db.commit()

        # Step 5: Return newly added founder details
        companies_list = [c.name for c in new_founder.companies]
        return FounderSearchResponse(
            name=new_founder.full_name,
            duke_affiliation=False,  # Placeholder
            companies=companies_list
        )

    finally:
        await scraper.close()

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
