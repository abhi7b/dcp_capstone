"""
Main application module for Duke VC Insight Engine.

This module initializes the FastAPI application and includes all routes.
It also sets up API documentation, CORS middleware, and error handlers.
"""
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from .routes import company, person, auth
from .utils.config import settings
from .utils.logger import configure_loggers
from .db.session import check_db_connection, engine
from .db.models import Base
from .utils.logger import app_logger as logger
from .services.redis import redis_service

# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request information and rate limiting."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request details before processing
        logger.info(
            f"Incoming request: {request.method} {request.url.path} "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response details
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"Status: {response.status_code} "
                f"Duration: {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"Error: {str(e)} "
                f"Duration: {process_time:.3f}s"
            )
            raise

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing rate limits per API key."""
    
    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "API key required"}
            )
            
        # Check rate limit using Redis
        rate_key = f"rate_limit:{api_key}"
        current = await redis_service.get(rate_key) or 0
        
        if current >= settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded"}
            )
            
        # Increment counter with 60s expiry
        await redis_service.set(rate_key, current + 1, expire=60)
        return await call_next(request)

# Create FastAPI app with custom metadata for docs
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    Duke VC Insight Engine API
    
    This API provides access to Duke-affiliated startups and founders using a three-layered search approach:
    1. Database Layer: Quick retrieval of existing records
    2. Processing Layer: Real-time data collection and analysis
    3. Storage Layer: Persistent storage with automatic updates
    
    Key Features:
    - Comprehensive company and founder search
    - Duke affiliation verification
    - Investment relevance scoring
    - Real-time data enrichment
    - Automatic 3-day refresh cycle
    
    Authentication:
    - API Key required for all endpoints (X-API-Key header)
    - Rate limiting enforced per API key
    """,
    version=settings.VERSION,
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with updated paths
app.include_router(company.router, prefix="/api/company")
app.include_router(person.router, prefix="/api/founder")
app.include_router(auth.router, prefix="/api/auth")

# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with detailed error responses."""
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    
    error_response = {
        "error": {
            "code": exc.status_code,
            "message": exc.detail,
            "type": "http_error"
        }
    }
    
    if hasattr(exc, 'headers'):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=exc.headers
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with sanitized error messages."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    error_response = {
        "error": {
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "An unexpected error occurred",
            "type": "internal_error"
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )

# Custom OpenAPI schema with authentication
def custom_openapi() -> Dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"] = {
        "securitySchemes": {
            "APIKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for authentication and rate limiting",
            }
        }
    }
    
    # Set global security requirement
    openapi_schema["security"] = [{"APIKeyHeader": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Documentation endpoints
@app.get("/api/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """Serve OpenAPI schema"""
    return app.openapi()

@app.get("/api/docs", include_in_schema=False)
async def get_documentation():
    """Serve Swagger UI documentation."""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.PROJECT_NAME} - API Documentation",
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/api/redoc", include_in_schema=False)
async def get_redoc_documentation():
    """Serve ReDoc documentation."""
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.PROJECT_NAME} - API Reference",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "documentation": "/api/docs",
        "reference": "/api/redoc",
        "health": "/api/health"
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint with comprehensive system status."""
    try:
        # Check database connection
        db_status = await check_db_connection()
        
        # Check Redis connection
        redis_status = await redis_service.get("health_check") is not None
                
        # Get data refresh status
        last_refresh = await redis_service.get("last_refresh_date") or datetime.now().strftime("%Y-%m-%d")
        next_refresh = (datetime.now().replace(hour=0, minute=0, second=0) + 
                       timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Get API usage stats
        total_requests_24h = await redis_service.get("total_requests_24h") or 0
        active_api_keys = await redis_service.get("active_api_keys") or 0
        
        return {
            "status": "healthy" if all([db_status, redis_status]) else "degraded",
            "version": settings.VERSION,
            "components": {
                "database": {
                    "status": "connected" if db_status else "disconnected",
                    "last_refresh": last_refresh,
                    "next_refresh": next_refresh
                },
                "redis": {
                    "status": "connected" if redis_status else "disconnected"
                },

            },
            "usage": {
                "requests_24h": total_requests_24h,
                "active_api_keys": active_api_keys
            },
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("ENV", "development")
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed"
        )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application services on startup."""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Create all required directories
    for dir_path in [
        settings.DATA_DIR,
        settings.RAW_DATA_DIR,
        settings.PROCESSED_DATA_DIR,
        settings.JSON_INPUTS_DIR,
        settings.LOGS_DIR
    ]:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"Ensured directory exists: {dir_path}")
        except Exception as e:
            print(f"Warning: Could not create directory {dir_path}: {str(e)}")
    
    # Configure logging
    configure_loggers(settings.LOGS_DIR)
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Initialize database
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    # Initialize Redis
    try:
        await redis_service.set("health_check", "ok")
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise
    
    # Initialize Celery tasks


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application services on shutdown."""
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    await engine.dispose()
    await redis_service.clear_cache()

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 