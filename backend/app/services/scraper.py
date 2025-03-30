import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from serpapi import GoogleSearch
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..utils.config import settings
from ..utils.logger import scraper_logger
from ..utils.query_utils import QueryBuilder

class SERPScraper:
    """
    Service for scraping search engine results using SERP API
    """
    
    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.raw_data_dir = settings.RAW_DATA_DIR
        self.query_builder = QueryBuilder()
        scraper_logger.info("SERPScraper initialized")
    
    def _save_raw_data(self, data: Dict[str, Any], entity_name: str) -> str:
        """Save raw JSON data to file and return the file path"""
        # Create timestamp and sanitize entity name for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_name = entity_name.replace('"', '').replace(' ', '_')[:50]  # Limit length
        
        # Create filename and path
        filename = f"serp_{sanitized_name}.json"
        file_path = os.path.join(self.raw_data_dir, filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write data to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        scraper_logger.info(f"Raw SERP data saved to {file_path}")
        return file_path
    
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
        scraper_logger.info(f"Executing SERP search for query: {query}")
        
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
            scraper_logger.debug(f"SERP API params: {params}")
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Limit number of organic results
            if "organic_results" in results and max_results > 0:
                results["organic_results"] = results["organic_results"][:max_results]
            
            # Log results summary
            organic_results_count = len(results.get("organic_results", []))
            scraper_logger.info(f"SERP search returned {organic_results_count} organic results")
            
            return results
        
        except Exception as e:
            scraper_logger.error(f"SERP search failed: {str(e)}")
            raise
    
    async def search_company(self, company_name: str, max_results_per_query: int = 10) -> Dict[str, Any]:
        """
        Search for comprehensive company information by running multiple optimized queries.
        Runs all query categories from query_utils to gather raw data.
        
        Args:
            company_name: Name of the company to search for
            max_results_per_query: Maximum number of results to keep from each query
            
        Returns:
            Dictionary containing combined search results from multiple queries
        """
        # Get all optimized queries for this company (always include all categories)
        company_queries = self.query_builder.get_company_queries(company_name, include_duke=True)
        
        # Start with company info query as primary search
        primary_query = company_queries["company_info"][0]
        scraper_logger.info(f"Executing primary company query: {primary_query}")
        primary_results = await self.search(primary_query, max_results=max_results_per_query)
        
        # Create a composite results dictionary that will contain all organic results
        combined_results = primary_results.copy()
        combined_results["organic_results"] = primary_results.get("organic_results", []) or []
        
        # Keep track of query categories and results for unified file
        query_results = {
            "company_info": {
                "query": primary_query,
                "results_count": len(combined_results["organic_results"])
            }
        }
        
        # Get all query categories (excluding the primary one we already ran)
        additional_categories = [
            "funding_info", 
            "leadership", 
            "market_info", 
            "social_media", 
            "founding_date",
            "duke_connection"  # Always include Duke queries, LLM will determine relevance
        ]
        
        # Run one query from each category
        for category in additional_categories:
            if category in company_queries and company_queries[category]:
                query = company_queries[category][0]
                scraper_logger.info(f"Running {category} query: {query}")
                category_results = await self.search(query, max_results=max_results_per_query)
                
                # Record query and results count
                query_results[category] = {
                    "query": query,
                    "results_count": len(category_results.get("organic_results", []))
                }
                
                # Add unique results to our combined set
                if "organic_results" in category_results and category_results["organic_results"]:
                    new_results = category_results["organic_results"]
                    scraper_logger.info(f"Found {len(new_results)} results for {category}")
                    
                    # Add to our combined results, avoiding duplicates by URL
                    existing_urls = [r.get("link") for r in combined_results["organic_results"]]
                    for result in new_results:
                        if result.get("link") not in existing_urls:
                            combined_results["organic_results"].append(result)
                            existing_urls.append(result.get("link"))
        
        # Add query information to combined results
        combined_results["query_summary"] = query_results
        
        total_results = len(combined_results.get("organic_results", []))
        scraper_logger.info(f"Combined results from multiple queries: {total_results} total results")
        
        if total_results > 0:
            scraper_logger.info(f"Found {total_results} total results for company: {company_name}")
        else:
            scraper_logger.warning(f"No results found for company: {company_name}")
            
        # Save all results to a single file
        file_path = self._save_raw_data(combined_results, company_name)
        combined_results["_file_path"] = file_path
            
        return combined_results
    
    async def search_founder(self, founder_name: str, max_results_per_query: int = 10) -> Dict[str, Any]:
        """
        Search for comprehensive founder information by running multiple optimized queries.
        Runs all query categories from query_utils to gather raw data.
        
        Args:
            founder_name: Name of the founder to search for
            max_results_per_query: Maximum number of results to keep from each query
            
        Returns:
            Dictionary containing combined search results from multiple queries
        """
        # Get all optimized queries for this founder (always include all categories)
        founder_queries = self.query_builder.get_founder_queries(founder_name, include_duke=True)
        
        # Start with bio info query as primary search
        primary_query = founder_queries["bio_info"][0]
        scraper_logger.info(f"Executing primary founder query: {primary_query}")
        primary_results = await self.search(primary_query, max_results=max_results_per_query)
        
        # Create a composite results dictionary that will contain all organic results
        combined_results = primary_results.copy()
        combined_results["organic_results"] = primary_results.get("organic_results", []) or []
        
        # Keep track of query categories and results for unified file
        query_results = {
            "bio_info": {
                "query": primary_query,
                "results_count": len(combined_results["organic_results"])
            }
        }
        
        # Get all query categories (excluding the primary one we already ran)
        additional_categories = [
            "company_info", 
            "education", 
            "social_media", 
            "funding_history",
            "duke_connection"  # Always include Duke queries, LLM will determine relevance
        ]
        
        # Run one query from each category
        for category in additional_categories:
            if category in founder_queries and founder_queries[category]:
                query = founder_queries[category][0]
                scraper_logger.info(f"Running {category} query: {query}")
                category_results = await self.search(query, max_results=max_results_per_query)
                
                # Record query and results count
                query_results[category] = {
                    "query": query,
                    "results_count": len(category_results.get("organic_results", []))
                }
                
                # Add unique results to our combined set
                if "organic_results" in category_results and category_results["organic_results"]:
                    new_results = category_results["organic_results"]
                    scraper_logger.info(f"Found {len(new_results)} results for {category}")
                    
                    # Add to our combined results, avoiding duplicates by URL
                    existing_urls = [r.get("link") for r in combined_results["organic_results"]]
                    for result in new_results:
                        if result.get("link") not in existing_urls:
                            combined_results["organic_results"].append(result)
                            existing_urls.append(result.get("link"))
        
        # Add query information to combined results
        combined_results["query_summary"] = query_results
        
        total_results = len(combined_results.get("organic_results", []))
        scraper_logger.info(f"Combined results from multiple queries: {total_results} total results")
        
        if total_results > 0:
            scraper_logger.info(f"Found {total_results} total results for founder: {founder_name}")
        else:
            scraper_logger.warning(f"No results found for founder: {founder_name}")
        
        # Save all results to a single file
        file_path = self._save_raw_data(combined_results, founder_name)
        combined_results["_file_path"] = file_path
            
        return combined_results
        
    async def search_person_duke_affiliation(self, person_name: str, max_results_per_query: int = 5) -> Dict[str, Any]:
        """
        Search specifically for evidence of a person's Duke affiliation using focused queries.
        
        Args:
            person_name: Name of the person to check for Duke affiliation
            max_results_per_query: Maximum number of results to keep from each query
            
        Returns:
            Dictionary containing results from Duke-specific searches
        """
        scraper_logger.info(f"Searching for Duke affiliation evidence for: {person_name}")
        
        # Get Duke-specific queries
        duke_queries = self.query_builder.get_person_duke_affiliation_queries(person_name)
        
        combined_results = {
            "person_name": person_name,
            "organic_results": [],
            "query_summary": {}
        }
        
        # Run each Duke-specific query (these are more focused, so we run all of them)
        for i, query in enumerate(duke_queries):
            query_key = f"duke_query_{i+1}"
            scraper_logger.info(f"Running Duke affiliation query {i+1}: {query}")
            
            # Run the search
            query_results = await self.search(query, max_results=max_results_per_query)
            
            # Record query and results count
            result_count = len(query_results.get("organic_results", []))
            combined_results["query_summary"][query_key] = {
                "query": query,
                "results_count": result_count
            }
            
            # Add results to combined set, avoiding duplicates
            if "organic_results" in query_results and query_results["organic_results"]:
                new_results = query_results["organic_results"]
                
                # Add to our combined results, avoiding duplicates by URL
                existing_urls = [r.get("link") for r in combined_results["organic_results"]]
                for result in new_results:
                    if result.get("link") not in existing_urls:
                        combined_results["organic_results"].append(result)
                        existing_urls.append(result.get("link"))
        
        total_results = len(combined_results.get("organic_results", []))
        scraper_logger.info(f"Found {total_results} Duke-related results for {person_name}")
        
        # Save all results to a single file
        file_path = self._save_raw_data(combined_results, f"{person_name}_duke_affiliation")
        combined_results["_file_path"] = file_path
            
        return combined_results
    
