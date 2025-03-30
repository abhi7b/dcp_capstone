"""
Main application module for Duke VC Insight Engine.

This module initializes the FastAPI application and includes all routes.
It also sets up API documentation, CORS middleware, and error handlers.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os
import time
from datetime import datetime

from backend.app.routes import company, founder, auth
from backend.app.utils.config import settings
from backend.app.utils.logger import get_logger, configure_loggers
from backend.app.db.session import check_db_connection

logger = get_logger("app")

# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request information."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log request details
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {process_time:.3f}s "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        return response

# Create FastAPI app with custom metadata for docs
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    Duke VC Insight Engine API
    
    This API provides access to Duke-affiliated startups and founders.
    It allows searching and filtering companies and founders based on
    various criteria, with a focus on investment relevance and Duke affiliation.
    """,
    version=settings.VERSION,
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(company.router, prefix="/api")
app.include_router(founder.router, prefix="/api")
app.include_router(auth.router, prefix="/api")

# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and return consistent error format."""
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions and return 500 error."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred"},
    )

# Custom OpenAPI schema with authentication
def custom_openapi():
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
                "description": "API key for authentication",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token for authentication",
            }
        }
    }
    
    # Set global security requirement
    openapi_schema["security"] = [
        {"APIKeyHeader": []},
        {"BearerAuth": []}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Expose OpenAPI schema
@app.get("/api/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """Serve OpenAPI schema"""
    return app.openapi()

# Custom documentation endpoints
@app.get("/api/docs", include_in_schema=False)
async def get_documentation():
    """Redirect to Swagger UI."""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.PROJECT_NAME} - Swagger UI",
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/api/redoc", include_in_schema=False)
async def get_redoc_documentation():
    """Redirect to ReDoc UI."""
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.PROJECT_NAME} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint that redirects to API documentation."""
    return {"message": f"Welcome to {settings.PROJECT_NAME} API", "docs": "/api/docs"}

# Simple health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    db_status = await check_db_connection()
    return {
        "status": "ok", 
        "database": "connected" if db_status else "disconnected",
        "timestamp": datetime.now().isoformat()
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Run tasks when application starts."""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Use the BACKEND_DIR directly to create absolute paths
    backend_dir = os.path.abspath(os.path.dirname(__file__))
    data_dir = os.path.join(backend_dir, "data")
    raw_dir = os.path.join(data_dir, "raw")
    json_inputs_dir = os.path.join(data_dir, "json_inputs")
    logs_dir = os.path.join(data_dir, "logs")
    
    # Ensure all required directories exist
    for dir_path in [data_dir, raw_dir, json_inputs_dir, logs_dir]:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"Ensured directory exists: {dir_path}")
        except Exception as e:
            print(f"Warning: Could not create directory {dir_path}: {str(e)}")
    
    # Override the settings with actual backend paths
    settings.DATA_DIR = data_dir
    settings.RAW_DATA_DIR = raw_dir
    settings.JSON_INPUTS_DIR = json_inputs_dir
    settings.LOGS_DIR = logs_dir
    
    # Configure loggers with the proper paths
    configure_loggers(logs_dir)
    
    # Now that directories are set up, we can log properly
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Using data directory: {settings.DATA_DIR}")
    logger.info(f"Using logs directory: {settings.LOGS_DIR}")
    
    # Verify database connection
    db_status = await check_db_connection()
    if db_status:
        logger.info("Successfully connected to database")
    else:
        logger.error("Failed to connect to database")

@app.on_event("shutdown")
async def shutdown_event():
    """Run tasks when application shuts down."""
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True) 