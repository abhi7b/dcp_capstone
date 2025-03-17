# nlp/founder_processor.py
"""
Founder-specific NLP processor for the DCP AI Scouting Platform.

This module provides specialized NLP processing for founder data, including:
- Founder background extraction
- Duke affiliation detection
- Entrepreneurial history analysis
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from backend.config.logs import LogManager
from backend.config.cache import cached
from backend.config.config import settings
from backend.nlp.base_processor import BaseProcessor
from backend.nlp.prompts.founder_prompts import FOUNDER_SYSTEM_PROMPT, FOUNDER_USER_PROMPT
from backend.nlp.services.social_media import SocialMediaService

# Use the centralized logging configuration
logger = logging.getLogger(__name__)

class FounderProcessor(BaseProcessor):
    """
    Processor for analyzing founder data.
    
    This class extends the base processor to provide specialized
    functionality for analyzing founder information.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the founder processor.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: OpenAI model to use (defaults to settings)
        """
        super().__init__(api_key=api_key, model=model)
        logger.debug("FounderProcessor initialized")
    
    @cached("founder_analysis", expire=settings.CACHE_FOUNDER_TTL)
    async def analyze_founder(self, text: str, temperature: float = 0.0) -> Dict[str, Any]:
        """
        Analyze founder information from text.
        
        Args:
            text: Text to analyze
            temperature: Temperature for the OpenAI model (0.0-1.0)
            
        Returns:
            Dict[str, Any]: Analyzed founder data
        """
        if not text:
            logger.warning("Empty text provided for founder analysis")
            return {"error": "No text to analyze"}
            
        try:
            logger.info(f"Analyzing founder text (length: {len(text)} chars)")
            start_time = datetime.now()
            
            # Process the text using the base processor
            result = await self.process_text(
                text=text,
                system_prompt=FOUNDER_SYSTEM_PROMPT,
                user_prompt=FOUNDER_USER_PROMPT,
                temperature=temperature
            )
            
            # Check for errors from the base processor
            if "error" in result:
                logger.error(f"Error in base processing: {result['error']}")
                return result
            
            # Extract social media profiles from the text
            social_profiles = SocialMediaService.extract_social_media_profiles(result)
            if social_profiles and "social_media" in result:
                for platform, url in social_profiles.items():
                    if platform not in result["social_media"]:
                        result["social_media"][platform] = url
            
            # Log analysis completion
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Founder analysis completed in {elapsed_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing founder: {e}", exc_info=True)
            return {"error": f"Founder analysis failed: {str(e)}"}
    
    def extract_db_info(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract database-ready information from the analysis.
        
        Args:
            analysis: Full analysis from OpenAI
            
        Returns:
            Dict with structured data for database storage
        """
        # If there's an error, return empty dict
        if "error" in analysis:
            logger.warning(f"Cannot extract DB info due to error: {analysis['error']}")
            return {}
            
        # Simply return the analysis as-is
        return analysis 