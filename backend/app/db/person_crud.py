"""
Person CRUD Operations Module

This module provides specialized CRUD operations for Person entities.
Includes methods for searching, filtering, and managing person records.

Key Features:
- Person-specific database operations
- Search functionality
- Relationship management
- Bulk operations support
"""
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, text
from sqlalchemy.orm import selectinload
from . import models, schemas
from typing import List, Optional, Dict, Any, Union
from ..utils.logger import db_logger as logger
from datetime import datetime
from fastapi import HTTPException
from .formatting_utils import format_education, format_previous_companies, format_source_links

async def create_person(db: AsyncSession, person: Union[dict, schemas.PersonCreate]) -> models.Person:
    """
    Create a new person independently.
    Formats complex fields into simplified strings before saving.
    
    This function is used by the search API endpoint when a person
    is not found in the database and needs to be created.
    
    Args:
        db: The database session
        person: Person data for creation (either dict or PersonCreate object)
        
    Returns:
        The created Person model
    """
    try:
        # Handle both dict and PersonCreate inputs
        if isinstance(person, dict):
            person_data = person.copy() # Work with a copy
        else:
            person_data = person.dict()
            
        # Remove fields not in the model if they exist
        for field in ["duke_affiliation_score", "last_updated"]:
            person_data.pop(field, None)
            
        # Format list/dict fields into simplified strings
        if "education" in person_data:
            person_data["education"] = format_education(person_data["education"])
        if "previous_companies" in person_data:
            person_data["previous_companies"] = format_previous_companies(person_data["previous_companies"])
        if "source_links" in person_data:
             person_data["source_links"] = format_source_links(person_data["source_links"])
            
        # Set created_at and updated_at fields
        now = datetime.utcnow()
        person_data["created_at"] = now
        person_data["updated_at"] = now
        
        # Create the person object
        # Filter out None values before creating the model instance
        db_person_data = {k: v for k, v in person_data.items() if v is not None}
        db_person = models.Person(**db_person_data)
        
        db.add(db_person)
        await db.commit()
        await db.refresh(db_person)
        return db_person
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating person: {str(e)}")
        raise

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
    Formats complex fields into simplified strings before saving.
    Only updates fields if the incoming data provides a non-null value 
    (after formatting), preventing accidental overwrites with nulls.

    This function is used by the update API endpoint to modify
    a person's information in the database.
    
    Args:
        db: The database session
        person_id: The ID of the person to update
        person_data: Updated person data (PersonUpdate schema object)
        
    Returns:
        The updated Person model if found, None otherwise
    """
    db_person = await get_person(db, person_id)
    if not db_person:
        logger.warning(f"Attempted to update non-existent person with ID: {person_id}")
        return None

    try:
        # Convert schema to dict containing only fields that were explicitly set
        update_values = person_data.dict(exclude_unset=True)
        
        # Format list/dict fields into simplified strings if present
        # Store the formatted values separately to check for None after formatting
        formatted_values = {}
        if "education" in update_values:
            formatted_values["education"] = format_education(update_values["education"])
        if "previous_companies" in update_values:
            formatted_values["previous_companies"] = format_previous_companies(update_values["previous_companies"])
        if "source_links" in update_values:
            formatted_values["source_links"] = format_source_links(update_values["source_links"])
        
        # Set updated_at timestamp
        update_values['updated_at'] = datetime.utcnow()
        
        # Build the final update dictionary: include only non-None values
        final_update_data = {}
        for key, value in update_values.items():
            # Use the formatted value if it exists for the complex fields
            formatted_value = formatted_values.get(key, value) 
            if formatted_value is not None:
                final_update_data[key] = formatted_value

        # Remove fields that are not part of the model or shouldn't be updated directly
        allowed_keys = {col.name for col in models.Person.__table__.columns if col.name not in ['id', 'created_at']}
        final_update_data = {k: v for k, v in final_update_data.items() if k in allowed_keys}

        if not final_update_data or not any(k != 'updated_at' for k in final_update_data):
            # No actual field updates to perform besides timestamp
            logger.info(f"No data fields to update for person {person_id}. Only updating timestamp.")
            if 'updated_at' in final_update_data:
                 await db.execute(text("UPDATE persons SET updated_at = :updated_at WHERE id = :person_id"),
                                {"updated_at": final_update_data['updated_at'], "person_id": person_id})
                 await db.commit()
                 await db.refresh(db_person)
            return db_person # Return the person object even if only timestamp was updated

        # Dynamically build the UPDATE statement
        set_clauses = ", ".join([f"{key} = :{key}" for key in final_update_data])
        update_query = text(f"""
            UPDATE persons 
            SET {set_clauses}
            WHERE id = :person_id
        """)
        
        logger.info(f"Executing update for person {person_id} with fields: {list(final_update_data.keys())}")
        await db.execute(update_query, {**final_update_data, "person_id": person_id})
        await db.commit()
        
        # Refresh and return the updated person
        await db.refresh(db_person)
        logger.info(f"Successfully updated person {person_id}")
        return db_person
        
    except Exception as e:
        logger.error(f"Error updating person {person_id}: {str(e)}")
        await db.rollback()
        # Consider if raising HTTPException is always correct here, or if None might be better
        raise HTTPException(status_code=500, detail=f"Error updating person: {str(e)}") 