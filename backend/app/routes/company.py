from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging

from ..db.session import get_db
from ..db.models import Company
from ..db.schemas import CompanyResponse, CompanyCreate, CompanyUpdate
from ..db.migrate_json_to_db import process_company_data, process_company_people
from ..services.scraper import SERPScraper
from ..services.nlp_processor import NLPProcessor
from ..services.nitter import NitterScraper
from ..services.nitter_nlp import NitterNLP
from ..services.company_scorer import CompanyScorer
from ..utils.storage import StorageService
from ..utils.logger import get_logger
from ..utils.config import settings

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    responses={404: {"description": "Not found"}}
)

logger = get_logger("company_routes")

@router.get("/{name}", response_model=CompanyResponse)
async def get_company(
    name: str,
    force_refresh: bool = Query(False, description="Force refresh data from sources"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get company information using a three-layered search approach:
    1. Check database for existing entry (unless force_refresh is True)
    2. If not found or force_refresh, scrape and process new data
    3. Store processed data in database
    """
    try:
        # Layer 1: Check database (unless force_refresh is True)
        if not force_refresh:
            result = await db.execute(
                select(Company).where(Company.name.ilike(f"%{name}%"))
            )
            company = result.scalars().first()
            
            if company:
                return CompanyResponse.from_orm(company)
            
        # Layer 2: Initialize services for data collection and processing
        scraper = SERPScraper()
        processor = NLPProcessor()
        nitter_scraper = NitterScraper()
        nitter_nlp = NitterNLP()
        company_scorer = CompanyScorer()
        storage = StorageService()
        
        # Get SERP results
        serp_results = await scraper.search_company(name)
        if not serp_results or "organic_results" not in serp_results:
            raise HTTPException(status_code=404, detail=f"No information found for company: {name}")
            
        # Save raw SERP data
        storage.save_raw_data(serp_results, "serp_company", name)
        
        # Process company data
        company_data = await processor.process_company(name, serp_results)
        if not company_data:
            raise HTTPException(status_code=404, detail=f"Could not process company data for: {name}")
            
        # Save intermediate data
        storage.save_processed_data(company_data, "company", f"{name}_intermediate")
        
        # Get and process Twitter data if handle exists
        twitter_urgency_score = None
        if company_data.get("twitter_handle"):
            nitter_results = await nitter_scraper.get_raw_tweets(name)
            if nitter_results and "raw_tweets" in nitter_results:
                storage.save_raw_data(nitter_results, "nitter", name)
                
                # Analyze tweets
                summary, urgency_score = await nitter_nlp.analyze_tweets(nitter_results["raw_tweets"])
                twitter_urgency_score = urgency_score
                
                # Save Twitter analysis
                nitter_analysis = {
                    "summary": summary,
                    "urgency_score": urgency_score
                }
                storage.save_processed_data(nitter_analysis, "nitter_analysis", name)
                company_data["twitter_summary"] = summary
        
        # Process people data
        if "people" in company_data:
            storage.save_processed_data({"people": company_data["people"]}, "company", f"{name}_people")
            
        # Calculate final score
        company_data["relevance_score"] = company_scorer.calculate_relevance_score(
            company_data=company_data,
            processed_people=company_data.get("people", []),
            twitter_urgency_score=twitter_urgency_score
        )
        
        # Save final data
        storage.save_data(company_data, "company", name, settings.JSON_INPUTS_DIR)
        
        # Layer 3: Store in database
        company = await process_company_data(company_data, db)
        if not company:
            raise HTTPException(status_code=500, detail="Failed to store company data")
            
        # Store associated people
        if "people" in company_data:
            await process_company_people(company, company_data["people"], db)
            
        return CompanyResponse.from_orm(company)
        
    except Exception as e:
        logger.error(f"Error processing company {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    duke_affiliated: Optional[bool] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List companies with optional filtering by Duke affiliation and minimum score.
    """
    try:
        query = select(Company)
        
        if duke_affiliated is not None:
            query = query.where(Company.duke_affiliation_status == "confirmed" if duke_affiliated else Company.duke_affiliation_status != "confirmed")
            
        if min_score is not None:
            query = query.where(Company.relevance_score >= min_score)
            
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        companies = result.scalars().all()
        
        return [CompanyResponse.from_orm(company) for company in companies]
        
    except Exception as e:
        logger.error(f"Error listing companies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new company entry manually.
    """
    try:
        # Check if company exists
        result = await db.execute(
            select(Company).where(Company.name.ilike(f"%{company.name}%"))
        )
        existing = result.scalars().first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Company {company.name} already exists")
            
        # Process company data
        company_dict = company.dict()
        new_company = await process_company_data(company_dict, db)
        if not new_company:
            raise HTTPException(status_code=500, detail="Failed to create company")
            
        # Process associated people if any
        if company.people:
            await process_company_people(new_company, company.people, db)
            
        return CompanyResponse.from_orm(new_company)
        
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing company entry.
    """
    try:
        # Check if company exists
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        existing = result.scalars().first()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")
            
        # Update company data
        update_dict = company_update.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(existing, key, value)
            
        await db.commit()
        await db.refresh(existing)
        
        return CompanyResponse.from_orm(existing)
        
    except Exception as e:
        logger.error(f"Error updating company {company_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 