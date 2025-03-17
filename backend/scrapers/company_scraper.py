# backend/scrapers/company_scraper.py
"""
Company-specific scraper for the DCP AI Scouting Platform.

This module provides specialized functionality for scraping information about
companies, with a focus on funding, market position, and Duke University connections.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.config.logs import LogManager
from backend.config.cache import cached
from backend.scrapers.base_scraper import BaseScraper

# Use the centralized logging configuration
LogManager.setup_logging()
logger = logging.getLogger(__name__)

class CompanyScraper(BaseScraper):
    """
    Company-specific scraper optimized for gathering information about companies.
    
    Focuses on company funding, growth metrics, market position, 
    key executives, and Duke University connections.
    """
    
    def __init__(self):
        """Initialize the company scraper."""
        super().__init__()
    
    def get_company_queries(self, company_name: str) -> Dict[str, List[str]]:
        """
        Generate company-specific search queries.
        
        Args:
            company_name: Name of the company to search for
            
        Returns:
            Dictionary mapping query types to lists of query strings
        """
        # Optimized queries focused on Duke connections and investment relevance
        queries = {
            "company_info": [
                f"{company_name} company overview",
                f"{company_name} description industry sector"
            ],
            "funding_info": [
                f"{company_name} funding rounds series seed investment site:crunchbase.com OR site:pitchbook.com",
                f"{company_name} valuation funding amount investors"
            ],
            "founding_date": [
                f"{company_name} company history founded year"
            ],
            "leadership": [
                f"{company_name} co-founders leadership management team"
            ],
            "duke_connection": [
                f"{company_name} Duke University alumni founder executive" 
                f"{company_name} site:duke.edu OR site:alumni.duke.edu",
                f"{company_name} graduated Duke University"
            ],
            "market_info": [
                f"{company_name} market size competitors industry",
            ],
            "social_media": [
                f"{company_name} twitter linkedin social media profiles"
            ]
        }
        
        logger.info(f"Generated optimized company queries for '{company_name}'")
        return queries
    
    @cached("company_search", expire=86400)  # Cache for 24 hours
    async def comprehensive_search(self, company_name: str) -> Dict[str, Any]:
        """
        Perform a comprehensive search for company information.
        
        Args:
            company_name: Name of the company to search for
            
        Returns:
            Dictionary containing search results and metadata
        """
        logger.info(f"Starting search for company: {company_name}")
        start_time = datetime.now()
        
        # Generate search queries
        queries = self.get_company_queries(company_name)
        
        # Execute search queries
        search_results = await self.execute_search_queries(queries)
        
        # Filter results for relevance
        filtered_results = {}
        for query_type, results in search_results.items():
            filtered_results[query_type] = self.filter_results(results, company_name)
        
        # Calculate metadata
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        total_results = sum(len(results) for results in filtered_results.values())
        
        # Compile final result
        result = {
            "company_name": company_name,
            "results": filtered_results,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "total_results": total_results,
                "query_types": list(filtered_results.keys())
            }
        }
        
        logger.info(f"Completed search for '{company_name}' in {duration:.2f}s with {total_results} results")
        return result
    
    async def search_and_analyze(self, company_name: str) -> Dict[str, Any]:
        """
        Search for company information and collect raw data for NLP processing.
        
        Args:
            company_name: Name of the company to search for
            
        Returns:
            Dictionary containing raw search results for NLP processing
        """
        # Get search results
        search_data = await self.comprehensive_search(company_name)
        
        # Return raw data for NLP processing
        return {
            "company_name": company_name,
            "search_data": search_data,
            "timestamp": datetime.now().isoformat()
        } 