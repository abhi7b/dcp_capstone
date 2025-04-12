"""
Database Models Module

This module defines SQLAlchemy ORM models for the application's database schema.
Models include Person and Company entities with their relationships and fields.
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime, Text, JSON, Float, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from sqlalchemy.orm import relationship

Base = declarative_base()

# Association table for company-person relationships
company_person_association = Table(
    'company_person_association',
    Base.metadata,
    Column('company_id', Integer, ForeignKey('companies.id'), primary_key=True),
    Column('person_id', Integer, ForeignKey('persons.id'), primary_key=True)
)

class Company(Base):
    """
    Company model representing organizations in the database.
    Stores company information, metrics, and relationships.
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False, unique=True)
    duke_affiliation_status = Column(String, nullable=False)
    relevance_score = Column(Integer, nullable=True)
    summary = Column(String, nullable=True)
    investors = Column(String, nullable=True)
    funding_stage = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    founded = Column(String, nullable=True)
    location = Column(String, nullable=True)
    twitter_handle = Column(String, nullable=True)
    linkedin_handle = Column(String, nullable=True)
    twitter_summary = Column(String, nullable=True)
    source_links = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Define relationship with Person model
    people = relationship(
        "Person",
        secondary=company_person_association,
        back_populates="companies"
    )

class Person(Base):
    """
    Person model representing individuals in the database.
    Stores personal information, affiliations, and scores.
    """
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=True)
    duke_affiliation_status = Column(String, nullable=False)
    relevance_score = Column(Integer, nullable=False)
    education = Column(String, nullable=True)
    current_company = Column(String, nullable=True)
    previous_companies = Column(String, nullable=True)
    twitter_handle = Column(String, nullable=True)
    linkedin_handle = Column(String, nullable=True)
    twitter_summary = Column(String, nullable=True)
    source_links = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Define relationship with Company model
    companies = relationship(
        "Company",
        secondary=company_person_association,
        back_populates="people"
    )

class APIKey(Base):
    """
    API Key model for authentication.
    
    This model stores API keys for authenticating API requests,
    including rate limiting and expiration information.
    """
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=100)  # Requests per minute
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True) 