"""
Company and API Key CRUD operations.

This module contains database operations for Company and API Key entities,
used by the application's API endpoints and background tasks.

Key Features:
- Async database operations
- Error handling and logging
- Transaction management
- Relationship handling
"""

# Import necessary modules
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from sqlalchemy.orm import selectinload
from . import models, schemas
from typing import List, Optional, Dict, Any, Union
from ..utils.logger import db_logger as logger
from datetime import datetime
import json
from fastapi import HTTPException
from . import person_crud  # Import person CRUD operations


# Company CRUD operations
async def create_company(db: AsyncSession, company: Union[dict, schemas.CompanyCreate]) -> models.Company:
    """
    Create a new company in the database.
    
    Args:
        db: Database session
        company: Company data (dict or CompanyCreate schema)
        
    Returns:
        Created Company object
        
    Raises:
        Exception: If creation fails
    """
    try:
        # Convert to dict if schema
        if isinstance(company, schemas.CompanyCreate):
            company_data = company.dict()
        else:
            company_data = company.copy()
            
        # Extract people data before creating company
        people_data = company_data.pop("people", [])
        
        # Create company
        db_company = models.Company(**company_data)
        db.add(db_company)
        await db.flush()  # Get the ID
        
        # Process people only if provided and not empty
        if people_data and len(people_data) > 0:
            # Store the association data for each person
            for person_data in people_data:
                # Get person name from either dict or schema object
                person_name = person_data.name if hasattr(person_data, 'name') else person_data['name']
                person_title = person_data.title if hasattr(person_data, 'title') else person_data['title']
                
                # First, create or get the person
                person = await person_crud.get_person_by_name(db, person_name)
                if not person:
                    # Create new person with all available data
                    person = await person_crud.create_person(db, {
                        "name": person_name,
                        "title": person_title,
                        "duke_affiliation_status": getattr(person_data, 'duke_affiliation_status', 'no') if hasattr(person_data, 'duke_affiliation_status') else person_data.get('duke_affiliation_status', 'no'),
                        "relevance_score": getattr(person_data, 'relevance_score', 0) if hasattr(person_data, 'relevance_score') else person_data.get('relevance_score', 0),
                        "current_company": company_data['name'],
                        "education": getattr(person_data, 'education', None) if hasattr(person_data, 'education') else person_data.get('education'),
                        "previous_companies": getattr(person_data, 'previous_companies', None) if hasattr(person_data, 'previous_companies') else person_data.get('previous_companies'),
                        "twitter_handle": getattr(person_data, 'twitter_handle', None) if hasattr(person_data, 'twitter_handle') else person_data.get('twitter_handle'),
                        "linkedin_handle": getattr(person_data, 'linkedin_handle', None) if hasattr(person_data, 'linkedin_handle') else person_data.get('linkedin_handle'),
                        "twitter_summary": getattr(person_data, 'twitter_summary', None) if hasattr(person_data, 'twitter_summary') else person_data.get('twitter_summary'),
                        "source_links": getattr(person_data, 'source_links', None) if hasattr(person_data, 'source_links') else person_data.get('source_links')
                    })
                else:
                    # Update existing person with new data
                    person_update = {
                        "name": person_name,
                        "title": person_title,
                        "duke_affiliation_status": getattr(person_data, 'duke_affiliation_status', 'no') if hasattr(person_data, 'duke_affiliation_status') else person_data.get('duke_affiliation_status', 'no'),
                        "relevance_score": getattr(person_data, 'relevance_score', 0) if hasattr(person_data, 'relevance_score') else person_data.get('relevance_score', 0),
                        "current_company": company_data['name'],
                        "education": getattr(person_data, 'education', None) if hasattr(person_data, 'education') else person_data.get('education'),
                        "previous_companies": getattr(person_data, 'previous_companies', None) if hasattr(person_data, 'previous_companies') else person_data.get('previous_companies'),
                        "twitter_handle": getattr(person_data, 'twitter_handle', None) if hasattr(person_data, 'twitter_handle') else person_data.get('twitter_handle'),
                        "linkedin_handle": getattr(person_data, 'linkedin_handle', None) if hasattr(person_data, 'linkedin_handle') else person_data.get('linkedin_handle'),
                        "twitter_summary": getattr(person_data, 'twitter_summary', None) if hasattr(person_data, 'twitter_summary') else person_data.get('twitter_summary'),
                        "source_links": getattr(person_data, 'source_links', None) if hasattr(person_data, 'source_links') else person_data.get('source_links')
                    }
                    person = await person_crud.update_person(db, person.id, person_update)
                
                # Add the association
                await db.execute(
                    models.company_person_association.insert().values(
                        company_id=db_company.id,
                        person_id=person.id
                    )
                )
            
            await db.commit()
            await db.refresh(db_company)
        
        return db_company
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating company: {str(e)}")
        raise

async def get_company(db: AsyncSession, company_id: int) -> Optional[models.Company]:
    """
    Get a company by ID.
    
    Args:
        db: The database session
        company_id: The ID of the company to retrieve
        
    Returns:
        The Company model if found, None otherwise
    """
    result = await db.execute(select(models.Company).where(models.Company.id == company_id))
    return result.scalars().first()

async def get_company_by_name(db: AsyncSession, name: str) -> Optional[models.Company]:
    """
    Get a company by name.
    
    Args:
        db: The database session
        name: The name of the company to retrieve
        
    Returns:
        The Company model if found, None otherwise
    """
    result = await db.execute(select(models.Company).where(models.Company.name == name))
    return result.scalars().first()


async def get_companies(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    duke_affiliation_status: Optional[str] = None
) -> List[models.Company]:
    """
    Get a list of companies with optional filtering.
    
    Args:
        db: The database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        duke_affiliation_status: Optional filter for Duke affiliation
        
    Returns:
        List of Company models
    """
    query = select(models.Company).offset(skip).limit(limit)
    
    if duke_affiliation_status:
        query = query.where(models.Company.duke_affiliation_status == duke_affiliation_status)
    
    result = await db.execute(query)
    return result.scalars().all()

async def update_company(
    db: AsyncSession, 
    company_id: int, 
    company_data: schemas.CompanyUpdate
) -> Optional[models.Company]:
    """
    Update an existing company in the database.
    
    Args:
        db: Database session
        company_id: ID of company to update
        company_data: Updated company data
        
    Returns:
        Updated Company object or None if update fails
    """
    try:
        # Convert to dict and remove None values
        update_data = {k: v for k, v in company_data.dict().items() if v is not None}
        
        # Extract people data before updating company
        people_data = update_data.pop("people", None)

        # Handle JSON fields
        for field in ["investors", "source_links"]:
            if field in update_data and isinstance(update_data[field], (list, dict)):
                update_data[field] = json.dumps(update_data[field])

        # Update company fields
        if update_data:
            await db.execute(
                update(models.Company)
                .where(models.Company.id == company_id)
                .values(**update_data)
            )
            await db.flush()

        # Handle people updates if provided
        if people_data is not None:
            # Clear existing associations
            await db.execute(
                delete(models.company_person_association)
                .where(models.company_person_association.c.company_id == company_id)
            )
            await db.flush()

            # Add new associations
            if people_data:
                for person_data in people_data:
                    # Helper function to get value from either dict or schema object
                    def get_value(field):
                        if hasattr(person_data, field):
                            return getattr(person_data, field)
                        elif isinstance(person_data, dict):
                            return person_data.get(field)
                        return None

                    # Get person name and title
                    person_name = get_value('name')
                    person_title = get_value('title')
                    
                    # Get or create person
                    person = await person_crud.get_person_by_name(db, person_name)
                    if person:
                        # Create PersonUpdate schema with all fields, ensuring we pass all data
                        person_update = schemas.PersonUpdate(
                            name=person_name,
                            title=person_title,
                            duke_affiliation_status=get_value('duke_affiliation_status') or 'no',
                            relevance_score=get_value('relevance_score') or 0,
                            current_company=update_data.get('name'),
                            education=get_value('education'),
                            previous_companies=get_value('previous_companies'),
                            twitter_handle=get_value('twitter_handle'),
                            linkedin_handle=get_value('linkedin_handle'),
                            twitter_summary=get_value('twitter_summary'),
                            source_links=get_value('source_links')
                        )
                        # Update person with all fields
                        person = await person_crud.update_person(db, person.id, person_update)
                        if not person:
                            logger.error(f"Failed to update person: {person_name}")
                            continue
                    else:
                        # Create PersonCreate schema with all fields
                        person_create = schemas.PersonCreate(
                            name=person_name,
                            title=person_title,
                            duke_affiliation_status=get_value('duke_affiliation_status') or 'no',
                            relevance_score=get_value('relevance_score') or 0,
                            current_company=update_data.get('name'),
                            education=get_value('education'),
                            previous_companies=get_value('previous_companies'),
                            twitter_handle=get_value('twitter_handle'),
                            linkedin_handle=get_value('linkedin_handle'),
                            twitter_summary=get_value('twitter_summary'),
                            source_links=get_value('source_links')
                        )
                        # Create person with all fields
                        person = await person_crud.create_person(db, person_create)
                        if not person:
                            logger.error(f"Failed to create person: {person_name}")
                            continue
                    
                    # Add association
                    await db.execute(
                        models.company_person_association.insert().values(
                            company_id=company_id,
                            person_id=person.id
                        )
                    )
                await db.flush()

        # Commit all changes
        await db.commit()
        
        # Reload the company
        result = await db.execute(
            select(models.Company)
            .where(models.Company.id == company_id)
        )
        return result.scalars().first()
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating company: {str(e)}")
        raise

async def delete_company(db: AsyncSession, company_id: int) -> bool:
    """
    Delete a company by ID.
    
    Args:
        db: The database session
        company_id: The ID of the company to delete
        
    Returns:
        True if the company was deleted, False if not found
    """
    db_company = await get_company(db, company_id)
    if not db_company:
        return False
    
    try:
        # First delete all associated people from the association table
        await db.execute(
            delete(models.company_person_association)
            .where(models.company_person_association.c.company_id == company_id)
        )
        
        # Then delete the company
        await db.delete(db_company)
        await db.commit()
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting company ID {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting company: {e}") from e

# API Key CRUD operations
async def create_api_key(db: AsyncSession, api_key: schemas.APIKeyCreate) -> models.APIKey:
    """
    Create a new API key.
    
    Args:
        db: The database session
        api_key: API key data for creation
        
    Returns:
        The created APIKey model
    """
    db_api_key = models.APIKey(
        name=api_key.name,
        rate_limit=api_key.rate_limit
    )
    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)
    return db_api_key

async def get_api_key(db: AsyncSession, key: str) -> Optional[models.APIKey]:
    """
    Get an API key by value.
    
    Args:
        db: The database session
        key: The API key to look up
        
    Returns:
        The APIKey model if found, None otherwise
    """
    result = await db.execute(select(models.APIKey).where(models.APIKey.key == key))
    return result.scalars().first()

async def deactivate_api_key(db: AsyncSession, key: str) -> bool:
    """
    Deactivate an API key.
    
    Args:
        db: The database session
        key: The API key to deactivate
        
    Returns:
        True if the key was deactivated, False if not found
    """
    db_api_key = await get_api_key(db, key)
    if not db_api_key:
        return False
    
    db_api_key.is_active = False
    await db.commit()
    
    return True

def company_to_dict(company: models.Company) -> Dict[str, Any]:
    """Convert a Company model instance to a dictionary."""
    return {
        "id": company.id,
        "name": company.name,
        "duke_affiliation_status": company.duke_affiliation_status,
        "relevance_score": company.relevance_score,
        "summary": company.summary,
        "investors": company.investors or "",
        "funding_stage": company.funding_stage,
        "industry": company.industry,
        "founded": company.founded,
        "location": company.location,
        "twitter_handle": company.twitter_handle,
        "linkedin_handle": company.linkedin_handle,
        "twitter_summary": company.twitter_summary or "",
        "source_links": company.source_links or "",
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "people": [person_to_dict(person) for person in company.people] if company.people else []
    }

def person_to_dict(person: models.Person) -> Dict[str, Any]:
    """Convert a Person model instance to a dictionary."""
    return {
        "id": person.id,
        "name": person.name,
        "title": person.title,
        "duke_affiliation_status": person.duke_affiliation_status,
        "relevance_score": person.relevance_score,
        "education": person.education or "",
        "current_company": person.current_company,
        "previous_companies": person.previous_companies or "",
        "twitter_handle": person.twitter_handle,
        "linkedin_handle": person.linkedin_handle,
        "twitter_summary": person.twitter_summary or "",
        "source_links": person.source_links or "",
        "created_at": person.created_at,
        "updated_at": person.updated_at,
        "companies": [{"id": c.id, "name": c.name} for c in person.companies] if person.companies else []
    } 