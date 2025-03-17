"""
Twitter data analyzer for the DCP AI Scouting Platform.

This module provides specialized NLP processing for Twitter data, including:
- Tweet content analysis
- Engagement metrics evaluation
- Actionability scoring
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.config.logs import LogManager
from backend.config.cache import cached
from backend.config.config import settings
from backend.nlp.base_processor import BaseProcessor
from backend.nlp.prompts.twitter_prompts import TWITTER_SYSTEM_PROMPT, TWITTER_USER_PROMPT

# Use the centralized logging configuration
logger = logging.getLogger(__name__)

class TwitterAnalyzer(BaseProcessor):
    """
    Twitter content analyzer for extracting actionable investment insights.
    
    This analyzer focuses on:
    - Identifying funding announcements
    - Detecting new startup launches
    - Extracting key business metrics
    - Assessing investment potential
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Twitter analyzer.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: OpenAI model to use (defaults to settings)
        """
        super().__init__(api_key=api_key, model=model)
        logger.debug("TwitterAnalyzer initialized")
    
    @cached("twitter_analysis", expire=settings.CACHE_DEFAULT_TTL)
    async def analyze_tweets(self, tweets_data: Dict[str, Any], temperature: float = 0.0) -> Dict[str, Any]:
        """
        Analyze tweets for actionable investment insights.
        
        Args:
            tweets_data: Dictionary containing tweets and profile data
            temperature: Temperature for the OpenAI model (0.0-1.0)
            
        Returns:
            Dict[str, Any]: Analysis with actionability score and key insights
        """
        if not tweets_data or not tweets_data.get("tweets", []):
            logger.warning("No tweets provided for analysis")
            return {
                "summary": "No tweets to analyze",
                "topics": [],
                "actionability_score": 0,
                "key_insights": [],
                "duke_connection": {"has_connection": False}
            }
            
        try:
            logger.info(f"Analyzing tweets for investment insights")
            start_time = datetime.now()
            
            # Extract username if available
            username = tweets_data.get("username", "Unknown")
            if "user" in tweets_data and "username" in tweets_data["user"]:
                username = tweets_data["user"]["username"]
                
            # Extract tweets
            tweets = tweets_data.get("tweets", [])
            tweet_texts = []
            
            # Format tweets for analysis
            for tweet in tweets:
                if isinstance(tweet, dict) and "text" in tweet:
                    tweet_text = f"Tweet: {tweet['text']}"
                    if "metrics" in tweet:
                        metrics = tweet.get("metrics", {})
                        tweet_text += f"\nLikes: {metrics.get('likes', 0)}, Retweets: {metrics.get('retweets', 0)}"
                    tweet_texts.append(tweet_text)
                elif isinstance(tweet, str):
                    tweet_texts.append(f"Tweet: {tweet}")
                    
            # Combine tweets into a single text
            combined_text = "\n\n".join(tweet_texts)
            
            # Process the tweets with OpenAI
            result = await self.process_text(
                text=combined_text,
                system_prompt=TWITTER_SYSTEM_PROMPT,
                user_prompt=TWITTER_USER_PROMPT,
                temperature=temperature
            )
            
            # Check for errors from the base processor
            if "error" in result:
                logger.error(f"Error in base processing: {result['error']}")
                return result
            
            # Add metadata
            result["metadata"] = {
                "username": username,
                "tweet_count": len(tweets),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            # Log completion time
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Tweet analysis completed in {elapsed_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing tweets: {e}", exc_info=True)
            return {
                "error": f"Tweet analysis failed: {str(e)}",
                "summary": "Analysis failed",
                "topics": [],
                "actionability_score": 0,
                "key_insights": []
            }
    
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