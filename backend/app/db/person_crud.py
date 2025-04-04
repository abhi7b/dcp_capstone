"""
Person CRUD operations.

This module contains database operations for Person entities,
used by the application's API endpoints and background tasks.
It focuses on operations for search, retrieval, and deletion of person records.
"""
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from sqlalchemy.orm import selectinload
from . import models, schemas
from typing import List, Optional, Dict, Any, Union
from ..utils.logger import db_logger
from datetime import datetime
import json
from fastapi import HTTPException

async def create_person(db: AsyncSession, person: schemas.PersonCreate) -> models.Person:
    """
    Create a new person independently.
    
    This function is used by the search API endpoint when a person
    is not found in the database and needs to be created.
    
    Args:
        db: The database session
        person: Person data for creation
        
    Returns:
        The created Person model
    """
    # Convert to dict and filter out fields not in the model
    person_dict = person.dict()
    if "duke_affiliation_score" in person_dict:
        person_dict.pop("duke_affiliation_score")
    # Remove last_updated field as it doesn't exist in the model
    if "last_updated" in person_dict:
        person_dict.pop("last_updated")
    
    # Set created_at and updated_at fields
    now = datetime.utcnow()
    person_dict["created_at"] = now
    person_dict["updated_at"] = now
    
    # Create the person object
    db_person = models.Person(**person_dict)
    
    db.add(db_person)
    await db.commit()
    await db.refresh(db_person)
    return db_person

async def get_person(db: AsyncSession, person_id: int) -> Optional[models.Person]:
    """
    Get a person by ID.
    
    This function is used internally by the delete_person function
    and may be used by future API endpoints.
    
    Args:
        db: The database session
        person_id: The ID of the person to retrieve
        
    Returns:
        The Person model if found, None otherwise
    """
    result = await db.execute(select(models.Person).where(models.Person.id == person_id))
    return result.scalars().first()

async def get_person_by_name(db: AsyncSession, name: str) -> Optional[models.Person]:
    """
    Get a person by name.
    
    This function is used by the search API endpoint to lookup
    a person before attempting to scrape new data.
    
    Args:
        db: The database session
        name: The name of the person to retrieve
        
    Returns:
        The Person model if found, None otherwise
    """
    result = await db.execute(select(models.Person).where(models.Person.name == name))
    return result.scalars().first()

async def get_persons(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    duke_affiliation_status: Optional[str] = None
) -> List[models.Person]:
    """
    Get a list of people with optional filtering.
    
    This function is used by the background tasks to process
    all people or filter by affiliation status.
    
    Args:
        db: The database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        duke_affiliation_status: Optional filter for Duke affiliation
        
    Returns:
        List of Person models
    """
    query = select(models.Person).offset(skip).limit(limit)
    
    if duke_affiliation_status:
        query = query.where(models.Person.duke_affiliation_status == duke_affiliation_status)
    
    result = await db.execute(query)
    return result.scalars().all()

async def delete_person(db: AsyncSession, person_id: int) -> bool:
    """
    Delete a person.
    
    This function is used by the delete API endpoint to remove
    a person from the database.
    
    Args:
        db: The database session
        person_id: The ID of the person to delete
        
    Returns:
        True if the person was deleted, False if not found
    """
    db_person = await get_person(db, person_id)
    if not db_person:
        return False
    
    await db.delete(db_person)
    await db.commit()
    return True

async def update_person(
    db: AsyncSession, 
    person_id: int, 
    person_data: schemas.PersonUpdate
) -> Optional[models.Person]:
    """
    Update a person.
    
    This function is used by the update API endpoint to modify
    a person's information in the database.
    
    Args:
        db: The database session
        person_id: The ID of the person to update
        person_data: Updated person data
        
    Returns:
        The updated Person model if found, None otherwise
    """
    db_person = await get_person(db, person_id)
    if not db_person:
        return None

    # Create a dict of updated fields
    update_data = person_data.dict(exclude_unset=True)
    
    # Handle specific field conversions if needed
    if "twitter_summary" in update_data and update_data["twitter_summary"]:
        if hasattr(update_data["twitter_summary"], "dict"):
            update_data["twitter_summary"] = update_data["twitter_summary"].dict()

    try:
        # Update the person
        await db.execute(
            update(models.Person)
            .where(models.Person.id == person_id)
            .values(**update_data)
        )
        await db.commit()
        
        # Refresh and return the updated person
        return await get_person(db, person_id)
    except Exception as e:
        db_logger.error(f"Error updating person {person_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating person: {str(e)}") 