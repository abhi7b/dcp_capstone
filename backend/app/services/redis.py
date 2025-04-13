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
from typing import Optional, Any
import json
from datetime import timedelta
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
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Deserialized value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
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
            await self.redis.setex(
                key,
                timedelta(seconds=expire),
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
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