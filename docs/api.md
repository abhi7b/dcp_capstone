# API Documentation

## Authentication
- API Key authentication (X-API-Key header)
- Rate limiting per API key
- All endpoints prefixed with `/api/`

## Endpoints

### Company Search
```
GET /api/companies?name=CompanyName
```

**Flow:**
1. Check if company exists in database
2. If not found, query SERP API
3. Extract company details and Duke affiliation
4. Return structured company information

**Response Example:**
```json
{
  "name": "Example Corp",
  "founding_date": "2023-01-01",
  "stage": "Series A",
  "duke_affiliation": {
    "status": "confirmed",
    "score": 95,
    "details": "Founder is Duke alum"
  },
  "twitter_handle": "@examplecorp",
  "recent_tweets": [...],
  "score": 92
}
```

### Person Search
```
GET /api/person?name=PersonName
```

**Flow:**
1. Check if person exists in database
2. If not found, query SERP API
3. Extract person profile and Duke connection
4. Return structured person information

**Response Example:**
```json
{
  "name": "John Doe",
  "education": [
    {
      "institution": "Duke University",
      "degree": "MBA",
      "year": "2015"
    }
  ],
  "current_company": "Example Corp",
  "role": "CEO",
  "duke_affiliation": {
    "status": "confirmed",
    "score": 100
  },
  "twitter_handle": "@johndoe",
  "recent_tweets": [...],
  "score": 98
}
```

### Authentication
```
POST /api/auth/token
```

**Request Body:**
```json
{
  "api_key": "your_api_key"
}
```

**Response:**
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

## Error Handling
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Documentation
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI Schema: `/api/openapi.json`

## Health Check
```
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": {
    "status": "connected",
    "last_refresh": "2024-04-08",
    "next_refresh": "2024-04-11"
  },
  "timestamp": "2024-04-08T12:00:00Z",
  "environment": "development"
}
``` 