"""
Root conftest file for pytest.

This file is automatically loaded by pytest and contains setup
for making imports work correctly in tests.
"""
import os
import sys
from pathlib import Path
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.db.session import async_session, engine
from app.db.models import Base
from app.utils.config import settings
from app.db.crud import create_company
from app.db.person_crud import create_person
from app.db.schemas import CompanyCreate, PersonCreate, CompanyPersonAssociation

# Add the backend directory to the Python path for imports
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db",
        echo=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db(engine):
    """Create a test database session."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def test_company_data():
    """Create test company data."""
    return {
        "name": "Test Company",
        "duke_affiliation_status": "confirmed",
        "relevance_score": 75,
        "summary": "A test company",
        "investors": "Investor A, Investor B",
        "funding_stage": "Series A",
        "industry": "Technology",
        "founded": "2020-01-01",
        "location": "Durham, NC",
        "twitter_handle": "@testcompany",
        "linkedin_handle": "test-company",
        "twitter_summary": "Test company's Twitter activity",
        "source_links": "https://test.com, https://test2.com",
        "people": [
            CompanyPersonAssociation(
                name="John Doe",
                title="CEO",
                duke_affiliation_status="confirmed"
            ),
            CompanyPersonAssociation(
                name="Jane Smith",
                title="CTO",
                duke_affiliation_status="please review"
            )
        ]
    }

@pytest.fixture
async def test_person_data():
    """Create test person data."""
    return {
        "name": "Test Person",
        "title": "CEO",
        "duke_affiliation_status": "confirmed",
        "relevance_score": 85,
        "education": "Duke University, MIT",
        "current_company": "Test Company",
        "previous_companies": "Previous Company A, Previous Company B",
        "twitter_handle": "@testperson",
        "linkedin_handle": "test-person",
        "twitter_summary": "Test person's Twitter activity",
        "source_links": "https://test.com/person, https://test2.com/person"
    }

@pytest.fixture
async def test_company(db, test_company_data):
    """Create a test company in the database."""
    company = await create_company(db, CompanyCreate(**test_company_data))
    return company

@pytest.fixture
async def test_person(db, test_person_data):
    """Create a test person in the database."""
    person = await create_person(db, PersonCreate(**test_person_data))
    return person 