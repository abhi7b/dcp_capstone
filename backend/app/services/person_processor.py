import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_fixed

from ..utils.logger import nlp_logger
from .nlp_processor import NLPProcessor
from .founder_scorer import FounderScorer
from .nitter import NitterScraper
from .nitter_nlp import NitterNLP

class PersonProcessor(NLPProcessor):
    """
    NLP processor specialized for standalone person/founder data extraction.
    This processor is used only for the /api/founder endpoint.
    It does not participate in the company processing pipeline.
    """
    
    def __init__(self):
        super().__init__()
        self.scorer = FounderScorer()
        self.nitter_scraper = NitterScraper()
        self.nitter_nlp = NitterNLP()
        # Set up JSON directory for saving data
        self.json_dir = os.path.join(os.path.dirname(__file__), "..", "data", "json_inputs")
        os.makedirs(self.json_dir, exist_ok=True)
        nlp_logger.info("PersonProcessor initialized with FounderScorer and Nitter components")
    
    def _save_person_data(self, data: Dict[str, Any], name: str, data_type: str = "final") -> None:
        """Save person data to appropriate directory based on type"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"person_{name}_{timestamp}.json"
        
        save_dir = os.path.join(
            self.json_dir,
            "..",
            "raw" if data_type == "raw" else "processed" if data_type == "processed" else ""
        )
            
        filepath = os.path.join(save_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        nlp_logger.info(f"Saved {data_type} data to {filepath}")
    
    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    async def process_founder_data(self, serp_results: Dict[str, Any], twitter_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process search results for an individual person (founder/executive).
        
        This processes a standalone person query (not as part of company processing):
        1. Extract comprehensive personal details
        2. Determine Duke affiliation status based on education history
        3. Calculate relevance score
        4. Add Twitter analysis if available
        
        Used solely for the /api/founder endpoint.
        """
        # Extract person name from search parameters
        person_name = serp_results.get("search_parameters", {}).get("q", "Unknown Person")
        if '"' in person_name:
            person_name = person_name.split('"')[1]
        
        nlp_logger.info(f"Processing comprehensive data for person: {person_name}")
        
        # Initialize default person data
        person_data = {
            "name": person_name,
            "education": [],
            "duke_affiliation_status": "no",
            "current_company": None,
            "previous_companies": [],
            "twitter_handle": None,
            "linkedin_handle": None,
            "source_links": [],
            "relevance_score": 0
        }
        
        try:
            # Collect search results snippets
            all_snippets = [
                f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n"
                for result in serp_results.get("organic_results", [])
                if result.get("snippet")
            ]
            
            # Prepare Twitter context if available
            twitter_context = ""
            if twitter_data and "tweets" in twitter_data:
                twitter_context = "\nRECENT TWEETS:\n" + "\n".join(
                    f"- {tweet.get('content', '')}"
                    for tweet in twitter_data["tweets"]
                )
            
            # Comprehensive prompt for person extraction with education focus
            prompt = f"""
            You are a specialized venture capital researcher. Extract comprehensive information about {person_name} from the provided text.
            Focus on identifying their education history (especially any Duke University connections), work history, and contact information.
            
            Extract the following data in a JSON structure matching this exact format:
            {{{{
                "name": "<Full Name>",
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
                "twitter_handle": "<@handle or null>",
                "linkedin_handle": "<Full LinkedIn URL or null>",
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
            
            try:
                # Get response from LLM
                response = await self._process_with_llm(messages)
                
                # If response is already a dict, use it directly
                if isinstance(response, dict):
                    extracted_data = response
                else:
                    # Otherwise try to parse it as JSON
                    extracted_data = json.loads(response)
                
                # Update person_data with extracted information
                person_data.update(extracted_data)
                
            except Exception as e:
                nlp_logger.error(f"LLM processing failed: {str(e)}")
                # Continue with default data if LLM fails
                person_data["error"] = f"LLM processing failed: {str(e)}"
            
            # Validate affiliation status
            valid_statuses = ["confirmed", "please review", "no"]
            if person_data["duke_affiliation_status"] not in valid_statuses:
                nlp_logger.warning(f"Invalid affiliation status '{person_data['duke_affiliation_status']}' for {person_name}. Defaulting to 'please review'.")
                person_data["duke_affiliation_status"] = "please review"
            
            # Save initial data
            self._save_person_data(person_data, person_name, "processed")
            
            # Process Twitter data if available
            if twitter_data:
                if "error" in twitter_data or twitter_data.get("twitter_unavailable", False):
                    person_data["twitter_summary"] = "Twitter data unavailable"
                else:
                    try:
                        # Process tweets with NitterNLP
                        if isinstance(twitter_data.get("tweets"), list):
                            twitter_analysis = await self.nitter_nlp.analyze_tweets(twitter_data["tweets"])
                            # Convert twitter_analysis to string format
                            person_data["twitter_summary"] = f"Summary: {twitter_analysis.get('summary', 'No summary available')}\nUrgency Score: {twitter_analysis.get('urgency_score', 0)}"
                        else:
                            person_data["twitter_summary"] = "Invalid tweets data format"
                    except Exception as e:
                        nlp_logger.error(f"Error processing Twitter data for {person_name}: {e}")
                        person_data["twitter_summary"] = f"Error processing tweets: {str(e)}"
            
            # Calculate final relevance score
            try:
                person_data["relevance_score"] = self.scorer.calculate_person_relevance_score(person_data)
            except Exception as e:
                nlp_logger.error(f"Error calculating relevance score for {person_name}: {e}")
                person_data["relevance_score"] = 0
            
            # Save final data
            self._save_person_data(person_data, person_name, "final")
            
            return person_data
            
        except Exception as e:
            nlp_logger.error(f"Unexpected error processing person {person_name}: {e}", exc_info=True)
            person_data["error"] = f"Unexpected error: {str(e)}"
            return person_data
    
    async def process_with_twitter(self, person_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance person data with Twitter analysis if a handle is available.
        Updates the relevance score based on the complete data.
        """
        if not person_data.get("twitter_handle"):
            nlp_logger.info(f"No Twitter handle found for {person_data.get('name')}")
            return person_data
            
        try:
            # Fetch tweets
            twitter_data = await self.nitter_scraper.get_raw_tweets(person_data["twitter_handle"])
            
            if twitter_data and not twitter_data.get("twitter_unavailable", False):
                # Analyze tweets
                tweets = twitter_data.get("tweets", [])
                if tweets:
                    twitter_summary = await self.nitter_nlp.analyze_tweets(tweets)
                    person_data["twitter_summary"] = twitter_summary
                    
                    # Recalculate score with Twitter data
                    person_data["relevance_score"] = self.scorer.calculate_person_relevance_score(person_data)
                else:
                    person_data["twitter_summary"] = {"twitter_unavailable": True, "reason": "No tweets found"}
            else:
                person_data["twitter_summary"] = {"twitter_unavailable": True}
                
        except Exception as e:
            nlp_logger.error(f"Error processing Twitter data for {person_data.get('name')}: {e}")
            person_data["twitter_summary"] = {"twitter_unavailable": True, "error": str(e)}
            
        return person_data

# Test case
if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Sample SERP results
        mock_serp = {
            "search_parameters": {"q": "Sarah Chen Duke AI startup"},
            "organic_results": [
                {
                    "title": "Sarah Chen: Duke Graduate Leading AI Innovation",
                    "link": "https://example.com/profile",
                    "snippet": "Sarah Chen, a Duke University graduate, founded an AI startup in 2023. Previously worked at Google AI."
                }
            ]
        }
        
        # Sample Twitter data
        mock_twitter = {
            "tweets": [
                {
                    "content": "Excited to announce our seed funding round!",
                    "date": "2024-03-31"
                }
            ]
        }
        
        processor = PersonProcessor()
        result = await processor.process_founder_data(mock_serp, mock_twitter)
        
        print("\nTest Results:")
        print(f"Name: {result['name']}")
        print(f"Duke Affiliation: {result['duke_affiliation_status']}")
        print(f"Current Company: {result['current_company']}")
        print(f"Relevance Score: {result['relevance_score']}")
        if result.get('twitter_summary'):
            print("\nTwitter Summary:")
            print(result['twitter_summary'])
    
    asyncio.run(test()) 