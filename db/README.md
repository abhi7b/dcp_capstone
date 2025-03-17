# Database Module

This directory contains database components for the DCP AI Scouting Platform, designed with a focus on efficiency, simplicity, and reproducibility.

## Overview

The database module provides:
- Database connection management using SQLAlchemy
- ORM models for the application's data entities
- Pydantic schemas for request/response validation
- Utilities for database operations and management

## Directory Structure

```
db/
├── database/                # Database connection and models
│   ├── db.py                # Connection management
│   ├── models.py            # SQLAlchemy ORM models
│   ├── check_db.py          # Database connection check utility
│   ├── create_tables.py     # Table creation utility
│   ├── insert_test_data.py  # Test data insertion utility
│   ├── check_schema.py      # Schema verification utility
│   └── __init__.py          # Package exports
├── schemas/                 # Pydantic validation schemas
│   ├── schemas.py           # Request/response schemas
│   └── __init__.py          # Package exports
└── README.md                # This file
```

## Key Components

### Database Connection (`database/db.py`)

Manages database connections and sessions using SQLAlchemy with a focus on efficiency:
- Connection pooling for optimal performance
- Async session management for non-blocking operations
- Proper error handling and connection cleanup

```python
from db.database import get_db

@app.get("/companies")
async def get_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company))
    companies = result.scalars().all()
    return companies
```

### ORM Models (`database/models.py`)

Defines SQLAlchemy models for the application's database entities, focusing on:
- Essential fields for each entity
- Proper indexing for query performance
- Clear relationships between entities

#### Core Business Models
- `Company`: Startup companies with Duke affiliation tracking
- `Founder`: Company founders with Duke alumni status
- `CompanyFounder`: Association table for company-founder relationships

#### Authentication Models
- `User`: User accounts for API access
- `APIUser`: API keys associated with users for authentication

#### Utility Models
- `SERPUsage`: Tracks SERP API usage for quota management

### Validation Schemas (`schemas/schemas.py`)

Defines Pydantic models for request and response validation, using:
- Inheritance and mixins to reduce duplication
- Clear separation of concerns (create, update, response)
- Appropriate validation rules

#### Base Schemas and Mixins
- `BaseSchema`: Common configuration for all schemas
- `TimestampMixin`: Common timestamp fields
- `DukeAffiliationMixin`: Duke affiliation fields
- `SocialMediaMixin`: Social media related fields
- `DataQualityMixin`: Data quality and freshness fields

#### Domain-Specific Schemas
- Company schemas (`CompanyBase`, `CompanyCreate`, `CompanyUpdate`, `CompanyResponse`)
- Founder schemas (`FounderBase`, `FounderCreate`, `FounderUpdate`, `FounderResponse`)
- Search schemas for filtering and pagination
- Authentication schemas for users and API keys

## Database Management

The project includes several utilities for database management:

### Database Connection Check (`check_db.py`)

Verifies connection to the PostgreSQL database and lists tables:

```bash
# Check database connection
python -m db.database.check_db
```

### Table Creation (`create_tables.py`)

Creates all database tables defined in the models:

```bash
# Create tables
python -m db.database.create_tables

# Drop and recreate tables
python -m db.database.create_tables --recreate
```

### Test Data Insertion (`insert_test_data.py`)

Inserts sample data into the database for testing:

```bash
# Insert test data
python -m db.database.insert_test_data

# Force insert even if data exists
python -m db.database.insert_test_data --force
```

### Schema Verification (`check_schema.py`)

Checks the actual schema of the PostgreSQL database tables:

```bash
# Check database schema
python -m db.database.check_schema
```


## Testing the Database Module

To test the database module, you can use the following commands:

### 1. Test Database Connection

```bash

# Or using the Python module directly
python -m db.database.check_db
```

### 2. Test Table Creation

```bash
# Create tables
python -m db.database.create_tables

# Reset database (drop and recreate tables)
python -m db.database.create_tables --recreate
```

### 3. Test Data Insertion

```bash
# Insert test data
python -m db.database.insert_test_data

# Force insert even if data exists
python -m db.database.insert_test_data --force
```

### 4. Test Schema Verification

```bash
# Check database schema
python -m db.database.check_schema
```

### 5. Complete Database Setup Test

```bash
# Full test sequence
python -m db.database.create_tables --recreate
python -m db.database.insert_test_data
python -m db.database.check_db
python -m db.database.check_schema
```

## Environment Configuration

Set the following environment variables for database connection:

```
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
```

The system is configured to work with Supabase PostgreSQL by default, but can be adapted to work with any PostgreSQL provider by changing the DATABASE_URL.

## Model Relationships

### Company and Founder

Companies and founders have a many-to-many relationship through the `CompanyFounder` association table:

```python
# Company model
founders = relationship("Founder", secondary="company_founder", back_populates="companies")

# Founder model
companies = relationship("Company", secondary="company_founder", back_populates="founders")
```

### User and APIUser

Users and API keys have a one-to-many relationship:

```python
# User model
api_keys = relationship("APIUser", back_populates="user")

# APIUser model
user = relationship("User", back_populates="api_keys")
```
