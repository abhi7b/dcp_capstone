"""
Authentication package for the DCP AI Scouting Platform.

This package provides API key validation and rate limiting functionality.
"""

from backend.auth.auth import (
    get_api_key,
    get_current_user,
    check_scope,
    generate_api_key,
    API_KEY_HEADER
)

from backend.auth.rate_limit import (
    rate_limiter,
    get_rate_limiter,
    RateLimiter,
    InMemoryRateLimiter
)

__all__ = [
    # Authentication
    "get_api_key",
    "get_current_user",
    "check_scope",
    "generate_api_key",
    "API_KEY_HEADER",
    
    # Rate limiting
    "rate_limiter",
    "get_rate_limiter",
    "RateLimiter",
    "InMemoryRateLimiter"
] 