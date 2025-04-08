"""
Services package for Duke VC Insight Engine.
Contains core processing modules for data collection and analysis.
"""

from .nitter import NitterScraper
from .nitter_nlp import NitterNLP
from .company_scorer import CompanyScorer
from .founder_scorer import FounderScorer
from .nlp_processor import NLPProcessor
from .person_processor import PersonProcessor
from .scraper import SERPScraper
from .redis import redis_service
from .query_utils import QueryBuilder

__all__ = [
    'NitterScraper',    # Twitter data scraping
    'NitterNLP',        # Twitter content analysis
    'CompanyScorer',    # Company scoring and ranking
    'FounderScorer',    # Founder scoring and ranking
    'NLPProcessor',     # Core NLP processing
    'PersonProcessor',  # Person data processing
    'SERPScraper',     # Web data collection
    'redis_service',   # Caching and rate limiting
    'QueryBuilder'     # Search query construction
] 