"""
Query Builder Module

Provides utilities for constructing and managing search queries.
Handles query formatting, sanitization, and template management.
"""

from typing import List, Dict, Optional, Any
import re
from ..utils.config import settings

class QueryBuilder:
    """
    Utility for building optimized search queries.
    Handles parameter construction and query formatting.
    """

    def __init__(self):
        """Initialize query builder with default parameters."""
        self.default_params = {
            "num": 10,
            "hl": "en",
            "gl": "us"
        }

    @staticmethod
    def get_company_queries(company_name: str, include_duke: bool = False) -> Dict[str, List[str]]:
        """
        Generate a set of optimized search queries for comprehensive company information
        
        Args:
            company_name: Name of the company to search for
            include_duke: Whether to include Duke University as a search term
            
        Returns:
            Dictionary of query categories with lists of search queries
        """
        # Optimized queries focused on Duke connections and investment relevance
        queries = {
            "company_info": [
                f"{company_name} company overview",
                # f"{company_name} description industry sector"
            ],
            "funding_info": [
                # f"{company_name} funding rounds series seed investment site:crunchbase.com OR site:pitchbook.com",
                f"{company_name} valuation funding amount investors"
            ],
            "founding_date": [
                f"{company_name} company history founded year"
            ],
            "leadership": [
                f"{company_name} co-founders leadership management team"
            ],
            "market_info": [
                f"{company_name} market size competitors industry"
            ],
            "social_media": [
                f"{company_name} twitter linkedin"
            ]
        }
    
            
        return queries
    
    @staticmethod
    def get_founder_queries(founder_name: str, include_duke: bool = False) -> Dict[str, List[str]]:
        """
        Generate a set of optimized search queries for comprehensive founder information
        
        Args:
            founder_name: Name of the founder to search for
            include_duke: Whether to include Duke University as a search term
            
        Returns:
            Dictionary of query categories with lists of search queries
        """
        queries = {
            "bio_info": [
                # f"{founder_name} biography entrepreneur",
                f"{founder_name} professional background experience"
            ],
            "company_info": [
                # f"{founder_name} founder CEO company startups",
                f"{founder_name} current role position"
            ],
            "education": [
                # f"{founder_name} education university degree alumni",
                # f"{founder_name} graduated school college",

            ],
            # Duke affiliation queries
            "duke affiliation": [
                f'"{founder_name}" "Duke University" alumni degree graduate',
                f'"{founder_name}" "Duke" education history affiliation',

            ],
            "social_media": [
                f"{founder_name} twitter linkedin profiles",
                # f"{founder_name} social media accounts"
            ]
        }
        
        return queries