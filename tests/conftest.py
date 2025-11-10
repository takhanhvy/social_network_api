import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")
os.environ.setdefault("ALLOWED_HOSTS", '["test","localhost","127.0.0.1"]')
os.environ.setdefault("RATE_LIMIT_DEFAULT", "100/minute")
os.environ.setdefault("RATE_LIMIT_AUTH", "3/minute")
os.environ.setdefault("RATE_LIMIT_REGISTER", "5/minute")

from app.main import app  # noqa: E402
from app.database import engine, init_db  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def setup_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await init_db()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    limiter.reset()
    yield
    limiter.reset()
