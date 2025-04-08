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
async def create_company(db: AsyncSession, company: schemas.CompanyCreate) -> models.Company:
    """
    Create a new company. Associated people are only used for scoring and association,
    not added as Person entries.
    
    Args:
        db: The database session
        company: Company data for creation, including optional people
        
    Returns:
        The created Company model
    """
    # Create company object with fields that exist in the model
    db_company = models.Company(
        name=company.name,
        duke_affiliation_status=company.duke_affiliation_status,
        relevance_score=company.relevance_score,
        summary=company.summary,
        investors=company.investors,
        funding_stage=company.funding_stage,
        industry=company.industry,
        founded=company.founded,
        location=company.location,
        twitter_handle=company.twitter_handle,
        linkedin_handle=company.linkedin_handle,
        twitter_summary=company.twitter_summary,
        source_links=company.source_links,
    )
    
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    
    # Process people only if provided and not empty
    if company.people and len(company.people) > 0:
        # Store the association data for each person
        for person_data in company.people:
            # Get title for association - default to person's title if available
            title_for_association = getattr(person_data, 'title', None) or "unknown"
            
            # Add the association with just the name and title
            await db.execute(
                models.company_person_association.insert().values(
                    company_id=db_company.id,
                    name=person_data.name,  # Store name directly in association
                    title=title_for_association,
                    duke_affiliation_status=person_data.duke_affiliation_status  # Store affiliation status for scoring
                )
            )
        
        await db.commit()
        await db.refresh(db_company)
    
    return db_company

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
    Update a company. Associated people are only used for scoring and association,
    not added as Person entries.
    
    Args:
        db: The database session
        company_id: The ID of the company to update
        company_data: Updated company data
        
    Returns:
        The updated Company model if found, None otherwise
        
    Raises:
        HTTPException: If there's an error during the update process
    """
    db_company = await get_company(db, company_id)
    if not db_company:
        return None

    # Create a dict of updated fields, excluding 'people'
    update_data = {}
    for key, value in company_data.dict(exclude_unset=True).items():
        if key != 'people':
            update_data[key] = value

    # Handle specific field conversions if needed
    if "twitter_summary" in update_data and update_data["twitter_summary"]:
        if hasattr(update_data["twitter_summary"], "dict"):
            update_data["twitter_summary"] = update_data["twitter_summary"].dict()

    try:
        # --- Update scalar fields --- 
        if update_data:
            await db.execute(
                update(models.Company)
                .where(models.Company.id == company_id)
                .values(**update_data)
            )
            await db.flush()

        # --- Handle people updates --- 
        people_data = getattr(company_data, 'people', None)
        if people_data is not None:  # Only process if explicitly included in the update
            # 1. Clear existing associations
            await db.execute(
                delete(models.company_person_association)
                .where(models.company_person_association.c.company_id == company_id)
            )
            await db.flush()

            # 2. Add new associations
            if people_data:  # Only process if there are people to add
                for person_data in people_data:
                    # Get title for association - default to person's title if available
                    title_for_association = getattr(person_data, 'title', None) or "unknown"
                    
                    # Add the association with just the name and title
                    await db.execute(
                        models.company_person_association.insert().values(
                            company_id=company_id,
                            name=person_data.name,  # Store name directly in association
                            title=title_for_association,
                            duke_affiliation_status=person_data.duke_affiliation_status  # Store affiliation status for scoring
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
        logger.error(f"Error updating company ID {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating company: {e}") from e

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