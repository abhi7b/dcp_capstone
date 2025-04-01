"""
API routes for person-related operations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..db import schemas, crud, session
from ..services.scraper import SERPScraper
from ..services.person_processor import PersonProcessor
from ..utils.logger import api_logger
from ..routes.auth import verify_api_key

router = APIRouter(
    prefix="/api/person",
    tags=["People"],
    dependencies=[Depends(verify_api_key)]
)

# Initialize services
serp_scraper = SERPScraper()
person_processor = PersonProcessor()

@router.get("/search/", response_model=schemas.PersonResponse)
async def search_person(
    name: str = Query(..., description="Name of the person to search for"),
    db: AsyncSession = Depends(session.get_db)
):
    """
    Search for a person by name. If not found in the database,
    initiate scraping to find and add them. This endpoint handles
    both retrieval and creation of person data.
    """
    api_logger.info(f"Received search request for person: {name}")
    db_person = await crud.get_person_by_name(db, name=name)
    
    if db_person:
        api_logger.info(f"Person '{name}' found in database (ID: {db_person.id}).")
        response_data = db_person.__dict__
        response_data["last_updated"] = db_person.updated_at.isoformat() if db_person.updated_at else db_person.created_at.isoformat()
        return schemas.PersonResponse(**response_data)
    
    api_logger.info(f"Person '{name}' not found in DB. Initiating scraping.")
    
    try:
        # Query SERP API for person details
        serp_results = serp_scraper.search_person(name)
        
        if not serp_results.get("organic_results"):
            api_logger.warning(f"No search results found for person: {name}")
            raise HTTPException(status_code=404, detail="No information found for this person")
        
        # Process person data
        person_data = await person_processor.process_founder_data(serp_results)
        
        if "error" in person_data:
            raise HTTPException(status_code=404, detail=person_data["error"])
        
        # Create structured person object for database
        person_create = schemas.PersonCreate(
            name=person_data["name"],
            duke_affiliation_status=person_data["duke_affiliation_status"],
            relevance_score=int(person_data.get("relevance_score", 0)),
            education=person_data.get("education", []),
            current_company=person_data.get("current_company"),
            previous_companies=person_data.get("previous_companies", []),
            twitter_handle=person_data.get("twitter_handle"),
            linkedin_handle=person_data.get("linkedin_handle"),
            twitter_summary=str(person_data.get("twitter_summary", "")),
            source_links=person_data.get("source_links", [])
        )
        
        # Save to database
        created_person = await crud.create_person(db=db, person=person_create)
        api_logger.info(f"Successfully scraped and created person '{name}' (ID: {created_person.id}).")
        
        response_data = created_person.__dict__
        response_data["last_updated"] = created_person.created_at.isoformat()
        return schemas.PersonResponse(**response_data)
        
    except Exception as e:
        api_logger.error(f"Error during scraping/creation for person {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape or create person '{name}'.")

@router.delete("/{person_id}", status_code=200, response_model=schemas.Message)
async def delete_person(
    person_id: int,
    db: AsyncSession = Depends(session.get_db)
):
    """
    Delete a person by ID.
    This is useful for removing incorrect entries or obsolete data.
    """
    api_logger.info(f"Received request to delete person ID: {person_id}")
    deleted = await crud.delete_person(db=db, person_id=person_id)
    if not deleted:
        api_logger.warning(f"Deletion failed: Person ID {person_id} not found.")
        raise HTTPException(status_code=404, detail="Person not found")
        
    api_logger.info(f"Successfully deleted person ID: {person_id}")
    return {"message": f"Person {person_id} deleted successfully"} 