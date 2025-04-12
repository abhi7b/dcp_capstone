"""
Migration script to load JSON data from json_inputs directory into the database.
This script handles both company and person data, maintaining relationships.
"""
import os
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from .session import async_session
from .models import Company, Person
from ..utils.logger import db_logger as logger
from ..utils.config import settings

def preprocess_json_field(value: Any) -> Any:
    """Preprocess JSON fields to ensure proper format."""
    if isinstance(value, list):
        # If it's a single-item list, convert to string
        if len(value) == 1:
            return str(value[0]).strip('"')
        # If it's a list of strings, join them with commas
        if all(isinstance(item, str) for item in value):
            return ", ".join(str(item).strip('"') for item in value)
        # If it's a list of dictionaries (like education), format each entry
        if all(isinstance(item, dict) for item in value):
            formatted_entries = []
            for item in value:
                # Only include non-null values in the education entry
                valid_fields = {k: v for k, v in item.items() if v and v != "null" and v != "None"}
                if valid_fields:
                    formatted_entries.append(json.dumps(valid_fields))
            return formatted_entries if formatted_entries else None
    elif isinstance(value, str):
        # Skip null values and empty strings
        if value == "null" or value == "None" or value == "":
            return None
        return value.strip('"')
    return value

async def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {str(e)}")
        return None

def get_model_fields(model_class) -> List[str]:
    """Get all column names for a SQLAlchemy model."""
    return [column.key for column in model_class.__table__.columns]

async def process_company_data(company_data: dict, db: AsyncSession) -> Company:
    """
    Process company data and insert/update into the database.
    
    Args:
        company_data: Dictionary containing company information
        db: Database session
        
    Returns:
        Company object
    """
    try:
        # Preprocess investors
        investors = None
        if "investors" in company_data and isinstance(company_data["investors"], list):
            investors = ", ".join(company_data["investors"])

        # Preprocess source links
        source_links = None
        if "source_links" in company_data and isinstance(company_data["source_links"], list):
            source_links = ", ".join(company_data["source_links"])

        # Prepare data for insertion
        company_values = {
            "name": company_data["name"],
            "duke_affiliation_status": company_data.get("duke_affiliation_status", "unknown"),
            "relevance_score": company_data.get("relevance_score", 0),
            "summary": company_data.get("summary"),
            "investors": investors,
            "funding_stage": company_data.get("funding_stage"),
            "industry": company_data.get("industry"),
            "founded": company_data.get("founded"),
            "location": company_data.get("location"),
            "twitter_handle": company_data.get("twitter_handle"),
            "linkedin_handle": company_data.get("linkedin_handle"),
            "twitter_summary": company_data.get("twitter_summary"),
            "source_links": source_links,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert or update company
        result = await db.execute(
            text("""
                INSERT INTO companies (
                    name, duke_affiliation_status, relevance_score,
                    summary, investors, funding_stage, industry,
                    founded, location, twitter_handle, linkedin_handle,
                    twitter_summary, source_links, created_at, updated_at
                ) VALUES (
                    :name, :duke_affiliation_status, :relevance_score,
                    :summary, :investors, :funding_stage, :industry,
                    :founded, :location, :twitter_handle, :linkedin_handle,
                    :twitter_summary, :source_links, :created_at, :updated_at
                ) ON CONFLICT (name) DO UPDATE SET
                    duke_affiliation_status = EXCLUDED.duke_affiliation_status,
                    relevance_score = EXCLUDED.relevance_score,
                    summary = EXCLUDED.summary,
                    investors = EXCLUDED.investors,
                    funding_stage = EXCLUDED.funding_stage,
                    industry = EXCLUDED.industry,
                    founded = EXCLUDED.founded,
                    location = EXCLUDED.location,
                    twitter_handle = EXCLUDED.twitter_handle,
                    linkedin_handle = EXCLUDED.linkedin_handle,
                    twitter_summary = EXCLUDED.twitter_summary,
                    source_links = EXCLUDED.source_links,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """),
            company_values
        )
        
        company_id = result.scalar_one()
        logger.info(f"Successfully inserted/updated company: {company_data['name']} with ID: {company_id}")
        
        # Commit the changes
        await db.commit()
        
        # Fetch and return the company object with a fresh query
        company = await db.get(Company, company_id)
        await db.refresh(company)  # Ensure we have the latest data
        return company
        
    except Exception as e:
        logger.error(f"Error processing company data: {str(e)}")
        await db.rollback()
        raise

async def process_person_data(db: AsyncSession, person_data: dict) -> Person:
    """
    Process person data and insert/update into the database.
    
    Args:
        db: Database session
        person_data: Dictionary containing person information
        
    Returns:
        Person object
    """
    try:
        # Preprocess education data
        education = None
        if "education" in person_data and isinstance(person_data["education"], list):
            education_entries = []
            for entry in person_data["education"]:
                if isinstance(entry, dict):
                    parts = []
                    if entry.get("school"):
                        parts.append(f"School: {entry['school']}")
                    if entry.get("degree"):
                        parts.append(f"Degree: {entry['degree']}")
                    if entry.get("field"):
                        parts.append(f"Field: {entry['field']}")
                    if entry.get("year"):
                        parts.append(f"Year: {entry['year']}")
                    if parts:
                        education_entries.append("; ".join(parts))
            if education_entries:
                education = " | ".join(education_entries)

        # Preprocess previous companies
        previous_companies = None
        if "previous_companies" in person_data and isinstance(person_data["previous_companies"], list):
            previous_companies = ", ".join(person_data["previous_companies"])

        # Preprocess source links
        source_links = None
        if "source_links" in person_data and isinstance(person_data["source_links"], list):
            links = []
            for link in person_data["source_links"]:
                if isinstance(link, dict) and "url" in link:
                    links.append(link["url"])
                elif isinstance(link, str):
                    links.append(link)
            if links:
                source_links = ", ".join(links)

        # Prepare data for insertion
        person_values = {
            "name": person_data["name"],
            "title": person_data.get("title"),
            "duke_affiliation_status": person_data.get("duke_affiliation_status", "unknown"),
            "relevance_score": person_data.get("relevance_score", 0),
            "education": education,
            "current_company": person_data.get("current_company"),
            "previous_companies": previous_companies,
            "twitter_handle": person_data.get("twitter_handle"),
            "linkedin_handle": person_data.get("linkedin_handle"),
            "twitter_summary": person_data.get("twitter_summary"),
            "source_links": source_links,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert or update person
        result = await db.execute(
            text("""
                INSERT INTO persons (
                    name, title, duke_affiliation_status, relevance_score,
                    education, current_company, previous_companies,
                    twitter_handle, linkedin_handle, twitter_summary,
                    source_links, created_at, updated_at
                ) VALUES (
                    :name, :title, :duke_affiliation_status, :relevance_score,
                    :education, :current_company, :previous_companies,
                    :twitter_handle, :linkedin_handle, :twitter_summary,
                    :source_links, :created_at, :updated_at
                ) ON CONFLICT (name) DO UPDATE SET
                    title = EXCLUDED.title,
                    duke_affiliation_status = EXCLUDED.duke_affiliation_status,
                    relevance_score = EXCLUDED.relevance_score,
                    education = EXCLUDED.education,
                    current_company = EXCLUDED.current_company,
                    previous_companies = EXCLUDED.previous_companies,
                    twitter_handle = EXCLUDED.twitter_handle,
                    linkedin_handle = EXCLUDED.linkedin_handle,
                    twitter_summary = EXCLUDED.twitter_summary,
                    source_links = EXCLUDED.source_links,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """),
            person_values
        )
        
        person_id = result.scalar_one()
        logger.info(f"Successfully inserted/updated person: {person_data['name']} with ID: {person_id}")
        
        # Commit the changes
        await db.commit()
        
        # Fetch and return the person object with a fresh query
        person = await db.get(Person, person_id)
        await db.refresh(person)  # Ensure we have the latest data
        return person
        
    except Exception as e:
        logger.error(f"Error processing person data: {str(e)}")
        await db.rollback()
        raise

async def process_company_people(company: Company, people_data: list, db: AsyncSession) -> None:
    """
    Process and insert company-people relationships.
    
    Args:
        company: Company object
        people_data: List of person data dictionaries
        db: Database session
    """
    try:
        logger.info(f"Processing {len(people_data)} people for company: {company.name} (ID: {company.id})")
        
        for person_data in people_data:
            logger.info(f"Processing person: {person_data.get('name')}")
            
            # First process the person to ensure they exist in the database
            person = await process_person_data(db, person_data)
            
            if person:
                logger.info(f"Found person in database: {person.name} (ID: {person.id})")
                
                # Create the association
                result = await db.execute(
                    text("""
                        INSERT INTO company_person_association 
                            (company_id, person_id)
                        VALUES 
                            (:company_id, :person_id)
                        ON CONFLICT (company_id, person_id) DO NOTHING
                        RETURNING company_id, person_id
                    """),
                    {"company_id": company.id, "person_id": person.id}
                )
                
                # Verify the association was created
                association = result.first()
                if association:
                    logger.info(f"Created association between {company.name} (ID: {company.id}) and {person.name} (ID: {person.id})")
                else:
                    logger.info(f"Association already exists between {company.name} (ID: {company.id}) and {person.name} (ID: {person.id})")
                
                # Commit after each association to ensure data is persisted
                await db.commit()
                logger.info(f"Committed association for {person.name}")
            else:
                logger.warning(f"Person {person_data.get('name')} not found in database")
        
        # Final commit to ensure all changes are persisted
        await db.commit()
        logger.info(f"Successfully committed all company-people associations for {company.name}")
        
        # Verify the associations were created
        result = await db.execute(
            text("""
                SELECT COUNT(*) 
                FROM company_person_association 
                WHERE company_id = :company_id
            """),
            {"company_id": company.id}
        )
        count = result.scalar_one()
        logger.info(f"Verified {count} associations exist for {company.name}")
        
    except Exception as e:
        logger.error(f"Error processing company people: {str(e)}")
        await db.rollback()
        raise

async def migrate_json_to_db():
    """Main migration function to process all JSON files."""
    # Process company data from json_inputs
    json_dir = settings.JSON_INPUTS_DIR
    
    logger.info(f"Starting migration from JSON directory: {json_dir}")
    
    if not os.path.exists(json_dir):
        logger.error(f"JSON inputs directory not found: {json_dir}")
        return
    
    async with async_session() as db:
        try:
            # Process all JSON files
            for filename in os.listdir(json_dir):
                if not filename.endswith('.json'):
                    continue
                    
                file_path = os.path.join(json_dir, filename)
                logger.info(f"Processing file: {file_path}")
                
                data = await load_json_file(file_path)
                if not data:
                    logger.warning(f"Could not load data from {file_path}")
                    continue
                
                logger.info(f"Successfully loaded data from {filename}")
                
                if filename.startswith('company_'):
                    # Process company data
                    logger.info(f"Processing company data from {filename}")
                    company = await process_company_data(data, db)
                    if company:
                        logger.info(f"Successfully processed company: {company.name} (ID: {company.id})")
                        
                        # Process people from the company data
                        if "people" in data:
                            logger.info(f"Found {len(data['people'])} people in company data")
                            await process_company_people(company, data["people"], db)
                            logger.info(f"Processed {len(data['people'])} people for {company.name}")
                        else:
                            logger.warning(f"No people data found in {filename}")
                    else:
                        logger.warning(f"Failed to process company from {filename}")
                elif filename.startswith('person_'):
                    # Process standalone person data
                    logger.info(f"Processing standalone person data from {filename}")
                    person = await process_person_data(db, data)
                    if person:
                        logger.info(f"Successfully processed person: {person.name} (ID: {person.id})")
                    else:
                        logger.warning(f"Failed to process person from {filename}")
            
            # Final commit to ensure all changes are persisted
            await db.commit()
            logger.info("Successfully completed migration")
            
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(migrate_json_to_db()) 