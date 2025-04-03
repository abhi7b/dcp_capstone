import json
from typing import Dict, Any, List, Tuple
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.logger import nitter_logger
from ..utils.config import settings

class NitterNLP:
    """
    Service for analyzing tweets using OpenAI to generate summaries
    and calculate urgency scores.
    """
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        nitter_logger.info("NitterNLP initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def analyze_tweets(self, tweets: List[Dict[str, Any]]) -> Tuple[str, int]:
        """
        Analyze tweets to generate a summary and calculate urgency score.
        Returns a tuple of (summary, urgency_score).
        """
        if not tweets:
            return "No tweets available.", 50
            
        # Combine tweet content
        combined_content = "\n".join([
            f"Tweet: {tweet.get('content', '')}"
            for tweet in tweets
        ])
        
        # Prepare message for OpenAI
        message = f"""
        Analyze these tweets and provide:
        1. A concise summary of key points
        2. An urgency score (0-100) based on:
           - Recent funding announcements
           - Product launches
           - Team growth
           - Market expansion
           - High engagement
           - Time sensitivity
        
        Tweets:
        {combined_content}
        
        Format your response as:
        Summary: [your summary]
        Urgency Score: [0-100]
        """
        
        try:
            # Get response from OpenAI
            response = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a startup analyst focused on identifying urgent and important company updates."},
                    {"role": "user", "content": message}
                ],
                temperature=0.3
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Extract summary and score
            summary = ""
            urgency_score = 50  # Default middle score
            
            for line in content.split("\n"):
                if line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                elif line.startswith("Urgency Score:"):
                    try:
                        urgency_score = int(line.replace("Urgency Score:", "").strip())
                        # Ensure score is in range 0-100
                        urgency_score = max(0, min(100, urgency_score))
                    except ValueError:
                        nitter_logger.warning("Failed to parse urgency score, using default")
            
            nitter_logger.info(f"Generated summary and urgency score: {urgency_score}")
            return summary, urgency_score
            
        except Exception as e:
            nitter_logger.error(f"Error analyzing tweets: {str(e)}")
            return "Error analyzing tweets.", 50
