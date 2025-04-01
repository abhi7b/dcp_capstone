"""
Unit tests for the schemas module.
"""
import pytest
from pydantic import ValidationError
from app.db import schemas
from datetime import datetime

def test_company_base_validation():
    """Test validation for CompanyBase schema."""
    # Test valid data
    valid_data = {
        "name": "Valid Company",
        "duke_affiliation_status": "confirmed",
        "relevance_score": 85,
        "twitter_handle": "validcompany"  # Should add @ automatically
    }
    company = schemas.CompanyBase(**valid_data)
    assert company.name == "Valid Company"
    assert company.duke_affiliation_status == "confirmed"
    assert company.relevance_score == 85
    assert company.twitter_handle == "@validcompany"  # @ was added
    
    # Test invalid affiliation status
    with pytest.raises(ValidationError):
        schemas.CompanyBase(
            name="Invalid Company",
            duke_affiliation_status="invalid_status",  # Not in allowed values
            relevance_score=50
        )
    
    # Test invalid score
    with pytest.raises(ValidationError):
        schemas.CompanyBase(
            name="Invalid Company",
            duke_affiliation_status="confirmed",
            relevance_score=101  # Above 100
        )

def test_person_base_validation():
    """Test validation for PersonBase schema."""
    # Test valid data
    valid_data = {
        "name": "Valid Person",
        "duke_affiliation_status": "confirmed", 
        "relevance_score": 75,
        "education": [{"school": "Duke University", "degree": "BS"}],
        "twitter_handle": "validperson"  # Note: This won't add @ automatically for PersonBase
    }
    person = schemas.PersonBase(**valid_data)
    assert person.name == "Valid Person"
    assert person.duke_affiliation_status == "confirmed"
    assert person.relevance_score == 75
    assert person.twitter_handle == "validperson"  # No @ added automatically
    
    # Test with all fields
    full_data = {
        "name": "Full Data Person",
        "title": "CEO",
        "duke_affiliation_status": "confirmed",
        "relevance_score": 95,
        "education": [
            {"school": "Duke University", "degree": "BS", "years": "2010-2014"},
            {"school": "Harvard", "degree": "MBA", "years": "2015-2017"}
        ],
        "current_company": "Tech Corp",
        "previous_companies": ["Old Tech", "Older Tech"],
        "twitter_handle": "@fulldata",  # This one already has @
        "linkedin_handle": "linkedin.com/in/fulldata",
        "source_links": ["https://example.com/source1", "https://example.com/source2"],
        "last_updated": datetime.utcnow()
    }
    person = schemas.PersonBase(**full_data)
    assert person.name == "Full Data Person"
    assert person.title == "CEO"
    assert len(person.education) == 2
    assert len(person.previous_companies) == 2
    assert person.twitter_handle == "@fulldata"  # @ preserved

def test_api_key_create():
    """Test APIKeyCreate schema."""
    # Test with required fields
    api_key = schemas.APIKeyCreate(name="Test Key")
    assert api_key.name == "Test Key"
    assert api_key.rate_limit == 100  # Default value
    
    # Test with all fields
    api_key = schemas.APIKeyCreate(name="Custom Rate Key", rate_limit=500)
    assert api_key.name == "Custom Rate Key"
    assert api_key.rate_limit == 500 