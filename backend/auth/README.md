# Authentication

API key authentication and rate limiting for the DCP AI Scouting Platform.

## Components

- `auth.py`: API key validation with caching
- `rate_limit.py`: Prevents API abuse
- `test_auth.py`: Tests authentication functionality

## Usage Examples

```python
# Protect an endpoint
@app.get("/protected")
async def protected_endpoint(api_key = Depends(get_api_key)):
    return {"message": "Protected endpoint"}

# Require admin access
@app.get("/admin")
async def admin_endpoint(has_scope = Depends(lambda: check_scope("admin"))):
    return {"message": "Admin endpoint"}

# Add rate limiting
@app.get("/limited")
async def limited_endpoint(
    api_key = Depends(get_api_key),
    _rate_limit = Depends(rate_limiter.limit(max_requests=10, window_seconds=60))
):
    return {"message": "Rate limited endpoint"}
```

## Testing

```
python -m backend.auth.test_auth
```

## Features

- Multi-level caching (memory + Redis)
- Fallback when Redis is unavailable
- Scope-based authorization
- Configurable rate limits

## Configuration

- `REDIS_URL`: Redis connection URL
- `API_KEY_CACHE_TTL`: Cache TTL in seconds (default: 300) 