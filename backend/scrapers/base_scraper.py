# backend/scrapers/base_scraper.py
"""
Base scraper for the DCP AI Scouting Platform.

This module provides a foundation for specialized scrapers with common functionality
for making search API requests, handling retries, and processing results.
"""
import logging
import httpx
import asyncio
import json
from datetime import datetime
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional, Dict, Any, List
from backend.config.config import settings
from backend.config.logs import LogManager
from backend.config.cache import cached

# Use the centralized logging configuration
LogManager.setup_logging()
logger = logging.getLogger(__name__)

class BaseScraper:
    """
    Base scraper class with common functionality for all entity types.
    
    Provides foundation for specialized scrapers with HTTP client setup,
    retry logic, result filtering, and common utility methods.
    """

    def __init__(self):
        """Initialize the base scraper with common configuration."""
        # API configuration
        self.api_key = settings.scraper.SERPAPI_KEY
        self.base_url = "https://serpapi.com/search.json"
        
        # Validate API key
        if not self.api_key:
            logger.error("No search API key found. Please set SCRAPER_SERPAPI_KEY in your .env file.")
            raise ValueError("Search API key is required but not provided")
            
        logger.info("Search API initialized with valid key")
        
        # Request configuration
        self.max_results_per_query = 5  # Optimized for relevant results
        self.timeout = settings.scraper.TIMEOUT or 30
        self.client = None
        
        # Rate limiting configuration
        self.rate_limit_delay = 2  # Seconds between batches of queries
        self.batch_size = 3  # Number of queries to run in parallel
        
        # High-quality domains for targeted searches
        self.high_quality_domains = [
            "linkedin.com", "crunchbase.com", "bloomberg.com", 
            "techcrunch.com", "forbes.com", "pitchbook.com",
            "duke.edu", "alumni.duke.edu"
        ]

    async def __aenter__(self):
        """Set up the HTTP client when entering context."""
        self.client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Close the HTTP client when exiting context."""
        if self.client:
            await self.client.aclose()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def fetch_serp(self, query: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Fetch search results from API with retry logic.
        
        Args:
            query: The search query string
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Dictionary containing search results or None if failed
        """
        if not self.client:
            logger.error("HTTP client not initialized. Use with 'async with' context.")
            return None
            
        try:
            # Prepare parameters
            params = {
                "api_key": self.api_key,
                "q": query,
                "google_domain": "google.com",
                "gl": "us",
                "hl": "en",
                "num": self.max_results_per_query,
            }
            params.update(kwargs)
            
            # Log the query (but not the API key)
            log_params = params.copy()
            log_params.pop("api_key", None)
            logger.info(f"Fetching search results: {log_params}")
            
            # Make the request
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Log success
            organic_results = len(data.get("organic_results", []))
            logger.info(f"Search query successful: {query} - {organic_results} organic results")
            
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during search query: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching search results: {e}")
            return None

    def filter_results(self, results: List[Dict[str, Any]], entity_name: str) -> List[Dict[str, Any]]:
        """
        Filter search results to remove irrelevant entries.
        
        Args:
            results: List of search result dictionaries
            entity_name: Name of the entity to filter for
            
        Returns:
            Filtered list of search results
        """
        if not results:
            return []
            
        filtered = []
        entity_lower = entity_name.lower()
        
        for result in results:
            # Skip results without title or snippet
            if not result.get("title") or not result.get("snippet"):
                continue
                
            # Check if entity name appears in title or snippet
            title_lower = result.get("title", "").lower()
            snippet_lower = result.get("snippet", "").lower()
            
            if entity_lower in title_lower or entity_lower in snippet_lower:
                filtered.append(result)
                continue
                
            # Check for high-quality domains
            link = result.get("link", "").lower()
            if any(domain in link for domain in self.high_quality_domains):
                filtered.append(result)
                continue
        
        logger.info(f"Filtered {len(results)} results to {len(filtered)} relevant results")
        return filtered

    async def execute_search_queries(self, queries: Dict[str, List[str]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Execute multiple search queries in batches.
        
        Args:
            queries: Dictionary mapping query types to lists of query strings
            
        Returns:
            Dictionary mapping query types to lists of search results
        """
        results = {}
        
        # Flatten queries for processing
        flat_queries = []
        for query_type, query_list in queries.items():
            for query in query_list:
                flat_queries.append((query_type, query))
        
        # Process in batches
        for i in range(0, len(flat_queries), self.batch_size):
            batch = flat_queries[i:i+self.batch_size]
            
            # Create tasks for concurrent execution
            tasks = []
            for query_type, query in batch:
                tasks.append(self.fetch_serp(query))
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, (query_type, query) in enumerate(batch):
                result = batch_results[j]
                
                # Skip exceptions
                if isinstance(result, Exception):
                    logger.error(f"Query failed: {query} - {str(result)}")
                    continue
                
                # Skip empty results
                if not result or not result.get("organic_results"):
                    continue
                
                # Add to results
                if query_type not in results:
                    results[query_type] = []
                
                results[query_type].extend(result.get("organic_results", []))
            
            # Rate limiting between batches
            if i + self.batch_size < len(flat_queries):
                await asyncio.sleep(self.rate_limit_delay)
        
        return results

    async def save_results(self, results: Dict[str, Any], filename: str) -> Optional[str]:
        """
        Save search results to a JSON file.
        
        Args:
            results: Dictionary containing search results
            filename: Base filename to save results to
            
        Returns:
            Path to saved file or None if failed
        """
        try:
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
            return str(filepath)
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return None 