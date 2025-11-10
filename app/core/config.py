"""Application configuration using pydantic settings."""

from functools import lru_cache
from typing import List

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "My Social Networks API"
    api_prefix: str = "/api"
    secret_key: str = Field("change-me", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(60, ge=15, le=60 * 24)
    algorithm: str = "HS256"
    database_url: AnyUrl = Field("sqlite+aiosqlite:///./app.db", env="DATABASE_URL")
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])
    allowed_hosts: List[str] = Field(default_factory=lambda: ["*"])
    enable_https_redirect: bool = Field(False, env="ENABLE_HTTPS_REDIRECT")
    content_security_policy: str = Field(
        "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'",
        env="CONTENT_SECURITY_POLICY",
    )
    permissions_policy: str = Field(
        "geolocation=(), microphone=(), camera=()",
        env="PERMISSIONS_POLICY",
    )
    referrer_policy: str = Field("same-origin", env="REFERRER_POLICY")
    rate_limit_default: str = Field("100/hour", env="RATE_LIMIT_DEFAULT")
    rate_limit_auth: str = Field("20/minute", env="RATE_LIMIT_AUTH")
    rate_limit_register: str = Field("5/hour", env="RATE_LIMIT_REGISTER")
    token_issuer: str = Field("my-social-networks-api", env="TOKEN_ISSUER")
    token_audience: str = Field("my-social-networks-clients", env="TOKEN_AUDIENCE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
