"""
Database package for the DCP AI Scouting Platform.

This package provides SQLAlchemy models and database utilities for connecting
to PostgreSQL. It exports all the necessary components for database
operations in the application.
"""
# Database connection and session management
from db.database.db import (
    engine, 
    Base, 
    get_db, 
    get_db_context, 
    test_connection, 
    close_db_connection
)

# ORM models
from db.database.models import (
    Company, 
    Founder, 
    CompanyFounder, 
    FundingStage,
    SERPUsage,
    User,
    APIUser
)


# Export commonly used functions and classes
__all__ = [
    # Database connection
    'engine',
    'Base',
    'get_db',
    'get_db_context',
    'test_connection',
    'close_db_connection',
    
    # Models
    'Company',
    'Founder',
    'CompanyFounder',
    'FundingStage',
    'SERPUsage',
    'User',
    'APIUser'
] 