import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import AsyncOpenAI

from ..utils.config import settings
from ..utils.logger import nlp_logger
from .company_scorer import Scorer
from .nitter import NitterScraper
from .nitter_nlp import NitterNLP

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
        self.scorer = Scorer()
        self.nitter_scraper = NitterScraper()
        self.nitter_nlp = NitterNLP()
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        nlp_logger.info(f"Initialized NLPProcessor with model: {self.openai_model}")
    
    def _save_json_data(self, data: Dict[str, Any], prefix: str, data_type: str = "final") -> str:
        """Save JSON data to appropriate directory based on type"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"
        
        # Determine directory based on data type
        if data_type == "raw":
            save_dir = os.path.join(self.json_output_dir, "..", "raw")
        elif data_type == "processed":
            save_dir = os.path.join(self.json_output_dir, "..", "processed")
        else:  # final
            save_dir = self.json_output_dir
            
        file_path = os.path.join(save_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        nlp_logger.info(f"Saved {data_type} data to {file_path}")
        return file_path
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _process_with_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process messages with OpenAI LLM"""
        try:
            response = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.2,
                response_format={ "type": "json_object" }
            )
            
            content = response.choices[0].message.content
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                nlp_logger.error(f"Failed to parse LLM response as JSON: {content}")
                return {"error": "Failed to parse response", "raw_content": content}
                
        except Exception as e:
            nlp_logger.error(f"LLM processing failed: {str(e)}")
            return {"error": str(e), "raw_content": None}
    
    async def process_company_step1(self, serp_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract company info and key people from SERP results"""
        company_name = serp_results.get("search_parameters", {}).get("q", "Unknown Company")
        if '"' in company_name:
            company_name = company_name.split('"')[1]
        
        nlp_logger.info(f"STEP 1: Processing company data for: {company_name}")
        
        # Extract snippets from SERP results
        snippets = [
            f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n"
            for result in serp_results.get("organic_results", [])
            if result.get("snippet")
        ]
        
        if not snippets:
            return {
                "name": company_name, 
                "error": "No data found",
                "duke_affiliation_status": "no",
                "people": []
            }
        
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
                "twitter_handle": "@handle",
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
            company_data = await self._process_with_llm(messages)
            if "error" in company_data:
                return {
                    "name": company_name,
                    "error": company_data["error"],
                    "duke_affiliation_status": "no",
                    "people": []
                }
            
            company_data.setdefault("twitter_summary", None)
            company_data.setdefault("people", [])
            
            self._save_json_data(company_data, f"company_{company_name}_step1", "processed")
            return company_data
            
        except Exception as e:
            nlp_logger.error(f"Step 1 failed for {company_name}: {str(e)}")
            return {
                "name": company_name, 
                "error": str(e),
                "duke_affiliation_status": "no",
                "people": []
            }
    
    async def process_person_step2(self, person: Dict[str, str], duke_search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Determine Duke affiliation for a person"""
        person_name = person["name"]
        person_title = person["title"]
        
        nlp_logger.info(f"STEP 2: Processing Duke affiliation for: {person_name}")
        
        snippets = [
            f"TITLE: {result.get('title', '')}\nURL: {result.get('link', '')}\nSNIPPET: {result.get('snippet', '')}\n"
            for result in duke_search_results.get("organic_results", [])
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
            {"role": "system", "content": "You are a Duke University affiliation verification specialist."},
            {"role": "user", "content": f"""
            Analyze if {person_name} ({person_title}) has Duke University affiliation.
            Return a JSON object with ONLY these fields:
            {{
                "name": "{person_name}",
                "title": "{person_title}",
                "duke_affiliation_status": "confirmed|please review|no",
                "education": [
                    {{"school": "University Name", "degree": "Degree", "years": "Years"}}
                ]
            }}
            
            CRITERIA:
            - "confirmed": Clear evidence of Duke attendance/graduation
            - "please review": Ambiguous Duke connection
            - "no": No Duke affiliation found
            
            TEXT TO ANALYZE:
            {chr(10).join(snippets)}
            """}
        ]
        
        try:
            person_data = await self._process_with_llm(messages)
            self._save_json_data(person_data, f"person_{person_name}_step2", "processed")
            return person_data
            
        except Exception as e:
            nlp_logger.error(f"Step 2 failed for {person_name}: {str(e)}")
            return {
                "name": person_name,
                "title": person_title,
                "duke_affiliation_status": "please review",
                "education": []
            }
    
    async def process_company_step3(self, 
                                  company_data: Dict[str, Any], 
                                  processed_people: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Finalize company data with Twitter analysis and scoring"""
        company_name = company_data["name"]
        nlp_logger.info(f"STEP 3: Finalizing data for: {company_name}")
        
        # Get Twitter data if handle exists
        twitter_handle = company_data.get("twitter_handle")
        if twitter_handle:
            try:
                raw_tweets = await self.nitter_scraper.get_raw_tweets(twitter_handle)
                if not raw_tweets.get("twitter_unavailable"):
                    company_data["twitter_summary"] = await self.nitter_nlp.analyze_tweets(raw_tweets)
            except Exception as e:
                nlp_logger.error(f"Twitter analysis failed for {twitter_handle}: {str(e)}")
                company_data["twitter_summary"] = None
        
        # Determine company Duke affiliation status
        has_confirmed = any(p["duke_affiliation_status"] == "confirmed" for p in processed_people)
        has_review = any(p["duke_affiliation_status"] == "please review" for p in processed_people)
        
        company_data["duke_affiliation_status"] = (
            "confirmed" if has_confirmed else "please review" if has_review else "no"
        )
        
        # Calculate relevance score
        company_data["relevance_score"] = self.scorer.calculate_company_relevance_score(
            company_data, processed_people
        )
        
        # Organize people into founders and executives for display
        company_data["people"] = {
            "founders": [
                {
                    "name": p["name"],
                    "title": p.get("title", "Founder"),
                    "duke_affiliation_status": p["duke_affiliation_status"],
                    "education": p.get("education", [])
                }
                for p in processed_people
                if "founder" in p.get("title", "").lower() or "ceo" in p.get("title", "").lower()
            ],
            "executives": [
                {
                    "name": p["name"],
                    "title": p.get("title", "Executive"),
                    "duke_affiliation_status": p["duke_affiliation_status"],
                    "education": p.get("education", [])
                }
                for p in processed_people
                if "founder" not in p.get("title", "").lower() and "ceo" not in p.get("title", "").lower()
            ]
        }
        
        self._save_json_data(company_data, f"company_{company_name}_final", "final")
        return company_data
    
    async def process_company_pipeline(self,
                                    company_serp_results: Dict[str, Any],
                                    person_duke_searches: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Run complete company processing pipeline"""
        company_data = await self.process_company_step1(company_serp_results)
        if "error" in company_data:
            return company_data
        
        processed_people = []
        for person in company_data.get("people", []):
            person_name = person["name"]
            duke_search = person_duke_searches.get(person_name, {})
            person_data = await self.process_person_step2(person, duke_search)
            processed_people.append(person_data)
        
        return await self.process_company_step3(company_data, processed_people)

# Test case
if __name__ == "__main__":    
    import asyncio
    
    # Mock SERP results
    mock_company_serp = {
        "search_parameters": {"q": "Acme AI"},
        "organic_results": [
            {
                "title": "Acme AI raises Series A funding",
                "link": "https://example.com/news",
                "snippet": "Acme AI, founded by Duke graduate John Smith, raises $10M Series A. The AI startup, based in Durham, NC, is revolutionizing machine learning."
            }
        ]
    }
    
    # Mock Duke search results for person
    mock_duke_search = {
        "organic_results": [
            {
                "title": "Duke Alumni Success Stories",
                "link": "https://duke.edu/alumni",
                "snippet": "John Smith graduated from Duke University's Computer Science program in 2020."
            }
        ]
    }
    
    mock_person_searches = {
        "John Smith": mock_duke_search
    }
    
    async def run_test():
        processor = NLPProcessor()
        result = await processor.process_company_pipeline(
            mock_company_serp,
            mock_person_searches
        )
        
        print("\nTest Results:")
        print(f"Company: {result['name']}")
        print(f"Duke Affiliation: {result['duke_affiliation_status']}")
        print(f"Relevance Score: {result.get('relevance_score', 'Not calculated')}")
        
        print("\nFounders:")
        for founder in result.get('people', {}).get('founders', []):
            print(f"- {founder['name']} ({founder['title']}): {founder['duke_affiliation_status']}")
        
        print("\nExecutives:")
        for executive in result.get('people', {}).get('executives', []):
            print(f"- {executive['name']} ({executive['title']}): {executive['duke_affiliation_status']}")
        
        if result.get('twitter_summary'):
            print("\nTwitter Analysis:")
            print(f"Summary: {result['twitter_summary'].get('summary', 'Not available')}")
            print(f"Urgency Score: {result['twitter_summary'].get('urgency_score', 'Not available')}")
    
    asyncio.run(run_test()) 