import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_fixed

from ..utils.logger import nlp_logger
from .nlp_processor import NLPProcessor

class PersonProcessor(NLPProcessor):
    """
    NLP processor specialized for standalone person/founder data extraction.
    This processor is used only for the /api/founder endpoint.
    It does not participate in the company processing pipeline.
    """
    
    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    async def process_founder_data(self, serp_results: Dict[str, Any], twitter_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process search results for an individual person (founder/executive).
        
        This processes a standalone person query (not as part of company processing):
        1. Extract comprehensive personal details
        2. Determine Duke affiliation status based on education history
        3. Calculate relevance score
        
        Used solely for the /api/founder endpoint.
        """
        # Extract person name from search parameters
        person_name = serp_results.get("search_parameters", {}).get("q", "Unknown Person")
        if '"' in person_name:
            person_name = person_name.split('"')[1]
        
        nlp_logger.info(f"Processing comprehensive data for person: {person_name}")
        
        # Collect search results snippets
        all_snippets = []
        if "organic_results" in serp_results:
            for result in serp_results["organic_results"]:
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                link = result.get("link", "")
                if snippet:
                    all_snippets.append(f"TITLE: {title}\nURL: {link}\nSNIPPET: {snippet}\n")
        
        # Prepare Twitter context if available
        twitter_context = ""
        if twitter_data and "tweets" in twitter_data:
            twitter_context = "\nRECENT TWEETS:\n"
            for tweet in twitter_data["tweets"]:
                twitter_context += f"\n- {tweet.get('content', '')}"
        
        # Comprehensive prompt for person extraction with education focus
        prompt = f"""
        You are a specialized venture capital researcher. Extract comprehensive information about {person_name} from the provided text.
        Focus on identifying their education history (especially any Duke University connections), work history, and contact information.
        
        Extract the following data in a JSON structure matching this exact format:
        {{{{
            "name": "<Full Name>",
            "title": "<Current Primary Role/Title>",
            "education": [
                {{{{
                    "school": "<University Name>",
                    "degree": "<Degree Name or null>",
                    "years": "<Years attended or null>"
                }}}},
                ...
            ],
            "duke_affiliation_status": "<confirmed | please review | no>",
            "current_company": "<Current Company Name>",
            "previous_companies": ["<Company 1>", "<Company 2>", ...],
            "twitter_handle": "<@handle>",
            "linkedin_handle": "<Full LinkedIn URL>",
            "source_links": ["<URL1>", "<URL2>", ...]
        }}}}
        
        DUKE AFFILIATION CRITERIA:
        - "confirmed": Clear evidence the person attended or graduated from Duke University or any Duke school (Fuqua, Law, etc.)
        - "please review": Ambiguous or indirect connection to Duke that needs review
        - "no": No evidence of Duke affiliation in the text
        
        IMPORTANT GUIDELINES:
        - Return well-formatted, valid JSON only
        - For any field where information is unavailable, use null instead of empty strings
        - Ensure arrays are empty lists [] not null when no items are found
        - ONLY extract information that appears in the provided text; do not make assumptions or add information not present
        - Use full, proper names (e.g., "John Smith" not "Smith" or "J. Smith")
        - Twitter handle should include @ symbol (e.g., "@person")
        - Education history should be comprehensive, listing ALL schools mentioned
        
        INFORMATION TO ANALYZE:
        {chr(10).join(all_snippets)}
        {twitter_context}
        """
        
        messages = [
            {"role": "system", "content": "You are an AI assistant specialized in biography research and data extraction. Extract structured information into clean JSON format."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = await self._process_with_llm(messages)
        
        try:
            # Parse the JSON response
            person_data = json.loads(response_text)
            
            # Basic validation and defaulting
            person_data.setdefault("name", person_name)
            person_data.setdefault("title", None)
            person_data.setdefault("education", [])
            person_data.setdefault("duke_affiliation_status", "no")  # Default to "no"
            person_data.setdefault("current_company", None)
            person_data.setdefault("previous_companies", [])
            person_data.setdefault("twitter_handle", None)
            person_data.setdefault("linkedin_handle", None)
            person_data.setdefault("source_links", [])
            
            # Validate affiliation status
            valid_statuses = ["confirmed", "please review", "no"]
            if person_data["duke_affiliation_status"] not in valid_statuses:
                nlp_logger.warning(f"Invalid affiliation status '{person_data['duke_affiliation_status']}' for {person_name}. Defaulting to 'please review'.")
                person_data["duke_affiliation_status"] = "please review"
            
            # Calculate relevance score
            relevance_score = self.scorer.calculate_person_relevance_score(person_data)
            person_data["relevance_score"] = relevance_score
            
            # Save the complete person data
            self._save_json_data(serp_results, person_data, f"{person_name}_final")
            
            return person_data
            
        except json.JSONDecodeError as e:
            nlp_logger.error(f"Failed to parse JSON response for person {person_name}: {e}\nResponse: {response_text}")
            return {
                "name": person_name, 
                "error": "Failed to parse JSON response",
                "duke_affiliation_status": "please review",
                "relevance_score": 0
            }
            
        except Exception as e:
            nlp_logger.error(f"Unexpected error processing person {person_name}: {e}", exc_info=True)
            return {
                "name": person_name, 
                "error": f"Unexpected error: {str(e)}",
                "duke_affiliation_status": "please review",
                "relevance_score": 0
            } 