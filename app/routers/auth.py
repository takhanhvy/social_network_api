"""Authentication endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.dependencies import get_db_session
from app.models import User
from app.schemas import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_register)
async def register_user(
    request: Request,  # noqa: ARG001  - required for rate limiter
    response: Response,  # noqa: ARG001 - used by slowapi for headers
    user_in: UserCreate, session: AsyncSession = Depends(get_db_session)
) -> UserRead:
    existing = await session.execute(select(User).where(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return UserRead.from_orm(user)


@router.post("/token", response_model=Token)
@limiter.limit(settings.rate_limit_auth)
async def login_for_access_token(
    request: Request,  # noqa: ARG001 - required for rate limiter
    response: Response,  # noqa: ARG001 - used by slowapi for headers
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> Token:
    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(subject=str(user.id), expires_delta=expires_delta)
    return Token(
        access_token=access_token,
        expires_in=int(expires_delta.total_seconds()),
    )
