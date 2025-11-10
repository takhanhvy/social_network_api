"""Centralized exception handlers to avoid leaking internals."""

import logging
from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.security")


def _json_response(status_code: int, error: str, detail: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"error": error, "detail": detail}),
    )


async def http_exception_handler(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return _json_response(exc.status_code, "http_error", exc.detail)


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return _json_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "validation_error",
        exc.errors(),
    )


async def rate_limit_handler(
    _: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return _json_response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "rate_limit_exceeded",
        exc.detail,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url, exc_info=exc)
    return _json_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "server_error",
        "Unexpected server error",
    )


__all__ = [
    "generic_exception_handler",
    "http_exception_handler",
    "rate_limit_handler",
    "validation_exception_handler",
]
