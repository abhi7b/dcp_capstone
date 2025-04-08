"""
Nitter Scraper Module

Service for scraping Twitter data through Nitter instances.
Handles tweet extraction, rate limiting, and error handling.

Key Features:
- Tweet scraping
- Rate limiting
- Instance rotation
- Error handling
"""

import json
from typing import Dict, Any, List, Optional
import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
import random

from ..utils.logger import nitter_logger as logger
from ..utils.config import settings
from ..utils.storage import StorageService


class NitterScraper:
    """
    Service for scraping Twitter data through Nitter instances.
    Handles instance rotation and retry logic.
    """
    
    def __init__(self):
        """Initialize scraper with Nitter instances."""
        self.instances = settings.NITTER_INSTANCES
        self.max_retries = 3
        self.storage = StorageService()
        logger.info("NitterScraper initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _fetch_page(self, url: str) -> str:
        """Fetch HTML content from a URL with retry logic"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                response.raise_for_status()
                return await response.text()
    
    async def get_raw_tweets(self, handle: str, limit: int = 20) -> Dict[str, Any]:
        """Get raw tweets from a user's profile page"""
        handle = handle.replace('@', '')
        logger.info(f"Fetching raw tweets for: {handle} (limit: {limit})")
        
        # Check for cached data
        recent_data = self.storage.load_data("nitter", handle, settings.RAW_DATA_DIR)
        if recent_data:
            recent_data["_file_path"] = self.storage.get_file_path("nitter", handle, settings.RAW_DATA_DIR)
            return recent_data
        
        # Try each Nitter instance
        for instance in self.instances:
            profile_url = f"{instance}/{handle}"
            try:
                html = await self._fetch_page(profile_url)
                soup = BeautifulSoup(html, 'html.parser')
                tweet_elements = soup.select('.timeline-item')
                
                if not tweet_elements:
                    logger.warning(f"No tweets found on {instance} for {handle}")
                    continue
                
                raw_tweets = []
                for i, tweet_elem in enumerate(tweet_elements):
                    if i >= limit:
                        break
                    
                    content_elem = tweet_elem.select_one('.tweet-content')
                    if not content_elem:
                        continue
                    
                    # Get tweet metadata
                    date_elem = tweet_elem.select_one('.tweet-date')
                    
                    raw_tweets.append({
                        "content": content_elem.text.strip(),
                        "date": date_elem.text if date_elem else None
                    })
                
                if raw_tweets:
                    logger.info(f"Successfully fetched {len(raw_tweets)} tweets from {instance}")
                    result_data = {
                        "handle": handle,
                        "raw_tweets": raw_tweets,
                        "twitter_unavailable": False
                    }
                    
                    # Save raw data
                    file_path = self.storage.save_raw_data(result_data, "nitter", handle)
                    result_data["_file_path"] = file_path
                    
                    return result_data
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {instance}: {str(e)}")
                continue
        
        # If all instances fail
        logger.error(f"All Nitter instances failed for {handle}")
        return {
            "handle": handle,
            "raw_tweets": [],
            "twitter_unavailable": True
        }
