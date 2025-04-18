"""
Person Routes Module

This module handles person-related API endpoints for searching, creating,
updating, and managing individual profiles.

Key Features:
- Person search and retrieval
- Profile management
- Duke affiliation verification
- Scoring and analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, join
from typing import List, Optional
import json
import asyncio

from ..db import schemas, crud, session, person_crud
from ..db.models import Person, Company, company_person_association
from ..services.scraper import SERPScraper
from ..services.nitter import NitterScraper
from ..services.person_processor import PersonProcessor
from ..services.founder_scorer import FounderScorer
from ..services.nitter_nlp import NitterNLP
from ..utils.storage import StorageService
from ..utils.logger import api_logger as logger
from ..utils.config import settings
from .auth import verify_api_key
from ..services.redis import redis_service

router = APIRouter(
    tags=["People"],
    dependencies=[Depends(verify_api_key)]
)

@router.get("/search/{name}", response_model=schemas.PersonResponse)
async def search_person(
    name: str,
    force_refresh: bool = Query(False, description="Force refresh data from sources"),
    db: AsyncSession = Depends(session.get_db)
):
    """
    Search for person information using a three-layered approach.
    
    Args:
        name: Person name to search for
        force_refresh: If True, bypass cache and fetch fresh data
        db: Database session
        
    Returns:
        PersonResponse containing person information
        
    Raises:
        HTTPException(404): If person not found in search results
        HTTPException(500): For processing errors
    """
    cache_key = f"person:{name.lower()}"
    try:
        # Layer 1: Check Redis cache (unless force_refresh is True)
        if not force_refresh:
            cached_data = await redis_service.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for person: {name}")
                return schemas.PersonResponse(**cached_data)
            
            # Layer 2: Check database
            person = await person_crud.get_person_by_name(db, name)
            if person:
                logger.info(f"Database hit for person: {name}")
                # Get associated companies
                result = await db.execute(
                    select(Company)
                    .join(company_person_association)
                    .where(company_person_association.c.person_id == person.id)
                )
                companies = result.scalars().all()
                
                # Create response dictionary
                person_dict = {
                    "id": person.id,
                    "name": person.name,
                    "title": person.title,
                    "current_company": person.current_company,
                    "education": person.education,
                    "previous_companies": person.previous_companies,
                    "twitter_handle": person.twitter_handle,
                    "linkedin_handle": person.linkedin_handle,
                    "duke_affiliation_status": person.duke_affiliation_status,
                    "relevance_score": person.relevance_score,
                    "twitter_summary": person.twitter_summary,
                    "source_links": person.source_links,
                    "created_at": person.created_at.isoformat() if person.created_at else None,
                    "updated_at": person.updated_at.isoformat() if person.updated_at else None,
                    "companies": [{"name": c.name} for c in companies]
                }
                
                # Cache the database result
                await redis_service.set(cache_key, person_dict, expire=3600)
                return schemas.PersonResponse(**person_dict)
        
        # Layer 3: Scrape and process new data
        logger.info(f"Performing full scrape and process for person: {name}")
        scraper = SERPScraper()
        processor = PersonProcessor()
        nitter_scraper = NitterScraper()
        nitter_nlp = NitterNLP()
        founder_scorer = FounderScorer()
        storage = StorageService()
        
        # Execute SERP search
        raw_serp_data = await scraper.search_founder(name)
        
        if not raw_serp_data or "organic_results" not in raw_serp_data:
            logger.warning(f"SERP search yielded no results for person: {name}")
            raise HTTPException(status_code=404, detail="Person not found in search results")
        
        # Save raw SERP data
        storage.save_raw_data(raw_serp_data, "serp_person", name)
        
        # Process with integrated NLP pipeline
        processed_data = await processor.process_person(name, raw_serp_data)
        
        if "error" in processed_data:
            logger.error(f"Processing failed for {name}: {processed_data['error']}")
            raise HTTPException(status_code=500, detail=f"Processing error: {processed_data['error']}")
            
        # Create or update person in database
        person_values = {
            "name": name,
            "title": processed_data.get("title"),
            "current_company": processed_data.get("current_company"),
            "education": processed_data.get("education", []),
            "previous_companies": processed_data.get("previous_companies", []),
            "twitter_handle": processed_data.get("twitter_handle"),
            "linkedin_handle": processed_data.get("linkedin_handle"),
            "duke_affiliation_status": processed_data.get("duke_affiliation_status", "no"),
            "relevance_score": processed_data.get("relevance_score", 0),
            "twitter_summary": processed_data.get("twitter_summary"),
            "source_links": processed_data.get("source_links", [])
        }
        
        # Check if person exists
        existing_person = await person_crud.get_person_by_name(db, name)
        if existing_person:
            # Convert dictionary to PersonUpdate schema and let validators handle conversion
            person_update = schemas.PersonUpdate(**person_values)
            person = await person_crud.update_person(db, existing_person.id, person_update)
            if not person:
                logger.error(f"Failed to update person in database: {name}")
                raise HTTPException(status_code=500, detail="Failed to update person data in database")
        else:
            # Convert dictionary to PersonCreate schema and let validators handle conversion
            person_create = schemas.PersonCreate(**person_values)
            person = await person_crud.create_person(db, person_create)
            if not person:
                logger.error(f"Failed to create person in database: {name}")
                raise HTTPException(status_code=500, detail="Failed to create person data in database")
            
        # Get associated companies for response
        result = await db.execute(
            select(Company)
            .join(company_person_association)
            .where(company_person_association.c.person_id == person.id)
        )
        companies = result.scalars().all()
        
        # Prepare response data
        person_dict = {
            "id": person.id,
            "name": person.name,
            "title": person.title,
            "current_company": person.current_company,
            "education": person.education,
            "previous_companies": person.previous_companies,
            "twitter_handle": person.twitter_handle,
            "linkedin_handle": person.linkedin_handle,
            "duke_affiliation_status": person.duke_affiliation_status,
            "relevance_score": person.relevance_score,
            "twitter_summary": person.twitter_summary,
            "source_links": person.source_links,
            "created_at": person.created_at.isoformat() if person.created_at else None,
            "updated_at": person.updated_at.isoformat() if person.updated_at else None,
            "companies": [{"name": c.name} for c in companies]
        }
        
        # Cache the final result
        await redis_service.set(cache_key, person_dict, expire=3600)
        logger.info(f"Successfully processed and cached person: {name}")
        return schemas.PersonResponse(**person_dict)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error searching person {name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/", response_model=List[schemas.PersonResponse])
async def list_people(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    duke_affiliated: Optional[bool] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    db: AsyncSession = Depends(session.get_db)
):
    """
    List people with optional filtering.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        duke_affiliated: Filter by Duke affiliation status
        min_score: Filter by minimum relevance score
        db: Database session
        
    Returns:
        List of PersonResponse objects
        
    Raises:
        HTTPException(500): For database errors
    """
    try:
        query = select(Person)
        
        if duke_affiliated is not None:
            query = query.where(Person.duke_affiliation_status == "confirmed" if duke_affiliated else Person.duke_affiliation_status != "confirmed")
            
        if min_score is not None:
            query = query.where(Person.relevance_score >= min_score)
            
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        people = result.scalars().all()
        
        # Get associated companies for each person
        response_list = []
        for person in people:
            companies_result = await db.execute(
                select(Company)
                .join(company_person_association)
                .where(company_person_association.c.person_id == person.id)
            )
            companies = companies_result.scalars().all()
            
            person_data = person.dict()
            person_data['companies'] = [{"name": c.name} for c in companies]
            response_list.append(schemas.PersonResponse(**person_data))
            
        return response_list
        
    except Exception as e:
        logger.error(f"Error listing people: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{name}", response_model=schemas.PersonResponse)
async def update_person_manual(
    name: str,
    person_update: schemas.PersonUpdate,
    db: AsyncSession = Depends(session.get_db)
):
    """
    Update an existing person entry manually.
    Requires the person name and updated data.
    """
    try:
        # Get person by name
        result = await db.execute(select(Person).where(Person.name == name))
        person = result.scalar_one_or_none()
        if not person:
            raise HTTPException(status_code=404, detail=f"Person {name} not found")
            
        # Use CRUD function to update
        update_data = person_update.dict(exclude_unset=True)
        updated_person = await person_crud.update_person(db, person.id, update_data)
        
        if not updated_person:
            raise HTTPException(status_code=500, detail="Failed to update person in database")
            
        # Clear cache
        await redis_service.delete(f"person:{name}")
        
        # Get associated companies
        companies_result = await db.execute(
            select(Company)
            .join(company_person_association)
            .where(company_person_association.c.person_id == updated_person.id)
        )
        companies = companies_result.scalars().all()
        
        # Prepare response
        person_data = updated_person.dict()
        person_data['companies'] = [{"name": c.name} for c in companies]
        
        return schemas.PersonResponse(**person_data)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error updating person {name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error during update: {str(e)}")

@router.delete("/{name}", status_code=200)
async def delete_person(
    name: str,
    db: AsyncSession = Depends(session.get_db)
):
    """
    Delete a person by name.
    
    Args:
        name: Name of person to delete
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException(404): If person not found
        HTTPException(500): For database errors
    """
    try:
        # Get person by name
        result = await db.execute(select(Person).where(Person.name == name))
        person = result.scalar_one_or_none()
        if not person:
            raise HTTPException(status_code=404, detail=f"Person {name} not found")
            
        # Delete from database
        await db.delete(person)
        await db.commit()
        
        # Clear cache
        await redis_service.delete(f"person:{name}")
        
        return {"message": "Person deleted successfully"}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error deleting person {name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error during deletion: {str(e)}") 