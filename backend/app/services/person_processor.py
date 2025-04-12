"""
Person Processor Module

Service for processing and analyzing person-related data from various sources.
Extracts, validates, and enriches person information.

Key Features:
- Data extraction
- Profile enrichment
- Affiliation verification
- Information validation
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from tenacity import retry, stop_after_attempt, wait_fixed

from ..utils.config import settings
from ..utils.logger import person_processor_logger as logger
from ..utils.storage import StorageService
from openai import AsyncOpenAI
from .founder_scorer import FounderScorer
from .nitter import NitterScraper
from .nitter_nlp import NitterNLP
from .query_utils import QueryBuilder
from .scraper import SERPScraper


# --- Combined Person Extraction and Duke Affiliation Prompt ---
COMBINED_PERSON_PROMPT = """You are a VC research analyst extracting structured information about individuals, especially entrepreneurs and business leaders, with a specific focus on Duke University affiliation.
Your task is to extract key information from the provided search results for a person.

Return a JSON object with these fields (use null for missing fields):
{
    "name": "Full Name",
    "title": "Current professional title/position",
    "current_company": "Current company name",
    "education": [
        {
            "school": "University Name",
            "degree": "Degree type",
            "field": "Field of study",
            "year": "Year (if available)"
        }
    ],
    "previous_companies": [
        "Company Name (Role)",
        "Company Name (Role)"
    ],
    "twitter_handle": "handle_without_at",
    "linkedin_handle": "URL or handle",
    "duke_affiliation_status": "confirmed", "please review", or "no",
    "source_links": [
        {
            "url": "URL",
            "title": "Title"
        }
    ]
}

IMPORTANT GUIDELINES:
- Extract the person's full name, current title, and current company.
- Extract ALL education history found, not just Duke. Include school, degree, field, and year if available. Be specific about Duke University vs other institutions. Note any ambiguity.
- Extract previous companies with roles, if available.
- Extract Twitter and LinkedIn handles.
- Determine duke_affiliation_status based *only* on the provided text:
  - "confirmed": Requires clear, unambiguous evidence of Duke affiliation (student, alumni, faculty, staff, attending program, etc.) from a credible source (university site, reputable news, LinkedIn profile confirming Duke). Must be about the specific person (beware common names).
  - "please review": Use if there's some indication but it's not definitive (ambiguous mentions, potential name confusion, unclear source credibility, mentions like "attended Duke program" without confirmation of completion/degree). Also use if the name itself contains "Duke" (e.g., David Duke) unless affiliation is clearly confirmed.
  - "no": Use if there is no evidence of Duke connection, only mentions of other universities, or clear evidence points away from Duke.
- Include relevant source links.
- Use null for missing fields. Return all arrays as JSON arrays.
- Base your extraction *only* on the provided search results text. Do not infer information not present.
- Be careful with common names and verify identity matches the search.
- Consider source credibility.
"""
# --- (End of Combined Prompt) ---


# (Keep DUKE_AFFILIATION_PROMPT commented out or remove if no longer needed elsewhere)
# DUKE_AFFILIATION_PROMPT = """..."""

class PersonProcessor:
    """
    Service for processing person data from search results and other sources.
    Handles data extraction, validation, and enrichment of person profiles.
    """
    
    def __init__(self):
        """Initialize processor with NLP service."""
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.founder_scorer = FounderScorer()
        self.nitter_scraper = NitterScraper()
        self.nitter_nlp = NitterNLP()
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.storage = StorageService()
        self.scraper = SERPScraper()
        
        logger.info(f"PersonProcessor initialized with model: {self.openai_model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2)
    )
    async def _process_with_llm(self, messages: List[Dict[str, str]], response_format=None) -> Dict[str, Any]:
        """Process messages with OpenAI LLM"""
        try:
            params = {
                "model": self.openai_model,
                "messages": messages,
                "temperature": 0.2
            }
            
            if response_format:
                params["response_format"] = { "type": response_format }
            
            response = await self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            try:
                # Attempt to remove markdown code block formatting if present
                if content.strip().startswith("```json"):
                     content = content.strip()[7:-3].strip()
                elif content.strip().startswith("```"):
                     content = content.strip()[3:-3].strip()
                     
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {content}")
                return {"error": "Failed to parse response", "raw_content": content}
                
        except Exception as e:
            logger.error(f"LLM processing failed: {str(e)}", exc_info=True)
            return {"error": str(e), "raw_content": None}

    async def _extract_person_info(self, person_name: str, serp_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract person information from SERP results using LLM.
        
        Args:
            person_name: The name of the person to extract information for
            serp_results: Dictionary containing SERP search results
            
        Returns:
            Dictionary containing extracted person information
        """
        logger.info(f"Extracting person info for: {person_name}")
        
        # Prepare search results text for LLM
        snippets = []
        for result in serp_results.get("organic_results", []):
            if result.get("snippet"):
                snippets.append(f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n")
        
        if not snippets:
            error_msg = f"No snippets found in SERP results for {person_name}"
            logger.error(error_msg)
            return {"error": error_msg, "name": person_name}
        
        # Prepare messages for LLM
        messages = [
            {"role": "system", "content": "You are a data extraction bot. Respond ONLY with the valid JSON object requested."},
            {"role": "user", "content": f"{COMBINED_PERSON_PROMPT}\n\nSearch Results:\n{chr(10).join(snippets)}"}
        ]
        
        try:
            person_data = await self._process_with_llm(messages, "json_object")
            
            if "error" in person_data:
                logger.error(f"LLM processing failed during person info extraction: {person_data.get('raw_content', person_data['error'])}")
                return {"error": f"LLM Error: {person_data['error']}", "name": person_name}
            
            # Ensure name is set correctly
            person_data["name"] = person_name
            
            # Ensure arrays are lists
            for field in ["education", "previous_companies", "source_links"]:
                if field in person_data and not isinstance(person_data[field], list):
                    person_data[field] = []
            
            logger.info(f"Successfully extracted info for person {person_name}")
            return person_data
            
        except Exception as e:
            error_msg = f"Person info extraction failed for {person_name}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "name": person_name}

    async def process_person(self, person_name: str, initial_serp_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process search results for an individual person.
        The pipeline is identical regardless of the source of the person name.

        Pipeline Stages:
        1. Get/load SERP results
        2. Extract person info and determine Duke affiliation
        3. Save intermediate processed data
        4. Add Twitter analysis if handle is available
        5. Calculate relevance score
        6. Save final data
        
        Args:
            person_name: The full name of the person to process
            initial_serp_results: Optional pre-fetched SERP results
        
        Returns:
            A dictionary containing the fully processed person data
        """
        logger.info(f"Processing person data for: {person_name}")
        
        try:
            # --- Stage 1: Get/load SERP results ---
            clean_name = self.storage._clean_filename(person_name)
            serp_path = self.storage.get_file_path("serp_person", clean_name, settings.RAW_DATA_DIR)
            
            if initial_serp_results:
                serp_results = initial_serp_results
            elif os.path.exists(serp_path):
                logger.info(f"Loading existing SERP results for {person_name}")
                serp_results = self.storage.load_data("serp_person", clean_name, settings.RAW_DATA_DIR)
            else:
                logger.info(f"Scraping new SERP data for {person_name}")
                serp_results = await self.scraper.search_founder(person_name)
                if serp_results:
                    self.storage.save_raw_data(serp_results, "serp_person", person_name)
            
            if not serp_results or "organic_results" not in serp_results:
                error_msg = f"No valid SERP results found for {person_name}"
                logger.error(error_msg)
                return {"error": error_msg, "name": person_name}
            
            # --- Stage 2: Extract person info ---
            person_data = await self._extract_person_info(person_name, serp_results)
            if "error" in person_data:
                return person_data
                
            # --- Stage 3: Save intermediate processed data ---
            processed_data = self._format_for_storage(person_data)
            self.storage.save_processed_data(
                processed_data,
                f"person_{clean_name}",
                "processed"
            )
            
            # --- Stage 4: Twitter analysis ---
            twitter_handle = person_data.get("twitter_handle")
            if twitter_handle:
                try:
                    raw_tweets = await self.nitter_scraper.get_raw_tweets(twitter_handle)
                    if raw_tweets and isinstance(raw_tweets, dict) and not raw_tweets.get("twitter_unavailable", True):
                        twitter_analysis = await self.nitter_nlp.analyze_tweets(raw_tweets["raw_tweets"])
                        person_data["twitter_summary"] = twitter_analysis[0]
                        twitter_urgency_score = twitter_analysis[1]
                    else:
                        logger.info(f"Twitter data unavailable for {person_name}")
                        person_data["twitter_summary"] = None
                        twitter_urgency_score = 0
                except Exception as e:
                    logger.error(f"Twitter analysis failed for {person_name}: {str(e)}")
                    person_data["twitter_summary"] = None
                    twitter_urgency_score = 0
            else:
                person_data["twitter_summary"] = None
                twitter_urgency_score = 0
            
            # --- Stage 5: Calculate relevance score ---
            person_data["relevance_score"] = self.founder_scorer.calculate_relevance_score(
                person_data,
                twitter_urgency_score
            )
            
            # --- Stage 6: Save final data ---
            final_path = self.storage.save_final_data(
                person_data,
                "person",
                person_name
            )
            logger.info(f"Saved final person data to {final_path}")
            
            return person_data
            
        except Exception as e:
            error_msg = f"Person processing failed for {person_name}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "name": person_name}

    def _format_for_storage(self, person_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format person data for storage, excluding calculated fields."""
        # Create a copy of the input data
        storage_data = person_data.copy()
        
        # Remove calculated fields that should not be stored
        storage_data.pop("twitter_summary", None)
        storage_data.pop("relevance_score", None)
        
        # Ensure arrays are lists
        for field in ["education", "previous_companies", "source_links"]:
            if field in storage_data and not isinstance(storage_data[field], list):
                storage_data[field] = []
        
        return storage_data
