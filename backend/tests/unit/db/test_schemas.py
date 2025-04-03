"""
Unit tests for the schemas module.
"""
import pytest
from pydantic import ValidationError
from app.db import schemas
from datetime import datetime

def test_company_base_validation():
    """Test validation of CompanyBase schema."""
    # Valid data
    valid_data = {
        "name": "Test Company",
        "duke_affiliation_status": "confirmed",
        "relevance_score": 75,
        "summary": "A test company",
        "investors": "Investor A, Investor B",
        "funding_stage": "Series A",
        "industry": "Technology",
        "founded": "2020-01-01",
        "location": "Durham, NC",
        "twitter_handle": "@testcompany",
        "linkedin_handle": "test-company",
        "twitter_summary": "Test company's Twitter activity",
        "source_links": "https://test.com, https://test2.com"
    }
    company = schemas.CompanyBase(**valid_data)
    assert company.name == valid_data["name"]
    assert company.duke_affiliation_status == valid_data["duke_affiliation_status"]
    assert company.relevance_score == valid_data["relevance_score"]

    # Invalid data
    invalid_data = valid_data.copy()
    invalid_data["duke_affiliation_status"] = "invalid_status"
    with pytest.raises(ValidationError):
        schemas.CompanyBase(**invalid_data)

def test_person_base_validation():
    """Test validation of PersonBase schema."""
    # Valid data
    valid_data = {
        "name": "Test Person",
        "title": "CEO",
        "duke_affiliation_status": "confirmed",
        "relevance_score": 85,
        "education": "Duke University, MIT",
        "current_company": "Test Company",
        "previous_companies": "Previous Company A, Previous Company B",
        "twitter_handle": "@testperson",
        "linkedin_handle": "test-person",
        "twitter_summary": "Test person's Twitter activity",
        "source_links": "https://test.com/person, https://test2.com/person"
    }
    person = schemas.PersonBase(**valid_data)
    assert person.name == valid_data["name"]
    assert person.duke_affiliation_status == valid_data["duke_affiliation_status"]
    assert person.relevance_score == valid_data["relevance_score"]

    # Invalid data
    invalid_data = valid_data.copy()
    invalid_data["duke_affiliation_status"] = "invalid_status"
    with pytest.raises(ValidationError):
        schemas.PersonBase(**invalid_data)

def test_api_key_create():
    """Test validation of APIKeyCreate schema."""
    # Valid data with default rate limit
    api_key = schemas.APIKeyCreate()
    assert api_key.rate_limit == 100

    # Valid data with custom rate limit
    api_key = schemas.APIKeyCreate(rate_limit=200)
    assert api_key.rate_limit == 200

    # Valid data with name
    api_key = schemas.APIKeyCreate(name="Test Key")
    assert api_key.name == "Test Key" 