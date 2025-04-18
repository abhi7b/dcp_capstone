"""
Redis Service Module

Provides async Redis client service for caching and data storage.
Handles JSON serialization/deserialization and cache management.

Key Features:
- Async Redis operations
- JSON data handling
- Configurable expiration
- Error handling
"""

from redis import asyncio as aioredis
from typing import Optional, Any, Dict
import json
from datetime import timedelta, datetime
from ..utils.config import settings
from ..utils.logger import redis_service_logger as logger

class RedisService:
    """
    Async Redis service for caching and data management.
    Provides methods for getting, setting, and deleting cached data.
    """
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self.redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def get(self, key: str) -> Optional[Dict]:
        """
        Get value from Redis cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Deserialized value or None if not found
        """
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Dict,
        expire: int = 3600
    ) -> bool:
        """
        Set value in Redis cache.
        
        Args:
            key: Cache key
            value: Value to store (will be JSON serialized)
            expire: Cache expiration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert datetime objects to ISO format strings
            serialized_value = self._serialize_for_redis(value)
            await self.redis.setex(
                key,
                timedelta(seconds=expire),
                json.dumps(serialized_value)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
    def _serialize_for_redis(self, value: Any) -> Any:
        """Helper function to serialize data for Redis storage."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: self._serialize_for_redis(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_for_redis(item) for item in value]
        return value
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from Redis cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False
    
    async def clear_cache(self) -> bool:
        """
        Clear all cached data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            keys = await self.redis.keys("*")
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis clear cache error: {str(e)}")
            return False

# Create global Redis instance
redis_service = RedisService() 