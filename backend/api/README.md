# API Module for DCP AI Scouting Platform

This module provides RESTful API endpoints for accessing and manipulating data in the DCP AI Scouting Platform.

## Key Components

### Base Endpoint

- **BaseEndpoint** (`base_endpoint.py`): Generic base class that provides common functionality for all API endpoints:
  - Background refresh handling
  - Twitter data processing
  - Database operations
  - Error handling
  - Caching
  - Response formatting

### Entity Endpoints

- **Company Endpoints** (`company.py`): Endpoints for company data:
  - `GET /api/v1/company/{company_name}`: Retrieve company details
  - `POST /api/v1/company/search`: Search for companies
  - `GET /api/v1/company/stats`: Get company statistics

- **Founder Endpoints** (`founder.py`): Endpoints for founder data:
  - `GET /api/v1/founder/{founder_name}`: Retrieve founder details
  - `POST /api/v1/founder/search`: Search for founders
  - `GET /api/v1/founder/stats`: Get founder statistics

- **Test Endpoints** (`test.py`): Utility endpoints for system health checks:
  - `GET /api/v1/test/ping`: Simple health check
  - `GET /api/v1/test/db`: Database connection check

### Testing

- **Test Suite** (`test_api.py`): Comprehensive test suite for API functionality:
  - Mock tests for unit testing
  - Integration tests with real data
  - Database setup and teardown utilities

## Data Flow

1. **Request Handling**:
   - Endpoints receive HTTP requests
   - Parameters are validated
   - Authentication and rate limiting are applied

2. **Data Retrieval**:
   - Check cache for existing data
   - Query database if data exists
   - Trigger scrapers and NLP processors if data needs to be fetched/refreshed

3. **Background Processing**:
   - Long-running tasks are offloaded to background workers
   - Clients receive immediate response with status indication

4. **Response Formatting**:
   - Data is formatted according to Pydantic schemas
   - Consistent error handling across all endpoints

## Key Features

- **Caching**: Redis-based caching to improve performance
- **Background Processing**: Asynchronous data refresh without blocking client requests
- **Standardized Responses**: Consistent response format across all endpoints
- **Error Handling**: Comprehensive error handling with detailed error messages
- **Rate Limiting**: Protection against excessive API usage
- **Data Freshness**: Automatic refresh of stale data

## Usage Examples

### Retrieving Company Data

```python
import requests

# Get company details
response = requests.get("http://localhost:8000/api/v1/company/Example%20Company")
company_data = response.json()

# Search for companies
search_response = requests.post(
    "http://localhost:8000/api/v1/company/search",
    json={"query": "AI", "filters": {"duke_affiliated": True}}
)
search_results = search_response.json()
```

### Retrieving Founder Data

```python
import requests

# Get founder details
response = requests.get("http://localhost:8000/api/v1/founder/John%20Doe")
founder_data = response.json()

# Get founder statistics
stats_response = requests.get("http://localhost:8000/api/v1/founder/stats")
stats = stats_response.json()
```

## Testing

To run the API tests:

```bash
# Run mock tests only
python -m backend.api.test_api --mock-data

# Run all tests
python -m backend.api.test_api --all
``` 