"""
Authentication module for the DCP AI Scouting Platform.

This module provides API key validation and user management with multi-level caching
for improved performance and reliability.
"""
import secrets
import time
from typing import Dict, Optional, List, Union, Any
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader, APIKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from db.database.db import get_db
from db.database.models import APIUser, User
from backend.config.logs import get_logger
from backend.config.cache import CacheManager

# Initialize logger
logger = get_logger(__name__)

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# In-memory cache for API keys to reduce database lookups
# Format: {api_key: {"user_id": user_id, "expires": expires, "scopes": scopes}}
API_KEY_CACHE: Dict[str, Dict[str, Any]] = {}
# Cache expiration in seconds (5 minutes by default, can be overridden by environment variable)
CACHE_EXPIRATION = 300

# Maximum number of entries in the in-memory cache to prevent memory leaks
MAX_CACHE_ENTRIES = 1000

# Use UTC timezone for all datetime objects
def utc_now():
    """Get current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)

def _clean_cache_if_needed() -> None:
    """
    Clean the in-memory cache if it exceeds the maximum number of entries.
    This prevents memory leaks in long-running applications.
    """
    if len(API_KEY_CACHE) > MAX_CACHE_ENTRIES:
        # Remove expired entries first
        now = time.time()
        expired_keys = [k for k, v in API_KEY_CACHE.items() if v.get("expires", 0) < now]
        for key in expired_keys:
            del API_KEY_CACHE[key]
        
        # If still too many entries, remove oldest entries
        if len(API_KEY_CACHE) > MAX_CACHE_ENTRIES:
            # Sort by expiration time and keep only the newest entries
            sorted_keys = sorted(API_KEY_CACHE.keys(), 
                                key=lambda k: API_KEY_CACHE[k].get("expires", 0), 
                                reverse=True)
            keys_to_remove = sorted_keys[MAX_CACHE_ENTRIES:]
            for key in keys_to_remove:
                del API_KEY_CACHE[key]

async def get_api_key(
    api_key_header: str = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Validate API key from header.
    
    Args:
        api_key_header: API key from header
        db: Database session
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: If API key is missing, invalid, or expired
    """
    if not api_key_header:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing"
        )
    
    # Check cache first for better performance
    now = time.time()
    if api_key_header in API_KEY_CACHE:
        cache_entry = API_KEY_CACHE[api_key_header]
        # Check if cache entry is still valid
        if cache_entry.get("expires", 0) > now:
            return api_key_header
        # Remove expired cache entry
        del API_KEY_CACHE[api_key_header]
    
    # Try Redis cache if available
    redis_success = False
    if CacheManager.is_initialized():
        try:
            cache_key = f"api_key:{api_key_header}"
            cached_data = await CacheManager._redis.get(cache_key)
            if cached_data:
                user_data = json.loads(cached_data)
                # Check if API key is expired
                if user_data.get("expires_at"):
                    try:
                        expires_at = datetime.fromisoformat(user_data["expires_at"])
                        # Ensure we're comparing timezone-aware datetimes
                        if not expires_at.tzinfo:
                            # If the stored datetime is naive, assume it's UTC
                            expires_at = expires_at.replace(tzinfo=timezone.utc)
                        
                        if expires_at < utc_now():
                            logger.warning(f"Expired API key used: {api_key_header[:8]}...")
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="API key has expired"
                            )
                    except ValueError as e:
                        logger.error(f"Invalid datetime format in Redis cache: {e}")
                        # Continue to database check if datetime parsing fails
                
                # Update in-memory cache
                API_KEY_CACHE[api_key_header] = {
                    "user_id": user_data["user_id"],
                    "expires": now + CACHE_EXPIRATION,
                    "scopes": user_data["scopes"]
                }
                _clean_cache_if_needed()
                redis_success = True
                return api_key_header
        except Exception as e:
            logger.error(f"Redis cache error in get_api_key: {e}")
    
    # Check database if not found in caches
    try:
        query = select(APIUser).where(APIUser.api_key == api_key_header)
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user:
            logger.warning(f"Invalid API key used: {api_key_header[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Check if API key is expired
        if user.expires_at:
            # Ensure we're comparing timezone-aware datetimes
            expires_at = user.expires_at
            if not expires_at.tzinfo:
                # If the stored datetime is naive, assume it's UTC
                expires_at = expires_at.replace(tzinfo=timezone.utc)
                
            if expires_at < utc_now():
                logger.warning(f"Expired API key used: {api_key_header[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired"
                )
        
        # Update in-memory cache
        API_KEY_CACHE[api_key_header] = {
            "user_id": user.id,
            "expires": now + CACHE_EXPIRATION,
            "scopes": user.scopes
        }
        _clean_cache_if_needed()
        
        # Update Redis cache if available and previous Redis operation failed
        if CacheManager.is_initialized() and not redis_success:
            try:
                cache_key = f"api_key:{api_key_header}"
                # Ensure expires_at is serialized with timezone info
                expires_at_str = None
                if user.expires_at:
                    # Make sure it's timezone-aware before serializing
                    expires_at = user.expires_at
                    if not expires_at.tzinfo:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    expires_at_str = expires_at.isoformat()
                
                user_data = {
                    "user_id": user.id,
                    "scopes": user.scopes,
                    "expires_at": expires_at_str
                }
                await CacheManager._redis.set(
                    cache_key,
                    json.dumps(user_data),
                    ex=CACHE_EXPIRATION
                )
            except Exception as e:
                logger.error(f"Redis cache error in get_api_key: {e}")
        
        return api_key_header
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in get_api_key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )

async def get_current_user(
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
) -> Union[APIUser, User]:
    """
    Get current user from API key.
    
    Args:
        api_key: Validated API key
        db: Database session
        
    Returns:
        Union[APIUser, User]: Current API user or User
        
    Raises:
        HTTPException: If API key is invalid or user not found
    """
    try:
        # Check cache first
        if api_key in API_KEY_CACHE:
            user_id = API_KEY_CACHE[api_key].get("user_id")
            if user_id:
                # Get API user
                query = select(APIUser).where(APIUser.id == user_id)
                result = await db.execute(query)
                api_user = result.scalars().first()
                
                if api_user:
                    # Get actual user
                    query = select(User).where(User.id == api_user.user_id)
                    result = await db.execute(query)
                    user = result.scalars().first()
                    
                    if user:
                        return user
                    return api_user
        
        # If not in cache, query directly
        query = select(APIUser).where(APIUser.api_key == api_key)
        result = await db.execute(query)
        api_user = result.scalars().first()
        
        if not api_user:
            logger.warning(f"Invalid API key used: {api_key[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Get actual user
        query = select(User).where(User.id == api_user.user_id)
        result = await db.execute(query)
        user = result.scalars().first()
        
        if user:
            return user
        return api_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )

async def check_scope(
    required_scope: str,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
) -> bool:
    """
    Check if user has required scope.
    
    Args:
        required_scope: Required scope
        api_key: Validated API key
        db: Database session
        
    Returns:
        bool: True if user has required scope
        
    Raises:
        HTTPException: If user doesn't have required scope
    """
    try:
        # Check cache first for better performance
        if api_key in API_KEY_CACHE:
            scopes = API_KEY_CACHE[api_key].get("scopes", [])
            if required_scope in scopes or "admin" in scopes:
                return True
        
        # Check database
        query = select(APIUser).where(APIUser.api_key == api_key)
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user:
            logger.warning(f"Invalid API key used: {api_key[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        if required_scope not in user.scopes and "admin" not in user.scopes:
            logger.warning(f"Insufficient scope for API key: {api_key[:8]}... (required: {required_scope})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}"
            )
        
        # Update cache with scopes
        now = time.time()
        if api_key not in API_KEY_CACHE:
            API_KEY_CACHE[api_key] = {
                "user_id": user.id,
                "expires": now + CACHE_EXPIRATION,
                "scopes": user.scopes
            }
            _clean_cache_if_needed()
        
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in check_scope: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authorization error"
        )

async def generate_api_key(
    user_id: int,
    name: str,
    scopes: List[str],
    expires_in_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Generate a new API key for a user.
    
    Args:
        user_id: User ID
        name: API key name
        scopes: List of scopes
        expires_in_days: Number of days until expiration (None for no expiration)
        db: Database session
        
    Returns:
        str: Generated API key
        
    Raises:
        HTTPException: If there's an error generating the API key
    """
    try:
        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)
        
        # Calculate expiration date
        expires_at = None
        if expires_in_days is not None:
            expires_at = utc_now() + timedelta(days=expires_in_days)
        
        # Create API user
        api_user = APIUser(
            user_id=user_id,
            name=name,
            api_key=api_key,
            scopes=scopes,
            expires_at=expires_at,
            created_at=utc_now()
        )
        
        db.add(api_user)
        await db.commit()
        
        # Add to cache for immediate use
        now = time.time()
        API_KEY_CACHE[api_key] = {
            "user_id": api_user.id,
            "expires": now + CACHE_EXPIRATION,
            "scopes": scopes
        }
        _clean_cache_if_needed()
        
        # Add to Redis cache if available
        if CacheManager.is_initialized():
            try:
                cache_key = f"api_key:{api_key}"
                user_data = {
                    "user_id": api_user.id,
                    "scopes": scopes,
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
                await CacheManager._redis.set(
                    cache_key,
                    json.dumps(user_data),
                    ex=CACHE_EXPIRATION
                )
            except Exception as e:
                logger.error(f"Redis cache error in generate_api_key: {e}")
        
        logger.info(f"Generated new API key for user {user_id}: {api_key[:8]}...")
        return api_key
    except Exception as e:
        logger.error(f"Error generating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate API key"
        ) 