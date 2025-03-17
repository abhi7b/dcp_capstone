#!/usr/bin/env python3
"""
DCP AI Scouting Platform API Server

This is the main entry point for the DCP AI Scouting Platform backend.
It initializes the FastAPI application, sets up routes, middleware, and
starts the server when run directly.
"""

import logging
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
import os

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from backend.config.config import settings
from backend.config.logs import LogManager
from backend.config.cache import CacheManager
from db.database.db import get_db, engine, Base
from db.database.models import SERPUsage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.api import company, founder, test

# Setup logging
LogManager.setup_logging()
logger = logging.getLogger(__name__)

logger.info("FastAPI server starting...")

def validate_api_keys():
    """Validate that all required API keys are set."""
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check SerpAPI key
    if not settings.scraper.SERPAPI_KEY:
        logger.error("⚠️ SERPAPI_KEY is not set in .env file. Search functionality will not work.")
    else:
        logger.info(f"✅ SERPAPI_KEY is set (length: {len(settings.scraper.SERPAPI_KEY)})")
    
    # Check OpenAI API key
    if not settings.openai.API_KEY:
        logger.error("⚠️ OPENAI_API_KEY is not set in .env file. NLP functionality will not work.")
    else:
        logger.info(f"✅ OPENAI_API_KEY is set (length: {len(settings.openai.API_KEY)})")
    
    # Check database URL
    if not settings.database.URL:
        logger.error("⚠️ DATABASE_URL is not set in .env file. Database functionality will not work.")
    else:
        logger.info("✅ DATABASE_URL is set")

async def init_db():
    """Initialize the database with required tables."""
    if settings.ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("DB tables created (development mode).")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager:
    - Initialize Redis cache
    - Create DB tables automatically in development
    - Create logs directory
    - Dispose connections at shutdown
    """
    # 1) Create logs directory if it doesn't exist
    logs_dir = Path(settings.logging.FILE_PATH)
    logs_dir.mkdir(exist_ok=True)
    
    # 2) Initialize Redis-based caching
    await CacheManager.init_cache()
    logger.info(f"Cache initialized with Redis URL: {settings.cache.REDIS_URL}")

    # 3) Create DB tables automatically if in development
    await init_db()

    # 4) Log startup information
    logger.info(f"Starting DCP AI Scouting Platform in {settings.ENV} mode")
    logger.info(f"OpenAI model: {settings.openai.MODEL}")
    
    # Validate API keys
    validate_api_keys()

    yield

    # 5) Cleanup at shutdown
    logger.info("Shutting down DCP AI Scouting Platform")
    await engine.dispose()
    await CacheManager.close()

app = FastAPI(
    title="DCP AI Scouting Platform API",
    description="API for the Duke Capital Partners AI Scouting Platform",
    version="1.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
    openapi_url=None,  # Disable default openapi
    lifespan=lifespan
)

def custom_openapi():
    """
    Customize the OpenAPI schema.
    
    Returns:
        Dict: The customized OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Explicitly set OpenAPI version
    openapi_schema["openapi"] = "3.0.2"
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Add processing time to response headers.
    
    Args:
        request: The incoming request
        call_next: The next middleware or route handler
        
    Returns:
        Response with X-Process-Time header
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Register API Routes
app.include_router(company.router, prefix="/api/v1/company", tags=["company"])
app.include_router(founder.router, prefix="/api/v1/founder", tags=["founder"])
app.include_router(test.router, prefix="/api/v1/test", tags=["test"])

# Global Exception Handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Handle HTTP exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception
        
    Returns:
        JSONResponse: JSON response with error details
    """
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code, 
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Handle general exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception
        
    Returns:
        JSONResponse: JSON response with error details
    """
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Custom OpenAPI schema
@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """
    Get OpenAPI schema.
    
    This endpoint returns the OpenAPI schema for the API.
    """
    return get_openapi(
        title="DCP AI Scouting Platform API",
        version="1.0.0",
        description="API for the Duke Capital Partners AI Scouting Platform",
        routes=app.routes
    )

# Swagger UI
@app.get("/docs", include_in_schema=False)
async def get_documentation():
    """
    Get Swagger UI documentation.
    
    This endpoint returns the Swagger UI documentation for the API.
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="DCP AI Scouting Platform API"
    )

# ReDoc
@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation():
    """
    Get ReDoc documentation.
    
    This endpoint returns the ReDoc documentation for the API.
    """
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="DCP AI Scouting Platform API"
    )

# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict[str, Any]: Health status
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": app.version,
        "environment": settings.ENV
    }

@app.get("/health/db", tags=["Health"])
async def db_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Database health check endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Database health status
    """
    try:
        # Execute a simple query to check DB connection
        query = select(func.now())
        result = await db.execute(query)
        db_time = result.scalar_one()
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "db_timestamp": db_time.isoformat() if db_time else None,
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Database connection failed: {str(e)}"
        }

@app.get("/health/cache", tags=["Health"])
async def cache_health_check() -> Dict[str, Any]:
    """
    Cache health check endpoint.
    
    Returns:
        Dict[str, Any]: Cache health status
    """
    try:
        # Check if Redis is connected
        is_connected = await CacheManager.is_connected()
        
        if is_connected:
            # Set a test value
            test_key = "health_check_test"
            test_value = datetime.utcnow().isoformat()
            
            await CacheManager.set(test_key, test_value, expire=60)
            retrieved_value = await CacheManager.get(test_key)
            
            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "cache_test": retrieved_value == test_value,
                "message": "Cache connection successful"
            }
        else:
            return {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Cache connection failed"
            }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Cache check failed: {str(e)}"
        }

@app.get("/health/quota", tags=["Health"])
async def quota_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    API quota health check endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: API quota status
    """
    try:
        # Get today's date
        today = datetime.utcnow().date()
        start_of_day = datetime(today.year, today.month, today.day)
        
        # Query for today's SERP API usage
        query = select(func.count(SERPUsage.id)).where(
            SERPUsage.created_at >= start_of_day
        )
        result = await db.execute(query)
        today_count = result.scalar_one() or 0
        
        # Query for total SERP API usage
        query = select(func.count(SERPUsage.id))
        result = await db.execute(query)
        total_count = result.scalar_one() or 0
        
        # Calculate remaining quota
        daily_quota = settings.scraper.DAILY_QUOTA
        remaining = max(0, daily_quota - today_count)
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "serp_api": {
                "today_usage": today_count,
                "total_usage": total_count,
                "daily_quota": daily_quota,
                "remaining": remaining,
                "percentage_used": round((today_count / daily_quota) * 100, 2) if daily_quota > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Quota health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Quota check failed: {str(e)}"
        }

@app.get("/api/v1", tags=["API"])
async def api_root() -> Dict[str, Any]:
    """
    API root endpoint.
    
    Returns:
        Dict[str, Any]: API information
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": app.version,
        "description": "Duke Capital Partners AI Scouting Platform API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "environment": settings.ENV,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns:
        Dict[str, Any]: API information
    """
    return {
        "name": settings.PROJECT_NAME,
        "description": "Duke Capital Partners AI Scouting Platform",
        "api_url": "/api/v1",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    # Run the application
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting DCP AI Scouting Platform API on {host}:{port}")
    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=settings.DEBUG,
        log_level=settings.logging.LEVEL.lower(),
    )
