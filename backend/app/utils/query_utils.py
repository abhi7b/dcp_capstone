from typing import List, Dict, Optional

class QueryBuilder:
    """Utility class to build optimized search queries for various purposes"""
    
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
            "market_info": [
                f"{company_name} market size competitors industry"
            ],
            "social_media": [
                f"{company_name} twitter linkedin social media profiles"
            ]
        }
        
        # Add Duke-specific queries if requested
        if include_duke:
            queries["duke_connection"] = [
                f"{company_name} Duke University alumni founder executive",
                f"{company_name} site:duke.edu OR site:alumni.duke.edu",
                f"{company_name} graduated Duke University"
            ]
            
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
                f"{founder_name} biography entrepreneur",
                f"{founder_name} professional background experience"
            ],
            "company_info": [
                f"{founder_name} founder CEO company startups",
                f"{founder_name} current role position"
            ],
            "education": [
                f"{founder_name} education university degree alumni",
                f"{founder_name} graduated school college"
            ],
            "social_media": [
                f"{founder_name} twitter linkedin profiles",
                f"{founder_name} social media accounts"
            ],
            "funding_history": [
                f"{founder_name} funding raised investors venture capital"
            ]
        }
        
        # Add Duke-specific queries if requested
        if include_duke:
            queries["duke_connection"] = [
                f"{founder_name} Duke University alumni",
                f"{founder_name} site:duke.edu OR site:alumni.duke.edu",
                f"{founder_name} graduated Duke University"
            ]
            
        return queries
    
    @staticmethod
    def build_site_specific_query(term: str, sites: List[str]) -> str:
        """
        Build a site-specific search query using Google's site: operator
        
        Args:
            term: The search term
            sites: List of sites to search (e.g., ['techcrunch.com', 'crunchbase.com'])
            
        Returns:
            Formatted search query string with site: operators
        """
        site_operators = " OR ".join([f'site:{site}' for site in sites])
        return f'{term} ({site_operators})'
    
    @staticmethod
    def build_duke_startup_discovery_query(time_filter: str = "m6") -> str:
        """
        Build a search query to discover Duke-affiliated startups
        
        Args:
            time_filter: Time filter (m3 = 3 months, m6 = 6 months, y1 = 1 year)
            
        Returns:
            Formatted search query string
        """
        base_terms = [
            '"Duke University" AND "founder" AND startup',
            '"Duke alumni" AND "series a"',
            '"Duke graduate" AND "CEO" AND funding',
            '"Duke University" AND entrepreneur AND raised',
        ]
        
        # Return a random term from the list (when called by scheduler)
        # In a real implementation, we would cycle through all terms
        import random
        query = random.choice(base_terms)
        
        # Add time filter parameter for SERP API
        if time_filter:
            return f"{query} &tbs=qdr:{time_filter}"
        
        return query
    
    @staticmethod
    def get_predefined_search_queries() -> List[Dict[str, str]]:
        """
        Return a list of predefined search queries for the scheduler
        
        Returns:
            List of query dictionaries with query text and metadata
        """
        return [
            {
                "query": '"Duke University" AND "founder" AND startup',
                "type": "discovery",
                "time_filter": "m6"
            },
            {
                "query": '"Duke alumni" AND "series a"',
                "type": "discovery",
                "time_filter": "m6"
            },
            {
                "query": '"Duke graduate" AND "CEO" AND funding',
                "type": "discovery",
                "time_filter": "m6"
            },
            {
                "query": '"Duke University" AND entrepreneur AND raised',
                "type": "discovery",
                "time_filter": "m6"
            },
            {
                "query": 'site:techcrunch.com "Duke" AND funding',
                "type": "site_specific",
                "time_filter": "m6"
            },
            {
                "query": 'site:crunchbase.com "Duke University" AND founder',
                "type": "site_specific",
                "time_filter": "m6"
            }
        ]

    @staticmethod
    def get_person_duke_affiliation_queries(person_name: str) -> List[str]:
        """
        Generate specific search queries focused only on determining Duke affiliation for a person.
        
        Args:
            person_name: Name of the person to search for.
            
        Returns:
            List of targeted search query strings.
        """
        # Keep these queries tightly focused
        queries = [
            f'"{person_name}" "Duke University" alumni degree graduate',
            f'"{person_name}" "Duke University" graduation year',
            f'"{person_name}" site:today.duke.edu OR site:alumni.duke.edu OR site:pratt.duke.edu OR site:fuqua.duke.edu OR site:law.duke.edu',
            f'"{person_name}" "Duke" education history'
        ]
        return queries 