import json
import os
from datetime import datetime
from typing import Dict, Any, List
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.logger import nitter_logger
from ..utils.config import settings

class NitterNLP:
    """Service for analyzing raw tweets using NLP to generate summaries and urgency scores"""
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.processed_data_dir = settings.PROCESSED_DATA_DIR
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        nitter_logger.info("NitterNLP initialized")
    
    def _save_processed_data(self, data: Dict[str, Any], handle: str) -> str:
        """Save processed JSON data to file and return the file path"""
        sanitized_handle = handle.replace('@', '').replace('/', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nitter_analysis_{sanitized_handle}_{timestamp}.json"
        file_path = os.path.join(self.processed_data_dir, filename)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        nitter_logger.info(f"Processed Nitter data saved to {file_path}")
        return file_path
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _analyze_with_llm(self, content: str) -> Dict[str, Any]:
        """Process content with OpenAI LLM"""
        try:
            messages = [
                {"role": "system", "content": "You are an AI trained to analyze tweets for business and investment insights. Focus on funding, growth, and time-sensitive opportunities."},
                {"role": "user", "content": f"""
                Analyze these tweets and provide:
                1. A concise 1-2 sentence summary focusing on key business developments, funding activities, and opportunities
                2. An urgency score (1-100) based on:
                   - Funding activities/investment opportunities (40%)
                   - Growth indicators/business expansion (30%)
                   - Time sensitivity/deadlines (30%)
                
                Tweets:
                {content}
                
                Return only valid JSON with this structure:
                {{
                    "summary": "your summary here",
                    "urgency_score": number
                }}
                """}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            nitter_logger.error(f"LLM analysis failed: {str(e)}")
            raise
    
    async def analyze_tweets(self, raw_tweets_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze raw tweets to generate summary and urgency score"""
        try:
            # Handle both dict and list input formats
            if isinstance(raw_tweets_data, dict):
                handle = raw_tweets_data.get("handle", "unknown")
                raw_tweets = raw_tweets_data.get("raw_tweets", [])
            elif isinstance(raw_tweets_data, list):
                handle = "unknown"
                raw_tweets = raw_tweets_data
            else:
                return {
                    "handle": "unknown",
                    "summary": "Invalid input format",
                    "urgency_score": 0,
                    "twitter_unavailable": True,
                    "analysis_timestamp": datetime.now().isoformat()
                }
            
            if not raw_tweets:
                return {
                    "handle": handle,
                    "summary": "No tweets available for analysis",
                    "urgency_score": 0,
                    "twitter_unavailable": True,
                    "analysis_timestamp": datetime.now().isoformat()
                }
            
            # Combine tweet contents, focusing on recent tweets
            combined_content = "\n".join(
                f"[{tweet.get('date', 'No date')}] {tweet.get('content', '')}"
                for tweet in raw_tweets[:10]  # Focus on 10 most recent tweets
            )
            
            analysis = await self._analyze_with_llm(combined_content)
            
            result = {
                "handle": handle,
                "summary": analysis.get("summary", "No summary available"),
                "urgency_score": analysis.get("urgency_score", 0),
                "twitter_unavailable": False,
                "analysis_timestamp": datetime.now().isoformat(),
                "tweets_analyzed": len(raw_tweets)
            }
            
            file_path = self._save_processed_data(result, handle)
            result["_file_path"] = file_path
            
            return result
            
        except Exception as e:
            nitter_logger.error(f"Failed to analyze tweets: {str(e)}")
            return {
                "handle": "unknown",
                "summary": "Error analyzing tweets",
                "urgency_score": 0,
                "twitter_unavailable": True,
                "analysis_timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

# Simple test case
if __name__ == "__main__":    
    import asyncio
    
    # Mock tweet data with realistic content
    mock_tweets = {
        "handle": "OpenAI",
        "raw_tweets": [
            {
                "content": "Excited to announce our Series A funding round of $10M led by top VCs!",
                "date": "2024-03-31",
                "stats": "5k likes"
            },
            {
                "content": "We're expanding our team! Looking for talented engineers to join us.",
                "date": "2024-03-30",
                "stats": "2k likes"
            }
        ]
    }
    
    # Create analyzer with real config
    analyzer = NitterNLP()
    
    # Run asynchronously
    async def test():
        result = await analyzer.analyze_tweets(mock_tweets)
        print("\nTest Results:")
        print(f"Handle: @{result['handle']}")
        print(f"Summary: {result['summary']}")
        print(f"Urgency Score: {result['urgency_score']}")
        print(f"Twitter Available: {not result['twitter_unavailable']}")
        print(f"Output saved to: {result.get('_file_path', 'Not saved')}")
    
    asyncio.run(test())