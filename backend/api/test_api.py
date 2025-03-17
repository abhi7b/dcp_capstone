#!/usr/bin/env python3
"""
Unified test script for the API endpoints.

This script tests the company and founder endpoints of the DCP AI Scouting Platform API.
It can run both mock tests and tests with real data from processed files.

Usage:
    python -m backend.api.test_api [--real-data] [--mock-data] [--all]
"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from db.database.db import get_db, Base
from db.database.models import Company, Founder, CompanyFounder, SERPUsage, FundingStage
from backend.api import company, founder, test
from backend.config.logs import LogManager, get_logger
from backend.config.config import settings

# Set up logging
LogManager.setup_logging()
logger = get_logger(__name__)

# Project root and test data paths
project_root = Path(__file__).parent.parent.parent
OUTPUT_DIR = project_root / "output"

# Get database URL from environment variables
TEST_DATABASE_URL = os.getenv("DATABASE_URL")
logger.info(f"Using test database: {TEST_DATABASE_URL}")

# Create a test engine and session
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create a test app
app = FastAPI()
app.include_router(company.router, prefix="/api/v1/company", tags=["company"])
app.include_router(founder.router, prefix="/api/v1/founder", tags=["founder"])
app.include_router(test.router, prefix="/api/v1/test", tags=["test"])

# Override the get_db dependency
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Create a test client
client = TestClient(app)

# Database setup and cleanup functions
async def setup_database():
    """Set up the test database with sample data."""
    logger.info("Setting up test database...")
    
    # Create the database tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Add sample data
    async with TestingSessionLocal() as session:
        # Create a company
        db_company = Company(
            name="Existing Company",
            description="An existing company in the database",
            linkedin_url="https://linkedin.com/company/existingcompany",
            domain="existingcompany.com",
            industry="Technology",
            location="New York, NY",
            year_founded=2019,
            latest_funding_stage=FundingStage.SERIES_A,
            total_funding=5000000,
            latest_valuation=20000000,
            duke_affiliated=True,
            duke_connection_type=["founders"],
            duke_affiliation_confidence=0.8,
            twitter_handle="existingcompany",
            data_freshness_score=0.7,
            data_quality_score=0.8
        )
        session.add(db_company)
        
        # Create a founder
        db_founder = Founder(
            full_name="Existing Founder",
            current_position="CEO at Existing Company",
            current_company="Existing Company",
            duke_affiliated=True,
            graduation_year=2010,
            duke_affiliation_confidence=0.8,
            twitter_handle="existingfounder",
            data_freshness_score=0.7
        )
        session.add(db_founder)
        
        # Commit to get IDs
        await session.commit()
        
        # Create a company-founder relationship
        db_company_founder = CompanyFounder(
            company_id=db_company.id,
            founder_id=db_founder.id,
            role="CEO"
        )
        session.add(db_company_founder)
        
        await session.commit()
    
    logger.info("Test database setup complete.")

async def cleanup_database():
    """Clean up the test database."""
    logger.info("Cleaning up test database...")
    
    # Clean up the database
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Test database cleanup complete.")

# Basic API tests
async def test_ping():
    """Test the ping endpoint."""
    logger.info("Testing test_ping...")
    
    response = client.get("/api/v1/test/ping")
    
    assert response.status_code == 200
    assert response.json()["message"] == "pong"
    
    logger.info("✅ test_ping passed")

async def test_db_check():
    """Test the database check endpoint."""
    logger.info("Testing test_db_check...")
    
    response = client.get("/api/v1/test/db-check")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert "company_found" in data
    assert "founder_found" in data
    
    logger.info("✅ test_db_check passed")

# Company API tests
async def test_get_company_existing():
    """Test getting an existing company from the database."""
    logger.info("Testing get_company_existing...")
    
    response = client.get("/api/v1/company/Existing Company")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Existing Company"
    assert data["industry"] == "Technology"
    assert data["duke_affiliated"] == True
    
    logger.info("✅ test_get_company_existing passed")

async def test_get_company_new():
    """Test getting a new company that requires scraping."""
    logger.info("Testing test_get_company_new...")
    
    # Mock the necessary components for the company endpoint
    with patch('backend.api.company.CompanyScraper') as MockCompanyScraper, \
         patch('backend.api.company.CompanyProcessor') as MockCompanyProcessor, \
         patch('backend.api.company.TwitterScraper') as MockTwitterScraper, \
         patch('backend.api.company.TwitterAnalyzer') as MockTwitterAnalyzer, \
         patch('backend.api.company.IntegrationService.process_company_data') as mock_process_company_data, \
         patch('backend.api.company.create_company_from_integrated_data') as mock_create_company, \
         patch('backend.api.company.company_endpoint.prepare_response') as mock_prepare_response, \
         patch('backend.api.company.track_serp_usage'):
        
        # Configure the scraper mock
        mock_scraper = AsyncMock()
        mock_scraper.search_company = AsyncMock()
        mock_scraper.search_company.return_value = {
            "company_name": "New Company",
            "description": "A new company for testing",
            "website": "https://newcompany.com",
            "industry": "Fintech",
            "twitter_handle": "newcompany"
        }
        MockCompanyScraper.return_value = mock_scraper
        
        # Configure the processor mock
        mock_processor = AsyncMock()
        mock_processor.analyze_company = AsyncMock()
        mock_processor.analyze_company.return_value = {
            "name": "New Company",
            "description": "A new company for testing",
            "industry": "Fintech",
            "founding_date": "2020-01-01"
        }
        MockCompanyProcessor.return_value = mock_processor
        
        # Configure the Twitter scraper and analyzer mocks
        MockTwitterScraper.return_value = AsyncMock()
        MockTwitterAnalyzer.return_value = AsyncMock()
        
        # Configure the integration service mock
        integrated_data = {
            "name": "New Company",
            "description": "A new company for testing",
            "industry": "Fintech",
            "founding_date": "2020-01-01",
            "twitter_handle": "newcompany"
        }
        mock_process_company_data.return_value = integrated_data
        
        # Mock the company creation function to return a valid Company object
        db_company = Company(
            id=1,
            name="New Company",
            description="A new company for testing",
            industry="Fintech",
            year_founded=2020,
            twitter_handle="newcompany",
            duke_affiliated=False,
            data_freshness_score=0.9,
            data_quality_score=0.8,
            total_funding=1000000.0
        )
        mock_create_company.return_value = db_company
        
        # Mock the prepare_response method to return a valid response
        mock_prepare_response.return_value = {
            "id": 1,
            "name": "New Company",
            "description": "A new company for testing",
            "industry": "Fintech",
            "year_founded": 2020,
            "twitter_handle": "newcompany",
            "duke_affiliated": False,
            "data_freshness_score": 0.9,
            "data_quality_score": 0.8,
            "total_funding": 1000000.0
        }
        
        # Test the endpoint
        response = client.get("/api/v1/company/New Company")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["name"] == "New Company"
        
    logger.info("✅ test_get_company_new passed")

# Test runner functions
async def run_mock_tests():
    """Run all mock tests."""
    logger.info("Starting mock API tests...")
    
    # Set up the database
    await setup_database()
    
    try:
        # Run basic tests
        await test_ping()
        await test_db_check()
        
        # Run company tests
        await test_get_company_existing()
        await test_get_company_new()
        
        logger.info("All mock tests passed! ✅")
    except Exception as e:
        logger.error(f"Mock test failed: {e}")
        raise
    finally:
        # Clean up the database
        await cleanup_database()

async def run_all_tests():
    """Run all tests."""
    try:
        await run_mock_tests()
        logger.info("All tests completed successfully! ✅")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run API tests")
    parser.add_argument("--mock-data", action="store_true", help="Run mock tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    if args.all or not args.mock_data:
        # Run all tests by default
        asyncio.run(run_all_tests())
    elif args.mock_data:
        # Run only mock tests
        asyncio.run(run_mock_tests()) 