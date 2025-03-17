"""
Schemas package for the DCP AI Scouting Platform.

This package provides Pydantic models for request and response validation,
ensuring data consistency throughout the application.
"""

from db.schemas.schemas import (
    # Enums
    FundingStageEnum,
    
    # Company schemas
    FundingRound,
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyDetailResponse,
    CompanySearchResult,
    
    # Founder schemas
    FounderCreate,
    FounderUpdate,
    FounderResponse,
    FounderDetailResponse,
    FounderSearchResult,
    FounderListResponse,
    FounderSearchResponse,
    FounderBrief,
    CompanyBrief,
    
    # Search schemas
    SearchRequest,
    SearchResponse,
    SearchResult,
    PaginationParams,
    SearchFilters,
    
    # Social media schemas
    TwitterSummary,
    
    # Auth schemas
    UserCreate,
    UserResponse,
    APIKeyCreate,
    APIKeyResponse,
    
    # Stats schemas
    StatsResponse,
    
    # SERP usage schemas
    SERPUsageResponse,
    SERPUsageStats
)

__all__ = [
    # Enums
    "FundingStageEnum",
    
    # Company schemas
    "FundingRound",
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyResponse",
    "CompanyDetailResponse",
    "CompanySearchResult",
    
    # Founder schemas
    "FounderCreate",
    "FounderUpdate",
    "FounderResponse",
    "FounderDetailResponse",
    "FounderSearchResult",
    "FounderListResponse",
    "FounderSearchResponse",
    "FounderBrief",
    "CompanyBrief",
    
    # Search schemas
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "PaginationParams",
    "SearchFilters",
    
    # Social media schemas
    "TwitterSummary",
    
    # Auth schemas
    "UserCreate",
    "UserResponse",
    "APIKeyCreate",
    "APIKeyResponse",
    
    # Stats schemas
    "StatsResponse",
    
    # SERP usage schemas
    "SERPUsageResponse",
    "SERPUsageStats"
] 