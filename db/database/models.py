#database/models.py

"""
Database Models for the DCP AI Scouting Platform.

This module defines SQLAlchemy ORM models for the core entities in the system:
companies, founders, and their relationships.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Index, 
    func, JSON, Enum, ARRAY, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
import enum
from datetime import datetime

from db.database.db import Base
from backend.config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Enums
class FundingStage(enum.Enum):
    """Enumeration of possible funding stages for a company."""
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D = "series_d"
    SERIES_I = "series_i"
    LATE_STAGE = "late_stage"
    IPO = "ipo"
    ACQUIRED = "acquired"

# Association tables
class CompanyFounder(Base):
    """Association table for the many-to-many relationship between companies and founders."""
    __tablename__ = "company_founder"

    company_id = Column(Integer, ForeignKey('companies.id', ondelete="CASCADE"), primary_key=True)
    founder_id = Column(Integer, ForeignKey('founders.id', ondelete="CASCADE"), primary_key=True)
    role = Column(String(100))  # CEO, CTO, etc.
    
    __table_args__ = (
        Index('idx_company_founder', company_id, founder_id),
    )

class Company(Base):
    """
    Model representing a company.
    
    Stores core information about companies, with a focus on Duke affiliations
    and funding details relevant for investment decisions.
    """
    __tablename__ = "companies"

    # Basic information
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(50), nullable=True)
    year_founded = Column(Integer, nullable=True)
    industry = Column(String(100), nullable=True)
    description = Column(String(2000), nullable=True)
    location = Column(String(100), nullable=True)
    
    # Duke affiliation
    duke_affiliated = Column(Boolean, default=False, index=True)
    duke_connection_type = Column(ARRAY(String), nullable=True)  # ['founder_alumni', 'partnership', etc.]
    duke_department = Column(String(100), nullable=True)  # e.g., 'Computer Science', 'Fuqua'
    duke_affiliation_confidence = Column(Float, nullable=True)  # 0-1 confidence score
    
    # VC-specific fields
    total_funding = Column(Float, default=0)  # Total funding raised in full dollars
    latest_valuation = Column(Float, nullable=True)  # Latest valuation in full dollars
    latest_funding_stage = Column(Enum(FundingStage), nullable=True)
    competitors = Column(ARRAY(String), nullable=True)
    funding_rounds = Column(JSON, nullable=True)  # List of funding rounds with details
    
    # Social media fields
    social_media_score = Column(Integer, nullable=True)
    twitter_summary = Column(Text, nullable=True)  # Summary of recent tweets
    twitter_actionability = Column(Integer, nullable=True)  # Actionability score (0-100)
    twitter_last_updated = Column(DateTime(timezone=True), nullable=True)  # When Twitter data was last updated
    
    # Data quality and freshness
    data_freshness_score = Column(Float, nullable=True)  # 0-1 score based on data age
    last_data_refresh = Column(DateTime(timezone=True), nullable=True)
    data_sources = Column(ARRAY(String), nullable=True)  # List of data sources used
    data_quality_score = Column(Float, nullable=True)  # 0-1 score based on completeness
    
    
    # Timestamps
    last_scraped = Column(DateTime(timezone=True), nullable=True, default=datetime.utcnow)
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    founders = relationship("Founder", secondary="company_founder", back_populates="companies")

    __table_args__ = (
        Index('idx_company_name', func.lower(name)),
        Index('idx_company_duke', duke_affiliated),
        Index('idx_company_funding_stage', latest_funding_stage),
    )

class Founder(Base):
    """
    Model representing a company founder.
    
    Stores information about founders, with a focus on Duke affiliations
    and professional background relevant for investment decisions.
    """
    __tablename__ = "founders"

    # Basic information
    id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False, unique=True, index=True)
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(50), nullable=True)
    current_position = Column(String(100), nullable=True)
    current_company = Column(String(200), nullable=True)
    
    # Duke affiliation
    duke_affiliated = Column(Boolean, default=False, index=True)
    graduation_year = Column(Integer, nullable=True)
    duke_affiliation_confidence = Column(Float, nullable=True)  # 0-1 confidence score
    
    # Enhanced founder information
    education = Column(JSON, nullable=True)  # [{school: 'Duke', degree: 'BS', year: 2010}, ...]
    work_history = Column(JSON, nullable=True)
    
    # Social media fields
    social_media_score = Column(Integer, nullable=True)
    twitter_summary = Column(Text, nullable=True)  # Summary of recent tweets
    twitter_actionability = Column(Integer, nullable=True)  # Actionability score (0-100)
    twitter_last_updated = Column(DateTime(timezone=True), nullable=True)  # When Twitter data was last updated
   
    # Data quality and freshness
    data_freshness_score = Column(Float, nullable=True)  # 0-1 score based on data age
    last_data_refresh = Column(DateTime(timezone=True), nullable=True)
    data_sources = Column(ARRAY(String), nullable=True)  # List of data sources used
    
    # Timestamps
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    companies = relationship("Company", secondary="company_founder", back_populates="founders")

    __table_args__ = (
        Index('idx_founder_name', func.lower(full_name)),
        Index('idx_founder_duke', duke_affiliated),
    )

class SERPUsage(Base):
    """
    Model for tracking SERP API usage for quota management.
    
    Helps monitor and control usage of external search APIs to stay within
    rate limits and budget constraints.
    """
    __tablename__ = "serp_usage"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    query_count = Column(Integer, nullable=False)  # Number of SERP queries made
    entity_name = Column(String(200), nullable=False)  # Name of entity being searched
    entity_type = Column(String(50), nullable=False)  # Type of entity (company, founder)
    endpoint = Column(String(100), nullable=False)  # API endpoint making the request
    
    __table_args__ = (
        Index('idx_serp_usage_timestamp', timestamp),
        Index('idx_serp_usage_entity', entity_type, entity_name),
    )

class User(Base):
    """
    Model for user accounts.
    
    Stores information about users who can access the system,
    including authentication and authorization details.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    api_keys = relationship("APIUser", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_username', func.lower(username)),
        Index('idx_user_email', func.lower(email)),
    )

class APIUser(Base):
    """
    Model for API keys.
    
    Stores API keys associated with users for authentication
    when accessing the API programmatically.
    """
    __tablename__ = "api_users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # Name of the API key
    api_key = Column(String(100), unique=True, nullable=False, index=True)
    scopes = Column(ARRAY(String), nullable=False, default=[])  # List of scopes
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Expiration date
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index('idx_api_user_key', api_key),
        Index('idx_api_user_user', user_id),
    )




