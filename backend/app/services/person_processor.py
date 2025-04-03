import logging
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_fixed

from ..utils.config import settings
from ..utils.logger import nlp_logger
from ..utils.storage import StorageService
from openai import AsyncOpenAI
from .founder_scorer import FounderScorer
from .nitter import NitterScraper
from .nitter_nlp import NitterNLP
from ..db.schemas import PersonBase, PersonInDB

logger = logging.getLogger("person_processor")

# Combined person extraction prompt with education and Duke affiliation
PERSON_EXTRACTION_PROMPT = """You are a VC research analyst extracting structured information about individuals, especially entrepreneurs and business leaders.
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
- Extract ALL education history, not just Duke
- For duke_affiliation_status:
  - "confirmed" means clear evidence of Duke affiliation (student, alumni, faculty, etc.)
  - "please review" means some indication but not definitive
  - "no" means no evidence of Duke connection
- Include roles in previous_companies entries
- Return all arrays as JSON arrays
- Use null for missing fields
- Only extract information present in the text
"""

class PersonProcessor:
    """
    Standalone processor for person/founder data extraction.
    This processor is used only for the /api/founder endpoint.
    """
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.founder_scorer = FounderScorer()
        self.nitter_scraper = NitterScraper()
        self.nitter_nlp = NitterNLP()
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.storage = StorageService()
        
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
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {content}")
                return {"error": "Failed to parse response", "raw_content": content}
                
        except Exception as e:
            logger.error(f"LLM processing failed: {str(e)}")
            return {"error": str(e), "raw_content": None}
    
    async def process_person(self, person_name: str, serp_results: Dict[str, Any] = None) -> PersonInDB:
        """
        Process search results for an individual person (founder/executive).
        
        1. Extract comprehensive personal details including Duke affiliation
        2. Add Twitter analysis if handle is available
        3. Calculate relevance score
        """
        logger.info(f"Processing person data for: {person_name}")
        
        try:
            # If no SERP results provided, return error
            if not serp_results or not serp_results.get("organic_results"):
                logger.warning(f"No SERP results provided for {person_name}")
                return PersonInDB(
                    name=person_name,
                    duke_affiliation_status="please review",
                    twitter_summary="",
                    relevance_score=0
                )
            
            # Extract person data with education and Duke affiliation
            raw_person_data = await self._extract_person_info(serp_results, person_name)
            
            # Ensure all required fields exist with proper defaults
            raw_person_data.setdefault("name", person_name)
            raw_person_data.setdefault("title", None)
            raw_person_data.setdefault("current_company", None)
            raw_person_data.setdefault("education", [])
            raw_person_data.setdefault("previous_companies", [])
            raw_person_data.setdefault("twitter_handle", None)
            raw_person_data.setdefault("linkedin_handle", None)
            raw_person_data.setdefault("duke_affiliation_status", "please review")
            raw_person_data.setdefault("source_links", [])
            
            # Convert source links from dictionaries to strings
            if "source_links" in raw_person_data:
                raw_person_data["source_links"] = [
                    link["url"] if isinstance(link, dict) else link
                    for link in raw_person_data["source_links"]
                ]
            
            # Save intermediate data
            intermediate_path = self.storage.save_processed_data(
                raw_person_data,
                "person",
                raw_person_data.get("name", person_name)
            )
            
            # Add Twitter summary if available
            twitter_urgency_score = None
            if raw_person_data.get("twitter_handle"):
                try:
                    raw_tweets = await self.nitter_scraper.get_raw_tweets(raw_person_data["twitter_handle"])
                    if raw_tweets and not raw_tweets.get("twitter_unavailable", True) and raw_tweets.get("raw_tweets"):
                        twitter_analysis = await self.nitter_nlp.analyze_tweets(raw_tweets["raw_tweets"])
                        raw_person_data["twitter_summary"] = twitter_analysis[0]
                        twitter_urgency_score = twitter_analysis[1]
                    else:
                        raw_person_data["twitter_summary"] = "Twitter data unavailable"
                        twitter_urgency_score = 50  # Default middle score
                except Exception as e:
                    logger.error(f"Twitter analysis failed: {str(e)}")
                    raw_person_data["twitter_summary"] = "Error analyzing Twitter data"
                    twitter_urgency_score = 50  # Default middle score
            else:
                raw_person_data["twitter_summary"] = "No Twitter handle found"
                twitter_urgency_score = 50  # Default middle score
            
            # Calculate relevance score
            raw_person_data["relevance_score"] = self.founder_scorer.calculate_relevance_score(
                raw_person_data,
                twitter_urgency_score
            )
            
            # Create validated Person object
            person = PersonBase(**raw_person_data)
            
            # Save final data to JSON_INPUTS_DIR
            try:
                final_path = self.storage.save_final_data(
                    person.dict(),
                    "person",
                    person.name
                )
                logger.info(f"Saved final data to {final_path}")
            except Exception as e:
                logger.error(f"Failed to save final data: {str(e)}")
                # Continue with the process even if saving fails
            
            # Return processed result with additional fields for PersonInDB
            return PersonInDB(
                **person.dict(),
                id=0,  # This will be set by the database
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error processing person data for {person_name}: {str(e)}")
            # Create a basic person object with error information
            error_person = PersonBase(
                name=person_name,
                duke_affiliation_status="please review",
                twitter_summary="",
                relevance_score=0,
                error=str(e)
            )
            
            # Try to save the error state
            try:
                self.storage.save_final_data(
                    error_person.dict(),
                    "person",
                    person_name
                )
            except Exception as save_error:
                logger.error(f"Failed to save error state: {str(save_error)}")
            
            return PersonInDB(
                **error_person.dict(),
                id=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
    
    async def _extract_person_info(self, serp_results: Dict[str, Any], person_name: str = "") -> Dict[str, Any]:
        """Extract structured person information from SERP results"""
        try:
            if not serp_results or not serp_results.get("organic_results"):
                logger.warning("No SERP results to extract person data from")
                return {
                    "name": person_name,
                    "duke_affiliation_status": "please review",
                    "education": [],
                    "relevance_score": 0
                }
                
            # Extract snippets from SERP results
            snippets = [
                f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n"
                for result in serp_results.get("organic_results", [])
                if result.get("snippet")
            ]
            
            if not snippets:
                logger.warning("No snippets found in SERP results")
                return {
                    "name": person_name,
                    "duke_affiliation_status": "please review",
                    "education": [],
                    "relevance_score": 0
                }
            
            # Construct messages for LLM
            messages = [
                {"role": "system", "content": PERSON_EXTRACTION_PROMPT},
                {"role": "user", "content": f"""
                Extract information about {person_name if person_name else "the person"} from these search results:
                
                {chr(10).join(snippets)}
                """}
            ]
            
            # Send to GPT for extraction
            person_data = await self._process_with_llm(messages, "json_object")
            if "error" in person_data:
                logger.error(f"Error in LLM processing: {person_data['error']}")
                return {
                    "name": person_name,
                    "duke_affiliation_status": "please review",
                    "education": [],
                    "relevance_score": 0
                }
            
            logger.info(f"Extracted person data for {person_data.get('name', 'unknown person')}")
            logger.info(
                f"Duke affiliation for {person_data.get('name', 'unknown person')}: "
                f"{person_data.get('duke_affiliation_status', 'unknown')}"
            )
            
            return person_data
            
        except Exception as e:
            logger.error(f"Error extracting person data: {str(e)}")
            return {
                "name": person_name,
                "duke_affiliation_status": "please review",
                "education": [],
                "relevance_score": 0
            }

    def _preprocess_data(self, raw_person_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess raw person data to ensure required fields and formats."""
        # Set defaults for required fields
        raw_person_data.setdefault("name", "")
        raw_person_data.setdefault("title", "")
        raw_person_data.setdefault("duke_affiliation_status", "no")
        raw_person_data.setdefault("relevance_score", 0)
        
        # Convert list fields to comma-separated strings
        if "education" in raw_person_data:
            if isinstance(raw_person_data["education"], list):
                raw_person_data["education"] = ", ".join(str(edu) for edu in raw_person_data["education"])
            elif raw_person_data["education"] is None:
                raw_person_data["education"] = ""
        
        if "previous_companies" in raw_person_data:
            if isinstance(raw_person_data["previous_companies"], list):
                raw_person_data["previous_companies"] = ", ".join(str(company) for company in raw_person_data["previous_companies"])
            elif raw_person_data["previous_companies"] is None:
                raw_person_data["previous_companies"] = ""
        
        if "source_links" in raw_person_data:
            if isinstance(raw_person_data["source_links"], list):
                raw_person_data["source_links"] = ", ".join(str(link) for link in raw_person_data["source_links"])
            elif raw_person_data["source_links"] is None:
                raw_person_data["source_links"] = ""
        
        # Handle Twitter summary
        if "twitter_summary" not in raw_person_data or raw_person_data["twitter_summary"] is None:
            raw_person_data["twitter_summary"] = ""
        
        return raw_person_data

# Test case removed as requested 