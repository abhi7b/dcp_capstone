"""
Unit tests for the crud module.
"""
import pytest
from app.db import schemas, crud, models
import uuid

# Mark all tests as async
pytestmark = pytest.mark.asyncio

async def test_create_company(async_db_session):
    """Test creating a company."""
    # Create a test company using the schema
    company_data = schemas.CompanyCreate(
        name="Test Company",
        duke_affiliation_status="confirmed",
        relevance_score=90,
        summary="A test company for the unit tests",
        investors=["Investor A", "Investor B"],
        funding_stage="Series A",
        industry="Technology",
        founded="2022",
        location="Durham, NC",
        twitter_handle="@testcompany",
        linkedin_handle="linkedin.com/company/testcompany",
        source_links=["https://example.com/source1"]
    )
    
    # Create the company in the database
    created_company = await crud.create_company(async_db_session, company_data)
    
    # Test that the company was created with the expected values
    assert created_company.id is not None
    assert created_company.name == "Test Company"
    assert created_company.duke_affiliation_status == "confirmed"
    assert created_company.relevance_score == 90
    assert created_company.industry == "Technology"
    assert created_company.twitter_handle == "@testcompany"
    assert len(created_company.investors) == 2

async def test_get_company_by_name(async_db_session):
    """Test retrieving a company by name."""
    # Create a test company first
    company_data = schemas.CompanyCreate(
        name="Find This Company",
        duke_affiliation_status="please review",
        relevance_score=80
    )
    created_company = await crud.create_company(async_db_session, company_data)
    
    # Retrieve the company by name
    found_company = await crud.get_company_by_name(async_db_session, "Find This Company")
    
    # Test that the company was found
    assert found_company is not None
    assert found_company.id == created_company.id
    assert found_company.name == "Find This Company"
    
    # Test retrieving non-existent company
    non_existent_company = await crud.get_company_by_name(async_db_session, "Not Found")
    assert non_existent_company is None

async def test_update_company(async_db_session):
    """Test updating a company."""
    # Create a test company first
    company_data = schemas.CompanyCreate(
        name="Update Me",
        duke_affiliation_status="please review",
        relevance_score=75,
        industry="Fintech"
    )
    created_company = await crud.create_company(async_db_session, company_data)
    
    # Update company data
    update_data = schemas.CompanyUpdate(
        duke_affiliation_status="confirmed",
        relevance_score=95,
        industry="AI Fintech",
        summary="Updated company description"
    )
    
    # Update the company
    updated_company = await crud.update_company(async_db_session, created_company.id, update_data)
    
    # Test that update was successful
    assert updated_company is not None
    assert updated_company.id == created_company.id
    assert updated_company.name == "Update Me"  # Name stays the same
    assert updated_company.duke_affiliation_status == "confirmed"  # Updated
    assert updated_company.relevance_score == 95  # Updated
    assert updated_company.industry == "AI Fintech"  # Updated
    assert updated_company.summary == "Updated company description"  # New field added

async def test_create_api_key(async_db_session):
    """Test creating an API key."""
    # Create a test API key using the schema
    api_key_data = schemas.APIKeyCreate(
        name="Test API Key",
        rate_limit=100
    )
    
    # Create the API key in the database
    created_api_key = await crud.create_api_key(async_db_session, api_key_data)
    
    # Test that the API key was created with the expected values
    assert created_api_key.id is not None
    assert created_api_key.name == "Test API Key"
    assert created_api_key.rate_limit == 100
    assert created_api_key.is_active is True
    assert len(created_api_key.key) > 0  # A key was generated

async def test_deactivate_api_key(async_db_session):
    """Test deactivating an API key."""
    # Create a test API key first with a fixed key value for testing
    api_key = models.APIKey(
        key=str(uuid.uuid4()),
        name="Deactivate Me",
        is_active=True,
        rate_limit=50
    )
    async_db_session.add(api_key)
    await async_db_session.commit()
    await async_db_session.refresh(api_key)
    
    # Deactivate the API key
    result = await crud.deactivate_api_key(async_db_session, api_key.key)
    
    # Test that deactivation was successful
    assert result is True
    
    # Verify API key is deactivated
    deactivated_key = await crud.get_api_key(async_db_session, api_key.key)
    assert deactivated_key is not None
    assert deactivated_key.is_active is False 