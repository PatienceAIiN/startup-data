import pytest
import uuid as _uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _email():
    return f"user_{_uuid.uuid4().hex[:10]}@gmail.com"


async def test_signup_success(client: AsyncClient):
    payload = {
        "email": _email(),
        "password": "SecurePass@123",
        "full_name": "Test Person",
    }
    resp = await client.post("/auth/signup", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"].lower()


async def test_signup_duplicate_email(client: AsyncClient):
    email = _email()
    await client.post("/auth/signup", json={"email": email, "password": "Pass@1234", "full_name": "First"})
    resp = await client.post("/auth/signup", json={
        "email": email,
        "password": "AnotherPass@456",
        "full_name": "Duplicate User",
    })
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


async def test_login_success(client: AsyncClient, test_user):
    resp = await client.post("/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient, test_user):
    resp = await client.post("/auth/login", json={
        "email": test_user["email"],
        "password": "WrongPassword",
    })
    assert resp.status_code == 401


async def test_get_me_with_valid_token(client: AsyncClient, auth_headers):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200


async def test_get_me_without_token(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403
