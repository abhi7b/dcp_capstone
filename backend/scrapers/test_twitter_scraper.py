#!/usr/bin/env python
"""
Test script for the Twitter/Nitter scraper.

This script demonstrates how to use the TwitterScraper to fetch raw tweets
using both the Twitter API and Nitter fallback methods.
"""
import asyncio
import json
from pathlib import Path
import logging
from datetime import datetime

from backend.config.logs import LogManager
from backend.scrapers.twitter_scraper import TwitterScraper

# Set up logging
LogManager.setup_logging()
logger = logging.getLogger(__name__)

async def collect_raw_tweets(username: str, count: int = 20):
    """Collect raw tweets from a Twitter profile."""
    logger.info(f"Collecting raw tweets from @{username}")
    
    async with TwitterScraper() as scraper:
        tweets_data = await scraper.get_tweets(username, count)
        
        print(f"\n--- Raw Tweets from @{username} ---")
        if "error" in tweets_data:
            print(f"Error: {tweets_data['error']}")
            return tweets_data
            
        tweets = tweets_data.get("tweets", [])
        print(f"Found {len(tweets)} tweets via {tweets_data.get('source', 'unknown')}")
        
        # Show a sample of tweets
        for i, tweet in enumerate(tweets[:3], 1):  # Only show first 3 tweets for preview
            print(f"\n{i}. {tweet.get('created_at', 'Unknown date')}")
            print(f"   {tweet.get('text', '')[:100]}...")
        
        if len(tweets) > 3:
            print(f"\n... and {len(tweets) - 3} more tweets")
        
        return tweets_data

async def save_tweets(data, username: str):
    """Save tweets to a JSON file."""
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Add timestamp to filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"raw_tweets_{username}_{timestamp}.json"
    
    # Save to file
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved raw tweets to {filepath}")
    print(f"\nRaw tweets saved to: {filepath}")
    return filepath

async def main():
    """Run Twitter scraper to collect raw tweets."""
    logger.info("Starting Twitter scraper to collect raw tweets")
    
    # Collect tweets from a known Twitter account
    username = "stripe"  # Example: high-profile account likely to be available
    count = 30  # Number of tweets to collect
    
    # Collect and save raw tweets
    tweets_data = await collect_raw_tweets(username, count)
    await save_tweets(tweets_data, username)
    
    print("\nRaw tweet collection completed!")

if __name__ == "__main__":
    asyncio.run(main()) 