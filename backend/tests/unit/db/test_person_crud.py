"""
Unit tests for the person_crud module.
"""
import pytest
from app.db import schemas, person_crud
from app.db.models import Person

# Mark all tests as async
pytestmark = pytest.mark.asyncio

async def test_create_person(async_db_session):
    """Test creating a person."""
    # Create a test person using the schema
    person_data = schemas.PersonCreate(
        name="Test Person",
        title="CEO",
        duke_affiliation_status="confirmed",
        relevance_score=85,
        education=[{"school": "Duke University", "degree": "BS", "years": "2015-2019"}],
        current_company="Test Company",
        previous_companies=["Previous Company A", "Previous Company B"],
        twitter_handle="@testperson",
        linkedin_handle="linkedin.com/in/testperson",
        source_links=["https://example.com/source1", "https://example.com/source2"]
    )
    
    # Create the person in the database
    created_person = await person_crud.create_person(async_db_session, person_data)
    
    # Test that the person was created with the expected values
    assert created_person.id is not None
    assert created_person.name == "Test Person"
    assert created_person.title == "CEO"
    assert created_person.duke_affiliation_status == "confirmed"
    assert created_person.relevance_score == 85
    assert created_person.twitter_handle == "@testperson"
    assert len(created_person.previous_companies) == 2

async def test_get_person_by_name(async_db_session):
    """Test retrieving a person by name."""
    # Create a test person first
    person_data = schemas.PersonCreate(
        name="Find Me",
        title="CTO",
        duke_affiliation_status="please review",
        relevance_score=70
    )
    created_person = await person_crud.create_person(async_db_session, person_data)
    
    # Retrieve the person by name
    found_person = await person_crud.get_person_by_name(async_db_session, "Find Me")
    
    # Test that the person was found
    assert found_person is not None
    assert found_person.id == created_person.id
    assert found_person.name == "Find Me"
    assert found_person.title == "CTO"
    
    # Test retrieving non-existent person
    non_existent_person = await person_crud.get_person_by_name(async_db_session, "Not Found")
    assert non_existent_person is None

async def test_delete_person(async_db_session):
    """Test deleting a person."""
    # Create a test person first
    person_data = schemas.PersonCreate(
        name="Delete Me",
        title="CFO",
        duke_affiliation_status="no",
        relevance_score=30
    )
    created_person = await person_crud.create_person(async_db_session, person_data)
    
    # Delete the person
    result = await person_crud.delete_person(async_db_session, created_person.id)
    
    # Test that deletion was successful
    assert result is True
    
    # Verify person is gone
    person = await person_crud.get_person(async_db_session, created_person.id)
    assert person is None
    
    # Test deleting non-existent person
    result = await person_crud.delete_person(async_db_session, 999)
    assert result is False 