# DCP AI Scouting Platform Configuration

This directory contains the configuration system for the DCP AI Scouting Platform.

## Overview

The configuration system is built on three main components:

1. **Settings Management**: Uses Pydantic to load and validate configuration from environment variables.
2. **Logging System**: Provides structured logging with console and file output.
3. **Cache System**: Manages Redis-based caching for improved performance.

## Key Features

- **Simplified Settings Structure**: Flat settings structure with backward compatibility
- **Environment Variable Support**: Load configuration from .env files or environment variables
- **Structured Logging**: Console and file logging with different log levels
- **Efficient Caching**: Redis-based caching with key generation and invalidation

## Usage

### Basic Usage

```python
from backend.config import settings, get_logger, init_logging, init_cache

# Initialize logging at application startup
init_logging()

# Get a logger for your module
logger = get_logger(__name__)

# Access settings directly
db_url = settings.DATABASE_URL
api_key = settings.SERPAPI_KEY

# Initialize cache (in an async context)
await init_cache()

# Use the cache decorator
from backend.config import cached

@cached("company")
async def get_company(name: str):
    # This function's results will be cached
    ...
```

### Environment Variables

The configuration system uses environment variables with a flat structure. For example:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dcp_ai
LOG_LEVEL=INFO
SERPAPI_KEY=your-api-key-here
```

See the `.env` file in the project root directory for a complete list of available settings.

### Settings Structure

The settings are organized in a flat structure for simplicity:

- `settings.DATABASE_URL`: Database connection URL
- `settings.REDIS_URL`: Redis URL for caching
- `settings.LOG_LEVEL`: Logging level
- `settings.SERPAPI_KEY`: SerpAPI key
- `settings.OPENAI_API_KEY`: OpenAI API key

For backward compatibility, nested settings are still available:

```python
# These are equivalent
settings.DATABASE_URL
settings.database.URL

# These are equivalent
settings.OPENAI_MODEL
settings.openai.MODEL
```

### Logging

The logging system provides structured logs with different levels and outputs:

```python
logger = get_logger(__name__)

logger.debug("Detailed information for debugging")
logger.info("General information about system operation")
logger.warning("Warning about potential issues")
logger.error("Error that prevented an operation from completing")
logger.critical("Critical error that requires immediate attention")
```

Logs are written to both the console and log files (if enabled in settings).

### Caching

The caching system uses Redis to store frequently accessed data:

```python
# Use the cache decorator with a specific prefix
@cached("search")
async def search_companies(query: str, **filters):
    # Expensive operation...
    return results

# Manually invalidate cache
from backend.config import invalidate_search_cache
await invalidate_search_cache()
```

## Files

- `__init__.py`: Package exports and convenience functions
- `config.py`: Settings management using Pydantic
- `logs.py`: Logging configuration and utilities
- `cache.py`: Redis cache management and decorators
- `test_config.py`: Configuration testing script
- `README.md`: This documentation file
