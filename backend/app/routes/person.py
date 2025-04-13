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
    prefix="/api/person",
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
    Search for person information using a multi-layered approach.
    
    Args:
        name: Name of person to search for
        force_refresh: If True, bypass cache and fetch fresh data
        db: Database session
        
    Returns:
        PersonResponse containing person information
        
    Raises:
        HTTPException(404): If person not found
        HTTPException(500): For processing errors
    """
    try:
        # Layer 1: Check Redis cache (unless force_refresh is True)
        if not force_refresh:
            cached_data = await redis_service.get(f"person:{name}")
            if cached_data:
                logger.info(f"Cache hit for person: {name}")
                return schemas.PersonResponse(**cached_data)
            
            # Layer 2: Check database
            result = await db.execute(
                select(Person).where(Person.name.ilike(f"%{name}%"))
            )
            person = result.scalars().first()
            
            if person:
                # Get associated companies
                companies_result = await db.execute(
                    select(Company)
                    .join(company_person_association)
                    .where(company_person_association.c.person_id == person.id)
                )
                companies = companies_result.scalars().all()
                
                # Prepare person data with companies
                person_data = person.dict()
                person_data['companies'] = [{"name": c.name} for c in companies]
                
                # Cache the database result
                await redis_service.set(
                    f"person:{name}",
                    person_data,
                    expire=3600  # 1 hour cache
                )
                return schemas.PersonResponse(**person_data)
        
        # Layer 3: Scrape and process new data
        scraper = SERPScraper()
        processor = PersonProcessor()
        nitter_scraper = NitterScraper()
        nitter_nlp = NitterNLP()
        founder_scorer = FounderScorer()
        storage = StorageService()
        
        # Get SERP results
        serp_results = await scraper.search_person(name)
        if not serp_results or "organic_results" not in serp_results:
            raise HTTPException(status_code=404, detail=f"No information found for person: {name}")
            
        # Save raw SERP data
        storage.save_raw_data(serp_results, "serp_person", name)
        
        # Process person data
        person_data = await processor.process_person(name, serp_results)
        if not person_data:
            raise HTTPException(status_code=404, detail=f"Could not process person data for: {name}")
            
        # Save intermediate data
        storage.save_processed_data(person_data, "person", f"{name}_intermediate")
        
        # Get and process Twitter data if handle exists
        twitter_urgency_score = None
        if person_data.get("twitter_handle"):
            nitter_results = await nitter_scraper.get_raw_tweets(person_data["twitter_handle"])
            if nitter_results and not nitter_results.get("twitter_unavailable", True) and nitter_results.get("raw_tweets"):
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
                person_data["twitter_summary"] = summary
        
        # Calculate final score
        person_data["relevance_score"] = founder_scorer.calculate_relevance_score(
            person_data=person_data,
            twitter_urgency_score=twitter_urgency_score
        )
        
        # Save final data
        storage.save_data(person_data, "person", name, settings.JSON_INPUTS_DIR)
        
        # Layer 4: Store in database and cache
        person = await person_crud.create_person(db=db, person=person_data)
        if not person:
            raise HTTPException(status_code=500, detail="Failed to store person data")
            
        # Get associated companies
        companies_result = await db.execute(
            select(Company)
            .join(company_person_association)
            .where(company_person_association.c.person_id == person.id)
        )
        companies = companies_result.scalars().all()
        
        # Prepare person data with companies
        person_data = person.dict()
        person_data['companies'] = [{"name": c.name} for c in companies]
            
        # Cache the result
        await redis_service.set(
            f"person:{name}",
            person_data,
            expire=3600  # 1 hour cache
        )
        
        return schemas.PersonResponse(**person_data)
        
    except Exception as e:
        logger.error(f"Error processing person {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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