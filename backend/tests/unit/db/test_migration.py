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
from app.db.models import Company, Person
from app.utils.config import settings

@pytest.mark.asyncio
async def test_load_json_file():
    """Test loading JSON files."""
    # Test loading a valid file
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_OpenAI_final.json")
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
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_OpenAI_final.json")
    company_data = await load_json_file(file_path)
    assert company_data is not None
    
    # Process company
    company = await process_company_data(company_data, db)
    assert company is not None
    assert company.name == "OpenAI"
    assert company.duke_affiliation_status == "confirmed"  # Using real data value
    
    # Test updating existing company
    company_data["summary"] = "Updated summary"
    updated_company = await process_company_data(company_data, db)
    assert updated_company is not None
    assert updated_company.summary == "Updated summary"

@pytest.mark.asyncio
async def test_process_person_data(db: AsyncSession):
    """Test processing person data."""
    # Load Sam Altman's data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "person_Samuel_H_Altman.json")
    person_data = await load_json_file(file_path)
    assert person_data is not None
    
    # Process person
    person = await process_person_data(person_data, db)
    assert person is not None
    assert person.name == "Samuel H. Altman"
    assert person.title == "CEO"
    assert person.current_company == "OpenAI"
    
    # Test updating existing person
    person_data["title"] = "Chief Executive Officer"
    updated_person = await process_person_data(person_data, db)
    assert updated_person is not None
    assert updated_person.title == "Chief Executive Officer"

@pytest.mark.asyncio
async def test_process_company_people(db: AsyncSession):
    """Test processing company people and relationships."""
    # Load OpenAI company data
    file_path = os.path.join(settings.JSON_INPUTS_DIR, "company_OpenAI_final.json")
    company_data = await load_json_file(file_path)
    assert company_data is not None
    
    # Process company first
    company = await process_company_data(company_data, db)
    assert company is not None
    
    # Process people
    await process_company_people(company, company_data["people"], db)
    
    # Verify relationships
    result = await db.execute(
        select(Person).join(Company.people).where(Company.id == company.id)
    )
    people = result.scalars().all()
    assert len(people) > 0
    assert any(p.name == "Sam Altman" for p in people)
    assert any(p.name == "Greg Brockman" for p in people)

@pytest.mark.asyncio
async def test_full_migration(db: AsyncSession):
    """Test the complete migration process."""
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