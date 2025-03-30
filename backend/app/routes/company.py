from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json

from ..db.session import get_db
from ..db import crud, schemas
from ..services.scraper import SERPScraper
from ..services.nitter import NitterScraper
from ..services.nlp_processor import NLPProcessor
from ..services.scorer import Scorer
from ..utils.logger import api_logger

# Initialize router
router = APIRouter(prefix="/api/company", tags=["company"])

# Initialize services
serp_scraper = SERPScraper()
nitter_scraper = NitterScraper()
nlp_processor = NLPProcessor()
scorer = Scorer()

@router.get("/", response_model=List[schemas.CompanyResponse])
async def get_companies(
    skip: int = 0,
    limit: int = 100,
    duke_affiliation_status: Optional[str] = Query(
        None, 
        description="Filter by Duke affiliation status (confirmed, please review, no)"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of companies with optional filtering
    """
    api_logger.info(f"Getting companies: skip={skip}, limit={limit}, duke_affiliation_status={duke_affiliation_status}")
    companies = await crud.get_companies(db, skip=skip, limit=limit, duke_affiliation_status=duke_affiliation_status)
    return companies

@router.get("/{company_id}", response_model=schemas.CompanyResponse)
async def get_company_by_id(company_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a company by ID
    """
    api_logger.info(f"Getting company by ID: {company_id}")
    company = await crud.get_company(db, company_id)
    if company is None:
        api_logger.warning(f"Company not found: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.get("/search/", response_model=schemas.CompanyResponse)
async def search_company(
    name: str = Query(..., description="Company name to search for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for a company by name, scraping if not found in database
    """
    api_logger.info(f"Searching for company: {name}")
    
    # Check if company exists in database by name
    company = await crud.get_company_by_name(db, name)
    if company:
        api_logger.info(f"Company found in database by name: {name}")
        return company
    
    # Company not found by name, proceed with scraping
    api_logger.info(f"Company not found in database by name, scraping: {name}")
    
    try:
        # Query SERP API for company details - also searches for Duke affiliation
        serp_results = serp_scraper.search_company(name)
        
        # Check if we got any results
        if not serp_results.get("organic_results"):
            api_logger.warning(f"No search results found for company: {name}")
            raise HTTPException(status_code=404, detail="No information found for this company")
        
        # Extract Twitter handle from NLP results first
        company_data = await nlp_processor.process_company_data(serp_results)
        
        # If Twitter handle is available, scrape tweets and check if company with same handle exists
        twitter_data = None
        if company_data.get("twitter_handle"):
            handle = company_data["twitter_handle"]
            
            # Check if a company with this Twitter handle already exists
            existing_company = await crud.get_company_by_twitter_handle(db, handle)
            if existing_company:
                api_logger.info(f"Company found in database by Twitter handle: {handle}")
                return existing_company
                
            api_logger.info(f"Scraping Twitter for company: {name}, handle: {handle}")
            twitter_data = nitter_scraper.get_recent_tweets(handle)
            
            # Re-process with Twitter data if available
            if not twitter_data.get("twitter_unavailable", False):
                company_data = await nlp_processor.process_company_data(serp_results, twitter_data)
        
        # Score the company
        company_data = scorer.score_company(company_data)
        
        # Create structured company object for database
        company_create = schemas.CompanyCreate(
            name=company_data["name"],
            duke_affiliation_status=company_data["duke_affiliation_status"],
            duke_affiliation_score=company_data["duke_affiliation_score"],
            relevance_score=company_data["relevance_score"],
            summary=company_data["summary"],
            investors=company_data.get("investors"),
            funding_stage=company_data.get("funding_stage"),
            industry=company_data.get("industry"),
            founded=company_data.get("founded"),
            location=company_data.get("location"),
            twitter_handle=company_data.get("twitter_handle"),
            linkedin_handle=company_data.get("linkedin_handle"),
            twitter_summary=schemas.TwitterSummaryBase(
                tweets_analyzed=company_data.get("twitter_summary", {}).get("tweets_analyzed"),
                mentions_funding=company_data.get("twitter_summary", {}).get("mentions_funding"),
                engagement_score=company_data.get("twitter_summary", {}).get("engagement_score"),
                status=company_data.get("twitter_summary", {}).get("status", "unavailable")
            ) if company_data.get("twitter_summary") else None,
            source_links=company_data.get("source_links"),
            raw_data_path=serp_results.get("_file_path"),
            people=[schemas.PersonBase(
                name=person["name"],
                duke_affiliation_status=person["duke_affiliation_status"],
                duke_affiliation_score=person.get("duke_affiliation_score"),
                relevance_score=person["relevance_score"],
                education=person.get("education", []),
                current_company=person.get("current_company"),
                previous_companies=person.get("previous_companies", []),
                twitter_handle=person.get("twitter_handle"),
                linkedin_handle=person.get("linkedin_handle"),
                twitter_summary=person.get("twitter_summary"),
                source_links=person.get("source_links", []),
                title=person["title"]
            ) for person in company_data.get("people", [])]
        )
        
        # Save to database
        db_company = await crud.create_company(db, company_create)
        api_logger.info(f"Company saved to database: {db_company.name} (ID: {db_company.id})")
        
        return db_company
        
    except Exception as e:
        api_logger.error(f"Error searching for company {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing company information: {str(e)}")

@router.put("/{company_id}", response_model=schemas.CompanyResponse)
async def update_company(
    company_id: int,
    company_update: schemas.CompanyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a company by ID
    """
    api_logger.info(f"Updating company: {company_id}")
    company = await crud.update_company(db, company_id, company_update)
    if company is None:
        api_logger.warning(f"Company not found for update: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company

@router.delete("/{company_id}", response_model=schemas.ErrorResponse)
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a company by ID
    """
    api_logger.info(f"Deleting company: {company_id}")
    deleted = await crud.delete_company(db, company_id)
    if not deleted:
        api_logger.warning(f"Company not found for deletion: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": f"Company {company_id} deleted successfully"}
    ) 