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
from sqlalchemy import select, join
from typing import Optional, List
import logging
import json

from ..db.session import get_db
from ..db.models import Company, Person, company_person_association
from ..db.schemas import CompanyResponse, CompanyCreate, CompanyUpdate
from ..db.crud import get_company_by_name, create_company as create_company_in_db, update_company as update_company_in_db, delete_company as delete_company_from_db
from ..services.scraper import SERPScraper
from ..services.nlp_processor import NLPProcessor
from ..services.redis import redis_service
from ..utils.storage import StorageService
from ..utils.logger import api_logger as logger
from ..utils.config import settings
from .auth import verify_api_key

router = APIRouter(
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
    cache_key = f"company:{name.lower()}"
    try:
        # Layer 1: Check Redis cache (unless force_refresh is True)
        if not force_refresh:
            cached_data = await redis_service.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for company: {name}")
                return CompanyResponse(**cached_data)
            
            # Layer 2: Check database
            db_company = await get_company_by_name(db, name)
            if db_company:
                logger.info(f"Database hit for company: {name}")
                # Get associated people
                result = await db.execute(
                    select(Person)
                    .join(company_person_association)
                    .where(company_person_association.c.company_id == db_company.id)
                )
                people = result.scalars().all()
                
                company_dict = {c.name: getattr(db_company, c.name) for c in db_company.__table__.columns}
                # Reverted: Only include name and title
                company_dict['people'] = [
                    {
                        "name": p.name,
                        "title": p.title
                        # Removed: "duke_affiliation_status": p.duke_affiliation_status
                    }
                    for p in people
                ]
                
                # Cache the database result
                await redis_service.set(cache_key, company_dict, expire=3600) # 1 hour cache
                return CompanyResponse(**company_dict)
        
        # Layer 3: Scrape and process new data
        logger.info(f"Performing full scrape and process for company: {name}")
        scraper = SERPScraper()
        nlp = NLPProcessor()
        storage = StorageService()
        
        # Scrape company data
        raw_serp_data = await scraper.search_company(name)
        if not raw_serp_data or "organic_results" not in raw_serp_data:
            logger.warning(f"SERP search yielded no results for company: {name}")
            raise HTTPException(status_code=404, detail="Company not found in search results")
        
        # Save raw SERP data
        storage.save_raw_data(raw_serp_data, "serp_company", name)
        
        # Process with integrated NLP pipeline (handles company + person processing)
        processed_data = await nlp.process_company(raw_serp_data)
        
        if "error" in processed_data:
             logger.error(f"NLP processing failed for {name}: {processed_data['error']}")
             raise HTTPException(status_code=500, detail=f"Processing error: {processed_data['error']}")
             
        # Create or update company in database
        db_company = await get_company_by_name(db, name)
        if db_company:
            logger.info(f"Updating existing company in DB: {name}")
            company = await update_company_in_db(db, db_company.id, processed_data)
        else:
            logger.info(f"Creating new company in DB: {name}")
            company = await create_company_in_db(db, processed_data)
            
        if not company:
            logger.error(f"Failed to create or update company in DB: {name}")
            raise HTTPException(status_code=500, detail="Failed to save company data to database")

        # Get associated people
        result = await db.execute(
            select(Person)
            .join(company_person_association)
            .where(company_person_association.c.company_id == company.id)
        )
        people = result.scalars().all()
        
        # Prepare data for caching and response
        company_dict_for_cache = {c.name: getattr(company, c.name) for c in company.__table__.columns}
        # Reverted: Only include name and title here as well
        company_dict_for_cache['people'] = [
            {
                "name": p.name,
                "title": p.title
                # Removed: "duke_affiliation_status": p.duke_affiliation_status
            }
            for p in people
        ]
        
        # Cache the final processed result
        await redis_service.set(cache_key, company_dict_for_cache, expire=3600) # 1 hour cache
        
        logger.info(f"Successfully processed and cached company: {name}")
        return CompanyResponse(**company_dict_for_cache)
        
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions to maintain status codes
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting company {name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.delete("/{name}", status_code=200)
async def delete_company(
    name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a company by name.
    
    Args:
        name: Name of company to delete
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException(404): If company not found
        HTTPException(500): For database errors
    """
    try:
        # Get company by name
        result = await db.execute(select(Company).where(Company.name == name))
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {name} not found")

        # Delete from database using CRUD function
        deleted = await delete_company_from_db(db, company.id)
        
        if deleted:
            # Clear cache
            cache_key = f"company:{name.lower()}"
            await redis_service.delete(cache_key)
            logger.info(f"Cache cleared for deleted company: {name}")
                 
            return {"message": "Company deleted successfully"}
        
        # If delete_company_from_db returned False
        raise HTTPException(status_code=500, detail="Failed to delete company from database")
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error deleting company {name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error during deletion: {str(e)}")

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
            status_filter = "confirmed" if duke_affiliated else "no"
            query = query.where(Company.duke_affiliation_status == status_filter)
            
        if min_score is not None:
            query = query.where(Company.relevance_score >= min_score)
            
        query = query.order_by(Company.name).offset(skip).limit(limit)
        
        result = await db.execute(query)
        companies = result.scalars().all()
        
        # Convert ORM objects to response model, including associated people
        response_list = []
        for company in companies:
            # Get associated people
            people_result = await db.execute(
                select(Person)
                .join(company_person_association)
                .where(company_person_association.c.company_id == company.id)
            )
            people = people_result.scalars().all()
            
            company_dict = {c.name: getattr(company, c.name) for c in company.__table__.columns}
            # Reverted: Only include name and title here as well
            company_dict['people'] = [
                {
                    "name": p.name,
                    "title": p.title
                    # Removed: "duke_affiliation_status": p.duke_affiliation_status
                }
                for p in people
            ]
            response_list.append(CompanyResponse(**company_dict))
            
        return response_list
        
    except Exception as e:
        logger.error(f"Error listing companies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=CompanyResponse, status_code=201)
async def create_company_manual(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new company entry manually.
    Note: This endpoint bypasses the full processing pipeline.
    It expects pre-processed data conforming to CompanyCreate schema.
    """
    try:
        # Check if company exists
        existing = await get_company_by_name(db, company.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Company {company.name} already exists")
            
        # Use the CRUD function to create the company
        company_data = company.dict()
        # Convert people list to JSON string if provided
        if company_data.get('people') and isinstance(company_data['people'], list):
            company_data['people'] = json.dumps(company_data['people'])
            
        new_company = await create_company_in_db(db, company_data)
        if not new_company:
            raise HTTPException(status_code=500, detail="Failed to create company in database")
            
        # Clear cache if company was created
        cache_key = f"company:{new_company.name.lower()}"
        await redis_service.delete(cache_key)

        # Prepare response
        company_dict = {c.name: getattr(new_company, c.name) for c in new_company.__table__.columns}
        if company_dict.get('people') and isinstance(company_dict['people'], str):
             try:
                 company_dict['people'] = json.loads(company_dict['people'])
             except json.JSONDecodeError:
                 company_dict['people'] = []
        elif not company_dict.get('people'):
             company_dict['people'] = []
             
        return CompanyResponse(**company_dict)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error creating company manually: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error during manual creation: {str(e)}")

@router.put("/{name}", response_model=CompanyResponse)
async def update_company_manual(
    name: str,
    company_update: CompanyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing company entry manually.
    Requires the company name and updated data.
    """
    try:
        # Get company by name
        result = await db.execute(select(Company).where(Company.name == name))
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {name} not found")
            
        # Use CRUD function to update
        update_data = company_update.dict(exclude_unset=True) # Only include fields that were set
        # Convert people list to JSON string if provided
        if update_data.get('people') and isinstance(update_data['people'], list):
            update_data['people'] = json.dumps(update_data['people'])
            
        updated_company = await update_company_in_db(db, company.id, update_data)
        
        if not updated_company:
            raise HTTPException(status_code=500, detail="Failed to update company in database")
            
        # Clear cache
        cache_key = f"company:{updated_company.name.lower()}"
        await redis_service.delete(cache_key)

        # Prepare response
        company_dict = {c.name: getattr(updated_company, c.name) for c in updated_company.__table__.columns}
        if company_dict.get('people') and isinstance(company_dict['people'], str):
             try:
                 company_dict['people'] = json.loads(company_dict['people'])
             except json.JSONDecodeError:
                 company_dict['people'] = []
        elif not company_dict.get('people'):
             company_dict['people'] = []
             
        return CompanyResponse(**company_dict)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error updating company {name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error during update: {str(e)}") 