"""Security helpers for password hashing and JWT tokens."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.schemas import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": now,
    }
    if settings.token_issuer:
        to_encode["iss"] = settings.token_issuer
    if settings.token_audience:
        to_encode["aud"] = settings.token_audience
    if additional_claims:
        to_encode.update(additional_claims)
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()
    decode_kwargs: dict[str, Any] = {"algorithms": [settings.algorithm]}
    if settings.token_audience:
        decode_kwargs["audience"] = settings.token_audience
    if settings.token_issuer:
        decode_kwargs["issuer"] = settings.token_issuer
    try:
        payload = jwt.decode(token, settings.secret_key, **decode_kwargs)
        return TokenPayload(**payload)
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
