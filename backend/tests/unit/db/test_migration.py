"""Tests for the JSON to database migration script."""
import os
import json
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.migrate_json_to_db import (
    load_json_file,
    process_company_data,
    process_person_data,
    process_company_people,
    migrate_json_to_db
)
from app.db.models import Company, Person, company_person_association
from app.utils.config import settings

@pytest.mark.asyncio
async def test_load_json_file():
    """Test loading JSON files."""
    # Test loading a valid file
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_OpenAI.json")
    data = await load_json_file(file_path)
    assert data is not None
    assert "name" in data
    assert data["name"] == "OpenAI"
    
    # Test loading a non-existent file
    data = await load_json_file("nonexistent.json")
    assert data is None

@pytest.mark.asyncio
async def test_process_company_data(db: AsyncSession):
    """Test processing company data."""
    # Load OpenAI company data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_OpenAI.json")
    company_data = await load_json_file(file_path)
    assert company_data is not None
    
    try:
        # Process company
        company = await process_company_data(company_data, db)
        assert company is not None
        assert company.name == "OpenAI"
        assert company.duke_affiliation_status == "confirmed"
        assert company.relevance_score == 95
        assert "SoftBank" in company.investors
        assert "Goldman Sachs" in company.investors
        assert "Morgan Stanley" in company.investors
        assert company.funding_stage == "Series A"
        assert company.industry == "Artificial Intelligence"
        assert company.founded == "2015"
        assert company.location == "San Francisco, California"
        assert company.twitter_handle == "openai"
        assert company.linkedin_handle == "openai"
     
        
        # Test updating existing company
        company_data["summary"] = "Updated summary"
        updated_company = await process_company_data(company_data, db)
        assert updated_company is not None
        assert updated_company.summary == "Updated summary"
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise

@pytest.mark.asyncio
async def test_process_person_data(db: AsyncSession):
    """Test processing person data."""
    # Load Sam Altman's data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "person_Sam_Altman.json")
    person_data = await load_json_file(file_path)
    assert person_data is not None
    
    try:
        # Process person
        person = await process_person_data(db, person_data)
        assert person is not None
        assert person.name == "Sam Altman"
        assert person.title == "CEO & Co-Founder"
        assert person.current_company == "OpenAI"
        assert person.duke_affiliation_status == "confirmed"
        assert person.relevance_score == 89
        assert "School: John Burroughs School" in person.education
        assert "School: Stanford University; Field: Computer Science" in person.education
        assert "School: Duke University; Degree: Bachelor's" in person.education
        assert "Y Combinator (President)" in person.previous_companies
        assert "Loopt (CEO)" in person.previous_companies
        assert person.twitter_handle == "sama"
        assert person.linkedin_handle == "https://www.linkedin.com/in/samaltman"
        assert "OpenAI has made several significant updates" in person.twitter_summary
        assert "https://www.forbes.com" in person.source_links
        assert "https://en.wikipedia.org" in person.source_links
        
        # Test updating existing person
        person_data["title"] = "Chief Executive Officer"
        updated_person = await process_person_data(db, person_data)
        assert updated_person is not None
        assert updated_person.title == "Chief Executive Officer"
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise

@pytest.mark.asyncio
async def test_process_company_people(db: AsyncSession):
    """Test processing company people and relationships."""
    # Load OpenAI company data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_OpenAI.json")
    company_data = await load_json_file(file_path)
    assert company_data is not None
    
    try:
        # Process company first
        company = await process_company_data(company_data, db)
        assert company is not None
        
        # Process people
        await process_company_people(company, company_data["people"], db)
        
        # Verify relationships
        result = await db.execute(
            text("""
                SELECT p.name, p.title 
                FROM persons p
                JOIN company_person_association cpa ON p.id = cpa.person_id
                WHERE cpa.company_id = :company_id
            """),
            {"company_id": company.id}
        )
        people = result.all()
        assert len(people) > 0
        
        # Verify each person exists and has correct title
        person_titles = {p.name: p.title for p in people}
        assert person_titles["Sam Altman"] == "CEO & Co-Founder"
        assert person_titles["Greg Brockman"] == "President & Co-Founder"
        assert person_titles["Ilya Sutskever"] == "Chief Scientist"
        assert person_titles["Julia Villagra"] == "Chief People Officer"
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise

@pytest.mark.asyncio
async def test_full_migration(db: AsyncSession):
    """Test the complete migration process."""
    try:
        # Run the migration
        await migrate_json_to_db()
        
        # Verify companies were migrated
        result = await db.execute(select(Company))
        companies = result.scalars().all()
        assert len(companies) > 0
        
        # Verify people were migrated
        result = await db.execute(select(Person))
        people = result.scalars().all()
        assert len(people) > 0
        
        # Verify OpenAI relationships with eager loading
        result = await db.execute(
            select(Company)
            .options(selectinload(Company.people))
            .where(Company.name == "OpenAI")
        )
        openai = result.scalars().first()
        assert openai is not None
        assert len(openai.people) > 0
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise 