import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_fixed
from ..utils.config import settings
from ..utils.logger import nlp_logger
from ..utils.storage import StorageService
from openai import AsyncOpenAI
from .nitter import NitterScraper
from .nitter_nlp import NitterNLP
from .company_scorer import CompanyScorer
from ..db.models import Company
from ..db.schemas import CompanyCreate, PersonBase
from .query_utils import QueryBuilder
from .scraper import SERPScraper

logger = logging.getLogger("nlp_processor")

class NLPProcessor:
    """
    NLP Processing service using OpenAI for extracting structured data.
    Implements a pipeline to extract company data and determine Duke affiliations.
    """
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.scorer = CompanyScorer()
        self.nitter_scraper = NitterScraper()
        self.nitter_nlp = NitterNLP()
        self.scraper = SERPScraper()
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.storage = StorageService()
        
        nlp_logger.info(f"NLPProcessor initialized with model: {self.openai_model}")
    
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
                nlp_logger.error(f"Failed to parse LLM response as JSON: {content}")
                return {"error": "Failed to parse response", "raw_content": content}
                
        except Exception as e:
            nlp_logger.error(f"LLM processing failed: {str(e)}")
            return {"error": str(e), "raw_content": None}

    def _preprocess_company_data(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess company data to ensure required fields and formats."""
        # Set defaults for required fields
        company_data.setdefault("name", "")
        company_data.setdefault("duke_affiliation_status", "no")
        company_data.setdefault("relevance_score", 0)
        
        # Convert list fields to comma-separated strings
        if "investors" in company_data:
            if isinstance(company_data["investors"], list):
                company_data["investors"] = ", ".join(str(investor) for investor in company_data["investors"])
            elif company_data["investors"] is None:
                company_data["investors"] = ""
        
        if "source_links" in company_data:
            if isinstance(company_data["source_links"], list):
                company_data["source_links"] = ", ".join(str(link) for link in company_data["source_links"])
            elif company_data["source_links"] is None:
                company_data["source_links"] = ""
        
        # Handle Twitter summary
        if "twitter_summary" not in company_data or company_data["twitter_summary"] is None:
            company_data["twitter_summary"] = ""
        elif isinstance(company_data["twitter_summary"], dict):
            company_data["twitter_summary"] = str(company_data["twitter_summary"].get("summary", ""))
        
        return company_data

    async def process_company(self, company_name: str, serp_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process company data through the complete pipeline"""
        nlp_logger.info(f"Processing company: {company_name}")
        
        # Step 1: Extract company information from SERP results
        company_data = await self._extract_company_info(company_name, serp_results)
        if "error" in company_data:
            return company_data
            
        # Save intermediate company data
        self.storage.save_processed_data(
            company_data,
            f"company_{company_name}",
            "intermediate"
        )
        
        # Step 2: Process each person's education
        processed_people = []
        for person in company_data.get("people", []):
            person_data = await self._process_person_education(person)
            processed_people.append(person_data)
            
        # Save intermediate person data
        self.storage.save_processed_data(
            {"people": processed_people},
            f"company_{company_name}",
            "people"
        )
        
        # Step 3: Get Twitter data if handle exists
        twitter_urgency_score = None
        twitter_summary = None
        if company_data.get("twitter_handle"):
            try:
                raw_tweets = await self.nitter_scraper.get_raw_tweets(company_data["twitter_handle"])
                if not raw_tweets.get("twitter_unavailable", True):
                    twitter_analysis = await self.nitter_nlp.analyze_tweets(raw_tweets["raw_tweets"])
                    twitter_summary = twitter_analysis[0]
                    twitter_urgency_score = twitter_analysis[1]
                    
                    # Save Twitter analysis
                    twitter_data = {
                        "summary": twitter_summary,
                        "urgency_score": twitter_urgency_score
                    }
                    self.storage.save_processed_data(
                        twitter_data,
                        "nitter_analysis",
                        company_name
                    )
            except Exception as e:
                nlp_logger.error(f"Twitter analysis failed: {str(e)}")
                twitter_summary = None
                twitter_urgency_score = None
                
        # Step 4: Determine Duke affiliation based on people
        company_data["duke_affiliation_status"] = self._determine_company_affiliation(processed_people)
        
        # Step 5: Calculate relevance score
        company_data["relevance_score"] = self.scorer.calculate_relevance_score(
            company_data, processed_people, twitter_urgency_score
        )
        
        # Add Twitter summary to final data (just the summary text, not the score)
        if twitter_summary:
            company_data["twitter_summary"] = twitter_summary
        
        # Step 6: Save final company data
        final_path = self.storage.save_final_data(
            company_data,
            "company",
            company_name
        )
        nlp_logger.info(f"Saved final data to {final_path}")
        
        return company_data

    async def _extract_company_info(self, company_name: str, serp_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract company information from SERP results"""
        nlp_logger.info(f"Extracting company info for: {company_name}")
        
        # Extract snippets from SERP results
        snippets = [
            f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n"
            for result in serp_results.get("organic_results", [])
            if result.get("snippet")
        ]
        
        if not snippets:
            return {"error": "No data found"}
        
        messages = [
            {"role": "system", "content": "You are a VC research analyst extracting company information. Return valid JSON matching the specified structure."},
            {"role": "user", "content": f"""
            Extract information about {company_name} from the provided text.
            Return a JSON object with these fields (use null for missing fields):
            {{
                "name": "Company Name",
                "summary": "1-3 sentence description",
                "investors": ["Investor1", "Investor2"],
                "funding_stage": "e.g., Seed, Series A",
                "industry": "Primary industry",
                "founded": "YYYY or YYYY-MM-DD",
                "location": "HQ location",
                "twitter_handle": "handle_without_at",
                "linkedin_handle": "URL",
                "source_links": ["URL1", "URL2"],
                "people": [
                    {{"name": "Full Name", "title": "Role"}}
                ]
            }}
            
            IMPORTANT:
            - Use null for missing fields
            - Include ALL founders and C-level executives
            - Only extract information present in the text
            
            TEXT TO ANALYZE:
            {chr(10).join(snippets)}
            """}
        ]
        
        try:
            company_data = await self._process_with_llm(messages, "json_object")
            if "error" in company_data:
                return company_data
                
            # Ensure all required fields exist
            company_data.setdefault("name", company_name)
            company_data.setdefault("summary", None)
            company_data.setdefault("investors", None)
            company_data.setdefault("funding_stage", None)
            company_data.setdefault("industry", None)
            company_data.setdefault("founded", None)
            company_data.setdefault("location", None)
            company_data.setdefault("twitter_handle", None)
            company_data.setdefault("linkedin_handle", None)
            company_data.setdefault("source_links", None)
            company_data.setdefault("people", [])
            
            return company_data
            
        except Exception as e:
            nlp_logger.error(f"Company info extraction failed: {str(e)}")
            return {"error": str(e)}

    async def _process_person_education(self, person: Dict[str, Any]) -> Dict[str, Any]:
        """Process a person's education history"""
        person_name = person["name"]
        person_title = person["title"]
        
        nlp_logger.info(f"Processing education for: {person_name}")
        
        # Get Duke-specific queries for this person
        duke_queries = QueryBuilder.get_person_duke_affiliation_queries(person_name)
        
        # Run SERP search for each query and collect results
        all_results = []
        for query in duke_queries:
            try:
                serp_results = await self.scraper.search(query)
                if serp_results and "organic_results" in serp_results:
                    all_results.extend(serp_results["organic_results"])
            except Exception as e:
                nlp_logger.error(f"SERP search failed for query '{query}': {str(e)}")
                continue
        
        # Extract snippets from all search results
        snippets = [
            f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n"
            for result in all_results
            if result.get("snippet")
        ]
        
        if not snippets:
            return {
                "name": person_name,
                "title": person_title,
                "duke_affiliation_status": "no",
                "education": []
            }
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that determines if a person has an affiliation with Duke University based on search results."},
            {"role": "user", "content": f"""
            Analyze these search results for {person_name} and determine if they have any connection to Duke University.
            
            Return a JSON object with these fields:
            {{
                "name": "{person_name}",
                "title": "{person_title}",
                "duke_affiliation_status": "confirmed", "please review", or "no",
                "education": [
                    {{
                        "school": "University Name",
                        "degree": "Degree type",
                        "field": "Field of study",
                        "year": "Year (if available)"
                    }}
                ]
            }}
            
            IMPORTANT GUIDELINES:
            - "confirmed" means clear evidence of Duke affiliation (student, alumni, faculty, etc.)
            - "please review" means some indication but not definitive
            - "no" means no evidence of Duke connection
            - For education, include ALL education history found, not just Duke
            - Return a complete education list even if duke_affiliation_status is "no"
            
            SEARCH RESULTS:
            {chr(10).join(snippets)}
            """}
        ]
        
        try:
            person_data = await self._process_with_llm(messages, "json_object")
            return person_data
            
        except Exception as e:
            nlp_logger.error(f"Person education processing failed for {person_name}: {str(e)}")
            return {
                "name": person_name,
                "title": person_title,
                "duke_affiliation_status": "please review",
                "education": []
            }

    def _determine_company_affiliation(self, processed_people: List[Dict[str, Any]]) -> str:
        """Determine company's Duke affiliation status based on its people"""
        has_confirmed = any(p["duke_affiliation_status"] == "confirmed" for p in processed_people)
        has_review = any(p["duke_affiliation_status"] == "please review" for p in processed_people)
        
        if has_confirmed:
            return "confirmed"
        elif has_review:
            return "please review"
        else:
            return "no" 