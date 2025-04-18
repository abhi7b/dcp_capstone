"""
Database Schemas Module

This module defines Pydantic models for request/response validation and serialization.
Includes schemas for Person and Company entities with their relationships.

Key Features:
- Input validation
- Response serialization
- Nested relationship handling
- Optional and required field definitions
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import re
import json

# Base schemas
class EducationBase(BaseModel):
    """Schema representing educational background information."""
    school: str
    degree: Optional[str] = None
    years: Optional[str] = None

class EducationCreate(EducationBase):
    """Schema for creating a new education record."""
    pass

class ExecutiveBase(BaseModel):
    """Schema representing basic information about company executives."""
    name: str
    duke_affiliated: bool = False
    role: Optional[str] = None
    linkedin_handle: Optional[str] = None

class CurrentCompanyBase(BaseModel):
    """Schema representing a founder's current company information."""
    name: str
    role: Optional[str] = None
    funding_stage: Optional[str] = None

class TwitterSummaryBase(BaseModel):
    """Schema representing a summary of Twitter activity."""
    tweets_analyzed: Optional[int] = None
    mentions_funding: Optional[bool] = None
    engagement_score: Optional[int] = None
    status: str = "available"  # "available" or "unavailable"

# Define a minimal schema for people associated with companies
class CompanyPersonAssociation(BaseModel):
    """Schema representing a person associated with a company.
    Matches the structure used in the source JSON files.
    """
    name: str
    title: Optional[str] = None

# Company schemas
class CompanyBase(BaseModel):
    """Base schema for company data."""
    name: str
    duke_affiliation_status: str
    relevance_score: Optional[int] = None
    summary: Optional[str] = None
    investors: Optional[str] = Field(None, description="Comma-separated list of investors")
    funding_stage: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[str] = None
    location: Optional[str] = None
    twitter_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_summary: Optional[str] = Field(None, description="Summary of Twitter activity")
    source_links: Optional[str] = Field(None, description="Comma-separated list of source URLs")

    @validator('duke_affiliation_status')
    def validate_affiliation_status(cls, v):
        """Validate that affiliation status is one of the allowed values."""
        valid_statuses = ["confirmed", "please review", "no"]
        if v not in valid_statuses:
            raise ValueError(f"duke_affiliation_status must be one of {valid_statuses}")
        return v

    @validator('relevance_score')
    def validate_score(cls, v):
        """Validate that score is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Score must be between 0 and 100')
        return v

    @validator('twitter_handle')
    def validate_twitter_handle(cls, v):
        """Ensure Twitter handle starts with @ and has valid format."""
        if not v:
            return v
            
        # Add @ if missing
        if not v.startswith('@'):
            v = f'@{v}'
            
        # Basic format validation (alphanumeric and underscores)
        pattern = r'^@[A-Za-z0-9_]{1,15}$'
        if not re.match(pattern, v):
            raise ValueError('Twitter handle must be 1-15 alphanumeric characters or underscores after @')
            
        return v

class PersonBase(BaseModel):
    """Base schema for person data."""
    name: str
    title: Optional[str] = None
    duke_affiliation_status: str
    relevance_score: int
    education: Optional[str] = Field(None, description="Comma-separated list of educational institutions")
    current_company: Optional[str] = None
    previous_companies: Optional[str] = Field(None, description="Comma-separated list of previous companies")
    twitter_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_summary: Optional[str] = Field(None, description="Summary of Twitter activity")
    source_links: Optional[str] = Field(None, description="Comma-separated list of source URLs")

    @validator('duke_affiliation_status')
    def validate_affiliation_status(cls, v):
        """Validate that affiliation status is one of the allowed values."""
        valid_statuses = ["confirmed", "please review", "no"]
        if v not in valid_statuses:
            raise ValueError(f"duke_affiliation_status must be one of {valid_statuses}")
        return v

    @validator('relevance_score')
    def validate_score(cls, v):
        """Validate that score is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Score must be between 0 and 100')
        return v

    class Config:
        from_attributes = True
        # use_enum_values = True # If using Enums for status

class PersonCreate(PersonBase):
    """Schema for creating a new person. Inherits all fields from PersonBase."""
    # company_associations: Optional[List['CompanyPersonAssociationCreate']] = [] # Handled via company create/update
    pass

class PersonInDB(PersonBase):
    """Schema representing a person as stored in the database."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PersonResponse(PersonInDB):
    """Schema for person API responses with formatted timestamps."""
    last_updated: str

    @root_validator(pre=True)
    def set_last_updated(cls, values):
        from datetime import datetime
        if isinstance(values, dict):
            values["last_updated"] = datetime.now().isoformat()
        return values

# Define PersonUpdate schema
class PersonUpdate(BaseModel):
    """Schema for updating an existing person. All fields are optional."""
    name: Optional[str] = None
    title: Optional[str] = None
    duke_affiliation_status: Optional[str] = None
    relevance_score: Optional[int] = None
    education: Optional[Union[str, List[Dict[str, str]]]] = None
    current_company: Optional[str] = None
    previous_companies: Optional[Union[str, List[str]]] = None
    twitter_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_summary: Optional[str] = None
    source_links: Optional[Union[str, List[str]]] = None

    @validator('education', 'previous_companies', 'source_links', pre=True)
    def convert_to_json_string(cls, v):
        """Convert list/dict fields to JSON strings if needed."""
        if v is None:
            return None
        if isinstance(v, (list, dict)):
            return json.dumps(v)
        return v

# Define a minimal schema for people within company responses
class PersonBasicInfo(BaseModel):
    """Schema representing minimal person info within a company response."""
    name: str
    duke_affiliation_status: str  # Using a field that exists in the Person model

    class Config:
        from_attributes = True

class CompanyCreate(CompanyBase):
    """Schema for creating a new company record."""
    people: Optional[List[CompanyPersonAssociation]] = None

class CompanyUpdate(CompanyBase):
    """Schema for updating an existing company record."""
    name: Optional[str] = None
    duke_affiliation_status: Optional[str] = None
    relevance_score: Optional[int] = None
    summary: Optional[str] = None
    investors: Optional[str] = None
    funding_stage: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[str] = None
    location: Optional[str] = None
    twitter_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_summary: Optional[str] = None
    source_links: Optional[str] = None
    people: Optional[List[CompanyPersonAssociation]] = None

class CompanyInDB(CompanyBase):
    """Schema representing a company as stored in the database."""
    id: int
    people: Optional[List[CompanyPersonAssociation]] = None

    class Config:
        from_attributes = True

class CompanyResponse(CompanyBase):
    """Schema for company API responses with formatted timestamps."""
    id: int
    people: Optional[List[CompanyPersonAssociation]] = None
    last_updated: Optional[str] = None

    @root_validator(pre=True)
    def set_last_updated(cls, values):
        updated_at = values.get('updated_at') if isinstance(values, dict) else getattr(values, 'updated_at', None)
        created_at = values.get('created_at') if isinstance(values, dict) else getattr(values, 'created_at', None)
        
        if updated_at:
            last = updated_at
        elif created_at:
            last = created_at
        else:
            last = datetime.utcnow()
            
        if not isinstance(values, dict):
            orm_values = {k: getattr(values, k) for k in values.__dict__ if not k.startswith('_')}
            values = orm_values
            
        values["last_updated"] = last.isoformat()
        return values

    class Config:
        from_attributes = True

# API Key schemas
class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    name: Optional[str] = None
    rate_limit: int = 100  # Requests per minute

class APIKeyResponse(BaseModel):
    """Schema for API key responses."""
    key: str
    name: Optional[str] = None
    is_active: bool
    rate_limit: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Error response schemas
class ErrorResponse(BaseModel):
    """Schema for API error responses."""
    detail: str

# Token schemas
class Token(BaseModel):
    """Schema for authentication tokens."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for decoded token data."""
    api_key: Optional[str] = None

# Simple response schema for messages
class Message(BaseModel):
    """Schema for API response messages."""
    message: str

# Need to update forward refs after all models are defined
CompanyResponse.update_forward_refs()
PersonResponse.update_forward_refs()
