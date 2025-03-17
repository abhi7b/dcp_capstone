# backend/scrapers/founder_scraper.py
"""
Founder-specific scraper for the DCP AI Scouting Platform.

This module provides specialized functionality for scraping information about
founders and entrepreneurs, with a focus on their background, achievements,
and Duke University connections.
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

class FounderScraper(BaseScraper):
    """
    Founder-specific scraper optimized for gathering information about entrepreneurs.
    
    Focuses on founder background, education, professional experience,
    entrepreneurial history, and Duke University connections.
    """
    
    def __init__(self):
        """Initialize the founder scraper."""
        super().__init__()
    
    def get_founder_queries(self, founder_name: str) -> Dict[str, List[str]]:
        """
        Generate founder-specific search queries.
        
        Args:
            founder_name: Name of the founder to search for
            
        Returns:
            Dictionary mapping query types to lists of query strings
        """
        # Optimized queries focused on Duke connections and investment relevance
        queries = {
            "education": [
                f"{founder_name} education Duke University alumni site:linkedin.com",
                f"{founder_name} degree major university education"
            ],
            "professional_experience": [
                f"{founder_name} work experience career history site:linkedin.com",
            ],
            "entrepreneurial_history": [
                f"{founder_name} startup founder CEO companies founded",
                f"{founder_name} entrepreneur ventures founded site:crunchbase.com",
            ],
            "funding_history": [
                f"{founder_name} raised funding venture capital investment",
                f"{founder_name} investors funding rounds"
            ],
            "social_media": [
                f"{founder_name} twitter linkedin social profiles",            ],
            "achievements": [
                f"{founder_name} industry impact innovation"
            ],
        }
        
        logger.info(f"Generated optimized founder queries for '{founder_name}'")
        return queries
    
    @cached("founder_search", expire=86400)  # Cache for 24 hours
    async def comprehensive_search(self, founder_name: str) -> Dict[str, Any]:
        """
        Perform a comprehensive search for founder information.
        
        Args:
            founder_name: Name of the founder to search for
            
        Returns:
            Dictionary containing search results and metadata
        """
        logger.info(f"Starting search for founder: {founder_name}")
        start_time = datetime.now()
        
        # Generate search queries
        queries = self.get_founder_queries(founder_name)
        
        # Execute search queries
        search_results = await self.execute_search_queries(queries)
        
        # Filter results for relevance
        filtered_results = {}
        for query_type, results in search_results.items():
            filtered_results[query_type] = self.filter_results(results, founder_name)
        
        # Calculate metadata
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        total_results = sum(len(results) for results in filtered_results.values())
        
        # Compile final result
        result = {
            "founder_name": founder_name,
            "results": filtered_results,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "total_results": total_results,
                "query_types": list(filtered_results.keys())
            }
        }
        
        logger.info(f"Completed search for '{founder_name}' in {duration:.2f}s with {total_results} results")
        return result
    
    async def search_and_analyze(self, founder_name: str) -> Dict[str, Any]:
        """
        Search for founder information and collect raw data for NLP processing.
        
        Args:
            founder_name: Name of the founder to search for
            
        Returns:
            Dictionary containing raw search results for NLP processing
        """
        # Get search results
        search_data = await self.comprehensive_search(founder_name)
        
        # Return raw data for NLP processing
        return {
            "founder_name": founder_name,
            "search_data": search_data,
            "timestamp": datetime.now().isoformat()
        } 