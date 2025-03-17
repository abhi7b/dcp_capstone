"""
NLP package for the DCP AI Scouting Platform.

This package provides Natural Language Processing components for extracting
structured information from web scraping results, with a focus on identifying
investment opportunities related to Duke University.
"""

# Base processor
from backend.nlp.base_processor import BaseProcessor

# Specialized processors
from backend.nlp.company_processor import CompanyProcessor
from backend.nlp.founder_processor import FounderProcessor

# Twitter analyzer
from backend.nlp.twitter_analyzer import TwitterAnalyzer

# Services
from backend.nlp.services.social_media import SocialMediaService
from backend.nlp.services.scoring import ScoringService
from backend.nlp.services.integration import IntegrationService

# Export commonly used classes
__all__ = [
    # Processors
    'BaseProcessor',
    'CompanyProcessor',
    'FounderProcessor',
    
    # Analyzers
    'TwitterAnalyzer',
    
    # Services
    'SocialMediaService',
    'ScoringService',
    'IntegrationService',
] 