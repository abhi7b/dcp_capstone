#models.py
"""
Models

"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text, Index, func, literal_column
)
from sqlalchemy.orm import relationship, declarative_base
from database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    normalized_name = Column(String(200), index=True)  # For case-insensitive search
    domain = Column(String(255), index=True, nullable=True)
    crunchbase_id = Column(String(50), unique=True, nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    last_scraped = Column(DateTime(timezone=True), nullable=True)
    relevance_score = Column(Float, default=0.0, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    founders = relationship("Founder", secondary="company_founder", back_populates="companies")
    web_activity = relationship("WebActivity", back_populates="company")
    
    # Full-text search index
    __table_args__ = (
        Index('ix_company_search', func.to_tsvector(literal_column("'english'"), name), postgresql_using='gin'),
    )

class Founder(Base):
    __tablename__ = "founders"
    
    id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False)
    normalized_name = Column(String(150), index=True)
    linkedin_id = Column(String(50), unique=True, nullable=True)
    twitter_id = Column(String(50), unique=True, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    current_position = Column(String(100), nullable=True)
    verification_confidence = Column(Float, default=0.0, nullable=True)
    last_verified = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    companies = relationship("Company", secondary="company_founder", back_populates="founders")
    
    __table_args__ = (
        Index('ix_founder_search', func.to_tsvector(literal_column("'english'"), full_name), postgresql_using='gin'),
        Index('ix_graduation_year', 'graduation_year'),
    )

class CompanyFounder(Base):
    __tablename__ = "company_founder"

    company_id = Column(Integer, ForeignKey('companies.id', ondelete="CASCADE"), primary_key=True)
    founder_id = Column(Integer, ForeignKey('founders.id', ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False)
    relationship_source = Column(String(50), nullable=True)  # SERP, PitchBook, Manual

    __table_args__ = (
        Index('ix_company_founder', 'company_id', 'founder_id', unique=True),
    )

class WebActivity(Base):
    __tablename__ = "web_activity"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)  # NEWS, SOCIAL, BLOG, etc.
    sentiment_score = Column(Float, nullable=True)
    
    # Relationships
    company_id = Column(Integer, ForeignKey('companies.id', ondelete="SET NULL"), nullable=True)
    company = relationship("Company", back_populates="web_activity")

    __table_args__ = (
        Index('ix_webactivity_source_type', 'source_type'),
    )
