"""
NLP Processor Module

Natural Language Processing service for analyzing and extracting
information from text data using OpenAI's language models.

Key Features:
- Text analysis
- Entity extraction
- Content classification
- Sentiment analysis
"""

import openai
from typing import Dict, Any, List, Tuple, Optional
import json
import logging 
from tenacity import retry, stop_after_attempt, wait_fixed
from ..utils.config import settings
from ..utils.logger import nlp_logger as logger
from ..utils.storage import StorageService
from openai import AsyncOpenAI
from .nitter import NitterScraper
from .nitter_nlp import NitterNLP
from .company_scorer import CompanyScorer
from ..db.models import Company
from ..db.schemas import CompanyCreate, PersonBase
from .query_utils import QueryBuilder
from .scraper import SERPScraper
from .person_processor import PersonProcessor
from ..db import person_crud, schemas  # Add schemas import
from ..db.person_crud import get_person_by_name as get_person_from_db
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.session import get_db
from collections.abc import AsyncGenerator # For type hinting async generator
import contextlib # For closing async generator

# Helper to correctly handle async generator context
@contextlib.asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_generator = get_db()
    db = await session_generator.__anext__()
    try:
        yield db
    finally:
        await db.close()

class NLPProcessor:
    """
    Service for processing text data using OpenAI's language models.
    Handles entity extraction, classification, and text analysis.
    """
    
    def __init__(self):
        """Initialize OpenAI client with API key."""
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.scorer = CompanyScorer()
        self.nitter_scraper = NitterScraper()
        self.nitter_nlp = NitterNLP()
        self.scraper = SERPScraper()
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.storage = StorageService()
        self.person_processor = PersonProcessor()
        
        logger.info(f"NLPProcessor initialized with model: {self.openai_model}")
    
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

    async def process_company(self, serp_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process company data through a multi-stage pipeline:
        1. Extract initial company info + basic people list. Save intermediate.
        2. Process each person fully via PersonProcessor, save to DB. Save processed people list intermediate.
        3. Determine company affiliation, add company Twitter analysis, score company.
        4. Assemble and save final company data including fully processed people.
        """
        # Extract company name from search parameters
        search_query = serp_results.get("search_parameters", {}).get("query", "")
        # Extract company name from the query (e.g., "Multi-query search for OpenAI" -> "OpenAI")
        company_name = search_query.replace("Multi-query search for ", "").strip()
        if not company_name:
            company_name = "UnknownCompany"
            
        logger.info(f"Processing company: {company_name}")
        
        # --- Stage 1: Initial Company Extraction & Save ---
        initial_company_data = await self._extract_company_info(company_name, serp_results)
        if "error" in initial_company_data:
             logger.error(f"Stage 1: Company info extraction failed for {company_name}: {initial_company_data['error']}")
             return initial_company_data # Propagate error early
             
        initial_company_data.setdefault("name", company_name)
        initial_company_data.setdefault("people", [])
             
        # Clean company name for filename
        clean_company_name = self.storage._clean_filename(company_name)
        
        # Save intermediate extraction with all company fields except nitter summary, final score, and duke affiliation
        intermediate_data = {
            "name": initial_company_data["name"],
            "summary": initial_company_data.get("summary"),
            "investors": initial_company_data.get("investors", []),
            "funding_stage": initial_company_data.get("funding_stage"),
            "industry": initial_company_data.get("industry"),
            "founded": initial_company_data.get("founded"),
            "location": initial_company_data.get("location"),
            "twitter_handle": initial_company_data.get("twitter_handle"),
            "linkedin_handle": initial_company_data.get("linkedin_handle"),
            "source_links": initial_company_data.get("source_links", []),
            "people": initial_company_data["people"]
        }
        self.storage.save_processed_data(
            intermediate_data,
            f"company_{clean_company_name}",
            "intermediate_extraction" 
        )
        logger.info(f"Stage 1: Completed initial extraction for {company_name}")

        # --- Stage 2: Process Associated People ---
        fully_processed_people = []
        initial_people_stubs = initial_company_data.get("people", [])
        
        if initial_people_stubs:
            logger.info(f"Stage 2: Found {len(initial_people_stubs)} potential people for {company_name}. Processing each.")
            # Use a single DB session for all person operations within this company process
            async with get_db_session() as db:
                for person_stub in initial_people_stubs:
                    person_name_from_stub = person_stub.get("name")
                    if not person_name_from_stub or not isinstance(person_name_from_stub, str) or len(person_name_from_stub.strip()) == 0:
                        logger.warning("Found person entry with invalid or missing name, skipping.")
                        continue
                    
                    processed_person_dict = None # Define before try block
                    try:
                        logger.info(f"Stage 2: Invoking PersonProcessor for: {person_name_from_stub}")
                        processed_person_dict = await self.person_processor.process_person(person_name=person_name_from_stub)
                        
                        if "error" in processed_person_dict:
                            logger.error(f"Stage 2: PersonProcessor failed for {person_name_from_stub}: {processed_person_dict['error']}")
                            fully_processed_people.append({
                                "name": person_name_from_stub,
                                "title": person_stub.get("title"),
                                "duke_affiliation_status": "please review", # Default on error
                                "error": f"PersonProcessor Error: {processed_person_dict['error']}"
                            })
                            continue # Move to the next person
                        
                        # Successfully processed - Add to list for company output
                        fully_processed_people.append(processed_person_dict)
                                
                    except Exception as e:
                        logger.error(f"Stage 2: Error processing person {person_name_from_stub} via PersonProcessor: {str(e)}", exc_info=True)
                        fully_processed_people.append({
                            "name": person_name_from_stub,
                            "title": person_stub.get("title"),
                            "duke_affiliation_status": "please review",
                            "error": f"PersonProcessor call failed: {str(e)}"
                        })
                        continue # Move to the next person

            logger.info(f"Stage 2: Completed processing {len(initial_people_stubs)} people stubs for {company_name}. Resulted in {len(fully_processed_people)} entries.")
        else:
             logger.info(f"Stage 2: No people found in initial extraction for {company_name}. Skipping person processing.")

        # --- Stage 3: Final Company Enrichment & Save ---
        logger.info(f"Stage 3: Starting final enrichment for {company_name}")
        
        # Determine Company Duke affiliation based on fully processed people
        company_duke_affiliation = self._determine_company_affiliation(fully_processed_people)
        
        # Get Company Twitter data if handle exists
        company_twitter_urgency_score = None
        company_twitter_summary = None
        company_twitter_handle = initial_company_data.get("twitter_handle")
        if company_twitter_handle:
            try:
                raw_tweets = await self.nitter_scraper.get_raw_tweets(company_twitter_handle)
                if raw_tweets and isinstance(raw_tweets, dict) and not raw_tweets.get("twitter_unavailable", True) and raw_tweets.get("raw_tweets"):
                    twitter_analysis = await self.nitter_nlp.analyze_tweets(raw_tweets["raw_tweets"])
                    company_twitter_summary = twitter_analysis[0]
                    company_twitter_urgency_score = twitter_analysis[1]
                elif raw_tweets and isinstance(raw_tweets, dict) and raw_tweets.get("twitter_unavailable"):
                     logger.info(f"Stage 3: Company Twitter handle {company_twitter_handle} unavailable via Nitter.")
                else:
                     logger.warning(f"Stage 3: Unexpected Nitter response structure for {company_name}: {raw_tweets}")
            except Exception as e:
                logger.error(f"Stage 3: Company Twitter analysis failed for {company_name}: {str(e)}", exc_info=True)
        else:
            logger.info(f"Stage 3: No Twitter handle found for company {company_name}.")
                
        # Calculate Company relevance score
        company_relevance_score = self.scorer.calculate_relevance_score(
            initial_company_data, 
            fully_processed_people, 
            company_twitter_urgency_score
        )
        logger.info(f"Stage 3: Calculated company score for {company_name}: {company_relevance_score}")
        
        # Assemble final company data object with all fields from Company model
        final_company_data = {
            "name": intermediate_data["name"],
            "duke_affiliation_status": company_duke_affiliation,
            "relevance_score": company_relevance_score,
            "summary": intermediate_data.get("summary"),
            "investors": intermediate_data.get("investors", []),
            "funding_stage": intermediate_data.get("funding_stage"),
            "industry": intermediate_data.get("industry"),
            "founded": intermediate_data.get("founded"),
            "location": intermediate_data.get("location"),
            "twitter_handle": intermediate_data.get("twitter_handle"),
            "linkedin_handle": intermediate_data.get("linkedin_handle"),
            "twitter_summary": company_twitter_summary,
            "source_links": intermediate_data.get("source_links", []),
            # Format people data to only include name and title
            "people": [
                {
                    "name": person.get("name"),
                    "title": person.get("title")
                }
                for person in fully_processed_people
                if person.get("name") and person.get("title")
            ]
        }
        
        # Save final data to json_inputs (includes simplified people list)
        final_path = self.storage.save_final_data(
            final_company_data,
            "company",
            company_name
        )
        logger.info(f"Stage 3: Saved final company JSON data to {final_path}")
        
        # Prepare data suitable for DB save (lists to strings etc.)
        db_formatted_data = self._format_company_for_db(final_company_data)
        
        logger.info(f"Company processing pipeline completed successfully for {company_name}")
        return db_formatted_data

    async def _extract_company_info(self, company_name: str, serp_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract initial company information and basic people list from SERP results"""
        logger.info(f"Extracting initial company info for: {company_name}")
        
        snippets = [
            f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n"
            for result in serp_results.get("organic_results", [])
            if result.get("snippet")
        ]
        
        if not snippets:
            logger.warning(f"No snippets found for company {company_name} during info extraction.")
            return {"error": "No snippets found in SERP results"}
        
        extraction_prompt = f"""
        You are a VC research analyst extracting structured information about individuals, especially entrepreneurs and business leaders, with a specific focus on Duke University affiliation.
        Your task is to extract key information from the provided search results for a {company_name}.
        
        Return ONLY a valid JSON object with these fields (use null if info not found):
        {{
            "name": "Company Name" | string,
            "industry": "Company's industry" | string or null,
            "founded": "Year founded (YYYY)" | string or null,
            "location": "Company headquarters location" | string or null,
            "funding_stage": "Latest known stage (e.g., Seed, Series A)" | string or null,
            "investors": ["Investor 1", "Investor 2", ...] | array of strings or null,
            "summary": "Brief 1-2 sentence company description" | string or null,
            "twitter_handle": "@_handle" | string or null,
            "linkedin_handle": "Full LinkedIn company URL" | string or null,
            "people": [ {{ "name": "Person Name", "title": "Their role" }}, ... ] | array of objects or [],
            "source_links": ["URL1", "URL2", ...] | array of strings or []
        }}

        IMPORTANT: 
        - Focus on accuracy. If unsure, use null.
        - For 'people', include founders, CEO, key executives if mentioned. Only include name and title.
        - Provide ONLY the JSON object, no explanations or surrounding text.
        
        Search Results:
        {chr(10).join(snippets)}
        """

        messages = [
            {"role": "system", "content": "You are a data extraction bot. Respond ONLY with the valid JSON object requested."},
            {"role": "user", "content": extraction_prompt}
        ]
        
        try:
            company_data = await self._process_with_llm(messages, "json_object")
            
            if "error" in company_data:
                 logger.error(f"LLM processing failed during initial company info extraction: {company_data.get('raw_content', company_data['error'])}")
                 return {"error": f"LLM Error: {company_data['error']}", "raw_content": company_data.get("raw_content")}

            # Basic validation and defaulting after LLM
            company_data.setdefault("name", company_name)
            company_data.setdefault("people", [])
            company_data.setdefault("investors", [])
            company_data.setdefault("source_links", [])
            # Ensure people is a list of dicts with name/title
            if not isinstance(company_data["people"], list):
                company_data["people"] = []
            else:
                company_data["people"] = [
                    p for p in company_data["people"] 
                    if isinstance(p, dict) and p.get("name")
                ]
            
            logger.info(f"Successfully extracted initial info for company {company_name}")
            return company_data
            
        except Exception as e:
            logger.error(f"Initial company info extraction failed for {company_name}: {str(e)}", exc_info=True)
            return {"error": f"Initial company info extraction exception: {str(e)}"}

    def _determine_company_affiliation(self, fully_processed_people: List[Dict[str, Any]]) -> str:
        """Determine company's Duke affiliation status based on its fully processed people list."""
        if not fully_processed_people:
            logger.info("Determining company affiliation: No processed people found.")
            return "no" 
            
        # Check affiliation status, ignoring entries that had processing errors
        has_confirmed = any(p.get("duke_affiliation_status") == "confirmed" and "error" not in p for p in fully_processed_people)
        has_review = any(p.get("duke_affiliation_status") == "please review" and "error" not in p for p in fully_processed_people)
        
        if has_confirmed:
            logger.info("Company affiliation set to 'confirmed' based on associated people.")
            return "confirmed"
        elif has_review:
            logger.info("Company affiliation set to 'please review' based on associated people.")
            return "please review"
        else:
            # This means everyone processed successfully and had status 'no', or everyone failed processing
            all_failed = all("error" in p for p in fully_processed_people)
            if all_failed:
                 logger.warning("Could not determine company affiliation as all associated people failed processing.")
                 return "please review" # Default to review if all people failed
            else:
                 logger.info("No Duke affiliation confirmed or needing review among associated people.")
                 return "no"

    def _format_company_for_db(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Ensure company data is in the correct format for database operations """
        db_ready_data = company_data.copy()

        # Convert lists to comma-separated strings for specific DB columns
        if isinstance(db_ready_data.get("investors"), list):
            db_ready_data["investors"] = ", ".join(filter(None, db_ready_data["investors"]))
            
        if isinstance(db_ready_data.get("source_links"), list):
            db_ready_data["source_links"] = ", ".join(filter(None, db_ready_data["source_links"]))
            
        # Keep the people list for later processing
        people_data = db_ready_data.get("people", [])
        db_ready_data["people"] = people_data

        # Remove other potential non-model fields or error flags
        db_ready_data.pop("error", None)
        db_ready_data.pop("raw_content", None)
        db_ready_data.pop("db_error", None) # Remove DB error flags if present
        
        # Ensure all fields match Company model columns - remove any extras
        allowed_keys = {col.name for col in Company.__table__.columns}
        allowed_keys.add("people")  # Add people to allowed keys
        keys_to_remove = {key for key in db_ready_data if key not in allowed_keys}
        for key in keys_to_remove:
            db_ready_data.pop(key)
            
        return db_ready_data 