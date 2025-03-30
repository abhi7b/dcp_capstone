"""
API routes for person-related operations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from backend.app.db import schemas, crud, session
from backend.app.services import scraper # Assuming a scraper service exists for persons
from backend.app.utils.logger import api_logger
from backend.app.routes.auth import verify_api_key # Assuming auth mechanism

router = APIRouter(
    prefix="/api/person",
    tags=["People"],
    dependencies=[Depends(verify_api_key)] # Apply auth to all person routes
)

@router.post("/", response_model=schemas.PersonResponse, status_code=201)
async def create_new_person(
    person_in: schemas.PersonCreate,
    db: AsyncSession = Depends(session.get_db)
):
    """
    Create a new person record directly.
    Note: This does not automatically associate the person with companies.
    """
    api_logger.info(f"Received request to create person: {person_in.name}")
    # Optional: Check if person already exists by name or other unique identifier
    # db_person = await crud.get_person_by_name(db, name=person_in.name)
    # if db_person:
    #     raise HTTPException(status_code=400, detail="Person with this name already exists")
        
    try:
        created_person = await crud.create_person(db=db, person=person_in)
        api_logger.info(f"Successfully created person ID: {created_person.id}")
        # Manually construct response to include 'last_updated' if needed, Pydantic v2 handles this better
        response_data = created_person.__dict__
        response_data["last_updated"] = created_person.updated_at.isoformat() if created_person.updated_at else created_person.created_at.isoformat()
        return schemas.PersonResponse(**response_data)
    except Exception as e:
        api_logger.error(f"Error creating person {person_in.name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while creating person.")


@router.get("/search/", response_model=schemas.PersonResponse)
async def search_person(
    name: str = Query(..., description="Name of the person to search for"),
    db: AsyncSession = Depends(session.get_db)
):
    """
    Search for a person by name. If not found in the database,
    initiate scraping to find and add them.
    """
    api_logger.info(f"Received search request for person: {name}")
    db_person = await crud.get_person_by_name(db, name=name)
    
    if db_person:
        api_logger.info(f"Person '{name}' found in database (ID: {db_person.id}).")
        response_data = db_person.__dict__
        response_data["last_updated"] = db_person.updated_at.isoformat() if db_person.updated_at else db_person.created_at.isoformat()
        return schemas.PersonResponse(**response_data)
        
    api_logger.info(f"Person '{name}' not found in DB. Initiating scraping.")
    # --- Placeholder for scraping logic ---
    # This is where you would integrate your scraping service for people
    # try:
    #     scraped_data = await scraper.scrape_person_info(name) # Fictional function
    #     if not scraped_data:
    #         raise HTTPException(status_code=404, detail=f"Person '{name}' not found via scraping.")
            
    #     # Convert scraped_data into schemas.PersonCreate format
    #     person_to_create = schemas.PersonCreate(**scraped_data) # Needs careful mapping
        
    #     # Create the person using the CRUD function
    #     created_person = await crud.create_person(db=db, person=person_to_create)
    #     api_logger.info(f"Successfully scraped and created person '{name}' (ID: {created_person.id}).")
    #     response_data = created_person.__dict__
    #     response_data["last_updated"] = created_person.created_at.isoformat()
    #     return schemas.PersonResponse(**response_data)
        
    # except Exception as e:
    #     api_logger.error(f"Error during scraping/creation for person {name}: {str(e)}")
    #     raise HTTPException(status_code=500, detail=f"Failed to scrape or create person '{name}'.")
    # --- End Placeholder ---
    
    # If scraping is not implemented or fails without throwing 500
    raise HTTPException(status_code=404, detail=f"Person '{name}' not found in database and scraping is not implemented or failed.")


@router.get("/{person_id}", response_model=schemas.PersonResponse)
async def get_person_by_id(
    person_id: int,
    db: AsyncSession = Depends(session.get_db)
):
    """
    Retrieve a specific person by their ID.
    """
    api_logger.info(f"Received request for person ID: {person_id}")
    db_person = await crud.get_person(db, person_id=person_id)
    if db_person is None:
        api_logger.warning(f"Person ID {person_id} not found.")
        raise HTTPException(status_code=404, detail="Person not found")
    
    response_data = db_person.__dict__
    response_data["last_updated"] = db_person.updated_at.isoformat() if db_person.updated_at else db_person.created_at.isoformat()
    return schemas.PersonResponse(**response_data)


@router.get("/", response_model=List[schemas.PersonResponse])
async def get_all_people(
    skip: int = 0,
    limit: int = 100,
    duke_affiliation_status: Optional[str] = Query(None, description="Filter by Duke affiliation status"),
    db: AsyncSession = Depends(session.get_db)
):
    """
    Retrieve a list of people, with optional filtering and pagination.
    """
    api_logger.info(f"Received request for people list (skip={skip}, limit={limit}, status={duke_affiliation_status})")
    people = await crud.get_persons(db, skip=skip, limit=limit, duke_affiliation_status=duke_affiliation_status)
    
    response_list = []
    for person in people:
        person_data = person.__dict__
        person_data["last_updated"] = person.updated_at.isoformat() if person.updated_at else person.created_at.isoformat()
        response_list.append(schemas.PersonResponse(**person_data))
        
    return response_list

@router.put("/{person_id}", response_model=schemas.PersonResponse)
async def update_existing_person(
    person_id: int,
    person_in: schemas.PersonUpdate,
    db: AsyncSession = Depends(session.get_db)
):
    """
    Update an existing person's details.
    """
    api_logger.info(f"Received request to update person ID: {person_id}")
    updated_person = await crud.update_person(db=db, person_id=person_id, person_data=person_in)
    if updated_person is None:
        api_logger.warning(f"Update failed: Person ID {person_id} not found.")
        raise HTTPException(status_code=404, detail="Person not found")
        
    api_logger.info(f"Successfully updated person ID: {person_id}")
    response_data = updated_person.__dict__
    response_data["last_updated"] = updated_person.updated_at.isoformat() # Should always have updated_at after update
    return schemas.PersonResponse(**response_data)


@router.delete("/{person_id}", status_code=204)
async def delete_existing_person(
    person_id: int,
    db: AsyncSession = Depends(session.get_db)
):
    """
    Delete a person by ID.
    Note: This typically does not automatically remove their associations from companies.
    """
    api_logger.info(f"Received request to delete person ID: {person_id}")
    deleted = await crud.delete_person(db=db, person_id=person_id)
    if not deleted:
        api_logger.warning(f"Deletion failed: Person ID {person_id} not found.")
        raise HTTPException(status_code=404, detail="Person not found")
        
    api_logger.info(f"Successfully deleted person ID: {person_id}")
    return # Return None with 204 status code 