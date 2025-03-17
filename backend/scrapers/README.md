# Scrapers Module

This directory contains web scraping components for the DCP AI Scouting Platform, focused on gathering raw data about companies and founders from search engine results and social media.

## Overview

The scrapers module provides:
- A base scraper with common functionality
- Specialized scrapers for companies and founders
- Twitter/Nitter scraper for raw social media data
- Search engine integration for reliable data collection
- Optimized queries for NLP/LLM processing

## Directory Structure

```
scrapers/
├── __init__.py             # Package exports
├── base_scraper.py         # Base scraper with common functionality
├── company_scraper.py      # Company-specific scraper
├── founder_scraper.py      # Founder-specific scraper
├── twitter_scraper.py      # Twitter/Nitter scraper
├── test_scrapers.py        # Simple test script
├── test_twitter_scraper.py # Twitter scraper test script
└── README.md               # This file
```

## Key Components

### Base Scraper (`base_scraper.py`)

Provides common functionality for all scrapers:
- HTTP client setup and connection management
- Retry logic for API calls
- Result filtering and processing
- Common utility methods

### Company Scraper (`company_scraper.py`)

Specialized scraper for gathering information about companies with optimized queries for:
- Company overview and business description
- Funding rounds and investment information
- Founding date and company history
- Leadership team and executives
- Duke University connections
- Market information and competitors
- Company location
- Social media profiles

### Founder Scraper (`founder_scraper.py`)

Specialized scraper for gathering information about founders with optimized queries for:
- Educational background (with focus on Duke University)
- Professional experience and career history
- Entrepreneurial history and companies founded
- Duke University affiliations
- Funding and investment history
- Social media presence
- Achievements and recognition
- Personal background

### Twitter Scraper (`twitter_scraper.py`)

Specialized scraper for gathering raw Twitter data using multiple methods:
- Official Twitter API (when credentials are available)
- Nitter web scraping (no API required)

Features include:
- Profile information retrieval
- Raw tweet collection and search
- Graceful fallback between methods
- Caching for performance optimization

The Twitter scraper focuses solely on collecting raw data, leaving all processing and analysis to the LLM/NLP components.

## Usage

### Basic Usage

```python
import asyncio
from backend.scrapers.company_scraper import CompanyScraper

async def main():
    async with CompanyScraper() as scraper:
        results = await scraper.comprehensive_search("Example Company")
        print(f"Found {results['metadata']['total_results']} results")

if __name__ == "__main__":
    asyncio.run(main())
```

### Twitter Scraper Usage

```python
import asyncio
from backend.scrapers.twitter_scraper import TwitterScraper

async def main():
    async with TwitterScraper() as scraper:
        # Get profile information
        profile = await scraper.get_twitter_profile("elonmusk")
        print(f"Followers: {profile.get('followers_count', 0)}")
        
        # Get recent tweets
        tweets = await scraper.get_tweets("elonmusk", count=10)
        for tweet in tweets.get("tweets", []):
            print(tweet.get("text", ""))
            
        # Search for tweets
        search_results = await scraper.search_twitter("startup funding", count=10)
        print(f"Found {search_results.get('count', 0)} tweets")

if __name__ == "__main__":
    asyncio.run(main())
```

## Environment Configuration

The scrapers rely on the following environment variables (configured in the config module):

```
# SERP API Configuration
SCRAPER_SERPAPI_KEY=your_serp_api_key
SCRAPER_TIMEOUT=30

# Twitter API Configuration
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_SECRET=your_twitter_access_secret
TWITTER_NITTER_BASE_URL=https://nitter.net
```

## Integration with NLP/LLM

The scrapers are designed to collect raw data that will be processed by NLP/LLM components:

1. Scrapers collect raw data from various sources using optimized queries
2. Data is structured into categories that align with expected schema
3. Raw data is cached to improve performance and reduce API costs
4. NLP/LLM components process the raw data to:
   - Extract key information (founding date, funding rounds, etc.)
   - Detect Duke affiliations
   - Assess investment potential
   - Generate structured insights

## Data Schema Alignment

The query categories are designed to align with expected data schema:

### Company Data
- Basic information (name, description, industry)
- Founding information (date, founders)
- Funding details (rounds, amounts, investors)
- Leadership team (executives, founders)
- Duke connections (alumni, partnerships)
- Market information (size, competitors)
- Location data
- Social media presence

### Founder Data
- Personal information (name, background)
- Education (degrees, institutions, Duke affiliation)
- Professional experience (previous roles, companies)
- Entrepreneurial history (companies founded)
- Funding history (investments raised)
- Achievements and recognition
- Social media presence

## Caching

Results are cached to improve performance and reduce API costs:
- 24-hour cache for search results and profiles
- 12-hour cache for tweets and search queries
