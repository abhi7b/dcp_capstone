#!/usr/bin/env python
"""
Simple test script for the scrapers module.

This script demonstrates how to use the CompanyScraper and FounderScraper
classes to search for information about companies and founders.
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Import from the backend package
from backend.config import init_logging, get_logger
from backend.scrapers import CompanyScraper, FounderScraper

# Initialize logging
init_logging()
logger = get_logger(__name__)

async def test_company_scraper(company_name: str):
    """Test the CompanyScraper with a given company name."""
    logger.info(f"Testing CompanyScraper with company: {company_name}")
    
    async with CompanyScraper() as scraper:
        # Test comprehensive search
        logger.info("Running comprehensive search...")
        results = await scraper.comprehensive_search(company_name)
        
        # Print summary
        total_results = results["metadata"]["total_results"]
        duration = results["metadata"]["duration_seconds"]
        logger.info(f"Found {total_results} results in {duration:.2f} seconds")
        
        # Print query types and result counts
        for query_type, query_results in results["results"].items():
            logger.info(f"  - {query_type}: {len(query_results)} results")
        
        # Test search and analyze (now just returns raw data)
        logger.info("Running search and analyze...")
        raw_data = await scraper.search_and_analyze(company_name)
        logger.info(f"Raw data collected for {company_name} (timestamp: {raw_data['timestamp']})")
        
        return results

async def test_founder_scraper(founder_name: str):
    """Test the FounderScraper with a given founder name."""
    logger.info(f"Testing FounderScraper with founder: {founder_name}")
    
    async with FounderScraper() as scraper:
        # Test comprehensive search
        logger.info("Running comprehensive search...")
        results = await scraper.comprehensive_search(founder_name)
        
        # Print summary
        total_results = results["metadata"]["total_results"]
        duration = results["metadata"]["duration_seconds"]
        logger.info(f"Found {total_results} results in {duration:.2f} seconds")
        
        # Print query types and result counts
        for query_type, query_results in results["results"].items():
            logger.info(f"  - {query_type}: {len(query_results)} results")
        
        # Test search and analyze (now just returns raw data)
        logger.info("Running search and analyze...")
        raw_data = await scraper.search_and_analyze(founder_name)
        logger.info(f"Raw data collected for {founder_name} (timestamp: {raw_data['timestamp']})")
        
        return results

async def save_results(results, filename):
    """Save results to a JSON file."""
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Add timestamp to filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"{filename}_{timestamp}.json"
    
    # Save to file
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Saved results to {filepath}")
    return filepath

async def main():
    """Run tests for both scrapers."""
    logger.info("Starting scraper tests")
    
    # Test company scraper
    company_name = "Stripe"  # Example company with likely Duke connections
    company_results = await test_company_scraper(company_name)
    await save_results(company_results, f"company_{company_name.lower()}")
    
    # Test founder scraper
    founder_name = "Tim Cook"  # Example founder
    founder_results = await test_founder_scraper(founder_name)
    await save_results(founder_results, f"founder_{founder_name.lower().replace(' ', '_')}")
    
    logger.info("Scraper tests completed successfully")

if __name__ == "__main__":
    asyncio.run(main())