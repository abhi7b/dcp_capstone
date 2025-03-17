#!/usr/bin/env python
"""
Test data insertion utility.

Inserts sample data into the PostgreSQL database for testing purposes.
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import json


from backend.config import settings, init_logging, get_logger
from db.database.db import engine, close_db_connection, get_db_context
from db.database.models import Company, Founder, CompanyFounder, FundingStage, User, APIUser, SERPUsage
from sqlalchemy import select

# Initialize logging
init_logging()
logger = get_logger(__name__)

async def insert_test_data(force=False):
    """Insert sample data into the database."""
    logger.info("Inserting test data into the database")
    
    try:
        async with get_db_context() as session:
            # Check if data already exists
            if not force:
                company_count = await session.execute(select(Company))
                if len(company_count.scalars().all()) > 0:
                    logger.info("Test data already exists in the database. Use --force to override.")
                    return True
            
            # Sample data
            # Create test companies
            companies = [
                Company(
                    name="Duke AI Ventures",
                    domain="dukeaiventures.com",
                    linkedin_url="https://linkedin.com/company/duke-ai-ventures",
                    twitter_handle="dukeaiventures",
                    year_founded=2023,
                    industry="Artificial Intelligence",
                    description="A Duke-affiliated AI startup focused on venture capital investments.",
                    location="Durham, NC",
                    duke_affiliated=True,
                    duke_connection_type=["founder_alumni", "partnership"],
                    duke_department="Computer Science",
                    duke_affiliation_confidence=0.95,
                    total_funding=5000000,
                    latest_valuation=25000000,
                    latest_funding_stage=FundingStage.SEED,
                    competitors=["OpenAI Ventures", "Google Ventures"],
                    funding_rounds=json.dumps([
                        {
                            "stage": "pre-seed",
                            "amount": 1000000,
                            "date": "2023-01-15",
                            "lead_investor": "Duke Angel Network"
                        },
                        {
                            "stage": "seed",
                            "amount": 4000000,
                            "date": "2023-06-30",
                            "lead_investor": "Andreessen Horowitz"
                        }
                    ]),
                    data_freshness_score=0.9,
                    last_data_refresh=datetime.utcnow(),
                    data_sources=["LinkedIn", "Crunchbase", "Company Website"]
                ),
                Company(
                    name="Blue Devil Biotech",
                    domain="bluedevilbiotech.com",
                    linkedin_url="https://linkedin.com/company/blue-devil-biotech",
                    twitter_handle="bluedevilbio",
                    year_founded=2020,
                    industry="Biotechnology",
                    description="A biotechnology company founded by Duke alumni focused on gene therapy.",
                    location="Research Triangle Park, NC",
                    duke_affiliated=True,
                    duke_connection_type=["founder_alumni", "research_partnership"],
                    duke_department="School of Medicine",
                    duke_affiliation_confidence=0.98,
                    total_funding=12000000,
                    latest_valuation=60000000,
                    latest_funding_stage=FundingStage.SERIES_A,
                    competitors=["Genentech", "Biogen"],
                    data_freshness_score=0.85,
                    last_data_refresh=datetime.utcnow() - timedelta(days=30),
                    data_sources=["LinkedIn", "Crunchbase", "SEC Filings"]
                ),
                Company(
                    name="TechCorp Solutions",
                    domain="techcorpsolutions.com",
                    linkedin_url="https://linkedin.com/company/techcorp-solutions",
                    twitter_handle="techcorpsol",
                    year_founded=2019,
                    industry="Enterprise Software",
                    description="Enterprise software solutions for mid-market companies.",
                    location="San Francisco, CA",
                    duke_affiliated=False,
                    total_funding=8000000,
                    latest_funding_stage=FundingStage.SEED,
                    data_freshness_score=0.7,
                    last_data_refresh=datetime.utcnow() - timedelta(days=60),
                    data_sources=["Crunchbase", "Company Website"]
                )
            ]
            
            # Create test founders
            founders = [
                Founder(
                    full_name="Jane Smith",
                    linkedin_url="https://linkedin.com/in/janesmith",
                    twitter_handle="janesmith",
                    current_position="CEO",
                    current_company="Duke AI Ventures",
                    duke_affiliated=True,
                    graduation_year=2015,
                    duke_affiliation_confidence=0.99,
                    education=json.dumps([
                        {
                            "school": "Duke University",
                            "degree": "BS Computer Science",
                            "year": 2015
                        },
                        {
                            "school": "Stanford University",
                            "degree": "MBA",
                            "year": 2018
                        }
                    ]),
                    work_history=json.dumps([
                        {
                            "company": "Google",
                            "position": "Product Manager",
                            "start_year": 2015,
                            "end_year": 2018
                        },
                        {
                            "company": "Duke AI Ventures",
                            "position": "CEO",
                            "start_year": 2018,
                            "end_year": None
                        }
                    ]),
                    data_freshness_score=0.95,
                    last_data_refresh=datetime.utcnow(),
                    data_sources=["LinkedIn", "Duke Alumni Directory"]
                ),
                Founder(
                    full_name="Michael Johnson",
                    linkedin_url="https://linkedin.com/in/michaeljohnson",
                    twitter_handle="mjohnson",
                    current_position="CTO",
                    current_company="Duke AI Ventures",
                    duke_affiliated=True,
                    graduation_year=2016,
                    duke_affiliation_confidence=0.97,
                    education=json.dumps([
                        {
                            "school": "Duke University",
                            "degree": "MS Computer Science",
                            "year": 2016
                        }
                    ]),
                    data_freshness_score=0.9,
                    last_data_refresh=datetime.utcnow() - timedelta(days=15),
                    data_sources=["LinkedIn", "Company Website"]
                ),
                Founder(
                    full_name="Sarah Williams",
                    linkedin_url="https://linkedin.com/in/sarahwilliams",
                    twitter_handle="sarahw",
                    current_position="CEO",
                    current_company="Blue Devil Biotech",
                    duke_affiliated=True,
                    graduation_year=2010,
                    duke_affiliation_confidence=0.98,
                    education=json.dumps([
                        {
                            "school": "Duke University",
                            "degree": "PhD Biomedical Engineering",
                            "year": 2010
                        }
                    ]),
                    data_freshness_score=0.85,
                    last_data_refresh=datetime.utcnow() - timedelta(days=45),
                    data_sources=["LinkedIn", "Duke Alumni Directory"]
                ),
                Founder(
                    full_name="David Chen",
                    linkedin_url="https://linkedin.com/in/davidchen",
                    twitter_handle="dchen",
                    current_position="CEO",
                    current_company="TechCorp Solutions",
                    duke_affiliated=False,
                    education=json.dumps([
                        {
                            "school": "MIT",
                            "degree": "BS Computer Science",
                            "year": 2012
                        }
                    ]),
                    data_freshness_score=0.7,
                    last_data_refresh=datetime.utcnow() - timedelta(days=90),
                    data_sources=["LinkedIn", "Crunchbase"]
                )
            ]
            
            # Add to session
            for company in companies:
                session.add(company)
            
            for founder in founders:
                session.add(founder)
            
            # Commit to save companies and founders
            await session.commit()
            
            # Now create associations
            # Refresh objects to get their IDs
            for company in companies:
                await session.refresh(company)
            
            for founder in founders:
                await session.refresh(founder)
            
            # Create company-founder associations
            associations = [
                # Duke AI Ventures founders
                CompanyFounder(
                    company_id=companies[0].id,  # Duke AI Ventures
                    founder_id=founders[0].id,   # Jane Smith
                    role="CEO"
                ),
                CompanyFounder(
                    company_id=companies[0].id,  # Duke AI Ventures
                    founder_id=founders[1].id,   # Michael Johnson
                    role="CTO"
                ),
                # Blue Devil Biotech founders
                CompanyFounder(
                    company_id=companies[1].id,  # Blue Devil Biotech
                    founder_id=founders[2].id,   # Sarah Williams
                    role="CEO"
                ),
                # TechCorp Solutions founders
                CompanyFounder(
                    company_id=companies[2].id,  # TechCorp Solutions
                    founder_id=founders[3].id,   # David Chen
                    role="CEO"
                )
            ]
            
            for assoc in associations:
                session.add(assoc)
            
            # Create a test user
            test_user = User(
                username="testuser",
                email="test@example.com",
                full_name="Test User",
                is_active=True,
                is_admin=True
            )
            session.add(test_user)
            
            # Commit all associations and user
            await session.commit()
            
            # Add API key for the test user
            await session.refresh(test_user)
            api_key = APIUser(
                user_id=test_user.id,
                name="Test API Key",
                api_key="test_api_key_12345",
                scopes=["companies:read", "founders:read"],
                expires_at=datetime.utcnow() + timedelta(days=365)
            )
            session.add(api_key)
            
            # Add some SERP usage data
            serp_usages = [
                SERPUsage(
                    query_count=5,
                    entity_name="Duke AI Ventures",
                    entity_type="company",
                    endpoint="/api/v1/companies/search"
                ),
                SERPUsage(
                    query_count=3,
                    entity_name="Jane Smith",
                    entity_type="founder",
                    endpoint="/api/v1/founders/search"
                )
            ]
            
            for usage in serp_usages:
                session.add(usage)
            
            # Final commit
            await session.commit()
            
            logger.info(f"Successfully inserted test data: {len(companies)} companies, {len(founders)} founders")
            return True
            
    except Exception as e:
        logger.error(f"Failed to insert test data: {e}")
        return False

async def verify_test_data():
    """Verify that test data was inserted correctly."""
    try:
        async with get_db_context() as session:
            # Count companies
            company_result = await session.execute(select(Company))
            companies = company_result.scalars().all()
            logger.info(f"Found {len(companies)} companies in database")
            
            # Count founders
            founder_result = await session.execute(select(Founder))
            founders = founder_result.scalars().all()
            logger.info(f"Found {len(founders)} founders in database")
            
            # Get Duke-affiliated companies
            duke_company_result = await session.execute(
                select(Company).where(Company.duke_affiliated == True)
            )
            duke_companies = duke_company_result.scalars().all()
            logger.info(f"Found {len(duke_companies)} Duke-affiliated companies")
            
            # Get Duke-affiliated founders
            duke_founder_result = await session.execute(
                select(Founder).where(Founder.duke_affiliated == True)
            )
            duke_founders = duke_founder_result.scalars().all()
            logger.info(f"Found {len(duke_founders)} Duke-affiliated founders")
            
            return True
    except Exception as e:
        logger.error(f"Failed to verify test data: {e}")
        return False

async def main(force=False):
    """Insert test data and verify it."""
    logger.info("Starting test data insertion")
    
    try:
        # Insert test data
        success = await insert_test_data(force=force)
        if not success:
            logger.error("Failed to insert test data. Exiting.")
            return 1
        
        # Verify test data
        verify_success = await verify_test_data()
        if not verify_success:
            logger.error("Failed to verify test data. Exiting.")
            return 1
        
        logger.info("Test data insertion complete!")
        return 0
    finally:
        # Always close the database connection
        await close_db_connection()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Insert test data into the database")
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force insert even if data exists"
    )
    args = parser.parse_args()
    
    # Run the main function
    exit_code = asyncio.run(main(force=args.force))
    sys.exit(exit_code) 