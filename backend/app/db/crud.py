"""
Company and API Key CRUD operations.

This module contains database operations for Company and API Key entities,
used by the application's API endpoints and background tasks.
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
from . import person_crud  # Import person CRUD operations

# Company CRUD operations
async def create_company(db: AsyncSession, company: schemas.CompanyCreate) -> models.Company:
    """
    Create a new company with optional related people.
    
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
        twitter_summary=company.twitter_summary.dict() if company.twitter_summary else None,
        source_links=company.source_links,
    )
    
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    
    # Process people only if provided and not empty
    if company.people and len(company.people) > 0:
        people_to_add = []
        
        # Add people if provided
        for person_data in company.people:
            # Check if person already exists
            person_result = await db.execute(
                select(models.Person).where(models.Person.name == person_data.name)
            )
            person = person_result.scalars().first()
            
            # Create new person if not exists
            if not person:
                person = models.Person(
                    name=person_data.name,
                    title=person_data.title,
                    duke_affiliation_status=person_data.duke_affiliation_status,
                    relevance_score=person_data.relevance_score,
                    education=person_data.education,
                    current_company=person_data.current_company,
                    previous_companies=getattr(person_data, 'previous_companies', []),
                    twitter_handle=person_data.twitter_handle,
                    linkedin_handle=person_data.linkedin_handle,
                    twitter_summary=person_data.twitter_summary,
                    source_links=getattr(person_data, 'source_links', [])
                )
                db.add(person)
                await db.commit()
                await db.refresh(person)
            
            # Determine title for association - default to person's title if available, or "unknown" if not
            title_for_association = getattr(person_data, 'title', None) or "unknown"
            
            # Track for addition
            people_to_add.append((person, title_for_association))
        
        # Now add all the people in a separate query
        for person, title in people_to_add:
            # Add the relationship through a junction table query
            stmt = models.company_person_association.insert().values(
                company_id=db_company.id,
                person_id=person.id,
                title=title
            )
            await db.execute(stmt)
        
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
    Update a company and optionally its related people.
    
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
                    # Find or create the person
                    result = await db.execute(
                        select(models.Person).where(models.Person.name == person_data.name)
                    )
                    db_person = result.scalars().first()
                    
                    if not db_person:
                        # Create a new person if not found
                        db_person = models.Person(
                            name=person_data.name,
                            title=person_data.title,
                            duke_affiliation_status=person_data.duke_affiliation_status,
                            relevance_score=person_data.relevance_score,
                            education=person_data.education,
                            current_company=person_data.current_company,
                            previous_companies=getattr(person_data, 'previous_companies', []),
                            twitter_handle=person_data.twitter_handle,
                            linkedin_handle=person_data.linkedin_handle,
                            twitter_summary=person_data.twitter_summary,
                            source_links=getattr(person_data, 'source_links', [])
                        )
                        db.add(db_person)
                        await db.flush()
                        await db.refresh(db_person)
                    
                    # Get title for association - default to person's title if available
                    title_for_association = getattr(person_data, 'title', None) or "unknown"
                    
                    # Add the association
                    await db.execute(
                        models.company_person_association.insert().values(
                            company_id=company_id,
                            person_id=db_person.id,
                            title=title_for_association
                        )
                    )
                await db.flush()

        # Commit all changes
        await db.commit()
        
        # Reload the company with its people
        result = await db.execute(
            select(models.Company)
            .options(selectinload(models.Company.people))
            .where(models.Company.id == company_id)
        )
        return result.scalars().first()
        
    except Exception as e:
        await db.rollback()
        db_logger.error(f"Error updating company ID {company_id}: {e}")
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
    
    # Delete the company - note, this may cause cascade issues depending on
    # the constraints in the database and model relationships
    await db.delete(db_company)
    
    await db.commit()
    return True

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