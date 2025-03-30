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

# Company CRUD operations
async def create_company(db: AsyncSession, company: schemas.CompanyCreate) -> models.Company:
    """Create a new company"""
    db_company = models.Company(
        name=company.name,
        duke_affiliation_status=company.duke_affiliation_status,
        duke_affiliation_score=company.duke_affiliation_score,
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
                    duke_affiliation_status=person_data.duke_affiliation_status,
                    duke_affiliation_score=person_data.duke_affiliation_score,
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
            
            # Track for addition
            people_to_add.append((person, person_data.title))
        
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
    """Get a company by ID"""
    result = await db.execute(select(models.Company).where(models.Company.id == company_id))
    return result.scalars().first()

async def get_company_by_name(db: AsyncSession, name: str) -> Optional[models.Company]:
    """Get a company by name"""
    result = await db.execute(select(models.Company).where(models.Company.name == name))
    return result.scalars().first()

async def get_company_by_twitter_handle(db: AsyncSession, twitter_handle: str) -> Optional[models.Company]:
    """Get a company by Twitter handle"""
    # Ensure the handle starts with @ for consistency
    if twitter_handle and not twitter_handle.startswith('@'):
        twitter_handle = f'@{twitter_handle}'
        
    result = await db.execute(select(models.Company).where(models.Company.twitter_handle == twitter_handle))
    return result.scalars().first()

async def get_companies(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    duke_affiliation_status: Optional[str] = None
) -> List[models.Company]:
    """Get a list of companies with optional filtering"""
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
    """Update a company"""
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
                            duke_affiliation_status=person_data.duke_affiliation_status,
                            duke_affiliation_score=person_data.duke_affiliation_score,
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
                    
                    # Add the association
                    await db.execute(
                        models.company_person_association.insert().values(
                            company_id=company_id,
                            person_id=db_person.id,
                            title=person_data.title
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
    """Delete a company"""
    # First check if company exists
    company = await get_company(db, company_id)
    if not company:
        return False
    
    await db.execute(delete(models.Company).where(models.Company.id == company_id))
    await db.commit()
    return True

# API Key CRUD operations
async def create_api_key(db: AsyncSession, api_key: schemas.APIKeyCreate) -> models.APIKey:
    """Create a new API key"""
    db_api_key = models.APIKey(
        name=api_key.name,
        rate_limit=api_key.rate_limit
    )
    
    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)
    return db_api_key

async def get_api_key(db: AsyncSession, key: str) -> Optional[models.APIKey]:
    """Get an API key by value"""
    result = await db.execute(select(models.APIKey).where(models.APIKey.key == key))
    return result.scalars().first()

async def deactivate_api_key(db: AsyncSession, key: str) -> bool:
    """Deactivate an API key"""
    api_key = await get_api_key(db, key)
    if not api_key:
        return False
    
    await db.execute(
        update(models.APIKey)
        .where(models.APIKey.key == key)
        .values(is_active=False)
    )
    
    await db.commit()
    return True

# Person CRUD operations
async def create_person(db: AsyncSession, person: schemas.PersonCreate) -> models.Person:
    """Create a new person independently."""
    # Check if person already exists by name (optional, decide if names must be unique)
    # existing_person = await get_person_by_name(db, name=person.name)
    # if existing_person:
    #     # Handle duplicate name scenario if necessary (e.g., raise error, update existing)
    #     # For now, we allow duplicate names as people might share names
    #     pass 

    db_person = models.Person(
        name=person.name,
        duke_affiliation_status=person.duke_affiliation_status,
        duke_affiliation_score=person.duke_affiliation_score,
        relevance_score=person.relevance_score,
        education=person.education,
        current_company=person.current_company,
        previous_companies=person.previous_companies,
        twitter_handle=person.twitter_handle,
        linkedin_handle=person.linkedin_handle,
        twitter_summary=person.twitter_summary, # Assuming this is a simple string or dict now
        source_links=person.source_links
        # Note: Company association is NOT handled here
    )
    db.add(db_person)
    await db.commit()
    await db.refresh(db_person)
    return db_person

async def get_person(db: AsyncSession, person_id: int) -> Optional[models.Person]:
    """Get a person by ID."""
    # Use eager loading for companies if needed frequently when getting a person
    # from sqlalchemy.orm import selectinload
    # result = await db.execute(select(models.Person).options(selectinload(models.Person.companies)).where(models.Person.id == person_id))
    result = await db.execute(select(models.Person).where(models.Person.id == person_id))
    return result.scalars().first()

async def get_person_by_name(db: AsyncSession, name: str) -> Optional[models.Person]:
    """Get a person by name."""
    result = await db.execute(select(models.Person).where(models.Person.name == name))
    # If multiple people can have the same name, use .first() or adjust logic
    return result.scalars().first()

async def get_persons(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    duke_affiliation_status: Optional[str] = None
) -> List[models.Person]:
    """Get a list of people with optional filtering."""
    query = select(models.Person).offset(skip).limit(limit)
    
    if duke_affiliation_status:
        query = query.where(models.Person.duke_affiliation_status == duke_affiliation_status)
    
    result = await db.execute(query)
    return result.scalars().all()

async def update_person(
    db: AsyncSession, 
    person_id: int, 
    person_data: schemas.PersonUpdate # Need to define PersonUpdate schema
) -> Optional[models.Person]:
    """Update a person's details. Does not handle company associations."""
    db_person = await get_person(db, person_id)
    if not db_person:
        return None

    update_data = person_data.dict(exclude_unset=True)
    
    # Update fields
    for key, value in update_data.items():
        setattr(db_person, key, value)
        
    await db.commit()
    await db.refresh(db_person)
    return db_person

async def delete_person(db: AsyncSession, person_id: int) -> bool:
    """Delete a person. Does not automatically handle company associations (they might remain)."""
    db_person = await get_person(db, person_id)
    if not db_person:
        return False
        
    # Decide on cascade behavior for associations if person is deleted
    # By default, SQLAlchemy might prevent deletion if associations exist,
    # Or nullify the foreign key depending on relationship settings.
    # Explicitly deleting associations might be needed depending on requirements.
    # await db.execute(delete(models.company_person_association).where(models.company_person_association.c.person_id == person_id))
    
    await db.delete(db_person) # Use db.delete for ORM object
    await db.commit()
    return True 