# API Documentation

## Authentication
All API endpoints require an API key to be passed in the `X-API-Key` header:
```http
X-API-Key: your-api-key
```

## Base URL
The API base URL is configurable:
- Development: `http://localhost:8000`
- Production: `https://api.duke-vc-insight.com`

## Endpoints

### Company Search
```http
GET /api/company/search/{name}
```

**Parameters:**
- `name` (path): Company name to search for
- `force_refresh` (query): Boolean to force fresh data fetch (default: false)

**Response:**
```json
{
  "id": 1,
  "name": "Company Name",
  "duke_affiliation_status": "confirmed",
  "relevance_score": 85,
  "summary": "Company description",
  "investors": "Investor1, Investor2",
  "funding_stage": "Seed",
  "industry": "Technology",
  "founded": "2020-01-01",
  "location": "San Francisco, CA",
  "twitter_handle": "@company",
  "linkedin_handle": "company-name",
  "twitter_summary": "Recent Twitter activity summary",
  "source_links": "https://example1.com,https://example2.com",
  "people": [
    {
      "name": "Founder Name",
      "title": "CEO"
    }
  ],
  "last_updated": "2024-04-18T12:00:00Z"
}
```

### Founder Search
```http
GET /api/founder/search/{name}
```

**Parameters:**
- `name` (path): Founder name to search for
- `force_refresh` (query): Boolean to force fresh data fetch (default: false)

**Response:**
```json
{
  "id": 1,
  "name": "Founder Name",
  "title": "CEO",
  "current_company": "Company Name",
  "education": "Duke University, MBA 2010",
  "previous_companies": [
    {
      "name": "Previous Company",
      "role": "CTO",
      "duration": "2015-2020"
    }
  ],
  "twitter_handle": "@founder",
  "linkedin_handle": "founder-name",
  "duke_affiliation_status": "confirmed",
  "relevance_score": 90,
  "twitter_summary": "Recent Twitter activity summary",
  "source_links": "https://example1.com,https://example2.com",
  "companies": [
    {
      "name": "Current Company"
    }
  ],
  "last_updated": "2024-04-18T12:00:00Z"
}
```

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-04-18T12:00:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "openai": "connected"
  }
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing API key"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting
- 100 requests per minute per API key
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time until limit resets

## Caching
- Responses are cached in Redis for 1 hour
- Use `force_refresh=true` to bypass cache
- Cache can be cleared by restarting the Redis service

## Documentation
- Swagger UI: `/api/docs`
