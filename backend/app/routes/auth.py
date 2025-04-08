"""
Authentication Routes Module

This module handles API authentication and authorization using API keys.
Provides endpoints for managing API keys and middleware for request verification.

Key Features:
- API key management
- Request authentication
- Rate limiting
- Access control
"""

from fastapi import APIRouter, Depends, HTTPException, status, Security, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import time
import logging

from ..db.session import get_db
from ..db import crud, schemas
from ..db.models import APIKey
from ..utils.config import settings
from ..utils.logger import get_logger
from ..utils.storage import StorageService

# Define API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Initialize router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

logger = get_logger("auth_routes")

# Rate limiting data (in-memory cache)
rate_limit_cache = {}

async def verify_api_key(
    request: Request,
    api_key: str = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db)
) -> schemas.APIKeyResponse:
    """
    Verify API key and rate limits for incoming requests.
    
    Args:
        request: FastAPI request object
        api_key: API key from request header
        db: Database session
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid or rate limit exceeded
    """
    if not api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Layer 1: Rate limiting check
    cache_key = f"rate_limit:{api_key}"
    current_time = time.time()
    minute_start = int(current_time / 60) * 60  # Start of current minute
    
    # Initialize or get current minute's request count
    if cache_key not in rate_limit_cache or rate_limit_cache[cache_key]["minute"] != minute_start:
        rate_limit_cache[cache_key] = {
            "minute": minute_start,
            "count": 0
        }
    
    # Increment request count
    rate_limit_cache[cache_key]["count"] += 1
    
    # Layer 2: Basic validation
    if len(api_key) < 32:  # Minimum length check
        logger.warning(f"Invalid API key format: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Layer 3: Database validation
    result = await db.execute(
        select(APIKey).where(APIKey.key == api_key)
    )
    api_key_obj = result.scalars().first()
    
    if not api_key_obj or not api_key_obj.is_active:
        logger.warning(f"Invalid or inactive API key: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check if API key is expired
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now():
        logger.warning(f"Expired API key: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check rate limit from database
    if rate_limit_cache[cache_key]["count"] > api_key_obj.rate_limit:
        logger.warning(f"Rate limit exceeded for API key: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {api_key_obj.rate_limit} requests per minute allowed.",
        )
    
    logger.debug(f"API key validated: {api_key[:8]}...")
    return api_key_obj

# API key management endpoints
@router.post("/keys", response_model=schemas.APIKeyResponse)
async def create_api_key(
    api_key_data: schemas.APIKeyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key.
    
    Args:
        api_key: API key creation data
        db: Database session
        
    Returns:
        Created API key details
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # Layer 1: Input validation
        if not api_key_data.name or not api_key_data.rate_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name and rate limit are required"
            )
        
        # Layer 2: Check for existing key with same name
        result = await db.execute(
            select(APIKey).where(APIKey.name == api_key_data.name)
        )
        existing = result.scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API key with name '{api_key_data.name}' already exists"
            )
        
        # Layer 3: Create and store new key
        logger.info(f"Creating new API key for: {api_key_data.name}")
        api_key = await crud.create_api_key(db, api_key_data)
        logger.info(f"API key created: {api_key.key[:8]}...")
        return api_key
        
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys/{api_key}/deactivate", response_model=schemas.Message)
async def deactivate_api_key(
    api_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate an existing API key.
    
    Args:
        key: API key to deactivate
        db: Database session
        
    Returns:
        Success/failure message
        
    Raises:
        HTTPException: If key not found or deactivation fails
    """
    try:
        # Layer 1: Basic validation
        if len(api_key) < 32:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid API key format"
            )
        
        # Layer 2: Check key existence
        result = await db.execute(
            select(APIKey).where(APIKey.key == api_key)
        )
        existing = result.scalars().first()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Layer 3: Deactivate key
        logger.info(f"Deactivating API key: {api_key[:8]}...")
        deactivated = await crud.deactivate_api_key(db, api_key)
        if not deactivated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate API key"
            )
        
        logger.info(f"API key deactivated: {api_key[:8]}...")
        return {"message": "API key deactivated successfully"}
        
    except Exception as e:
        logger.error(f"Error deactivating API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# JWT token operations for alternative authentication
async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create JWT access token with three-layered validation:
    1. Validate input data
    2. Set expiration
    3. Generate token
    """
    try:
        # Layer 1: Input validation
        if not data or "sub" not in data:
            raise ValueError("Invalid token data")
        
        # Layer 2: Set expiration
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.API_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Layer 3: Generate token
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.API_SECRET_KEY, algorithm=settings.API_ALGORITHM)
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    api_key_header: str = Depends(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db)
):
    """
    Get JWT token using API key with three-layered validation:
    1. Validate API key
    2. Check token eligibility
    3. Generate token
    """
    try:
        # Layer 1: API key validation
        api_key = await verify_api_key(api_key_header, db)
        
        # Layer 2: Check token eligibility
        if not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is not active"
            )
        
        # Layer 3: Generate token
        access_token_expires = timedelta(minutes=settings.API_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await create_access_token(
            data={"sub": api_key.key},
            expires_delta=access_token_expires
        )
        
        logger.info(f"JWT token created for API key: {api_key.key[:8]}...")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        logger.error(f"Error generating access token: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 