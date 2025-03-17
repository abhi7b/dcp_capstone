"""
Scrapers package for the DCP AI Scouting Platform.

This module provides web scraping components for gathering raw data about
companies and founders from search engine results and social media.
The raw data is intended to be processed by NLP/LLM components.
"""

# Base scraper
from backend.scrapers.base_scraper import BaseScraper

# Specialized scrapers
from backend.scrapers.company_scraper import CompanyScraper
from backend.scrapers.founder_scraper import FounderScraper
from backend.scrapers.twitter_scraper import TwitterScraper

# Export commonly used classes
__all__ = [
    'BaseScraper',
    'CompanyScraper',
    'FounderScraper',
    'TwitterScraper',
] 