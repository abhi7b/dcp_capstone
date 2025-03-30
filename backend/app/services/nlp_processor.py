import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import openai
from openai import AsyncOpenAI

from ..utils.config import settings
from ..utils.logger import nlp_logger
from .scorer import Scorer

class NLPProcessor:
    """
    NLP Processing service using OpenAI for extracting structured data.
    Implements a three-step process for company data processing:
    1. Extract company info and identify key people
    2. Determine Duke affiliation for each person
    3. Calculate final company Duke affiliation status and relevance score
    """
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.json_output_dir = settings.JSON_INPUTS_DIR
        # Initialize scorer for final step
        self.scorer = Scorer()
        
        # Use OpenAI client
        try:
            self.client = AsyncOpenAI(api_key=self.openai_api_key)
            nlp_logger.info(f"Initialized NLPProcessor with model: {self.openai_model}")
        except ImportError:
            nlp_logger.error("Failed to import AsyncOpenAI. Please install the OpenAI Python package.")
            raise
    
    def _save_json_data(self, raw_data: Dict[str, Any], extracted_data: Dict[str, Any], entity_type: str) -> None:
        """Save JSON data to file in the configured output directory."""
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get entity name from the extracted data or raw data
        entity_name = extracted_data.get("name", "unknown")
        # Sanitize filename
        entity_name = entity_name.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        
        # Create filename based on entity type and entity name
        filename = f"{entity_type}_{entity_name}_{timestamp}.json"
        file_path = os.path.join(self.json_output_dir, filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save data
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        
        nlp_logger.info(f"Saved {entity_type} data to {file_path}")
        
    async def _process_with_llm(self, messages: List[Dict[str, str]]) -> str:
        """Process messages with the OpenAI LLM and return the response text."""
        try:
            response = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.2,  # Low temperature for more deterministic outputs
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            nlp_logger.error(f"Error processing LLM request: {str(e)}")
            raise
    
    # ========== STEP 1: Initial Company Data Extraction ==========
    
    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    async def process_company_step1(self, serp_results: Dict[str, Any], twitter_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        STEP 1: Process raw SERP and Twitter data to extract company info and associated people.
        
        This initial step extracts all company details and identifies the list of key people
        (name and title) without attempting to determine Duke affiliation.
        """
        # Extract company name from the search parameters or other source
        company_name = serp_results.get("search_parameters", {}).get("q", "Unknown Company")
        if '"' in company_name:
            company_name = company_name.split('"')[1]
        
        nlp_logger.info(f"STEP 1: Processing company data for: {company_name}")
        
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
        
        # Comprehensive VC-tailored prompt for company extraction
        prompt = f"""
        You are a specialized venture capital research analyst. Extract comprehensive information about the company '{company_name}' from the provided text.
        Focus on identifying key information for VC evaluation, including all key people (founders, executives, leadership team).
        
        Extract the following data in a JSON structure matching this exact format:
        {{{{
            "name": "<Full Company Name>",
            "summary": "<1-3 sentence company description>",
            "investors": ["<Investor 1>", "<Investor 2>", ...],
            "funding_stage": "<e.g., Seed, Series A, etc.>",
            "industry": "<Primary industry/sector>",
            "founded": "<Year founded or YYYY-MM-DD>",
            "location": "<Headquarters location>",
            "twitter_handle": "<@handle>",
            "linkedin_handle": "<Full LinkedIn URL>",
            "twitter_summary": "<1-2 sentence summary of recent Twitter activity>",
            "source_links": ["<URL1>", "<URL2>", ...],
            "people": [
                {{{{
                    "name": "<Person's Full Name>",
                    "title": "<Person's Role at Company>"
                }}}},
                ...
            ]
        }}}}
        
        CRITERIA FOR EXTRACTING PEOPLE:
        - Include all founders and co-founders
        - Include C-suite executives (CEO, CTO, CFO, COO, etc.)
        - Include other key leadership (VP, Director-level)
        - For each person, extract ONLY their name and title within the company
        - The "people" list should contain all key individuals associated with the company
        
        IMPORTANT GUIDELINES:
        - Return well-formatted, valid JSON only
        - For any field where information is unavailable, use null instead of empty strings
        - Ensure arrays are empty lists [] not null when no items are found
        - ONLY extract information that appears in the provided text; do not make assumptions or add information not present
        - Use full, proper names (e.g., "John Smith" not "Smith" or "J. Smith")
        - Twitter handle should include @ symbol (e.g., "@company")
        - DO NOT include duke_affiliation_status; this will be determined in a later step
        - DO NOT add markdown code blocks or any other formatting around the JSON
        
        INFORMATION TO ANALYZE:
        {chr(10).join(all_snippets)}
        {twitter_context}
        """
        
        messages = [
            {"role": "system", "content": "You are an AI assistant specialized in venture capital research and data extraction. Extract structured information into clean JSON format. Do not format the JSON output with markdown code blocks."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = await self._process_with_llm(messages)
        
        try:
            # Clean up response text if it contains markdown code blocks
            cleaned_response = response_text
            
            # Remove code block markers if present
            if cleaned_response.startswith("```"):
                # Extract content between code block markers
                nlp_logger.info("Removing markdown code block markers from response")
                code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
                import re
                matches = re.search(code_block_pattern, cleaned_response)
                if matches:
                    cleaned_response = matches.group(1).strip()
                else:
                    # If regex fails, try a simpler approach
                    cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
            
            # Parse the cleaned JSON response
            extracted_data = json.loads(cleaned_response)
            
            # Basic validation and defaulting
            extracted_data.setdefault("name", company_name)
            extracted_data.setdefault("summary", None)
            extracted_data.setdefault("investors", [])
            extracted_data.setdefault("funding_stage", None)
            extracted_data.setdefault("industry", None)
            extracted_data.setdefault("founded", None)
            extracted_data.setdefault("location", None)
            extracted_data.setdefault("twitter_handle", None)
            extracted_data.setdefault("linkedin_handle", None)
            extracted_data.setdefault("twitter_summary", None)
            extracted_data.setdefault("source_links", [])
            extracted_data.setdefault("people", [])
            
            # Ensure people list has valid entries with name and title
            valid_people = []
            for person in extracted_data.get("people", []):
                if isinstance(person, dict) and person.get("name") and person.get("title"):
                    valid_people.append({
                        "name": person["name"],
                        "title": person["title"]
                    })
            extracted_data["people"] = valid_people
            
            # Save STEP 1 data
            self._save_json_data(serp_results, extracted_data, f"{company_name}_step1")
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            nlp_logger.error(f"STEP 1: Failed to parse JSON response for {company_name}: {e}\nResponse: {response_text}")
            return {"name": company_name, "error": "Failed to parse JSON response", "people": []}
        
        except Exception as e:
            nlp_logger.error(f"STEP 1: Unexpected error processing {company_name}: {e}", exc_info=True)
            return {"name": company_name, "error": f"Unexpected error: {str(e)}", "people": []}
    
    # ========== STEP 2: Person Duke Affiliation Determination ==========
    
    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    async def determine_person_duke_affiliation(self, person_name: str, person_title: str, duke_search_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        STEP 2: Determine if a person has Duke affiliation based on targeted search results.
        
        Returns person data with duke_affiliation_status determined.
        """
        nlp_logger.info(f"STEP 2: Determining Duke affiliation for: {person_name} ({person_title})")
        
        # Extract snippets from the Duke-specific search results
        all_snippets = []
        if "organic_results" in duke_search_results:
            for result in duke_search_results["organic_results"]:
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                link = result.get("link", "")
                if snippet:
                    all_snippets.append(f"TITLE: {title}\nURL: {link}\nSNIPPET: {snippet}\n")
        
        if not all_snippets:
            nlp_logger.warning(f"No snippets found in Duke search for {person_name}")
            return {
                "name": person_name,
                "title": person_title,
                "duke_affiliation_status": "no",
                "education": []
            }
        
        # Focused prompt for determining Duke affiliation
        prompt = f"""
        Analyze the provided text to determine if {person_name} ({person_title}) has a Duke University affiliation.
        Extract their education details, focusing specifically on evidence of Duke affiliation.
        
        Return your analysis as a JSON object with this exact structure:
        {{{{
            "name": "{person_name}",
            "title": "{person_title}",
            "duke_affiliation_status": "<confirmed | please review | no>",
            "education": [
                {{{{
                    "school": "<University Name>",
                    "degree": "<Degree Name or null>",
                    "years": "<Years attended or null>"
                }}}}
            ]
        }}}}
        
        DUKE AFFILIATION CRITERIA:
        - "confirmed": Clear evidence the person attended or graduated from Duke University or any Duke school (Fuqua, Law, etc.)
        - "please review": Ambiguous or indirect connection to Duke that needs review
        - "no": No evidence of Duke affiliation in the text
        
        IMPORTANT:
        - You must extract EDUCATION data for ANY schools mentioned (not just Duke)
        - The education array should be empty [] if no education data is found
        - Based ONLY on evidence in the provided text, do not make assumptions
        - Return valid JSON only without markdown code block formatting
        
        TEXT TO ANALYZE:
        {chr(10).join(all_snippets)}
        """
        
        messages = [
            {"role": "system", "content": "You are an AI assistant specialized in education background research and verification. Extract Duke University affiliation information with high precision. Return only JSON without markdown code blocks."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = await self._process_with_llm(messages)
        
        try:
            # Clean up response text if it contains markdown code blocks
            cleaned_response = response_text
            
            # Remove code block markers if present
            if cleaned_response.startswith("```"):
                # Extract content between code block markers
                nlp_logger.info("Removing markdown code block markers from response")
                code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
                import re
                matches = re.search(code_block_pattern, cleaned_response)
                if matches:
                    cleaned_response = matches.group(1).strip()
                else:
                    # If regex fails, try a simpler approach
                    cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
            
            # Parse the cleaned JSON response
            person_data = json.loads(cleaned_response)
            
            # Validate that required fields are present
            person_data.setdefault("name", person_name)
            person_data.setdefault("title", person_title)
            person_data.setdefault("duke_affiliation_status", "no")  # Default to "no"
            person_data.setdefault("education", [])
            
            # Validate affiliation status
            valid_statuses = ["confirmed", "please review", "no"]
            if person_data["duke_affiliation_status"] not in valid_statuses:
                nlp_logger.warning(f"Invalid affiliation status '{person_data['duke_affiliation_status']}' for {person_name}. Defaulting to 'please review'.")
                person_data["duke_affiliation_status"] = "please review"
            
            nlp_logger.info(f"Determined Duke affiliation for {person_name}: {person_data['duke_affiliation_status']}")
            
            # Save individual person affiliation data
            self._save_json_data(duke_search_results, person_data, f"person_{person_name}_affiliation")
            
            return person_data
            
        except json.JSONDecodeError as e:
            nlp_logger.error(f"STEP 2: Failed to parse JSON for {person_name} affiliation: {e}\nResponse: {response_text}")
            return {
                "name": person_name,
                "title": person_title,
                "duke_affiliation_status": "please review",  # Default to review if parsing fails
                "education": []
            }
            
        except Exception as e:
            nlp_logger.error(f"STEP 2: Unexpected error determining affiliation for {person_name}: {e}", exc_info=True)
            return {
                "name": person_name,
                "title": person_title,
                "duke_affiliation_status": "please review",
                "education": []
            }
    
    # ========== STEP 3: Finalize Company Data with Affiliation Status and Score ==========
    
    async def finalize_company_data(self, company_data: Dict[str, Any], processed_people: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        STEP 3: Finalize company data by determining overall Duke affiliation status and calculating scores.
        
        This final step:
        1. Determines overall company Duke affiliation status based on people
        2. Calculates the final relevance score using the Scorer
        3. Formats the complete company data for database storage
        """
        company_name = company_data.get("name", "Unknown Company")
        nlp_logger.info(f"STEP 3: Finalizing data for company: {company_name}")
        
        # 1. Determine company affiliation status based on people
        has_confirmed_person = any(p.get("duke_affiliation_status") == "confirmed" for p in processed_people)
        has_review_person = any(p.get("duke_affiliation_status") == "please review" for p in processed_people)
        
        if has_confirmed_person:
            company_duke_status = "confirmed"
        elif has_review_person:
            company_duke_status = "please review"
        else:
            company_duke_status = "no"
        
        nlp_logger.info(f"Company '{company_name}' Duke affiliation status: {company_duke_status}")
        
        # 2. Calculate final relevance score
        relevance_score = self.scorer.calculate_company_relevance_score(company_data, processed_people)
        
        # 3. Create the final company data structure
        final_company = {
            # Basic info from initial extraction
            "name": company_data.get("name"),
            "summary": company_data.get("summary"),
            "investors": company_data.get("investors"),
            "funding_stage": company_data.get("funding_stage"),
            "industry": company_data.get("industry"),
            "founded": company_data.get("founded"),
            "location": company_data.get("location"),
            "twitter_handle": company_data.get("twitter_handle"),
            "linkedin_handle": company_data.get("linkedin_handle"),
            "twitter_summary": company_data.get("twitter_summary"),
            "source_links": company_data.get("source_links"),
            
            # Determined affiliation and score
            "duke_affiliation_status": company_duke_status,
            "relevance_score": relevance_score,
            
            # Process people with full details
            "people": processed_people
        }
        
        # Save final company data
        self._save_json_data(company_data, final_company, f"{company_name}_final")
        
        return final_company
    
    # ========== Full Pipeline Method ==========
    
    async def process_company_pipeline(self, 
                                     company_serp_results: Dict[str, Any], 
                                     twitter_data: Optional[Dict[str, Any]] = None,
                                     person_duke_searches: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Run the complete 3-step pipeline to process a company:
        1. Extract company info and associated people
        2. Determine Duke affiliation for each person
        3. Finalize company data with affiliation status and score
        
        Args:
            company_serp_results: Raw SERP results for company search
            twitter_data: Optional Twitter data for the company
            person_duke_searches: Dict mapping person names to their Duke-specific search results
            
        Returns:
            Finalized company data ready for database insertion
        """
        # STEP 1: Extract basic company info and associated people
        company_step1 = await self.process_company_step1(company_serp_results, twitter_data)
        
        if "error" in company_step1:
            nlp_logger.error(f"Failed at step 1 for company: {company_step1.get('error')}")
            return company_step1
        
        # Extract people from step 1 results
        people = company_step1.get("people", [])
        if not people:
            nlp_logger.warning(f"No people found for company: {company_step1.get('name')}")
        
        # STEP 2: Process each person to determine Duke affiliation
        processed_people = []
        
        for person in people:
            person_name = person.get("name")
            person_title = person.get("title")
            
            # Skip if missing name
            if not person_name:
                continue
                
            # Get person's Duke search results if available
            person_duke_search = person_duke_searches.get(person_name) if person_duke_searches else None
            
            if person_duke_search:
                # Determine affiliation from search results
                person_data = await self.determine_person_duke_affiliation(
                    person_name, 
                    person_title, 
                    person_duke_search
                )
                processed_people.append(person_data)
            else:
                # No Duke search results available, default to "please review"
                nlp_logger.warning(f"No Duke search results for {person_name}, defaulting to 'please review'")
                processed_people.append({
                    "name": person_name,
                    "title": person_title,
                    "duke_affiliation_status": "please review",
                    "education": []
                })
        
        # STEP 3: Finalize company data with affiliation status and score
        final_company_data = await self.finalize_company_data(company_step1, processed_people)
        
        return final_company_data 