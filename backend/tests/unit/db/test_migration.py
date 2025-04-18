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
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_Anthropic.json")
    data = await load_json_file(file_path)
    assert data is not None
    assert "name" in data
    assert data["name"] == "Anthropic"
    
    # Test loading a non-existent file
    data = await load_json_file("nonexistent.json")
    assert data is None

@pytest.mark.asyncio
async def test_process_company_data(db: AsyncSession):
    """Test processing company data."""
    # Load Anthropic company data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_Anthropic.json")
    company_data = await load_json_file(file_path)
    assert company_data is not None
    
    try:
        # Process company
        company = await process_company_data(company_data, db)
        assert company is not None
        assert company.name == "Anthropic"
        assert company.duke_affiliation_status == "confirmed"
        assert company.relevance_score == 78
        assert "Lightspeed Venture Partners" in company.investors
        assert "Salesforce Ventures" in company.investors
        assert "Amazon" in company.investors
        assert "Google" in company.investors
        assert company.funding_stage == "Series E"
        assert company.industry == "Artificial Intelligence"
        assert company.founded == "2021"
        assert company.linkedin_handle == "anthropicresearch"
        assert "https://www.anthropic.com/company" in company.source_links
        assert "https://en.wikipedia.org/wiki/Anthropic" in company.source_links
        
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
    # Load Dario Amodei's data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "person_Dario_Amodei.json")
    person_data = await load_json_file(file_path)
    assert person_data is not None
    
    try:
        # Process person
        person = await process_person_data(db, person_data)
        assert person is not None
        assert person.name == "Dario Amodei"
        assert person.title == "CEO"
        assert person.current_company == "Anthropic"
        
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
    # Load Anthropic company data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_Anthropic.json")
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
        assert len(people) == 5  # Anthropic has 5 people
        
        # Verify each person exists and has correct title
        person_titles = {p.name: p.title for p in people}
        assert person_titles["Dario Amodei"] == "CEO"
        assert person_titles["Daniela Amodei"] == "President/Co-Founder"
        assert person_titles["Jack Clark"] == "Policy Director"
        assert person_titles["Tom Brown"] == "Partner"
        assert person_titles["Jason Clinton"] == "Chief Information Security Officer"
        
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
        
        # Verify Anthropic relationships with eager loading
        result = await db.execute(
            select(Company)
            .options(selectinload(Company.people))
            .where(Company.name == "Anthropic")
        )
        anthropic = result.scalars().first()
        assert anthropic is not None
        assert len(anthropic.people) == 5  # Anthropic has 5 people
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise 