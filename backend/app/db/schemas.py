"""
Pydantic schemas for API request and response validation.

This module defines schemas that are used for:
1. Validating incoming request data
2. Defining the structure of API responses
3. Converting between database models and API interfaces
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import re

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

# Company schemas
class CompanyBase(BaseModel):
    """
    Base schema for company data.
    
    Contains fields common to all company-related schemas.
    """
    name: str
    duke_affiliation_status: Optional[str] = "please review"
    duke_affiliation_score: Optional[int] = None
    relevance_score: Optional[int] = None
    summary: Optional[str] = None
    investors: Optional[List[str]] = None
    funding_stage: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[str] = None
    location: Optional[str] = None
    twitter_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_summary: Optional[TwitterSummaryBase] = None
    source_links: Optional[List[str]] = None

    @validator('duke_affiliation_status')
    def validate_affiliation_status(cls, v):
        """Validate that affiliation status is one of the allowed values."""
        valid_statuses = ["confirmed", "please review", "no"]
        if v not in valid_statuses:
            raise ValueError(f"duke_affiliation_status must be one of {valid_statuses}")
        return v

    @validator('duke_affiliation_score', 'relevance_score')
    def validate_score(cls, v):
        """Validate that score is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Score must be between 0 and 100')
        return v

    @validator('twitter_handle')
    def validate_twitter_handle(cls, v):
        """Ensure Twitter handle starts with @."""
        if v and not v.startswith('@'):
            return f'@{v}'
        return v

class PersonBase(BaseModel):
    """Shared base attributes for a person."""
    name: str = Field(..., description="Full name of the person.")
    title: Optional[str] = Field(None, description="Primary job title.")
    duke_affiliation_status: str = Field("no", description="Duke affiliation status: confirmed, please review, no.")
    relevance_score: Optional[int] = Field(None, description="Calculated relevance score (0-100).")
    education: Optional[List[Dict[str, Any]]] = Field(None, description="List of educational institutions.")
    current_company: Optional[str] = Field(None, description="Name of the current primary company.")
    previous_companies: Optional[List[str]] = Field(None, description="List of previous company names.")
    twitter_handle: Optional[str] = Field(None, description="Twitter handle (e.g., @handle).")
    linkedin_handle: Optional[str] = Field(None, description="Full LinkedIn profile URL.")
    source_links: Optional[List[str]] = Field(None, description="List of source URLs.")
    last_updated: Optional[datetime] = Field(None, description="Timestamp of the last update.")

    class Config:
        orm_mode = True
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
    education: Optional[List[Dict[str, Any]]] = None
    current_company: Optional[str] = None
    previous_companies: Optional[List[str]] = None
    twitter_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    source_links: Optional[List[str]] = None
    last_updated: Optional[datetime] = datetime.now()

    # Add validators if needed for update context

# Define a minimal schema for people within company responses
class PersonBasicInfo(BaseModel):
    """Schema representing minimal person info within a company response."""
    name: str
    title: str

    class Config:
        from_attributes = True # Allow creating from ORM objects

class CompanyCreate(CompanyBase):
    """Schema for creating a new company record."""
    people: Optional[List[PersonBase]] = None
    raw_data_path: Optional[str] = None

class CompanyUpdate(CompanyBase):
    """Schema for updating an existing company record."""
    name: Optional[str] = None
    duke_affiliation_status: Optional[str] = None
    duke_affiliation_score: Optional[int] = None
    relevance_score: Optional[int] = None
    summary: Optional[str] = None
    investors: Optional[List[str]] = None
    funding_stage: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[str] = None
    location: Optional[str] = None
    twitter_handle: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_summary: Optional[TwitterSummaryBase] = None
    source_links: Optional[List[str]] = None
    people: Optional[List[PersonBase]] = None

class CompanyInDB(CompanyBase):
    """Schema representing a company as stored in the database."""
    id: int
    people: Optional[List[PersonInDB]] = None

    class Config:
        from_attributes = True

class CompanyResponse(CompanyBase):
    """Schema for company API responses with formatted timestamps."""
    id: int
    people: Optional[List[PersonBasicInfo]] = None
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
    message: str

# Need to update forward refs after all models are defined
CompanyResponse.update_forward_refs()
PersonResponse.update_forward_refs()
