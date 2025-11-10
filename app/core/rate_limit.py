"""Centralized SlowAPI limiter configuration."""

from fastapi import Request
from slowapi import Limiter

from app.core.config import get_settings

settings = get_settings()


def _client_id(request: Request) -> str:
    """Return a stable identifier for rate limiting."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "anonymous"
    return "anonymous"


limiter = Limiter(
    key_func=_client_id,
    default_limits=[settings.rate_limit_default],
    headers_enabled=True,
)

__all__ = ["limiter"]
