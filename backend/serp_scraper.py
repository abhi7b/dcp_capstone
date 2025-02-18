#serp_scraper.py
"""
Scraper

Features:
- Proxy rotation
- Request retries
- Rate limiting handling
- Multi-source integration
"""
import re
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Dict, Optional
from config import settings  

logger = logging.getLogger(__name__)

class DCPScraper:
    """Unified scraper for multiple data sources"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=10),
            timeout=30.0,
            follow_redirects=True
        )

    async def search_founder(self, founder_name: str) -> List[Dict]:
        """Search for a founder's information using the SERP API"""
        logger.info(f"Searching for founder: {founder_name}")
        results = await self.fetch_serp(founder_name)

        if not results:
            logger.warning(f"⚠️ No results found for {founder_name}")
            return []

        # Clean and format names before returning
        formatted_results = []
        for item in results:
            name = item.get("name", "").strip()
            if re.match(r"^[A-Za-z]+ [A-Za-z]+$", name):  # Ensure it's a valid full name
                formatted_results.append({"name": name, "snippet": item.get("snippet", ""), "source": item.get("source", "")})

        logger.info(f"Found {len(formatted_results)} results for {founder_name}")
        return formatted_results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_serp(self, query: str) -> Optional[List[Dict]]:
        """Fetch SERP data with retry logic"""
        params = {
            "q": f"{query}",
            "api_key": settings.SERPAPI_KEY,
            "num": 10  # Adjust based on rate limits
        }

        try:
            response = await self.client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()

            if response.status_code == 429:
                logger.warning("⚠️ SERP API rate limit exceeded, retrying...")
                return None

            json_data = response.json()
            logger.info(f"SERP API Raw Response: {json_data}")  # Log full response

            return self._process_serp_data(json_data)

        except httpx.ConnectError:
            logger.error("SERP API is unreachable. Check network or API status.")
            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            return None

        except Exception as e:
            logger.error(f"Unexpected SERP API Error: {e}")
            return None

    def _process_serp_data(self, data: Dict) -> List[Dict]:
        """Extract structured founder/company data from SERP API response."""
        results = []
        seen_names = set()
        # Extract from "knowledge_graph"
        if "knowledge_graph" in data:
            kg = data["knowledge_graph"]
            name = kg.get("title", "").strip()
            description = kg.get("description", "").strip()
            source = kg.get("source", {}).get("link", "")

            # Extract company names from subtitles
            companies = []
            if "subtitles" in kg:
                for subtitle in kg["subtitles"]:
                    if "text" in subtitle:
                        companies.append(subtitle["text"])

            if name and name not in seen_names:
                results.append({
                    "name": name, 
                    "snippet": description, 
                    "source": source, 
                    "companies": companies
                })
                seen_names.add(name)

        # Extract from "organic_results"
        for item in data.get("organic_results", []):
            name = item.get("title", "").strip()
            snippet = item.get("snippet", "").strip()
            source = item.get("link", "")

            # Try to extract company name from the snippet
            possible_company = None
            snippet_words = snippet.split()
            if "at" in snippet_words:
                at_index = snippet_words.index("at")
                if at_index + 1 < len(snippet_words):
                    possible_company = snippet_words[at_index + 1]

            if name and name not in seen_names:
                results.append({
                    "name": name, 
                    "snippet": snippet, 
                    "source": source, 
                    "companies": [possible_company] if possible_company else []
                })
                seen_names.add(name)

        return results


    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

