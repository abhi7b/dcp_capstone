#!/usr/bin/env python3
"""
Test script for the improved company scraper.

This script demonstrates how to use the updated CompanyScraper to gather
comprehensive information about companies with a focus on Duke connections
and investment potential.
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from backend.scrapers.company_scraper import CompanyScraper
from backend.config.logs import LogManager

# Set up logging
LogManager.setup_logging()
logger = logging.getLogger(__name__)

# Create output directory if it doesn't exist
OUTPUT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

async def test_company_scraper():
    """Test the improved company scraper with Duke-affiliated companies."""
    logger.info("Starting improved company scraper test")
    
    # Initialize the company scraper
    scraper = CompanyScraper()
    
    # List of companies to test (including known Duke-affiliated companies)
    companies = [
        "Stripe",  # For comparison with previous results
        "SoFi",    # Financial technology company
        "Coinbase", # Cryptocurrency exchange
        "Aerie Pharmaceuticals", # Duke-affiliated pharmaceutical company
        "Precision BioSciences"  # Duke-affiliated biotech company
    ]
    
    # Process each company
    for company in companies:
        logger.info(f"Processing company: {company}")
        
        # Get comprehensive company information
        result = await scraper.comprehensive_search(company)
        
        # Save the result to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"company_{company.lower().replace(' ', '_')}_{timestamp}.json"
        output_path = OUTPUT_DIR / filename
        
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Saved results for {company} to {output_path}")
        
        # Print summary of results
        print(f"\n=== {company} Search Results Summary ===")
        print(f"Total results: {result['metadata']['total_results']}")
        print(f"Query types: {', '.join(result['metadata']['query_types'])}")
        print(f"Duration: {result['metadata']['duration_seconds']:.2f} seconds")
        
        # Print sample of results for each query type
        for query_type, results in result['results'].items():
            print(f"\n{query_type.upper()} ({len(results)} results):")
            # Show first result snippet for each query type
            if results:
                print(f"  - {results[0]['snippet'][:150]}...")
        
        print("\n" + "="*50)

async def test_duke_affiliation_search():
    """Test specific Duke affiliation search capabilities."""
    logger.info("Testing Duke affiliation search")
    
    # Initialize the company scraper
    scraper = CompanyScraper()
    
    # Known Duke-affiliated companies
    duke_companies = [
        "Aerie Pharmaceuticals",
        "Precision BioSciences",
        "Cellective Therapeutics",
        "Humacyte"
    ]
    
    for company in duke_companies:
        # Focus on Duke connection queries
        duke_queries = {
            "duke_connection": scraper.get_company_queries(company)["duke_connection"]
        }
        
        # Execute only Duke-related queries
        results = await scraper.execute_search_queries(duke_queries)
        
        # Save the results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"duke_connection_{company.lower().replace(' ', '_')}_{timestamp}.json"
        output_path = OUTPUT_DIR / filename
        
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Saved Duke connection results for {company} to {output_path}")
        
        # Print summary
        print(f"\n=== Duke Connection: {company} ===")
        if results["duke_connection"]:
            for i, result in enumerate(results["duke_connection"][:3]):
                print(f"{i+1}. {result['title']}")
                print(f"   {result['snippet'][:150]}...")
        else:
            print("No Duke connections found")
        
        print("\n" + "="*50)

async def main():
    """Run the test functions."""
    logger.info("Starting improved scraper tests")
    
    # Run the tests
    await test_company_scraper()
    await test_duke_affiliation_search()
    
    logger.info("Completed improved scraper tests")

if __name__ == "__main__":
    asyncio.run(main()) 