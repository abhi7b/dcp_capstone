"""
Duke VC Insight Engine - Backend Application

This package implements a FastAPI-based backend service for identifying and analyzing
Duke-affiliated startups and investment opportunities. The application is structured
into modular components that handle different aspects of the data pipeline.

Core Components:
- main: FastAPI application setup, middleware, and API documentation
- routes: REST API endpoints for companies, founders, and authentication
- services: Core processing services (SERP, NLP, scoring, caching)
- db: Database models, schemas, and CRUD operations
- tasks: Background processing tasks for data collection and updates
- utils: Configuration, logging, and helper utilities
- data: Data storage for raw inputs, processed outputs, and logs


For detailed setup and usage instructions, see the project README.
For API documentation, visit /api/docs when the server is running.
"""

# Version
__version__ = "1.0.0"

# Package exports
__all__ = [
    "main",           # FastAPI application
    "routes",         # API endpoints
    "services",       # Core services
    "db",            # Database operations
    "tasks",         # Background tasks
    "utils",         # Utilities
] 