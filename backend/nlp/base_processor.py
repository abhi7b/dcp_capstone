"""
Base NLP processor for the DCP AI Scouting Platform.

This module provides the foundation for all NLP processing tasks, including:
- OpenAI API integration
- Data quality assessment
- Error handling and retry logic
"""
import json
import logging
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from openai import AsyncOpenAI, APIError, RateLimitError

from backend.config.logs import LogManager
from backend.config.cache import cached
from backend.config.config import settings

# Use the centralized logging configuration
logger = logging.getLogger(__name__)

class BaseProcessor:
    """
    Base class for NLP processors.
    
    This class provides common functionality for processing text data
    and extracting structured information using OpenAI's API.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the processor.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: OpenAI model to use (defaults to settings)
        """
        # Use API key from settings or directly provided parameter
        self.api_key = api_key or settings.openai.API_KEY
        self.model = model or settings.openai.MODEL
        
        if not self.api_key:
            logger.error("No OpenAI API key provided in settings")
            raise ValueError("OpenAI API key is required in settings")
            
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.debug(f"BaseProcessor initialized with model: {self.model}")
        
    def _calculate_data_freshness(self, last_updated: Optional[datetime]) -> float:
        """
        Calculate data freshness score (0-1).
        
        Args:
            last_updated: Last update timestamp
            
        Returns:
            float: Freshness score
        """
        if not last_updated:
            return 0.0
            
        age = datetime.utcnow() - last_updated
        days = age.days
        
        # Score decreases over time
        if days <= 1:
            return 1.0
        elif days <= 7:
            return 0.8
        elif days <= 30:
            return 0.6
        elif days <= 90:
            return 0.4
        elif days <= 180:
            return 0.2
        else:
            return 0.1
    
    def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """
        Calculate data quality score (0-1).
        
        Args:
            data: Data dictionary
            
        Returns:
            float: Quality score
        """
        if not data:
            return 0.0
            
        # Define required fields and their weights
        required_fields = {
            "name": 0.2,
            "description": 0.15,
            "industry": 0.1,
            "location": 0.1,
            "year_founded": 0.1,
            "duke_affiliated": 0.1,
            "social_media_score": 0.15
        }
        
        score = 0.0
        for field, weight in required_fields.items():
            if field in data and data[field] is not None:
                score += weight
                
        return score
    
    def _calculate_duke_affiliation_confidence(self, data: Dict[str, Any]) -> float:
        """
        Calculate Duke affiliation confidence score (0-1).
        
        Args:
            data: Data dictionary
            
        Returns:
            float: Confidence score
        """
        if not data or not data.get("duke_affiliated"):
            return 0.0
            
        # Define confidence factors and their weights
        confidence_factors = {
            "direct_alumni": 0.4,  # Direct Duke alumni
            "founder_alumni": 0.3,  # Founder is Duke alumni
            "partnership": 0.2,     # Partnership with Duke
            "indirect": 0.1         # Indirect connection
        }
        
        score = 0.0
        connection_types = data.get("duke_connection_type", [])
        
        if isinstance(connection_types, str):
            connection_types = [connection_types]
            
        for conn_type in connection_types:
            if conn_type in confidence_factors:
                score += confidence_factors[conn_type]
                
        return min(score, 1.0)  # Cap at 1.0
    
    def _prepare_metadata(self, data: Dict[str, Any], source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for storage.
        
        Args:
            data: Processed data
            source_data: Raw source data
            
        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        now = datetime.utcnow()
        
        return {
            "last_updated": now.isoformat(),
            "data_freshness_score": self._calculate_data_freshness(now),
            "data_quality_score": self._calculate_data_quality(data),
            "duke_affiliation_confidence": self._calculate_duke_affiliation_confidence(data),
            "data_sources": data.get("data_sources", []),
            "source": source_data.get("source", "unknown")
        }
    
    @cached("nlp_processing", expire=settings.cache.DEFAULT_TTL)
    async def process_text(self, 
                          text: str, 
                          system_prompt: str, 
                          user_prompt: str, 
                          temperature: float = 0.0,
                          max_tokens: int = None) -> Dict[str, Any]:
        """
        Process text using OpenAI API.
        
        Args:
            text: Text to process
            system_prompt: System prompt for the OpenAI model
            user_prompt: User prompt for the OpenAI model
            temperature: Temperature for the OpenAI model (0.0-1.0)
            max_tokens: Maximum tokens for the response
            
        Returns:
            Processed response as a dictionary
        """
        if not text:
            logger.warning("Empty text provided for processing")
            return {"error": "No text to process"}
        
        # Use settings if not provided
        max_tokens = max_tokens or settings.openai.MAX_TOKENS
        
        logger.info(f"Processing text with model {self.model} (length: {len(text)} chars)")
        start_time = datetime.now()
        
        try:
            # Prepare the full user prompt
            full_user_prompt = f"{user_prompt}\n\nHere is the text to analyze:\n\n{text}"
            
            # Call the OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            # Extract the response
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            try:
                parsed_response = json.loads(response_text)
                
                # Log completion time
                elapsed_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Text processing completed in {elapsed_time:.2f}s")
                
                return parsed_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return {"error": "Failed to parse JSON response", "raw_text": response_text}
                
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return {"error": "Rate limit exceeded", "details": str(e)}
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": "API error", "details": str(e)}
        except Exception as e:
            logger.error(f"Error processing text with OpenAI: {e}")
            return {"error": str(e)} 