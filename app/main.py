"""FastAPI application entrypoint."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from secure import Secure, Server, StrictTransportSecurity, XContentTypeOptions
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core import error_handlers
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.database import init_db
from app.routers import (
    addons,
    auth,
    discussions,
    events,
    groups,
    media,
    polls,
    tickets,
    users,
)

settings = get_settings()

app = FastAPI(title=settings.app_name)

secure_headers = Secure(
    hsts=StrictTransportSecurity().max_age(31536000).include_subdomains().preload(),
    xcto=XContentTypeOptions().nosniff(),
    server=Server().set(""),
)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)
if settings.enable_https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)


@app.middleware("http")
async def set_secure_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    secure_headers.set_headers(response)
    response.headers.setdefault(
        "Content-Security-Policy", settings.content_security_policy
    )
    response.headers.setdefault("Permissions-Policy", settings.permissions_policy)
    response.headers.setdefault("Referrer-Policy", settings.referrer_policy)
    response.headers.setdefault("X-Frame-Options", "DENY")
    return response


app.add_exception_handler(
    StarletteHTTPException, error_handlers.http_exception_handler
)
app.add_exception_handler(
    RequestValidationError, error_handlers.validation_exception_handler
)
app.add_exception_handler(
    RateLimitExceeded, error_handlers.rate_limit_handler
)
app.add_exception_handler(Exception, error_handlers.generic_exception_handler)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/")
async def healthcheck() -> dict[str, str]:
    return {"message": "My Social Networks API ready"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(groups.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(discussions.router, prefix=settings.api_prefix)
app.include_router(media.router, prefix=settings.api_prefix)
app.include_router(polls.router, prefix=settings.api_prefix)
app.include_router(tickets.router, prefix=settings.api_prefix)
app.include_router(addons.router, prefix=settings.api_prefix)
