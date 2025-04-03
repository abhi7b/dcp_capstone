"""
Unit tests for database CRUD operations.
"""
import pytest
from datetime import datetime
from typing import Dict, Any
from app.db.crud import (
    create_company,
    get_company,
    update_company,
    delete_company
)
from app.db.person_crud import (
    create_person,
    get_person,
    update_person,
    delete_person
)
from app.db.schemas import CompanyCreate, CompanyUpdate, PersonCreate, PersonUpdate
from app.db.models import Company, Person

@pytest.fixture
def test_company_data(test_company_data):
    """Return test company data."""
    return test_company_data

@pytest.fixture
def test_person_data(test_person_data):
    """Return test person data."""
    return test_person_data

@pytest.mark.asyncio
async def test_create_company(db, test_company_data):
    """Test creating a new company."""
    company = await create_company(db, CompanyCreate(**test_company_data))
    assert company.name == test_company_data["name"]
    assert company.industry == test_company_data["industry"]
    assert company.funding_stage == test_company_data["funding_stage"]
    assert company.duke_affiliation_status == test_company_data["duke_affiliation_status"]
    assert company.twitter_handle == test_company_data["twitter_handle"]
    assert company.linkedin_handle == test_company_data["linkedin_handle"]
    assert company.created_at is not None
    assert company.updated_at is not None

@pytest.mark.asyncio
async def test_get_company(db, test_company_data):
    """Test retrieving a company."""
    # Create company first
    company = await create_company(db, CompanyCreate(**test_company_data))
    
    # Retrieve company
    retrieved = await get_company(db, company.id)
    assert retrieved is not None
    assert retrieved.name == company.name
    assert retrieved.industry == company.industry
    assert retrieved.funding_stage == company.funding_stage
    assert retrieved.duke_affiliation_status == company.duke_affiliation_status
    assert retrieved.twitter_handle == company.twitter_handle
    assert retrieved.linkedin_handle == company.linkedin_handle

@pytest.mark.asyncio
async def test_delete_company(db, test_company_data):
    """Test deleting a company."""
    # Create company first
    company = await create_company(db, CompanyCreate(**test_company_data))
    
    # Delete company
    await delete_company(db, company.id)
    
    # Verify company is deleted
    deleted = await get_company(db, company.id)
    assert deleted is None

@pytest.mark.asyncio
async def test_create_person(db, test_person_data):
    """Test creating a new person."""
    person = await create_person(db, PersonCreate(**test_person_data))
    assert person.name == test_person_data["name"]
    assert person.title == test_person_data["title"]
    assert person.current_company == test_person_data["current_company"]
    assert person.duke_affiliation_status == test_person_data["duke_affiliation_status"]
    assert person.twitter_handle == test_person_data["twitter_handle"]
    assert person.linkedin_handle == test_person_data["linkedin_handle"]
    assert person.created_at is not None
    assert person.updated_at is not None

@pytest.mark.asyncio
async def test_get_person(db, test_person_data):
    """Test retrieving a person."""
    # Create person first
    person = await create_person(db, PersonCreate(**test_person_data))
    
    # Retrieve person
    retrieved = await get_person(db, person.id)
    assert retrieved is not None
    assert retrieved.name == person.name
    assert retrieved.title == person.title
    assert retrieved.current_company == person.current_company
    assert retrieved.duke_affiliation_status == person.duke_affiliation_status
    assert retrieved.twitter_handle == person.twitter_handle
    assert retrieved.linkedin_handle == person.linkedin_handle

@pytest.mark.asyncio
async def test_delete_person(db, test_person_data):
    """Test deleting a person."""
    # Create person first
    person = await create_person(db, PersonCreate(**test_person_data))
    
    # Delete person
    await delete_person(db, person.id)
    
    # Verify person is deleted
    deleted = await get_person(db, person.id)
    assert deleted is None 