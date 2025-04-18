"""
Migration script to load JSON data from json_inputs directory into the database.
This script handles both company and person data, maintaining relationships.
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from .session import async_session
from .models import Company, Person
from ..utils.logger import db_logger as logger
from ..utils.config import settings
from . import person_crud # Import person_crud for lookup
# Import the formatters
from .formatting_utils import format_education, format_previous_companies, format_source_links

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

async def process_person_data(db: AsyncSession, person_data: dict, current_company_name: Optional[str] = None) -> Optional[Person]:
    """
    Process person data from JSON and insert or update into database.
    Formats complex fields into simplified strings using utility functions.
    Ensures that existing data is not overwritten with None when updating via company processing.
    
    Args:
        db: Database session
        person_data: Dictionary containing person data
        current_company_name: Optional name of the current company (used when called from company processing)
        
    Returns:
        Created or updated Person model if successful, None otherwise
    """
    try:
        person_name = person_data["name"]
        
        # Check if person already exists
        result = await db.execute(select(Person).where(Person.name == person_name))
        existing_person = result.scalars().first()

        # Prepare base values from incoming data
        person_values = {
            "name": person_name,
            "title": person_data.get("title"),
            "duke_affiliation_status": person_data.get("duke_affiliation_status", "no"),
            "relevance_score": person_data.get("relevance_score", 0),
            "current_company": current_company_name if current_company_name else person_data.get("current_company"),
            "twitter_handle": person_data.get("twitter_handle"),
            "linkedin_handle": person_data.get("linkedin_handle"),
            "twitter_summary": person_data.get("twitter_summary"),
            "updated_at": datetime.utcnow()
        }

        # Format complex fields using imported functions
        # Handle education as a list of dictionaries
        if "education" in person_data and isinstance(person_data["education"], list):
            person_values["education"] = format_education(person_data["education"])
        
        # Handle previous_companies as a list
        if "previous_companies" in person_data and isinstance(person_data["previous_companies"], list):
            person_values["previous_companies"] = format_previous_companies(person_data["previous_companies"])
        
        # Handle source_links as a list of dictionaries
        if "source_links" in person_data and isinstance(person_data["source_links"], list):
            person_values["source_links"] = format_source_links(person_data["source_links"])
        
        if existing_person:
            # Update: Merge incoming data with existing, prioritizing incoming non-None values
            logger.info(f"Person {person_name} exists. Merging data.")
            update_data = {}
            allowed_fields = get_model_fields(Person) 
            
            for key in allowed_fields:
                if key == 'created_at': # Don't overwrite created_at
                    update_data[key] = existing_person.created_at
                    continue
                if key == 'id': # Don't try to update id
                    continue 
                    
                incoming_value = person_values.get(key)
                if incoming_value is not None:
                    update_data[key] = incoming_value
                else:
                    update_data[key] = getattr(existing_person, key, None)
            
            # Execute update
            set_clauses = ", ".join([f"{key} = :{key}" for key in update_data if key not in ['name', 'id']])
            update_query = text(f"""
                    UPDATE persons SET {set_clauses}
                    WHERE name = :name
                """)
            await db.execute(update_query, {**update_data, "name": person_name})
            person_id = existing_person.id
            logger.info(f"Successfully updated person: {person_name} with ID: {person_id}")

        else:
            # Insert: Use prepared values, set created_at
            logger.info(f"Person {person_name} does not exist. Inserting new record.")
            person_values["created_at"] = datetime.utcnow()
            
            insert_data = {k: v for k, v in person_values.items() if v is not None}
            columns = ", ".join(insert_data.keys())
            placeholders = ", ".join([f":{key}" for key in insert_data.keys()])
            
            insert_query = text(f"""
                INSERT INTO persons ({columns})
                VALUES ({placeholders})
                RETURNING id
            """)
            result = await db.execute(insert_query, insert_data)
            person_id = result.scalar_one()
            logger.info(f"Successfully inserted person: {person_name} with ID: {person_id}")

        await db.commit()
        
        person = await db.get(Person, person_id)
        return person
        
    except Exception as e:
        logger.error(f"Error processing person data for {person_data.get('name', '?')}: {str(e)}")
        await db.rollback()
        raise

async def process_company_people(company: Company, people_data: list, db: AsyncSession) -> None:
    """
    Process company-people relationships using names from company data.
    Loads complete person data from JSON files when creating/updating person records.
    
    Args:
        company: Company object
        people_data: List of person data dictionaries (containing at least 'name')
        db: Database session
    """
    try:
        logger.info(f"Processing associations for {len(people_data)} people listed under company: {company.name} (ID: {company.id})")
        
        # First, clear any existing associations for this company to ensure clean state
        await db.execute(
            text("""
                DELETE FROM company_person_association 
                WHERE company_id = :company_id
            """),
            {"company_id": company.id}
        )
        await db.commit()
        logger.info(f"Cleared existing associations for company {company.name}")
        
        associations_created = 0
        for person_info in people_data:
            person_name = person_info.get('name')
            if not person_name:
                logger.warning(f"Skipping person entry with no name in company {company.name}")
                continue

            logger.info(f"Processing person: {person_name} for company {company.name}")
            
            # Construct the person JSON file path
            person_filename = f"person_{person_name.replace(' ', '_')}.json"
            person_file_path = os.path.join(settings.JSON_INPUTS_DIR, person_filename)
            
            # Load the complete person data from their JSON file
            person_data = await load_json_file(person_file_path)
            if not person_data:
                logger.warning(f"Could not load person data from {person_filename}. Skipping.")
                continue
                
            logger.info(f"Loaded complete person data for {person_name}")
            
            # Process the person with their complete data
            person = await process_person_data(db, person_data, current_company_name=company.name)
            
            if person:
                logger.info(f"Successfully processed person: {person.name} (ID: {person.id})")
                
                # Create association
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
                
                # Verify the association was created or already existed
                association = result.first()
                if association:
                    logger.info(f"Created association between {company.name} (ID: {company.id}) and {person.name} (ID: {person.id})")
                    associations_created += 1
                else:
                    logger.info(f"Association already exists between {company.name} (ID: {company.id}) and {person.name} (ID: {person.id})")
                    associations_created += 1
                
                # Commit after each successful association attempt
                await db.commit()
                logger.info(f"Committed association attempt for {person.name}")
                
            else:
                logger.warning(f"Failed to process person data for {person_name}. Skipping association.")
        
        # Final commit (optional, as commits happen per person, but good for safety)
        await db.commit()
        logger.info(f"Finished processing associations for {company.name}")
        
        # Verify the final count of associations
        result = await db.execute(
            text("""
                SELECT COUNT(*) 
                FROM company_person_association 
                WHERE company_id = :company_id
            """),
            {"company_id": company.id}
        )
        count = result.scalar_one()
        logger.info(f"Verified {count} associations exist for {company.name}. Process created/found {associations_created} associations.")
        if count != associations_created:
             logger.warning(f"Mismatch in expected ({associations_created}) and actual ({count}) association count for company {company.name}.")
        
    except Exception as e:
        logger.error(f"Error processing company people associations for {company.name}: {str(e)}")
        await db.rollback()
        raise

async def migrate_json_to_db():
    """Main migration function to process specific JSON files."""
    # Process company data from json_inputs
    json_dir = settings.JSON_INPUTS_DIR
    
    logger.info(f"Starting migration from JSON directory: {json_dir}")
    
    if not os.path.exists(json_dir):
        logger.error(f"JSON inputs directory not found: {json_dir}")
        return
    
    # List of specific files to process
    files_to_process = [
        "person_Derek_Carlson.json",
        "person_Devon_Spinnler.json",
        "person_Steven_Galanis.json",
        "person_Dario_Amodei.json",
        "company_Cameo.json"
    ]
    
    async with async_session() as db:
        try:
            # Process only the specified JSON files
            for filename in files_to_process:
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
                else:
                    # Process person data
                    logger.info(f"Processing person data from {filename}")
                    person = await process_person_data(db, data)
                    if person:
                        logger.info(f"Successfully processed person: {person.name} (ID: {person.id})")
            
            logger.info("Migration completed successfully")
            
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(migrate_json_to_db()) 