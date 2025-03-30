import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..utils.config import settings
from ..utils.logger import nitter_logger

class NitterScraper:
    """
    Service for scraping Twitter data using Nitter as a proxy
    """
    
    def __init__(self):
        self.base_url = settings.TWITTER_NITTER_BASE_URL
        self.raw_data_dir = settings.RAW_DATA_DIR
        nitter_logger.info("NitterScraper initialized")
    
    def _save_raw_data(self, data: Dict[str, Any], handle: str) -> str:
        """Save raw JSON data to file and return the file path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_handle = handle.replace('@', '')
        
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
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _fetch_page(self, url: str) -> str:
        """Fetch HTML content from a URL with retry logic"""
        nitter_logger.info(f"Fetching URL: {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.text
    
    def get_user_profile(self, handle: str) -> Dict[str, Any]:
        """Get Twitter user profile information"""
        # Normalize handle (remove @ if present)
        handle = handle.replace('@', '')
        
        nitter_logger.info(f"Fetching Twitter profile for: {handle}")
        profile_url = f"{self.base_url}/{handle}"
        
        try:
            # Fetch profile page
            html = self._fetch_page(profile_url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract profile data
            profile_data = {
                "handle": handle,
                "name": None,
                "bio": None,
                "location": None,
                "joined_date": None,
                "follower_count": None,
                "following_count": None,
                "tweet_count": None,
                "twitter_unavailable": False
            }
            
            # Name
            name_elem = soup.select_one('.profile-card-fullname')
            if name_elem:
                profile_data["name"] = name_elem.text.strip()
            
            # Bio
            bio_elem = soup.select_one('.profile-bio')
            if bio_elem:
                profile_data["bio"] = bio_elem.text.strip()
            
            # Location
            location_elem = soup.select_one('.profile-location')
            if location_elem:
                profile_data["location"] = location_elem.text.strip()
            
            # Joined date
            joined_elem = soup.select_one('.profile-joindate')
            if joined_elem:
                date_text = joined_elem.text.strip()
                date_match = re.search(r'Joined (.+)', date_text)
                if date_match:
                    profile_data["joined_date"] = date_match.group(1)
            
            # Stats (followers, following, tweets)
            stats_elem = soup.select('.profile-stat-num')
            if len(stats_elem) >= 3:
                profile_data["tweet_count"] = stats_elem[0].text.strip()
                profile_data["following_count"] = stats_elem[1].text.strip()
                profile_data["follower_count"] = stats_elem[2].text.strip()
            
            # Save raw data
            file_path = self._save_raw_data(profile_data, handle)
            profile_data["_file_path"] = file_path
            
            return profile_data
                
        except Exception as e:
            nitter_logger.error(f"Failed to fetch Twitter profile for {handle}: {str(e)}")
            return {"handle": handle, "twitter_unavailable": True}
    
    def get_recent_tweets(self, handle: str, limit: int = 20) -> Dict[str, Any]:
        """Get recent tweets from a user's profile page"""
        # Normalize handle
        handle = handle.replace('@', '')
        
        nitter_logger.info(f"Fetching recent tweets for: {handle} (limit: {limit})")
        profile_url = f"{self.base_url}/{handle}"

        try:
            html = self._fetch_page(profile_url)
            soup = BeautifulSoup(html, 'html.parser')
            tweet_elements = soup.select('.timeline-item')

            tweets = []
            for i, tweet_elem in enumerate(tweet_elements):
                if i >= limit:
                    break

                # Extract tweet content
                content_elem = tweet_elem.select_one('.tweet-content')
                if not content_elem:
                    continue
                
                tweet_data = {
                    "content": content_elem.text.strip(),
                    "date": None,
                    "url": None,
                    "replies": "0",
                    "retweets": "0",
                    "likes": "0"
                }

                # Extract date and URL
                date_elem = tweet_elem.select_one('.tweet-date a')
                if date_elem:
                    tweet_data["date"] = date_elem.text.strip()
                    tweet_data["url"] = date_elem.get('href')

                # Extract engagement stats
                stats_elems = tweet_elem.select('.tweet-stat')
                for stat_elem in stats_elems:
                    stat_text = stat_elem.text.strip()
                    value = stat_text.split()[0] if stat_text else '0'
                    
                    icon_class = str(stat_elem.select_one('span.icon') or '')
                    if 'comment' in icon_class or 'reply' in stat_text.lower():
                        tweet_data['replies'] = value
                    elif 'retweet' in icon_class or 'retweet' in stat_text.lower():
                        tweet_data['retweets'] = value
                    elif 'heart' in icon_class or 'like' in stat_text.lower():
                        tweet_data['likes'] = value

                tweets.append(tweet_data)

            nitter_logger.info(f"Found {len(tweets)} tweets for {handle}")

            result_data = {
                "handle": handle,
                "tweets": tweets,
                "twitter_unavailable": False
            }

            # Save raw data
            file_path = self._save_raw_data({"tweets": tweets}, handle)
            result_data["_file_path"] = file_path

            return result_data

        except Exception as e:
            nitter_logger.error(f"Failed to fetch tweets for {handle}: {str(e)}")
            return {"handle": handle, "tweets": [], "twitter_unavailable": True} 