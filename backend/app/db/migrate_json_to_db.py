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
from ..utils.logger import get_logger
from ..utils.config import settings

logger = get_logger("migration")

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

async def process_company_data(company_data: Dict[str, Any], db: AsyncSession) -> Company:
    """Process company data and create/update company record."""
    try:
        # Check if company exists
        result = await db.execute(
            select(Company).where(Company.name == company_data["name"])
        )
        company = result.scalars().first()
        
        # Get valid model fields
        valid_fields = get_model_fields(Company)
        
        # Set default values for required fields
        if "duke_affiliation_status" not in company_data:
            company_data["duke_affiliation_status"] = "Unknown"
        
        # Preprocess JSON fields
        for field in ["investors", "twitter_summary", "source_links"]:
            if field in company_data:
                company_data[field] = preprocess_json_field(company_data[field])
        
        if company:
            # Update existing company with valid fields
            for key, value in company_data.items():
                if key in valid_fields:
                    setattr(company, key, value)
            company.updated_at = datetime.utcnow()
        else:
            # Create new company with valid fields only
            filtered_data = {k: v for k, v in company_data.items() if k in valid_fields}
            company = Company(**filtered_data)
            db.add(company)
        
        await db.commit()
        await db.refresh(company)
        return company
    except Exception as e:
        logger.error(f"Error processing company {company_data.get('name')}: {str(e)}")
        await db.rollback()
        return None

async def process_person_data(db: AsyncSession, person_data: dict) -> None:
    """Process and insert a single person's data into the database."""
    try:
        # Set required fields with defaults if missing
        if "duke_affiliation_status" not in person_data:
            person_data["duke_affiliation_status"] = "please review"
        if "relevance_score" not in person_data:
            person_data["relevance_score"] = 0

        # Preprocess all fields
        for field in ['education', 'experience', 'skills', 'interests', 'awards', 'patents', 'publications']:
            if field in person_data:
                # Special handling for education data
                if field == 'education' and isinstance(person_data[field], list):
                    # Filter out null values from each education entry
                    valid_entries = []
                    for entry in person_data[field]:
                        filtered_entry = {k: v for k, v in entry.items() if v is not None and v != "null" and v != ""}
                        if filtered_entry:
                            valid_entries.append(filtered_entry)
                    
                    if valid_entries:
                        # Convert education data to a string format
                        education_str = "; ".join([
                            ", ".join([f"{k}: {v}" for k, v in entry.items()])
                            for entry in valid_entries
                        ])
                        person_data[field] = education_str
                    else:
                        person_data[field] = None
                else:
                    person_data[field] = preprocess_json_field(person_data[field])

        # Convert list fields to strings
        if "previous_companies" in person_data and isinstance(person_data["previous_companies"], list):
            person_data["previous_companies"] = ", ".join(person_data["previous_companies"])
        if "source_links" in person_data and isinstance(person_data["source_links"], list):
            person_data["source_links"] = ", ".join(person_data["source_links"])

        # Insert person data
        query = text("""
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
            ) RETURNING id
        """)
        
        result = await db.execute(query, {
            **person_data,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        await db.commit()
        
        person_id = result.scalar()
        logger.info(f"Successfully inserted person: {person_data['name']} with ID: {person_id}")
        
    except Exception as e:
        logger.error(f"Error processing person {person_data.get('name', 'Unknown')}: {str(e)}")
        await db.rollback()
        raise

async def process_company_people(company: Company, people_data: List[Dict[str, Any]], db: AsyncSession):
    """Process people associated with a company and store them in the association table."""
    try:
        for person_data in people_data:
            # Get required fields with defaults
            name = person_data.get("name", "Unknown")
            title = person_data.get("title", "Unknown")
            duke_affiliation_status = person_data.get("duke_affiliation_status", "Unknown")
            
            # Create association with person info directly in the association table
            await db.execute(
                text("""
                INSERT INTO company_person_association 
                    (company_id, name, title, duke_affiliation_status)
                VALUES 
                    (:company_id, :name, :title, :duke_affiliation_status)
                ON CONFLICT (company_id, name) 
                DO UPDATE SET 
                    title = EXCLUDED.title,
                    duke_affiliation_status = EXCLUDED.duke_affiliation_status
                """),
                {
                    "company_id": company.id,
                    "name": name,
                    "title": title,
                    "duke_affiliation_status": duke_affiliation_status
                }
            )
        await db.commit()
    except Exception as e:
        logger.error(f"Error processing people for company {company.name}: {str(e)}")
        await db.rollback()

async def migrate_json_to_db():
    """Main migration function to process all JSON files."""
    # Process company data from json_inputs
    json_dir = settings.JSON_INPUTS_DIR
    if not os.path.exists(json_dir):
        logger.error(f"JSON inputs directory not found: {json_dir}")
        return
    
    async with async_session() as db:
        # Process all JSON files
        for filename in os.listdir(json_dir):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(json_dir, filename)
            data = await load_json_file(file_path)
            if not data:
                continue
            
            logger.info(f"Processing {filename}")
            
            if filename.startswith('company_'):
                # Process company data
                company = await process_company_data(data, db)
                if company:
                    # Look for people data in processed directory
                    processed_dir = settings.PROCESSED_DATA_DIR
                    people_file = f"company_{company.name.lower().replace(' ', '_')}_people.json"
                    people_file_path = os.path.join(processed_dir, people_file)
                    
                    if os.path.exists(people_file_path):
                        people_data = await load_json_file(people_file_path)
                        if people_data and "people" in people_data:
                            await process_company_people(company, people_data["people"], db)
                            logger.info(f"Processed {len(people_data['people'])} people for {company.name}")
            elif filename.startswith('person_'):
                # Process standalone person data
                await process_person_data(db, data)

if __name__ == "__main__":
    asyncio.run(migrate_json_to_db()) 