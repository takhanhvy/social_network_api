import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_enforces_password_policy(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "weak@example.com",
            "password": "weakpass",
            "full_name": " Weak Name ",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


@pytest.mark.asyncio
async def test_login_rate_limit_triggers(client: AsyncClient) -> None:
    register = await client.post(
        "/api/auth/register",
        json={
            "email": "ratelimit@example.com",
            "password": "StrongPass!1",
            "full_name": "Rate Limited",
        },
    )
    assert register.status_code == 201

    payload = {"username": "ratelimit@example.com", "password": "StrongPass!1"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    for _ in range(3):
        ok = await client.post(
            "/api/auth/token",
            data=payload,
            headers=headers,
        )
        assert ok.status_code == 200

    blocked = await client.post(
        "/api/auth/token",
        data=payload,
        headers=headers,
    )
    assert blocked.status_code == 429
    detail = blocked.json()
    assert detail["error"] == "rate_limit_exceeded"
