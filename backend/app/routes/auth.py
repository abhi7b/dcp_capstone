from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import time

from ..db.session import get_db
from ..db import crud, schemas
from ..utils.config import settings
from ..utils.logger import api_logger

# Define API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Initialize router
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limiting data (in-memory cache)
rate_limit_cache = {}

async def get_api_key(
    api_key_header: str = Depends(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db)
) -> schemas.APIKeyResponse:
    """
    Validate API key and apply rate limiting
    """
    if not api_key_header:
        api_logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Get API key from database
    api_key = await crud.get_api_key(db, api_key_header)
    if not api_key or not api_key.is_active:
        api_logger.warning(f"Invalid or inactive API key: {api_key_header[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check if API key is expired
    if api_key.expires_at and api_key.expires_at < datetime.now():
        api_logger.warning(f"Expired API key: {api_key_header[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Apply rate limiting
    cache_key = f"rate_limit:{api_key.key}"
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
    
    # Check if rate limit exceeded
    if rate_limit_cache[cache_key]["count"] > api_key.rate_limit:
        api_logger.warning(f"Rate limit exceeded for API key: {api_key_header[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {api_key.rate_limit} requests per minute allowed.",
        )
    
    api_logger.debug(f"API key validated: {api_key_header[:8]}...")
    return api_key

# API key management endpoints
@router.post("/keys", response_model=schemas.APIKeyResponse)
async def create_api_key(
    api_key_data: schemas.APIKeyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key
    """
    api_logger.info("Creating new API key")
    api_key = await crud.create_api_key(db, api_key_data)
    api_logger.info(f"API key created: {api_key.key[:8]}...")
    return api_key

@router.post("/keys/{api_key}/deactivate", response_model=schemas.ErrorResponse)
async def deactivate_api_key(
    api_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate an API key
    """
    api_logger.info(f"Deactivating API key: {api_key[:8]}...")
    deactivated = await crud.deactivate_api_key(db, api_key)
    if not deactivated:
        api_logger.warning(f"API key not found for deactivation: {api_key[:8]}...")
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_logger.info(f"API key deactivated: {api_key[:8]}...")
    return {"detail": "API key deactivated successfully"}

# JWT token operations for alternative authentication
async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.API_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.API_SECRET_KEY, algorithm=settings.API_ALGORITHM)
    return encoded_jwt

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    api_key_header: str = Depends(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db)
):
    """
    Get JWT token using API key
    """
    api_key = await get_api_key(api_key_header, db)
    
    access_token_expires = timedelta(minutes=settings.API_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": api_key.key},
        expires_delta=access_token_expires
    )
    
    api_logger.info(f"JWT token created for API key: {api_key.key[:8]}...")
    return {"access_token": access_token, "token_type": "bearer"} 