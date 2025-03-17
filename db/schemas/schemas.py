"""
Schemas for the DCP AI Scouting Platform.

This module provides Pydantic models for request and response validation,
focusing on the core functionality required by the application.
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums
class FundingStageEnum(str, Enum):
    """Enum for company funding stages."""
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D = "series_d"
    SERIES_I = "series_i"
    LATE_STAGE = "late_stage"
    IPO = "ipo"
    ACQUIRED = "acquired"

# ----------------
# Base Schemas
# ----------------

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

class DukeAffiliationMixin(BaseModel):
    """Mixin for Duke affiliation fields."""
    duke_affiliated: bool = False
    duke_affiliation_confidence: Optional[float] = None

class SocialMediaMixin(BaseModel):
    """Mixin for social media fields."""
    social_media_score: Optional[int] = None
    twitter_summary: Optional[str] = None
    twitter_actionability: Optional[int] = None
    twitter_last_updated: Optional[datetime] = None

class TwitterSummary(BaseSchema):
    """Schema for Twitter summary data."""
    username: str
    summary: str
    sentiment_score: Optional[float] = None
    actionability_score: Optional[int] = None
    key_topics: Optional[List[str]] = None
    last_updated: Optional[datetime] = None

class DataQualityMixin(BaseModel):
    """Mixin for data quality fields."""
    data_freshness_score: Optional[float] = None
    last_data_refresh: Optional[datetime] = None
    data_sources: Optional[List[str]] = None
    data_quality_score: Optional[float] = None

# ----------------
# Company Schemas
# ----------------

class FundingRound(BaseSchema):
    """Schema for funding round data."""
    stage: str
    amount: int
    date: datetime
    lead_investor: Optional[str] = None
    investors: Optional[List[str]] = None

class CompanyBase(BaseSchema):
    """Base schema for company data."""
    name: str
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    year_founded: Optional[int] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

class CompanyCreate(CompanyBase, DukeAffiliationMixin):
    """Schema for creating a new company."""
    duke_connection_type: Optional[List[str]] = None
    duke_department: Optional[str] = None
    total_funding: Optional[float] = 0
    latest_valuation: Optional[float] = None
    latest_funding_stage: Optional[FundingStageEnum] = None
    competitors: Optional[List[str]] = None
    funding_rounds: Optional[List[FundingRound]] = None

class CompanyUpdate(BaseSchema):
    """Schema for updating an existing company."""
    name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    year_founded: Optional[int] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    duke_affiliated: Optional[bool] = None
    duke_connection_type: Optional[List[str]] = None
    duke_department: Optional[str] = None
    duke_affiliation_confidence: Optional[float] = None
    total_funding: Optional[float] = None
    latest_valuation: Optional[float] = None
    latest_funding_stage: Optional[FundingStageEnum] = None
    competitors: Optional[List[str]] = None
    funding_rounds: Optional[List[FundingRound]] = None
    # Social media fields
    social_media_score: Optional[int] = None
    twitter_summary: Optional[str] = None
    twitter_actionability: Optional[int] = None
    twitter_last_updated: Optional[datetime] = None
    # Data quality fields
    data_freshness_score: Optional[float] = None
    last_data_refresh: Optional[datetime] = None
    data_sources: Optional[List[str]] = None
    data_quality_score: Optional[float] = None

class CompanyResponse(CompanyBase, DukeAffiliationMixin, SocialMediaMixin, DataQualityMixin, TimestampMixin):
    """Schema for company response."""
    id: int
    duke_connection_type: Optional[List[str]] = None
    duke_department: Optional[str] = None
    total_funding: float = 0
    latest_valuation: Optional[float] = None
    latest_funding_stage: Optional[FundingStageEnum] = None
    competitors: Optional[List[str]] = None
    funding_rounds: Optional[List[Dict[str, Any]]] = None
    last_scraped: Optional[datetime] = None
    founders: Optional[List["FounderBrief"]] = None

# Alias for backward compatibility
CompanyDetailResponse = CompanyResponse

class CompanySearchResult(BaseSchema):
    """Schema for company search results."""
    id: int
    name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    year_founded: Optional[int] = None
    duke_affiliated: bool = False
    total_funding: float = 0
    latest_funding_stage: Optional[FundingStageEnum] = None
    match_score: Optional[float] = None
    match_reason: Optional[str] = None

# ----------------
# Founder Schemas
# ----------------

class FounderBase(BaseSchema):
    """Base schema for founder data."""
    full_name: str
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None

class FounderCreate(FounderBase, DukeAffiliationMixin):
    """Schema for creating a new founder."""
    graduation_year: Optional[int] = None
    education: Optional[List[Dict[str, Any]]] = None
    work_history: Optional[List[Dict[str, Any]]] = None

class FounderUpdate(BaseSchema):
    """Schema for updating an existing founder."""
    full_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    duke_affiliated: Optional[bool] = None
    graduation_year: Optional[int] = None
    duke_affiliation_confidence: Optional[float] = None
    education: Optional[List[Dict[str, Any]]] = None
    work_history: Optional[List[Dict[str, Any]]] = None
    # Social media fields
    social_media_score: Optional[int] = None
    twitter_summary: Optional[str] = None
    twitter_actionability: Optional[int] = None
    twitter_last_updated: Optional[datetime] = None
    # Data quality fields
    data_freshness_score: Optional[float] = None
    last_data_refresh: Optional[datetime] = None
    data_sources: Optional[List[str]] = None
    data_quality_score: Optional[float] = None

class FounderResponse(FounderBase, DukeAffiliationMixin, SocialMediaMixin, DataQualityMixin, TimestampMixin):
    """Schema for founder response."""
    id: int
    graduation_year: Optional[int] = None
    education: Optional[List[Dict[str, Any]]] = None
    work_history: Optional[List[Dict[str, Any]]] = None
    companies: Optional[List["CompanyBrief"]] = None

# Alias for backward compatibility
FounderDetailResponse = FounderResponse

class FounderBrief(BaseSchema):
    """Brief schema for founder in company responses."""
    id: int
    full_name: str
    current_position: Optional[str] = None
    duke_affiliated: bool = False

class CompanyBrief(BaseSchema):
    """Brief schema for company in founder responses."""
    id: int
    name: str
    industry: Optional[str] = None
    latest_funding_stage: Optional[FundingStageEnum] = None

class FounderSearchResult(BaseSchema):
    """Schema for founder search results."""
    id: int
    full_name: str
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    duke_affiliated: bool = False
    graduation_year: Optional[int] = None
    match_score: Optional[float] = None
    match_reason: Optional[str] = None

class FounderListResponse(BaseSchema):
    """Schema for a list of founders."""
    founders: List[FounderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class FounderSearchResponse(BaseSchema):
    """Schema for founder search responses."""
    results: List[FounderSearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int

# ----------------
# Search Schemas
# ----------------

class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""
    page: int = 1
    page_size: int = 20
    
class SortParams(BaseSchema):
    """Schema for sorting parameters."""
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"

class CompanyFilters(BaseSchema):
    """Schema for company filters."""
    industry: Optional[List[str]] = None
    funding_stage: Optional[List[FundingStageEnum]] = None
    min_funding: Optional[float] = None
    max_funding: Optional[float] = None
    duke_affiliated: Optional[bool] = None
    year_founded_min: Optional[int] = None
    year_founded_max: Optional[int] = None
    location: Optional[List[str]] = None

class FounderFilters(BaseSchema):
    """Schema for founder filters."""
    duke_affiliated: Optional[bool] = None
    graduation_year_min: Optional[int] = None
    graduation_year_max: Optional[int] = None
    current_company: Optional[str] = None

# Union type for search filters
SearchFilters = Union[CompanyFilters, FounderFilters]

class SearchRequest(BaseSchema):
    """Schema for search requests."""
    query: str
    entity_type: str = "company"  # "company" or "founder"
    pagination: Optional[PaginationParams] = PaginationParams()
    sort: Optional[SortParams] = SortParams()
    filters: Optional[SearchFilters] = None

class SearchResponse(BaseSchema):
    """Schema for search responses."""
    results: List[Union[CompanySearchResult, FounderSearchResult]]
    total: int
    page: int
    page_size: int
    total_pages: int

# Alias for backward compatibility - SearchResult can be either a CompanySearchResult or FounderSearchResult
SearchResult = Union[CompanySearchResult, FounderSearchResult]

# ----------------
# Auth Schemas
# ----------------

class UserCreate(BaseSchema):
    """Schema for creating a new user."""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_admin: bool = False

class UserResponse(BaseSchema):
    """Schema for user responses."""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

class APIKeyCreate(BaseSchema):
    """Schema for creating a new API key."""
    name: str
    scopes: List[str] = []
    expires_at: Optional[datetime] = None

class APIKeyResponse(BaseSchema):
    """Schema for API key responses."""
    id: int
    name: str
    api_key: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used: Optional[datetime] = None
    user_id: int

# ----------------
# Utility Schemas
# ----------------

class SERPUsageStats(BaseSchema):
    """Schema for SERP API usage statistics."""
    total_queries: int
    daily_average: float
    daily_quota: int
    quota_remaining: int
    quota_reset_time: Optional[datetime] = None

class SERPUsageResponse(BaseSchema):
    """Schema for SERP API usage responses."""
    id: int
    timestamp: datetime
    query_count: int
    entity_name: str
    entity_type: str
    endpoint: str

class StatsResponse(BaseSchema):
    """Schema for statistics responses."""
    total_companies: int
    duke_affiliated_companies: int
    total_founders: int
    duke_affiliated_founders: int
    companies_by_funding_stage: Dict[str, int]
    companies_by_industry: Dict[str, int]
    data_freshness: Dict[str, float]

# Update forward references
CompanyResponse.model_rebuild()
FounderResponse.model_rebuild() 