# api/founder.py
import logging
import json
import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from backend.scrapers.founder_scraper import FounderScraper
from backend.nlp.founder_processor import FounderProcessor
from backend.nlp.twitter_analyzer import TwitterAnalyzer
from backend.scrapers.twitter_scraper import TwitterScraper
from backend.nlp.services.integration import IntegrationService
from db.database.db import get_db
from db.database.models import Founder, Company, CompanyFounder, SERPUsage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from backend.config.logs import LogManager
from backend.config.cache import cached, invalidate_founder_cache, CacheManager
from db.schemas.schemas import FounderDetailResponse, TwitterSummary, SearchRequest, SearchResponse, SearchResult, StatsResponse, FounderListResponse, FounderSearchResponse
from backend.config.config import settings
from fastapi import status
from backend.api.base_endpoint import BaseEndpoint

# Set up logging
LogManager.setup_logging()
logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize base endpoint
founder_endpoint = BaseEndpoint(
    model_class=Founder,
    response_class=FounderDetailResponse,
    entity_type="founder",
    cache_prefix="founder",
    cache_expire=settings.cache.FOUNDER_TTL
)

async def track_serp_usage(db: AsyncSession, query_count: int, entity_name: str, entity_type: str = "founder"):
    """Track SERP API usage for monitoring and quota management."""
    try:
        usage = SERPUsage(
            timestamp=datetime.utcnow(),
            query_count=query_count,
            entity_name=entity_name,
            entity_type=entity_type,
            endpoint="founder_api"
        )
        db.add(usage)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to track SERP usage: {e}")

@router.get("/{founder_name}", response_model=FounderDetailResponse)
async def get_founder(
    founder_name: str,
    refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a founder.
    
    If the founder exists in the database, returns the stored data.
    If not, triggers a SERP search and NLP analysis to gather information.
    
    Args:
        founder_name: Name of the founder to look up
        refresh: Whether to force a refresh of the data
        background_tasks: FastAPI background tasks
        db: Database session
    """
    logger.info(f"Founder API request for: {founder_name}")
    
    # Normalize founder name
    founder_name = founder_name.strip().title()
    
    # Get founder from database
    founder = await founder_endpoint.get_entity_from_db(db, founder_name)
    
    # Check if we should refresh the data
    needs_refresh = refresh or (
        founder and 
        not await founder_endpoint.check_data_freshness(founder, max_age_hours=24)
    )
    
    # If founder exists and no refresh needed, return it
    if founder and not needs_refresh:
        logger.info(f"Returning cached founder data for: {founder_name}")
        return founder_endpoint.prepare_response(founder)
    
    # If founder exists and refresh requested, schedule background refresh
    if founder and needs_refresh and background_tasks:
        logger.info(f"Scheduling background refresh for founder: {founder_name}")
        background_tasks.add_task(background_refresh_founder, founder_name, db)
        return founder_endpoint.prepare_response(founder, is_refreshing=True)
    
    # If founder doesn't exist or we need to refresh without background tasks,
    # fetch data synchronously
    logger.info(f"Fetching founder data for: {founder_name}")
    
    try:
        # Check SERP API quota before proceeding
        await founder_endpoint.track_serp_usage(db, 1, founder_name)
        
        # Initialize scrapers and processors
        founder_scraper = FounderScraper()
        founder_processor = FounderProcessor()
        twitter_scraper = TwitterScraper()
        twitter_analyzer = TwitterAnalyzer()
        
        # Scrape founder data
        serp_data = await founder_scraper.search_founder(founder_name)
        
        if not serp_data or "error" in serp_data:
            logger.error(f"Error scraping founder data: {serp_data.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find information for founder: {founder_name}"
            )
        
        # Process founder data with NLP
        founder_analysis = await founder_processor.analyze_founder(json.dumps(serp_data))
        
        if "error" in founder_analysis:
            logger.error(f"Error analyzing founder data: {founder_analysis['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error analyzing founder data: {founder_analysis['error']}"
            )
        
        # Extract Twitter handle if available
        twitter_handle = None
        if "social_media" in founder_analysis and "twitter" in founder_analysis["social_media"]:
            twitter_handle = founder_analysis["social_media"]["twitter"]
        
        # Scrape Twitter data if handle is available
        twitter_data = None
        twitter_analysis = None
        if twitter_handle:
            logger.info(f"Scraping Twitter data for: {twitter_handle}")
            twitter_data = await twitter_scraper.get_user_tweets(twitter_handle)
            
            if twitter_data and "tweets" in twitter_data and twitter_data["tweets"]:
                twitter_analysis = await twitter_analyzer.analyze_tweets(twitter_data)
        
        # Integrate all data
        integrated_data = await IntegrationService.process_founder_data(
            founder_name=founder_name,
            serp_data=serp_data,
            twitter_data=twitter_data,
            founder_processor_result=founder_analysis,
            twitter_analysis=twitter_analysis
        )
        
        # Create or update founder in database
        if founder:
            founder = await update_founder_from_integrated_data(db, founder, integrated_data)
        else:
            founder = await create_founder_from_integrated_data(db, integrated_data)
        
        # Process companies if available
        if "companies" in integrated_data and integrated_data["companies"]:
            await process_founder_companies(db, founder, integrated_data)
        
        # Invalidate cache
        await invalidate_founder_cache(founder_name)
        
        return founder_endpoint.prepare_response(founder)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing founder data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing founder data: {str(e)}"
        )

async def create_founder_from_integrated_data(db: AsyncSession, integrated_data: Dict[str, Any]) -> Founder:
    """
    Create a new founder from integrated data.
    
    Args:
        db: Database session
        integrated_data: Integrated data from scrapers and processors
        
    Returns:
        Founder: Created founder
    """
    try:
        # Extract founder data
        founder_data = integrated_data.get("founder_profile", {})
        
        # Create founder object
        founder = Founder(
            full_name=founder_data.get("full_name", "Unknown"),
            current_position=founder_data.get("current_position"),
            bio=founder_data.get("bio"),
            education=json.dumps(founder_data.get("education", [])),
            work_experience=json.dumps(founder_data.get("work_experience", [])),
            location=founder_data.get("location"),
            duke_affiliated=founder_data.get("duke_affiliated", False),
            duke_connection_type=json.dumps(founder_data.get("duke_connection_type", [])),
            duke_department=founder_data.get("duke_department"),
            duke_affiliation_confidence=founder_data.get("duke_affiliation_confidence", 0.0),
            duke_affiliation_sources=json.dumps(founder_data.get("duke_affiliation_sources", [])),
            linkedin_url=founder_data.get("linkedin_url"),
            twitter_handle=founder_data.get("twitter_handle"),
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
            founder.twitter_data = json.dumps(twitter_analysis)
            founder.twitter_summary = twitter_analysis.get("summary", "")
            founder.twitter_actionability = twitter_analysis.get("actionability_score", 0)
            founder.twitter_last_updated = datetime.utcnow()
        
        # Add to database
        db.add(founder)
        await db.commit()
        await db.refresh(founder)
        
        logger.info(f"Created new founder: {founder.full_name} (ID: {founder.id})")
        return founder
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating founder: {e}", exc_info=True)
        raise

async def update_founder_from_integrated_data(db: AsyncSession, founder: Founder, integrated_data: Dict[str, Any]) -> Founder:
    """
    Update an existing founder from integrated data.
    
    Args:
        db: Database session
        founder: Existing founder
        integrated_data: Integrated data from scrapers and processors
        
    Returns:
        Founder: Updated founder
    """
    try:
        # Extract founder data
        founder_data = integrated_data.get("founder_profile", {})
        
        # Update founder fields
        founder.current_position = founder_data.get("current_position", founder.current_position)
        founder.bio = founder_data.get("bio", founder.bio)
        
        if "education" in founder_data:
            founder.education = json.dumps(founder_data["education"])
        
        if "work_experience" in founder_data:
            founder.work_experience = json.dumps(founder_data["work_experience"])
        
        founder.location = founder_data.get("location", founder.location)
        founder.duke_affiliated = founder_data.get("duke_affiliated", founder.duke_affiliated)
        
        if "duke_connection_type" in founder_data:
            founder.duke_connection_type = json.dumps(founder_data["duke_connection_type"])
        
        founder.duke_department = founder_data.get("duke_department", founder.duke_department)
        founder.duke_affiliation_confidence = founder_data.get("duke_affiliation_confidence", founder.duke_affiliation_confidence)
        
        if "duke_affiliation_sources" in founder_data:
            founder.duke_affiliation_sources = json.dumps(founder_data["duke_affiliation_sources"])
        
        founder.linkedin_url = founder_data.get("linkedin_url", founder.linkedin_url)
        founder.twitter_handle = founder_data.get("twitter_handle", founder.twitter_handle)
        
        if "data_sources" in integrated_data:
            founder.data_sources = json.dumps(integrated_data["data_sources"])
        
        founder.data_quality_score = integrated_data.get("data_quality_score", founder.data_quality_score)
        founder.data_freshness_score = integrated_data.get("data_freshness_score", founder.data_freshness_score)
        founder.last_updated = datetime.utcnow()
        founder.last_scraped = datetime.utcnow()
        
        # Update Twitter data if available
        if "twitter_analysis" in integrated_data and integrated_data["twitter_analysis"]:
            twitter_analysis = integrated_data["twitter_analysis"]
            founder.twitter_data = json.dumps(twitter_analysis)
            founder.twitter_summary = twitter_analysis.get("summary", "")
            founder.twitter_actionability = twitter_analysis.get("actionability_score", 0)
            founder.twitter_last_updated = datetime.utcnow()
        
        # Update in database
        await db.commit()
        await db.refresh(founder)
        
        logger.info(f"Updated founder: {founder.full_name} (ID: {founder.id})")
        return founder
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating founder: {e}", exc_info=True)
        raise

async def process_founder_companies(db: AsyncSession, founder: Founder, integrated_data: Dict[str, Any]):
    """
    Process companies associated with a founder.
    
    Args:
        db: Database session
        founder: Founder
        integrated_data: Integrated data from scrapers and processors
    """
    try:
        # Extract companies data
        companies_data = integrated_data.get("companies", [])
        
        for company_data in companies_data:
            # Skip if no name
            if not company_data.get("name"):
                continue
                
            # Normalize company name
            company_name = company_data["name"].strip().title()
            
            # Check if company exists
            query = select(Company).where(Company.name == company_name)
            result = await db.execute(query)
            company = result.scalars().first()
            
            # Create company if not exists
            if not company:
                company = Company(
                    name=company_name,
                    description=company_data.get("description"),
                    industry=company_data.get("industry"),
                    duke_affiliated=company_data.get("duke_affiliated", False),
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                db.add(company)
                await db.commit()
                await db.refresh(company)
                
                logger.info(f"Created new company: {company.name} (ID: {company.id})")
            
            # Check if founder-company relationship exists
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
                
                logger.info(f"Linked founder {founder.full_name} with company {company.name}")
                
    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing founder companies: {e}", exc_info=True)
        raise

async def background_refresh_founder(founder_name: str, db: AsyncSession):
    """
    Background task to refresh founder data.
    
    Args:
        founder_name: Founder name
        db: Database session
    """
    logger.info(f"Starting background refresh for founder: {founder_name}")
    
    try:
        # Get founder from database
        query = select(Founder).where(Founder.full_name == founder_name)
        result = await db.execute(query)
        founder = result.scalars().first()
        
        if not founder:
            logger.error(f"Founder not found for background refresh: {founder_name}")
            return
        
        # Initialize scrapers and processors
        founder_scraper = FounderScraper()
        founder_processor = FounderProcessor()
        twitter_scraper = TwitterScraper()
        twitter_analyzer = TwitterAnalyzer()
        
        # Scrape founder data
        serp_data = await founder_scraper.search_founder(founder_name)
        
        if not serp_data or "error" in serp_data:
            logger.error(f"Error scraping founder data: {serp_data.get('error', 'Unknown error')}")
            return
        
        # Process founder data with NLP
        founder_analysis = await founder_processor.analyze_founder(json.dumps(serp_data))
        
        if "error" in founder_analysis:
            logger.error(f"Error analyzing founder data: {founder_analysis['error']}")
            return
        
        # Extract Twitter handle if available
        twitter_handle = None
        if "social_media" in founder_analysis and "twitter" in founder_analysis["social_media"]:
            twitter_handle = founder_analysis["social_media"]["twitter"]
        
        # Scrape Twitter data if handle is available
        twitter_data = None
        twitter_analysis = None
        if twitter_handle:
            logger.info(f"Scraping Twitter data for: {twitter_handle}")
            twitter_data = await twitter_scraper.get_user_tweets(twitter_handle)
            
            if twitter_data and "tweets" in twitter_data and twitter_data["tweets"]:
                twitter_analysis = await twitter_analyzer.analyze_tweets(twitter_data)
        
        # Integrate all data
        integrated_data = await IntegrationService.process_founder_data(
            founder_name=founder_name,
            serp_data=serp_data,
            twitter_data=twitter_data,
            founder_processor_result=founder_analysis,
            twitter_analysis=twitter_analysis
        )
        
        # Update founder in database
        await update_founder_from_integrated_data(db, founder, integrated_data)
        
        # Process companies if available
        if "companies" in integrated_data and integrated_data["companies"]:
            await process_founder_companies(db, founder, integrated_data)
        
        # Invalidate cache
        await invalidate_founder_cache(founder_name)
        
        logger.info(f"Background refresh completed for founder: {founder_name}")
        
    except Exception as e:
        logger.error(f"Error in background refresh for founder {founder_name}: {e}", exc_info=True)

@router.get("/", response_model=FounderListResponse)
async def list_founders(
    duke_affiliated: Optional[bool] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List founders with optional filtering.
    
    Args:
        duke_affiliated: Filter by Duke affiliation
        limit: Maximum number of results
        offset: Offset for pagination
        db: Database session
    """
    try:
        # Build query
        query = select(Founder)
        
        # Apply filters
        if duke_affiliated is not None:
            query = query.where(Founder.duke_affiliated == duke_affiliated)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        founders = result.scalars().all()
        
        # Format results
        items = []
        for founder in founders:
            items.append(founder_endpoint.prepare_response(founder))
        
        return FounderListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing founders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing founders"
        )

@router.post("/search", response_model=SearchResponse)
async def search_founders(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search for founders.
    
    Args:
        request: Search request
        db: Database session
        
    Returns:
        SearchResponse: Search results
    """
    logger.info(f"Searching founders with query: {request.query}")
    
    try:
        # Build filters
        filters = {}
        
        # Add query filter if provided
        if request.query:
            # Search in name, bio, and current position
            query = select(Founder).where(
                or_(
                    Founder.full_name.ilike(f"%{request.query}%"),
                    Founder.bio.ilike(f"%{request.query}%"),
                    Founder.current_position.ilike(f"%{request.query}%")
                )
            )
        else:
            # Use filters
            if request.duke_affiliated is not None:
                filters["duke_affiliated"] = request.duke_affiliated
        
        # Get founders by filter
        founders, total_count = await founder_endpoint.get_entities_by_filter(
            db=db,
            filters=filters,
            page=request.page,
            page_size=request.page_size
        )
        
        # Prepare results
        results = []
        for founder in founders:
            results.append(SearchResult(
                id=founder.id,
                name=founder.full_name,
                description=founder.bio,
                duke_affiliated=founder.duke_affiliated,
                entity_type="founder",
                relevance_score=founder.data_quality_score * 100 if founder.data_quality_score else 50
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
        logger.error(f"Error searching founders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching founders"
        )

@router.get("/stats", response_model=StatsResponse)
@cached("founder_stats", expire=300)  # Cache for 5 minutes
async def get_founder_stats(db: AsyncSession = Depends(get_db)):
    """
    Get founder statistics.
    
    Returns:
        StatsResponse: Founder statistics
    """
    logger.info("Getting founder statistics")
    
    try:
        stats = await founder_endpoint.get_stats(db)
        
        # Add duke affiliation distribution
        duke_query = select(
            Founder.duke_affiliated,
            func.count(Founder.id).label('count')
        ).group_by(Founder.duke_affiliated)
        
        duke_result = await db.execute(duke_query)
        duke_distribution = [
            {"affiliated": row.duke_affiliated, "count": row.count}
            for row in duke_result
        ]
        
        stats["duke_distribution"] = duke_distribution
        
        return StatsResponse(
            entity_type="founder",
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting founder statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving founder statistics"
        )
