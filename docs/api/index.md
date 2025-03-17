# API Documentation

<!-- 
This file serves as the index for the API documentation. It should provide a comprehensive
overview of the API, including authentication methods, endpoint structure, response formats,
and usage examples. This documentation is essential for developers who need to interact
with the platform programmatically.
-->

The DCP AI Scouting Platform provides a RESTful API for accessing and manipulating data. This documentation provides detailed information about the API endpoints, authentication, and usage.

## Base URL

All API endpoints are relative to the base URL:

```
http://localhost:8000/api/v1
```

For production, the base URL would be your deployed domain.

## Authentication

The API uses API key authentication. To authenticate, include your API key in the `X-API-Key` header:

```
X-API-Key: your-api-key
```

See the [Authentication](authentication.md) page for more details.

## Rate Limiting

The API implements rate limiting to prevent abuse. By default, clients are limited to 100 requests per minute.

See the [Rate Limiting](rate-limiting.md) page for more details.

## Endpoints

### Company Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/company/{company_name}` | GET | Get company details |
| `/company/search` | POST | Search for companies |
| `/company/stats` | GET | Get company statistics |

See the [Company Endpoints](endpoints/company.md) page for more details.

### Founder Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/founder/{founder_name}` | GET | Get founder details |
| `/founder/search` | POST | Search for founders |
| `/founder/stats` | GET | Get founder statistics |

See the [Founder Endpoints](endpoints/founder.md) page for more details.

### Test Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/test/ping` | GET | Simple health check |
| `/test/db` | GET | Database connection check |

See the [Test Endpoints](endpoints/test.md) page for more details.

## Response Format

All API responses are in JSON format. Successful responses have the following structure:

```json
{
  "id": 1,
  "name": "Example Company",
  "description": "An example company",
  ...
}
```

Error responses have the following structure:

```json
{
  "detail": "Error message"
}
```

## Status Codes

The API uses standard HTTP status codes:

| Code | Description |
|------|-------------|
| 200 | OK - The request was successful |
| 400 | Bad Request - The request was invalid |
| 401 | Unauthorized - Authentication failed |
| 403 | Forbidden - You don't have permission |
| 404 | Not Found - The resource was not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |

## Examples

### Get Company Details

```bash
curl -X GET "http://localhost:8000/api/v1/company/Example%20Company" \
  -H "X-API-Key: your-api-key"
```

### Search for Companies

```bash
curl -X POST "http://localhost:8000/api/v1/company/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI", "filters": {"duke_affiliated": true}}'
```

### Get Founder Details

```bash
curl -X GET "http://localhost:8000/api/v1/founder/John%20Doe" \
  -H "X-API-Key: your-api-key"
``` 