"""
Rate limiting module for the DCP AI Scouting Platform.

This module provides rate limiting functionality using Redis with a fallback to in-memory rate limiting.
"""
import time
import threading
from typing import Optional, Callable, Dict, List, Tuple
from collections import defaultdict
from fastapi import Depends, HTTPException, Request, status
from fastapi.security.api_key import APIKey

from backend.auth.auth import get_api_key
from backend.config.logs import get_logger
from backend.config.cache import CacheManager
from backend.config.config import settings

# Initialize logger
logger = get_logger(__name__)

class InMemoryRateLimiter:
    """In-memory rate limiter for fallback when Redis is unavailable."""
    
    def __init__(self):
        """Initialize the in-memory rate limiter."""
        # Format: {key: [(timestamp, count), ...]}
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if a key is rate limited.
        
        Args:
            key: Rate limit key
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple[bool, int]: (is_limited, reset_time)
        """
        now = int(time.time())
        cutoff = now - window_seconds
        
        with self.lock:
            # Remove old requests
            self.requests[key] = [
                (ts, count) for ts, count in self.requests[key]
                if ts >= cutoff
            ]
            
            # Count current requests
            count = sum(count for _, count in self.requests[key])
            
            # Check if rate limited
            if count >= max_requests:
                # Calculate reset time
                if self.requests[key]:
                    oldest = min(ts for ts, _ in self.requests[key])
                    reset_time = oldest + window_seconds - now
                else:
                    reset_time = 0
                return True, reset_time
            
            # Add current request
            self.requests[key].append((now, 1))
            return False, 0

# Create a global in-memory rate limiter for fallback
memory_rate_limiter = InMemoryRateLimiter()

class RateLimiter:
    """Rate limiter for API endpoints using Redis with in-memory fallback."""
    
    def __init__(self):
        """Initialize the rate limiter."""
        self.initialized = False
        self.use_redis = True
    
    async def init(self):
        """Initialize Redis connection."""
        if self.initialized:
            return
            
        try:
            # Use the cache manager's Redis connection
            await CacheManager.init_cache()
            self.initialized = CacheManager.is_initialized()
            self.use_redis = self.initialized
            
            if self.initialized:
                logger.info("Rate limiter initialized with Redis backend")
            else:
                logger.warning("Redis not available, using in-memory rate limiting")
        except Exception as e:
            logger.error(f"Failed to initialize Redis rate limiter: {e}")
            logger.warning("Falling back to in-memory rate limiting")
            self.use_redis = False
    
    async def close(self):
        """Close Redis connection."""
        # We don't close the Redis connection here since it's managed by CacheManager
        self.initialized = False
        logger.info("Rate limiter connection closed")
    
    async def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if a key is rate limited.
        
        Args:
            key: Rate limit key
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple[bool, int]: (is_limited, reset_time)
        """
        # Use Redis if available
        if self.use_redis and CacheManager.is_initialized():
            try:
                # Get current timestamp
                now = int(time.time())
                
                # Get Redis connection from CacheManager
                redis = CacheManager._redis
                
                # Remove old requests
                await redis.zremrangebyscore(key, 0, now - window_seconds)
                
                # Count current requests
                count = await redis.zcard(key)
                
                # Check if rate limited
                if count >= max_requests:
                    # Get oldest request timestamp
                    oldest = await redis.zrange(key, 0, 0, withscores=True)
                    reset_time = 0
                    if oldest:
                        reset_time = int(oldest[0][1]) + window_seconds - now
                    return True, reset_time
                
                # Add current request
                await redis.zadd(key, {str(now): now})
                
                # Set expiration
                await redis.expire(key, window_seconds)
                
                return False, 0
            except Exception as e:
                logger.error(f"Redis rate limit error: {e}")
                logger.warning("Falling back to in-memory rate limiting")
                self.use_redis = False
        
        # Fallback to in-memory rate limiting
        return memory_rate_limiter.is_rate_limited(key, max_requests, window_seconds)
    
    def limit(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func: Optional[Callable] = None
    ):
        """
        Rate limiting dependency.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            key_func: Function to generate rate limit key
            
        Returns:
            Dependency function
        """
        async def rate_limit_dependency(
            request: Request,
            api_key: APIKey = Depends(get_api_key)
        ):
            if not self.initialized:
                await self.init()
            
            # Generate rate limit key
            if key_func:
                rate_limit_key = key_func(request, api_key)
            else:
                # Default: use API key and path
                rate_limit_key = f"rate_limit:{api_key}:{request.url.path}"
            
            # Check if rate limited
            is_limited, reset_time = await self.is_rate_limited(
                rate_limit_key,
                max_requests,
                window_seconds
            )
            
            if is_limited:
                logger.warning(f"Rate limit exceeded for key: {rate_limit_key}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={
                        "Retry-After": str(reset_time),
                        "X-Rate-Limit-Limit": str(max_requests),
                        "X-Rate-Limit-Window": str(window_seconds)
                    }
                )
        
        return rate_limit_dependency

# Create a global rate limiter instance
rate_limiter = RateLimiter()

# Convenience function to get rate limiter
async def get_rate_limiter() -> RateLimiter:
    """Get the rate limiter instance."""
    if not rate_limiter.initialized:
        await rate_limiter.init()
    return rate_limiter 