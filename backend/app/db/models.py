"""
SQLAlchemy ORM models for the Duke VC Insight Engine database.

This module defines the database schema using SQLAlchemy ORM.
It includes models for companies, founders, executives, and API keys.
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime, Text, JSON, Float, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime

Base = declarative_base()

# Association table for many-to-many relationships with title
company_person_association = Table(
    'company_person_association',
    Base.metadata,
    Column('company_id', Integer, ForeignKey('companies.id'), primary_key=True),
    Column('person_id', Integer, ForeignKey('persons.id'), primary_key=True),
    Column('title', String, nullable=False)  # Role within the company
    # Column('company_name', String, nullable=True), # Removed company name
    # Column('person_name', String, nullable=True)  # Removed person name
)

class Company(Base):
    """
    Company model representing startup/company entities.
    
    This model stores information about companies including their
    Duke affiliation status, founders, and other relevant details.
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    duke_affiliation_status = Column(String, nullable=False)
    relevance_score = Column(Integer, nullable=True)
    summary = Column(String, nullable=True)
    investors = Column(JSON, nullable=True)
    funding_stage = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    founded = Column(String, nullable=True)
    location = Column(String, nullable=True)
    twitter_handle = Column(String, nullable=True)
    linkedin_handle = Column(String, nullable=True)
    twitter_summary = Column(JSON, nullable=True)
    source_links = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    people = relationship(
        "Person",
        secondary=company_person_association,
        back_populates="companies"
    )

class Person(Base):
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    title = Column(String, nullable=True)
    duke_affiliation_status = Column(String, nullable=False)
    relevance_score = Column(Integer, nullable=False)
    education = Column(JSON, nullable=True)
    current_company = Column(String, nullable=True)
    previous_companies = Column(JSON, nullable=True)
    twitter_handle = Column(String, nullable=True)
    linkedin_handle = Column(String, nullable=True)
    twitter_summary = Column(String, nullable=True)
    source_links = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationship
    companies = relationship("Company", secondary=company_person_association, back_populates="people")

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