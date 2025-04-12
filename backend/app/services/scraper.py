"""
SERP Scraper Module

Service for scraping search engine results using SERP API.
Handles search queries, result parsing, and rate limiting.

Key Features:
- Search result scraping
- Query optimization
- Result parsing
- Rate limiting
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from serpapi import GoogleSearch
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..utils.config import settings
from ..utils.logger import scraper_logger as logger
from .query_utils import QueryBuilder
from ..utils.storage import StorageService

class SERPScraper:
    """
    Service for scraping search engine results.
    Handles API interaction and result processing.
    """
    
    def __init__(self):
        """Initialize scraper with API key and StorageService."""
        self.api_key = settings.SERPAPI_KEY
        self.query_builder = QueryBuilder()
        self.storage = StorageService()
        logger.info("SERPScraper initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception, ConnectionError))
    )
    async def search(self, query: str, time_filter: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
        """
        Execute a search query using SERP API
        
        Args:
            query: The search query
            time_filter: Time filter (e.g., 'm3', 'm6', 'y1')
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results
        """
        logger.info(f"Executing SERP search for query: {query}")
        
        # Build search parameters
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": 20,  # Number of results to request from API
            "gl": "us",  # Country code for Google search
        }
        
        # Add time filter if provided
        if time_filter:
            params["tbs"] = f"qdr:{time_filter}"
        
        try:
            # Execute search
            logger.debug(f"SERP API params: {params}")
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Limit number of organic results
            if "organic_results" in results and max_results > 0:
                results["organic_results"] = results["organic_results"][:max_results]
            
            # Log results summary
            organic_results_count = len(results.get("organic_results", []))
            logger.info(f"SERP search returned {organic_results_count} organic results")
            
            return results
        
        except Exception as e:
            logger.error(f"SERP search failed: {str(e)}")
            raise
    
    async def search_company(self, company_name: str, max_results_per_query: int = 5) -> Dict[str, Any]:
        """
        Search for comprehensive company information by running multiple optimized queries.
        Runs ALL queries defined for each category in query_utils to gather raw data.
        
        Args:
            company_name: Name of the company to search for
            max_results_per_query: Maximum number of results to keep from each individual query (default: 5)
            
        Returns:
            Dictionary containing combined, deduplicated search results from all executed queries.
        """
        logger.info(f"Starting multi-query search for company: {company_name}")
        company_queries = self.query_builder.get_company_queries(company_name)
        
        all_categories = [
            "company_info", "funding_info", "leadership", 
            "market_info", "social_media", "founding_date"
        ]
        
        combined_results = {
            "search_parameters": {"query": f"Multi-query search for {company_name}"},
            "organic_results": [],
            "query_summary": {}
        }
        existing_urls = set()
        total_queries_run = 0

        # Run ALL queries from each category
        for category in all_categories:
            combined_results["query_summary"][category] = [] # Store list of query results for category
            if category in company_queries and company_queries[category]:
                for query in company_queries[category]: # Iterate through all queries in the list
                    logger.info(f"Running {category} query: {query}")
                    total_queries_run += 1
                    try:
                        category_results = await self.search(query, max_results=max_results_per_query)
                    except Exception as e:
                         logger.error(f"SERP search failed for query '{query}': {e}. Skipping query.")
                         combined_results["query_summary"][category].append({
                             "query": query,
                             "results_count": 0,
                             "error": str(e)
                         })
                         continue # Skip to next query if one fails

                    results_count = len(category_results.get("organic_results", []))
                    combined_results["query_summary"][category].append({
                        "query": query,
                        "results_count": results_count
                    })
                    
                    if results_count > 0:
                        new_results = category_results["organic_results"]
                        logger.info(f"Found {results_count} results for query: {query}")
                        
                        for result in new_results:
                            url = result.get("link")
                            if url and url not in existing_urls:
                                combined_results["organic_results"].append(result)
                                existing_urls.add(url)
            else:
                 logger.warning(f"No queries defined for category '{category}' for {company_name}")

        total_results = len(combined_results["organic_results"])
        logger.info(f"Ran {total_queries_run} total queries across {len(all_categories)} categories. Found {total_results} unique results.")
        
        if total_results == 0:
            logger.warning(f"Multi-query search found no results for company: {company_name}")
            
        file_path = self.storage.save_raw_data(combined_results, "serp_company", company_name)
        combined_results["_file_path"] = file_path
            
        return combined_results
    
    async def search_founder(self, founder_name: str, max_results_per_query: int = 5) -> Dict[str, Any]:
        """
        Search for comprehensive founder information by running multiple optimized queries.
        Runs ALL queries defined for each category in query_utils (including Duke affiliation) to gather raw data.
        
        Args:
            founder_name: Name of the founder to search for
            max_results_per_query: Maximum number of results to keep from each individual query (default: 5)
            
        Returns:
            Dictionary containing combined, deduplicated search results from all executed queries.
        """
        logger.info(f"Starting multi-query search for founder: {founder_name}")
        founder_queries = self.query_builder.get_founder_queries(founder_name)
        
        all_categories = [
            "bio_info", "company_info", "education", 
            "duke affiliation", "social_media", "funding_history"
        ]
        
        combined_results = {
            "search_parameters": {"query": f"Multi-query search for {founder_name}"},
            "organic_results": [],
            "query_summary": {}
        }
        existing_urls = set()
        total_queries_run = 0
        
        # Run ALL queries from each category
        for category in all_categories:
            combined_results["query_summary"][category] = [] # Store list of query results
            if category in founder_queries and founder_queries[category]:
                for query in founder_queries[category]: # Iterate through all queries
                    logger.info(f"Running {category} query: {query}")
                    total_queries_run += 1
                    try:
                        category_results = await self.search(query, max_results=max_results_per_query)
                    except Exception as e:
                         logger.error(f"SERP search failed for query '{query}': {e}. Skipping query.")
                         combined_results["query_summary"][category].append({
                             "query": query,
                             "results_count": 0,
                             "error": str(e)
                         })
                         continue # Skip to next query
                         
                    results_count = len(category_results.get("organic_results", []))
                    combined_results["query_summary"][category].append({
                        "query": query,
                        "results_count": results_count
                    })
                    
                    if results_count > 0:
                        new_results = category_results["organic_results"]
                        logger.info(f"Found {results_count} results for query: {query}")
                        
                        for result in new_results:
                            url = result.get("link")
                            if url and url not in existing_urls:
                                combined_results["organic_results"].append(result)
                                existing_urls.add(url)
            else:
                 logger.warning(f"No queries defined for category '{category}' for {founder_name}")

        total_results = len(combined_results["organic_results"])
        logger.info(f"Ran {total_queries_run} total queries across {len(all_categories)} categories. Found {total_results} unique results.")
        
        if total_results == 0:
            logger.warning(f"Multi-query search found no results for founder: {founder_name}")
        
        file_path = self.storage.save_raw_data(combined_results, "serp_person", founder_name)
        combined_results["_file_path"] = file_path
            
        return combined_results
       