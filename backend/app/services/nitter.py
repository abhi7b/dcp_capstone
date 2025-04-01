import json
import os
from datetime import datetime
from typing import Dict, Any
import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from ..utils.logger import nitter_logger
from ..utils.config import settings

class NitterScraper:
    """Service for fetching raw tweets using Nitter as a proxy"""
    
    def __init__(self):
        # List of Nitter instances to try
        self.instances = [
            "https://nitter.net",
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
            "https://nitter.woodland.cafe"
        ]
        self.raw_data_dir = settings.RAW_DATA_DIR
        nitter_logger.info("NitterScraper initialized with multiple instances")
    
    def _save_raw_data(self, data: Dict[str, Any], handle: str) -> str:
        """Save raw JSON data to file and return the file path"""
        sanitized_handle = handle.replace('@', '').replace('/', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nitter_{sanitized_handle}_{timestamp}.json"
        file_path = os.path.join(self.raw_data_dir, filename)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        nitter_logger.info(f"Raw Nitter data saved to {file_path}")
        return file_path
    
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
        nitter_logger.info(f"Fetching raw tweets for: {handle} (limit: {limit})")
        
        # Try each Nitter instance
        for instance in self.instances:
            profile_url = f"{instance}/{handle}"
            try:
                html = await self._fetch_page(profile_url)
                soup = BeautifulSoup(html, 'html.parser')
                tweet_elements = soup.select('.timeline-item')
                
                if not tweet_elements:
                    nitter_logger.warning(f"No tweets found on {instance} for {handle}")
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
                    stats_elem = tweet_elem.select_one('.tweet-stats')
                    
                    raw_tweets.append({
                        "content": content_elem.text.strip(),
                        "date": date_elem.text if date_elem else None,
                        "stats": stats_elem.text if stats_elem else None,
                        "html": str(tweet_elem)
                    })
                
                if raw_tweets:
                    nitter_logger.info(f"Successfully fetched {len(raw_tweets)} tweets from {instance}")
                    result_data = {
                        "handle": handle,
                        "instance": instance,
                        "raw_tweets": raw_tweets,
                        "twitter_unavailable": False
                    }
                    file_path = self._save_raw_data(result_data, handle)
                    result_data["_file_path"] = file_path
                    return result_data
                    
            except Exception as e:
                nitter_logger.warning(f"Failed to fetch from {instance}: {str(e)}")
                continue
        
        # If all instances fail
        nitter_logger.error(f"All Nitter instances failed for {handle}")
        return {
            "handle": handle,
            "raw_tweets": [],
            "twitter_unavailable": True
        }

if __name__ == "__main__":
    import asyncio
    
    # Simple test using existing config
    async def test():
        scraper = NitterScraper()
        test_handle = "OpenAI"
        result = await scraper.get_raw_tweets(test_handle, limit=5)
        
        print(f"\nTest Results for @{test_handle}:")
        print(f"Twitter Available: {not result['twitter_unavailable']}")
        print(f"Tweets Found: {len(result['raw_tweets'])}")
        if result['raw_tweets']:
            print("\nFirst Tweet Content:")
            print(result['raw_tweets'][0]['content'][:100] + "...")
    
    asyncio.run(test())