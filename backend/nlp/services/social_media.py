"""
Social media analysis service for the DCP AI Scouting Platform.

This module provides functionality to analyze social media data,
calculate engagement metrics, and extract actionable insights.
"""
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.config.logs import LogManager

# Initialize logger
logger = logging.getLogger(__name__)

class SocialMediaService:
    """
    Service for social media data extraction.
    
    This class provides methods for extracting social media handles
    and basic profile information.
    """
    
    @staticmethod
    def extract_social_media_profiles(analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract social media profiles from analysis result.
        
        Args:
            analysis_result: Analysis result from LLM
            
        Returns:
            Dict[str, str]: Dictionary of social media profiles
        """
        if not analysis_result:
            return {}
            
        try:
            profiles = {}
            
            # First check if there's a dedicated social_media field
            social_media = analysis_result.get("social_media", {})
            
            # If not, try to find it in company_profile or founder_profile
            if not social_media and "company_profile" in analysis_result:
                social_media = analysis_result["company_profile"].get("social_media", {})
            elif not social_media and "founder_profile" in analysis_result:
                social_media = analysis_result["founder_profile"].get("social_media", {})
            
            # Extract all platforms from social_media
            if social_media and isinstance(social_media, dict):
                for platform, url in social_media.items():
                    if url and isinstance(url, str):
                        profiles[platform.lower()] = url.strip()
            
            # Special handling for Twitter
            if "twitter" in profiles:
                profiles["twitter"] = SocialMediaService.clean_twitter_handle(profiles["twitter"])
            
            # Look for handles in other fields if not found yet
            if "twitter_handle" in analysis_result and analysis_result["twitter_handle"] and "twitter" not in profiles:
                profiles["twitter"] = SocialMediaService.clean_twitter_handle(analysis_result["twitter_handle"])
                
            if "linkedin_url" in analysis_result and analysis_result["linkedin_url"] and "linkedin" not in profiles:
                profiles["linkedin"] = analysis_result["linkedin_url"]
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error extracting social media profiles: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def clean_twitter_handle(handle: Optional[str]) -> Optional[str]:
        """
        Clean and normalize a Twitter handle.
        
        Args:
            handle: Raw Twitter handle
            
        Returns:
            Cleaned Twitter handle
        """
        if not handle:
            return None
            
        try:
            # Remove whitespace
            handle = handle.strip()
            
            # Extract handle from URL if needed
            url_match = re.search(r'twitter\.com/([^/\s?]+)', handle)
            if url_match:
                handle = url_match.group(1)
            
            # Add @ if missing
            if not handle.startswith('@'):
                handle = f'@{handle}'
                
            return handle
            
        except Exception as e:
            logger.error(f"Error cleaning Twitter handle: {e}")
            return handle
    
    @staticmethod
    def format_twitter_data(twitter_handle: Optional[str], twitter_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Twitter data for storage.
        
        Args:
            twitter_handle: Twitter handle
            twitter_data: Twitter data from analysis
            
        Returns:
            Dict[str, Any]: Formatted Twitter data
        """
        if not twitter_handle or not twitter_data:
            return {}
            
        try:
            # Clean the handle
            clean_handle = SocialMediaService.clean_twitter_handle(twitter_handle)
            
            # Extract key fields with defaults
            return {
                "handle": clean_handle,
                "summary": twitter_data.get("summary", ""),
                "actionability_score": twitter_data.get("actionability_score", 0),
                "topics": twitter_data.get("topics", []),
                "key_insights": twitter_data.get("key_insights", [])[:3]  # Limit to 3 key insights
            }
        except Exception as e:
            logger.error(f"Error formatting Twitter data: {e}", exc_info=True)
            return {
                "handle": twitter_handle,
                "error": str(e)
            } 