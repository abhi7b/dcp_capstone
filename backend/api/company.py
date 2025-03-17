# api/company.py
import logging
import json
import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, status
from backend.scrapers.company_scraper import CompanyScraper
from backend.nlp.company_processor import CompanyProcessor
from backend.nlp.twitter_analyzer import TwitterAnalyzer
from backend.scrapers.twitter_scraper import TwitterScraper
from backend.nlp.services.integration import IntegrationService
from db.database.db import get_db
from db.database.models import Company, Founder, CompanyFounder, SERPUsage, FundingStage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from backend.config.logs import LogManager
from backend.config.cache import cached, invalidate_company_cache, CacheManager, invalidate_cache
from db.schemas.schemas import CompanyDetailResponse, TwitterSummary, SearchRequest, SearchResponse, SearchResult, StatsResponse
from backend.config.config import settings
from sqlalchemy.sql import func
from backend.api.base_endpoint import BaseEndpoint

# Set up logging
LogManager.setup_logging()
logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize base endpoint
company_endpoint = BaseEndpoint(
    model_class=Company,
    response_class=CompanyDetailResponse,
    entity_type="company",
    cache_prefix="company",
    cache_expire=settings.cache.COMPANY_TTL
)

async def track_serp_usage(db: AsyncSession, query_count: int, entity_name: str, entity_type: str = "company"):
    """Track SERP API usage for monitoring and quota management."""
    try:
        usage = SERPUsage(
            timestamp=datetime.utcnow(),
            query_count=query_count,
            entity_name=entity_name,
            entity_type=entity_type,
            endpoint="company_api"
        )
        db.add(usage)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to track SERP usage: {e}")

@router.get("/{company_name}", response_model=CompanyDetailResponse)
async def get_company(
    company_name: str,
    refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a company.
    
    If the company exists in the database, returns the stored data.
    If not, triggers a SERP search and NLP analysis to gather information.
    
    Args:
        company_name: Name of the company to look up
        refresh: Whether to force a refresh of the data
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        CompanyDetailResponse: Detailed company information
    """
    logger.info(f"Company API request for: {company_name}")
    
    # Normalize company name
    company_name = company_name.strip().title()
    
    # Get company from database
    company = await company_endpoint.get_entity_from_db(db, company_name)
    
    # Check if we should refresh the data
    needs_refresh = refresh or (
        company and 
        not await company_endpoint.check_data_freshness(company, max_age_hours=24)
    )
    
    # If company exists and no refresh needed, return it
    if company and not needs_refresh:
        logger.info(f"Returning cached company data for: {company_name}")
        return company_endpoint.prepare_response(company)
    
    # If company exists and refresh requested, schedule background refresh
    if company and needs_refresh and background_tasks:
        logger.info(f"Scheduling background refresh for company: {company_name}")
        background_tasks.add_task(background_refresh_company, company_name, db)
        return company_endpoint.prepare_response(company, is_refreshing=True)
    
    # If company doesn't exist or we need to refresh without background tasks,
    # fetch data synchronously
    logger.info(f"Fetching company data for: {company_name}")
    
    try:
        # Check SERP API quota before proceeding
        await company_endpoint.track_serp_usage(db, 1, company_name)
        
        # Initialize scrapers and processors
        company_scraper = CompanyScraper()
        company_processor = CompanyProcessor()
        twitter_scraper = TwitterScraper()
        twitter_analyzer = TwitterAnalyzer()
        
        # Scrape company data
        serp_data = await company_scraper.search_company(company_name)
        
        if not serp_data or "error" in serp_data:
            logger.error(f"Error scraping company data: {serp_data.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find information for company: {company_name}"
            )
        
        # Process company data with NLP
        company_analysis = await company_processor.analyze_company(json.dumps(serp_data))
        
        if "error" in company_analysis:
            logger.error(f"Error analyzing company data: {company_analysis['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error analyzing company data: {company_analysis['error']}"
            )
        
        # Extract Twitter handle if available
        twitter_handle = None
        if "social_media" in company_analysis and "twitter" in company_analysis["social_media"]:
            twitter_handle = company_analysis["social_media"]["twitter"]
        
        # Scrape Twitter data if handle is available
        twitter_data = None
        twitter_analysis = None
        if twitter_handle:
            logger.info(f"Scraping Twitter data for: {twitter_handle}")
            twitter_data = await twitter_scraper.get_user_tweets(twitter_handle)
            
            if twitter_data and "tweets" in twitter_data and twitter_data["tweets"]:
                twitter_analysis = await twitter_analyzer.analyze_tweets(twitter_data)
        
        # Integrate all data
        integrated_data = await IntegrationService.process_company_data(
            company_name=company_name,
            serp_data=serp_data,
            twitter_data=twitter_data,
            company_processor_result=company_analysis,
            twitter_analysis=twitter_analysis
        )
        
        # Create or update company in database
        if company:
            company = await update_company_from_integrated_data(db, company, integrated_data)
        else:
            company = await create_company_from_integrated_data(db, integrated_data)
        
        # Process founders if available
        if "founders" in integrated_data and integrated_data["founders"]:
            await process_company_founders(db, company, integrated_data)
        
        # Invalidate cache
        await invalidate_cache(f"company:{company_name}")
        
        return company_endpoint.prepare_response(company)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing company data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing company data: {str(e)}"
        )

async def create_company_from_integrated_data(db: AsyncSession, integrated_data: Dict[str, Any]) -> Company:
    """
    Create a new company from integrated data.
    
    Args:
        db: Database session
        integrated_data: Integrated data from scrapers and processors
        
    Returns:
        Company: Created company
    """
    try:
        # Extract company data
        company_data = integrated_data.get("company_profile", {})
        
        # Create company object
        company = Company(
            name=company_data.get("name", "Unknown"),
            domain=company_data.get("domain"),
            description=company_data.get("description"),
            industry=company_data.get("industry"),
            location=company_data.get("location"),
            year_founded=company_data.get("year_founded"),
            duke_affiliated=company_data.get("duke_affiliated", False),
            duke_connection_type=json.dumps(company_data.get("duke_connection_type", [])),
            duke_department=company_data.get("duke_department"),
            duke_affiliation_confidence=company_data.get("duke_affiliation_confidence", 0.0),
            duke_affiliation_sources=json.dumps(company_data.get("duke_affiliation_sources", [])),
            total_funding=company_data.get("total_funding"),
            latest_valuation=company_data.get("latest_valuation"),
            latest_funding_stage=company_data.get("latest_funding_stage"),
            competitors=json.dumps(company_data.get("competitors", [])),
            funding_rounds=json.dumps(company_data.get("funding_rounds", [])),
            linkedin_url=company_data.get("linkedin_url"),
            twitter_handle=company_data.get("twitter_handle"),
            data_sources=json.dumps(integrated_data.get("data_sources", [])),
            data_quality_score=integrated_data.get("data_quality_score", 0.0),
            data_freshness_score=integrated_data.get("data_freshness_score", 0.0),
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            last_scraped=datetime.utcnow()
        )
        
        # Add Twitter data if available
        if "twitter_analysis" in integrated_data and integrated_data["twitter_analysis"]:
            twitter_analysis = integrated_data["twitter_analysis"]
            company.twitter_data = json.dumps(twitter_analysis)
            company.twitter_summary = twitter_analysis.get("summary", "")
            company.twitter_actionability = twitter_analysis.get("actionability_score", 0)
            company.twitter_last_updated = datetime.utcnow()
        
        # Add to database
        db.add(company)
        await db.commit()
        await db.refresh(company)
        
        logger.info(f"Created new company: {company.name} (ID: {company.id})")
        return company
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating company: {e}", exc_info=True)
        raise

async def update_company_from_integrated_data(db: AsyncSession, company: Company, integrated_data: Dict[str, Any]) -> Company:
    """
    Update an existing company from integrated data.
    
    Args:
        db: Database session
        company: Existing company
        integrated_data: Integrated data from scrapers and processors
        
    Returns:
        Company: Updated company
    """
    try:
        # Extract company data
        company_data = integrated_data.get("company_profile", {})
        
        # Update company fields
        company.domain = company_data.get("domain", company.domain)
        company.description = company_data.get("description", company.description)
        company.industry = company_data.get("industry", company.industry)
        company.location = company_data.get("location", company.location)
        company.year_founded = company_data.get("year_founded", company.year_founded)
        company.duke_affiliated = company_data.get("duke_affiliated", company.duke_affiliated)
        
        if "duke_connection_type" in company_data:
            company.duke_connection_type = json.dumps(company_data["duke_connection_type"])
        
        company.duke_department = company_data.get("duke_department", company.duke_department)
        company.duke_affiliation_confidence = company_data.get("duke_affiliation_confidence", company.duke_affiliation_confidence)
        
        if "duke_affiliation_sources" in company_data:
            company.duke_affiliation_sources = json.dumps(company_data["duke_affiliation_sources"])
        
        company.total_funding = company_data.get("total_funding", company.total_funding)
        company.latest_valuation = company_data.get("latest_valuation", company.latest_valuation)
        company.latest_funding_stage = company_data.get("latest_funding_stage", company.latest_funding_stage)
        
        if "competitors" in company_data:
            company.competitors = json.dumps(company_data["competitors"])
        
        if "funding_rounds" in company_data:
            company.funding_rounds = json.dumps(company_data["funding_rounds"])
        
        company.linkedin_url = company_data.get("linkedin_url", company.linkedin_url)
        company.twitter_handle = company_data.get("twitter_handle", company.twitter_handle)
        
        if "data_sources" in integrated_data:
            company.data_sources = json.dumps(integrated_data["data_sources"])
        
        company.data_quality_score = integrated_data.get("data_quality_score", company.data_quality_score)
        company.data_freshness_score = integrated_data.get("data_freshness_score", company.data_freshness_score)
        company.last_updated = datetime.utcnow()
        company.last_scraped = datetime.utcnow()
        
        # Update Twitter data if available
        if "twitter_analysis" in integrated_data and integrated_data["twitter_analysis"]:
            twitter_analysis = integrated_data["twitter_analysis"]
            company.twitter_data = json.dumps(twitter_analysis)
            company.twitter_summary = twitter_analysis.get("summary", "")
            company.twitter_actionability = twitter_analysis.get("actionability_score", 0)
            company.twitter_last_updated = datetime.utcnow()
        
        # Update in database
        await db.commit()
        await db.refresh(company)
        
        logger.info(f"Updated company: {company.name} (ID: {company.id})")
        return company
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating company: {e}", exc_info=True)
        raise

async def process_company_founders(db: AsyncSession, company: Company, integrated_data: Dict[str, Any]):
    """
    Process company founders from integrated data.
    
    Args:
        db: Database session
        company: Company
        integrated_data: Integrated data from scrapers and processors
    """
    try:
        # Extract founders data
        founders_data = integrated_data.get("founders", [])
        
        for founder_data in founders_data:
            # Skip if no name
            if not founder_data.get("full_name"):
                continue
                
            # Normalize founder name
            founder_name = founder_data["full_name"].strip().title()
            
            # Check if founder exists
            query = select(Founder).where(Founder.full_name == founder_name)
            result = await db.execute(query)
            founder = result.scalars().first()
            
            # Create founder if not exists
            if not founder:
                founder = Founder(
                    full_name=founder_name,
                    current_position=founder_data.get("current_position"),
                    duke_affiliated=founder_data.get("duke_affiliated", False),
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                db.add(founder)
                await db.commit()
                await db.refresh(founder)
                
                logger.info(f"Created new founder: {founder.full_name} (ID: {founder.id})")
            
            # Check if company-founder relationship exists
            query = select(CompanyFounder).where(
                and_(
                    CompanyFounder.company_id == company.id,
                    CompanyFounder.founder_id == founder.id
                )
            )
            result = await db.execute(query)
            company_founder = result.scalars().first()
            
            # Create relationship if not exists
            if not company_founder:
                company_founder = CompanyFounder(
                    company_id=company.id,
                    founder_id=founder.id,
                    created_at=datetime.utcnow()
                )
                db.add(company_founder)
                await db.commit()
                
                logger.info(f"Linked company {company.name} with founder {founder.full_name}")
                
    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing company founders: {e}", exc_info=True)
        raise

async def background_refresh_company(company_name: str, db: AsyncSession):
    """
    Background task to refresh company data.
    
    Args:
        company_name: Company name
        db: Database session
    """
    logger.info(f"Starting background refresh for company: {company_name}")
    
    try:
        # Get company from database
        query = select(Company).where(Company.name == company_name)
        result = await db.execute(query)
        company = result.scalars().first()
        
        if not company:
            logger.error(f"Company not found for background refresh: {company_name}")
            return
        
        # Initialize scrapers and processors
        company_scraper = CompanyScraper()
        company_processor = CompanyProcessor()
        twitter_scraper = TwitterScraper()
        twitter_analyzer = TwitterAnalyzer()
        
        # Scrape company data
        serp_data = await company_scraper.search_company(company_name)
        
        if not serp_data or "error" in serp_data:
            logger.error(f"Error scraping company data: {serp_data.get('error', 'Unknown error')}")
            return
        
        # Process company data with NLP
        company_analysis = await company_processor.analyze_company(json.dumps(serp_data))
        
        if "error" in company_analysis:
            logger.error(f"Error analyzing company data: {company_analysis['error']}")
            return
        
        # Extract Twitter handle if available
        twitter_handle = None
        if "social_media" in company_analysis and "twitter" in company_analysis["social_media"]:
            twitter_handle = company_analysis["social_media"]["twitter"]
        
        # Scrape Twitter data if handle is available
        twitter_data = None
        twitter_analysis = None
        if twitter_handle:
            logger.info(f"Scraping Twitter data for: {twitter_handle}")
            twitter_data = await twitter_scraper.get_user_tweets(twitter_handle)
            
            if twitter_data and "tweets" in twitter_data and twitter_data["tweets"]:
                twitter_analysis = await twitter_analyzer.analyze_tweets(twitter_data)
        
        # Integrate all data
        integrated_data = await IntegrationService.process_company_data(
            company_name=company_name,
            serp_data=serp_data,
            twitter_data=twitter_data,
            company_processor_result=company_analysis,
            twitter_analysis=twitter_analysis
        )
        
        # Update company in database
        await update_company_from_integrated_data(db, company, integrated_data)
        
        # Process founders if available
        if "founders" in integrated_data and integrated_data["founders"]:
            await process_company_founders(db, company, integrated_data)
        
        # Invalidate cache
        await invalidate_cache(f"company:{company_name}")
        
        logger.info(f"Background refresh completed for company: {company_name}")
        
    except Exception as e:
        logger.error(f"Error in background refresh for company {company_name}: {e}", exc_info=True)

@router.get("/stats", response_model=StatsResponse)
@cached("company_stats", expire=300)  # Cache for 5 minutes
async def get_company_stats(db: AsyncSession = Depends(get_db)):
    """
    Get company statistics.
    
    Returns:
        StatsResponse: Company statistics
    """
    logger.info("Getting company statistics")
    
    try:
        stats = await company_endpoint.get_stats(db)
        
        # Add funding stage distribution
        funding_query = select(
            Company.latest_funding_stage,
            func.count(Company.id).label('count')
        ).group_by(Company.latest_funding_stage)
        
        funding_result = await db.execute(funding_query)
        funding_distribution = [
            {"stage": row.latest_funding_stage or "unknown", "count": row.count}
            for row in funding_result
        ]
        
        stats["funding_distribution"] = funding_distribution
        
        return StatsResponse(
            entity_type="company",
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting company statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving company statistics"
        )

@router.post("/search", response_model=SearchResponse)
async def search_companies(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search for companies.
    
    Args:
        request: Search request
        db: Database session
        
    Returns:
        SearchResponse: Search results
    """
    logger.info(f"Searching companies with query: {request.query}")
    
    try:
        # Build filters
        filters = {}
        
        # Add query filter if provided
        if request.query:
            # Search in name, description, and industry
            query = select(Company).where(
                or_(
                    Company.name.ilike(f"%{request.query}%"),
                    Company.description.ilike(f"%{request.query}%"),
                    Company.industry.ilike(f"%{request.query}%")
                )
            )
        else:
            # Use filters
            if request.duke_affiliated is not None:
                filters["duke_affiliated"] = request.duke_affiliated
                
            if request.funding_stage:
                filters["latest_funding_stage"] = request.funding_stage
                
            if request.industry:
                filters["industry"] = request.industry
        
        # Get companies by filter
        companies, total_count = await company_endpoint.get_entities_by_filter(
            db=db,
            filters=filters,
            page=request.page,
            page_size=request.page_size
        )
        
        # Prepare results
        results = []
        for company in companies:
            results.append(SearchResult(
                id=company.id,
                name=company.name,
                description=company.description,
                duke_affiliated=company.duke_affiliated,
                entity_type="company",
                relevance_score=company.data_quality_score * 100 if company.data_quality_score else 50
            ))
        
        # Return search response
        return SearchResponse(
            query=request.query,
            results=results,
            total_count=total_count,
            page=request.page,
            page_size=request.page_size,
            page_count=(total_count + request.page_size - 1) // request.page_size
        )
        
    except Exception as e:
        logger.error(f"Error searching companies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching companies"
        )
