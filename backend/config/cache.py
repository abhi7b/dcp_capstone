# config/cache.py
"""
Caching system for the DCP AI Scouting Platform.

This module provides a Redis-based caching system for the application,
with support for key generation, invalidation, and TTL management.
"""
import asyncio
import functools
import hashlib
import inspect
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as cache

from backend.config.config import settings
from backend.config.logs import get_logger

# Initialize logger
logger = get_logger(__name__)

# Cache key prefixes for different data types
CACHE_KEYS = {
    "company": "company:{name}",
    "founder": "founder:{name}",
    "search": "search:{query}",
    "duke_alumni": "duke_alumni:{name}",
    "twitter": "twitter:{username}"
}

class CacheManager:
    """Manages Redis cache initialization and operations."""
    
    _redis = None
    _initialized = False
    
    @classmethod
    async def init_cache(cls) -> None:
        """
        Initialize the Redis cache connection.
        """
        if cls._initialized:
            return
        
        # Skip initialization if Redis URL is empty
        if not settings.REDIS_URL:
            logger.info("Redis URL not provided, caching disabled")
            return
        
        try:
            # Connect to Redis
            redis = cache.from_url(
                settings.REDIS_URL,
                encoding="utf8",
                decode_responses=True
            )
            
            # Test connection
            await redis.ping()
            
            # Initialize FastAPICache
            FastAPICache.init(
                RedisBackend(redis),
                prefix="dcp_cache:",
                expire=settings.CACHE_DEFAULT_TTL
            )
            
            # Store Redis connection
            cls._redis = redis
            cls._initialized = True
            
            logger.info(f"Cache initialized with Redis at {settings.REDIS_URL}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")
            logger.warning("Application will continue without caching")
            cls._initialized = False
    
    @classmethod
    async def close(cls) -> None:
        """Close the Redis connection."""
        if cls._redis:
            await cls._redis.close()
            cls._redis = None
            cls._initialized = False
            logger.info("Cache connection closed")
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the cache is initialized."""
        return cls._initialized and cls._redis is not None
    
    @classmethod
    async def is_connected(cls) -> bool:
        """Check if Redis is connected and responding."""
        if not cls.is_initialized():
            return False
        
        try:
            # Test connection with ping
            await cls._redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis connection check failed: {e}")
            return False
    
    @staticmethod
    def generate_key(prefix: str, **kwargs) -> str:
        """Generate a cache key from a prefix and keyword arguments."""
        if prefix not in CACHE_KEYS:
            # Use a simple key format for unknown prefixes
            return f"{prefix}:{hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()}"
        
        template = CACHE_KEYS[prefix]
        try:
            return template.format(**kwargs)
        except KeyError:
            # Create a fallback key with available kwargs
            return f"{prefix}:{hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()}"
    
    @classmethod
    async def delete_keys(cls, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not cls.is_initialized():
            return 0
        
        try:
            # Use Redis SCAN to find keys matching the pattern
            cursor = b"0"
            count = 0
            
            while cursor:
                cursor, keys = await cls._redis.scan(
                    cursor=cursor, 
                    match=f"dcp_cache:{pattern}*", 
                    count=100
                )
                
                if keys:
                    await cls._redis.delete(*keys)
                    count += len(keys)
                
                if cursor == b"0":
                    break
            
            if count > 0:
                logger.info(f"Deleted {count} cache keys matching pattern '{pattern}'")
            
            return count
        except Exception as e:
            logger.error(f"Error deleting cache keys with pattern {pattern}: {e}")
            return 0

def cached(prefix: str, expire: int = None):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix from CACHE_KEYS
        expire: TTL in seconds (defaults to settings.CACHE_DEFAULT_TTL)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip caching if cache is not initialized
            if not CacheManager.is_initialized():
                return await func(*args, **kwargs)
            
            # Get TTL from settings if not specified
            ttl = expire
            if ttl is None:
                if prefix == "company":
                    ttl = settings.CACHE_COMPANY_TTL
                elif prefix == "founder":
                    ttl = settings.CACHE_FOUNDER_TTL
                elif prefix == "search":
                    ttl = settings.CACHE_SEARCH_TTL
                else:
                    ttl = settings.CACHE_DEFAULT_TTL
            
            # Extract parameters for key generation
            key_kwargs = {}
            
            # Extract kwargs from function signature and args
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Extract parameters for key generation
            for param_name, param_value in bound_args.arguments.items():
                # Skip self/cls for methods
                if param_name in ("self", "cls"):
                    continue
                
                # Only use simple types for keys
                if isinstance(param_value, (str, int, float, bool)) or param_value is None:
                    key_kwargs[param_name] = param_value
            
            # Generate cache key
            try:
                key = CacheManager.generate_key(prefix, **key_kwargs)
            except Exception as e:
                logger.warning(f"Failed to generate cache key: {e}")
                return await func(*args, **kwargs)
            
            # Check if result is in cache
            if CacheManager._redis:
                try:
                    cached_result = await CacheManager._redis.get(f"dcp_cache:{key}")
                    if cached_result:
                        return json.loads(cached_result)
                except Exception as e:
                    logger.warning(f"Error retrieving from cache: {e}")
            
            # Execute function if not in cache
            result = await func(*args, **kwargs)
            
            # Store result in cache
            if CacheManager._redis and result is not None:
                try:
                    await CacheManager._redis.setex(
                        f"dcp_cache:{key}",
                        ttl,
                        json.dumps(result)
                    )
                except Exception as e:
                    logger.warning(f"Error storing in cache: {e}")
            
            return result
        
        return wrapper
    
    return decorator

# Simplified cache invalidation functions
async def invalidate_cache(key_pattern: str) -> int:
    """
    Invalidate cache for any key pattern.
    
    Args:
        key_pattern: Cache key pattern to invalidate
        
    Returns:
        Number of keys invalidated
    """
    return await CacheManager.delete_keys(key_pattern)

async def invalidate_company_cache(name: str = None) -> int:
    """Invalidate company cache."""
    pattern = f"company:{name}" if name else "company"
    return await CacheManager.delete_keys(pattern)

async def invalidate_founder_cache(name: str = None) -> int:
    """Invalidate founder cache."""
    pattern = f"founder:{name}" if name else "founder"
    return await CacheManager.delete_keys(pattern)

async def invalidate_search_cache() -> int:
    """Invalidate search cache."""
    return await CacheManager.delete_keys("search")

async def invalidate_twitter_cache(username: str = None) -> int:
    """Invalidate Twitter cache."""
    pattern = f"twitter:{username}" if username else "twitter"
    return await CacheManager.delete_keys(pattern)

async def invalidate_duke_alumni_cache(name: str = None) -> int:
    """Invalidate Duke alumni cache."""
    pattern = f"duke_alumni:{name}" if name else "duke_alumni"
    return await CacheManager.delete_keys(pattern) 