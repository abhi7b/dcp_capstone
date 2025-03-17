"""
Twitter/Nitter scraper for the DCP AI Scouting Platform.

This module provides functionality for scraping Twitter data using multiple methods:
1. Twitter API (via tweepy) - requires API credentials
2. Nitter web scraping - no API required

The scraper focuses on gathering raw tweets and profiles for LLM/NLP processing.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import re

import tweepy
import requests
from bs4 import BeautifulSoup

from backend.config.logs import LogManager
from backend.config.cache import cached
from backend.config.config import settings
from backend.scrapers.base_scraper import BaseScraper

# Use the centralized logging configuration
LogManager.setup_logging()
logger = logging.getLogger(__name__)

class TwitterScraper(BaseScraper):
    """
    Twitter/Nitter scraper for gathering raw tweets and profile information.
    
    This scraper provides multiple methods to fetch Twitter data:
    - Official Twitter API (requires API credentials)
    - Nitter web scraping (no API required)
    
    It focuses on collecting raw data for LLM/NLP processing.
    """
    
    def __init__(self):
        """Initialize the Twitter scraper with API credentials and configuration."""
        super().__init__()
        
        # Twitter API configuration
        self.api_key = settings.twitter.API_KEY
        self.api_secret = settings.twitter.API_SECRET
        self.access_token = settings.twitter.ACCESS_TOKEN
        self.access_secret = settings.twitter.ACCESS_SECRET
        self.nitter_base_url = settings.twitter.NITTER_BASE_URL or "https://nitter.net"
        self.max_tweets = settings.twitter.MAX_TWEETS or 30
        
        # Initialize Twitter API client if credentials are available
        self.twitter_api = None
        if all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            try:
                auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
                auth.set_access_token(self.access_token, self.access_secret)
                self.twitter_api = tweepy.API(auth)
                logger.info("Twitter API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter API client: {e}")
                # Continue without Twitter API
        else:
            logger.warning("Twitter API credentials not provided, falling back to Nitter")
    
    @cached("twitter_profile", expire=86400)  # Cache for 24 hours
    async def get_twitter_profile(self, username: str) -> Dict[str, Any]:
        """
        Get Twitter profile information using the best available method.
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            Dictionary containing profile information
        """
        logger.info(f"Fetching Twitter profile for @{username}")
        
        # Normalize username (remove @ if present)
        username = username.lstrip('@')
        
        # Try Twitter API first if available
        if self.twitter_api:
            try:
                profile = await self._get_profile_via_api(username)
                if profile and not isinstance(profile, str):
                    logger.info(f"Successfully retrieved profile for @{username} via Twitter API")
                    return profile
                logger.warning(f"Twitter API failed for @{username}, falling back to Nitter")
            except Exception as e:
                logger.error(f"Error using Twitter API for @{username}: {e}")
        
        # Fall back to Nitter
        try:
            profile = await self._get_profile_via_nitter(username)
            if profile and not isinstance(profile, str):
                logger.info(f"Successfully retrieved profile for @{username} via Nitter")
                return profile
            
            # If we get here, both methods failed
            error_msg = f"Failed to retrieve profile for @{username} via any method"
            logger.error(error_msg)
            return {"error": error_msg, "username": username}
        except Exception as e:
            error_msg = f"Error retrieving profile for @{username}: {e}"
            logger.error(error_msg)
            return {"error": error_msg, "username": username}
    
    async def _get_profile_via_api(self, username: str) -> Union[Dict[str, Any], str]:
        """
        Get Twitter profile using the official Twitter API.
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            Dictionary containing profile information or error message
        """
        if not self.twitter_api:
            return "Twitter API not initialized"
        
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            user = await loop.run_in_executor(
                None, lambda: self.twitter_api.get_user(screen_name=username)
            )
            
            return {
                "username": user.screen_name,
                "name": user.name,
                "description": user.description,
                "followers_count": user.followers_count,
                "friends_count": user.friends_count,
                "statuses_count": user.statuses_count,
                "created_at": user.created_at.isoformat(),
                "source": "twitter_api"
            }
        except Exception as e:
            return f"Twitter API error: {str(e)}"
    
    async def _get_profile_via_nitter(self, username: str) -> Union[Dict[str, Any], str]:
        """
        Get Twitter profile using Nitter web scraping.
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            Dictionary containing profile information or error message
        """
        if not self.client:
            return "HTTP client not initialized"
        
        try:
            url = f"{self.nitter_base_url}/{username}"
            response = await self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract profile information
            profile_info = {}
            profile_info["username"] = username
            profile_info["name"] = self._extract_text(soup, ".profile-card-fullname")
            profile_info["description"] = self._extract_text(soup, ".profile-bio")
            profile_info["followers_count"] = self._extract_count(soup, ".profile-stat-num", 0)
            profile_info["friends_count"] = self._extract_count(soup, ".profile-stat-num", 1)
            profile_info["statuses_count"] = self._extract_count(soup, ".profile-stat-num", 2)
            profile_info["source"] = "nitter"
            
            return profile_info
        except Exception as e:
            return f"Nitter error: {str(e)}"
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract text from a BeautifulSoup element."""
        element = soup.select_one(selector)
        return element.get_text().strip() if element else ""
    
    def _extract_count(self, soup: BeautifulSoup, selector: str, index: int) -> int:
        """Extract count from a BeautifulSoup element."""
        elements = soup.select(selector)
        if index < len(elements):
            text = elements[index].get_text().strip()
            # Remove commas and convert to int
            return int(text.replace(",", ""))
        return 0
    
    @cached("twitter_search", expire=43200)  # Cache for 12 hours
    async def search_twitter(self, query: str, count: int = 20) -> Dict[str, Any]:
        """
        Search Twitter for tweets matching a query.
        
        Args:
            query: Search query
            count: Maximum number of tweets to return
            
        Returns:
            Dictionary containing raw search results
        """
        logger.info(f"Searching Twitter for: {query}")
        
        # Limit count to max_tweets
        count = min(count, self.max_tweets)
        
        # Try Twitter API first if available
        if self.twitter_api:
            try:
                results = await self._search_via_api(query, count)
                if results and isinstance(results, dict) and "tweets" in results:
                    logger.info(f"Successfully searched Twitter via API: {query}")
                    return results
                logger.warning(f"Twitter API search failed for: {query}, falling back to Nitter")
            except Exception as e:
                logger.error(f"Error searching Twitter API: {e}")
        
        # Fall back to Nitter
        try:
            results = await self._search_via_nitter(query, count)
            if results and isinstance(results, dict) and "tweets" in results:
                logger.info(f"Successfully searched Twitter via Nitter: {query}")
                return results
            
            # If we get here, both methods failed
            error_msg = f"Failed to search Twitter via any method: {query}"
            logger.error(error_msg)
            return {"error": error_msg, "query": query}
        except Exception as e:
            error_msg = f"Error searching Twitter: {e}"
            logger.error(error_msg)
            return {"error": error_msg, "query": query}
    
    async def _search_via_api(self, query: str, count: int) -> Dict[str, Any]:
        """
        Search Twitter using the official Twitter API.
        
        Args:
            query: Search query
            count: Maximum number of tweets to return
            
        Returns:
            Dictionary containing search results
        """
        if not self.twitter_api:
            return {"error": "Twitter API not initialized"}
        
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            tweets = await loop.run_in_executor(
                None, lambda: self.twitter_api.search_tweets(q=query, count=count)
            )
            
            results = {
                "query": query,
                "count": len(tweets),
                "tweets": [
                    {
                        "id": tweet.id_str,
                        "text": tweet.text,
                        "created_at": tweet.created_at.isoformat(),
                        "user": tweet.user.screen_name,
                        "retweet_count": tweet.retweet_count,
                        "favorite_count": tweet.favorite_count
                    }
                    for tweet in tweets
                ],
                "source": "twitter_api"
            }
            
            return results
        except Exception as e:
            return {"error": f"Twitter API error: {str(e)}"}
    
    async def _search_via_nitter(self, query: str, count: int) -> Dict[str, Any]:
        """
        Search Twitter using Nitter web scraping.
        
        Args:
            query: Search query
            count: Maximum number of tweets to return
            
        Returns:
            Dictionary containing search results
        """
        if not self.client:
            return {"error": "HTTP client not initialized"}
        
        try:
            url = f"{self.nitter_base_url}/search?f=tweets&q={query}"
            response = await self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            tweet_elements = soup.select(".timeline-item")[:count]
            
            tweets = []
            for tweet_el in tweet_elements:
                tweet = {}
                tweet["id"] = self._extract_tweet_id(tweet_el)
                tweet["text"] = self._extract_text(tweet_el, ".tweet-content")
                tweet["user"] = self._extract_text(tweet_el, ".username")
                tweet["created_at"] = self._extract_text(tweet_el, ".tweet-date")
                
                # Extract stats
                stats = tweet_el.select(".tweet-stat")
                tweet["retweet_count"] = self._extract_stat(stats, 0)
                tweet["favorite_count"] = self._extract_stat(stats, 1)
                
                tweets.append(tweet)
            
            results = {
                "query": query,
                "count": len(tweets),
                "tweets": tweets,
                "source": "nitter"
            }
            
            return results
        except Exception as e:
            return {"error": f"Nitter error: {str(e)}"}
    
    def _extract_tweet_id(self, tweet_el: BeautifulSoup) -> str:
        """Extract tweet ID from a tweet element."""
        link = tweet_el.select_one(".tweet-link")
        if link and "href" in link.attrs:
            match = re.search(r"/status/(\d+)", link["href"])
            if match:
                return match.group(1)
        return ""
    
    def _extract_stat(self, stats: List, index: int) -> int:
        """Extract stat count from tweet stats."""
        if index < len(stats):
            text = stats[index].get_text().strip()
            if text.isdigit():
                return int(text)
        return 0
    
    @cached("twitter_user_tweets", expire=43200)  # Cache for 12 hours
    async def get_tweets(self, username: str, count: int = 20) -> Dict[str, Any]:
        """
        Get recent tweets from a user.
        
        Args:
            username: Twitter username (without @)
            count: Maximum number of tweets to return
            
        Returns:
            Dictionary containing raw tweets
        """
        logger.info(f"Fetching tweets for @{username}")
        
        # Normalize username (remove @ if present)
        username = username.lstrip('@')
        
        # Limit count to max_tweets
        count = min(count, self.max_tweets)
        
        # Try Twitter API first if available
        if self.twitter_api:
            try:
                results = await self._get_tweets_via_api(username, count)
                if results and isinstance(results, dict) and "tweets" in results:
                    logger.info(f"Successfully retrieved tweets for @{username} via Twitter API")
                    return results
                logger.warning(f"Twitter API failed for @{username}, falling back to Nitter")
            except Exception as e:
                logger.error(f"Error using Twitter API for @{username}: {e}")
        
        # Fall back to Nitter
        try:
            results = await self._get_tweets_via_nitter(username, count)
            if results and isinstance(results, dict) and "tweets" in results:
                logger.info(f"Successfully retrieved tweets for @{username} via Nitter")
                return results
            
            # If we get here, both methods failed
            error_msg = f"Failed to retrieve tweets for @{username} via any method"
            logger.error(error_msg)
            return {"error": error_msg, "username": username}
        except Exception as e:
            error_msg = f"Error retrieving tweets for @{username}: {e}"
            logger.error(error_msg)
            return {"error": error_msg, "username": username}
    
    async def _get_tweets_via_api(self, username: str, count: int) -> Dict[str, Any]:
        """
        Get tweets using the official Twitter API.
        
        Args:
            username: Twitter username (without @)
            count: Maximum number of tweets to return
            
        Returns:
            Dictionary containing tweets
        """
        if not self.twitter_api:
            return {"error": "Twitter API not initialized"}
        
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            tweets = await loop.run_in_executor(
                None, lambda: self.twitter_api.user_timeline(screen_name=username, count=count)
            )
            
            results = {
                "username": username,
                "count": len(tweets),
                "tweets": [
                    {
                        "id": tweet.id_str,
                        "text": tweet.text,
                        "created_at": tweet.created_at.isoformat(),
                        "retweet_count": tweet.retweet_count,
                        "favorite_count": tweet.favorite_count
                    }
                    for tweet in tweets
                ],
                "source": "twitter_api"
            }
            
            return results
        except Exception as e:
            return {"error": f"Twitter API error: {str(e)}"}
    
    async def _get_tweets_via_nitter(self, username: str, count: int) -> Dict[str, Any]:
        """
        Get tweets using Nitter web scraping.
        
        Args:
            username: Twitter username (without @)
            count: Maximum number of tweets to return
            
        Returns:
            Dictionary containing tweets
        """
        if not self.client:
            return {"error": "HTTP client not initialized"}
        
        try:
            url = f"{self.nitter_base_url}/{username}"
            response = await self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            tweet_elements = soup.select(".timeline-item")[:count]
            
            tweets = []
            for tweet_el in tweet_elements:
                tweet = {}
                tweet["id"] = self._extract_tweet_id(tweet_el)
                tweet["text"] = self._extract_text(tweet_el, ".tweet-content")
                tweet["created_at"] = self._extract_text(tweet_el, ".tweet-date")
                
                # Extract stats
                stats = tweet_el.select(".tweet-stat")
                tweet["retweet_count"] = self._extract_stat(stats, 0)
                tweet["favorite_count"] = self._extract_stat(stats, 1)
                
                tweets.append(tweet)
            
            results = {
                "username": username,
                "count": len(tweets),
                "tweets": tweets,
                "source": "nitter"
            }
            
            return results
        except Exception as e:
            return {"error": f"Nitter error: {str(e)}"} 