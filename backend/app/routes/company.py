"""
Company Routes Module

This module handles company-related API endpoints for searching, creating,
updating, and managing company information.

Key Features:
- Company search and retrieval
- CRUD operations
- Data validation
- Cache management
"""

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
from ..services.redis import redis_service
from ..utils.storage import StorageService
from ..utils.logger import api_logger as logger
from ..utils.config import settings
from .auth import verify_api_key

router = APIRouter(
    prefix="/api/company",
    tags=["Companies"],
    dependencies=[Depends(verify_api_key)]
)

@router.get("/search/{name}", response_model=CompanyResponse)
async def search_company(
    name: str,
    force_refresh: bool = Query(False, description="Force refresh data from sources"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for company information using a three-layered approach.
    
    Args:
        name: Company name to search for
        force_refresh: If True, bypass cache and fetch fresh data
        db: Database session
        
    Returns:
        CompanyResponse containing company information
        
    Raises:
        HTTPException(404): If company not found
        HTTPException(500): For processing errors
    """
    try:
        # Layer 1: Check Redis cache (unless force_refresh is True)
        if not force_refresh:
            cached_data = await redis_service.get(f"company:{name}")
            if cached_data:
                logger.info(f"Cache hit for company: {name}")
                return CompanyResponse(**cached_data)
            
            # Layer 2: Check database
            result = await db.execute(
                select(Company).where(Company.name.ilike(f"%{name}%"))
            )
            company = result.scalars().first()
            
            if company:
                # Cache the database result
                await redis_service.set(
                    f"company:{name}",
                    company.dict(),
                    expire=3600  # 1 hour cache
                )
                return CompanyResponse.from_orm(company)
        
        # Layer 3: Scrape and process new data
        scraper = SERPScraper()
        nlp = NLPProcessor()
        nitter = NitterScraper()
        nitter_nlp = NitterNLP()
        scorer = CompanyScorer()
        storage = StorageService()
        
        # Scrape company data
        company_data = await scraper.search_company(name)
        if not company_data:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Process with NLP
        processed_data = await nlp.process_company(company_data)
        
        # Get Twitter data if available
        if processed_data.get("twitter_handle"):
            tweets = await nitter.get_tweets(processed_data["twitter_handle"])
            if tweets:
                tweet_analysis = await nitter_nlp.analyze_tweets(tweets)
                processed_data["recent_tweets"] = tweet_analysis
        
        # Score company
        scored_data = await scorer.score_company(processed_data)
        
        # Store in database
        company = Company(**scored_data)
        db.add(company)
        await db.commit()
        await db.refresh(company)
        
        # Cache the result
        await redis_service.set(
            f"company:{name}",
            company.dict(),
            expire=3600  # 1 hour cache
        )
        
        return CompanyResponse.from_orm(company)
        
    except Exception as e:
        logger.error(f"Error getting company {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{company_id}", status_code=200)
async def delete_company(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a company by ID.
    
    Args:
        company_id: ID of company to delete
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException(404): If company not found
        HTTPException(500): For database errors
    """
    try:
        # Delete from database
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalars().first()
        
        if company:
            await db.delete(company)
            await db.commit()
            
            # Clear cache
            await redis_service.delete(f"company:{company.name}")
            
            return {"message": "Company deleted successfully"}
        
        raise HTTPException(status_code=404, detail="Company not found")
        
    except Exception as e:
        logger.error(f"Error deleting company {company_id}: {str(e)}")
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
    List companies with optional filtering.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        duke_affiliated: Filter by Duke affiliation status
        min_score: Filter by minimum relevance score
        db: Database session
        
    Returns:
        List of CompanyResponse objects
        
    Raises:
        HTTPException(500): For database errors
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