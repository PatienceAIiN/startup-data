"""
conftest.py — integration-test fixtures

Uses uvicorn in a background thread to avoid asyncpg/BaseHTTPMiddleware
event loop conflicts. Tables already exist from alembic migrations.
"""
import os
import socket
import threading
import time
import uuid

import pytest
import pytest_asyncio
import httpx
import uvicorn

os.environ["RATE_LIMIT_AUTH"] = "1000/minute"
os.environ["RATE_LIMIT_SCRAPER"] = "1000/hour"

from app.main import app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server_url():
    port = _free_port()
    host = "127.0.0.1"

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        loop="asyncio",
        log_level="warning",
        lifespan="on",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError(f"Test server on {base_url} did not start within 15s")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


@pytest_asyncio.fixture
async def client(live_server_url: str):
    async with httpx.AsyncClient(base_url=live_server_url, timeout=30.0) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(client: httpx.AsyncClient):
    email = f"testuser_{uuid.uuid4().hex[:10]}@gmail.com"
    payload = {
        "email": email,
        "password": "TestPass@123",
        "full_name": "Test User",
    }
    resp = await client.post("/auth/signup", json=payload)
    assert resp.status_code == 201, f"Signup failed: {resp.text}"
    data = resp.json()
    return {**payload, "token": data.get("access_token"), "id": data.get("user", {}).get("id")}


@pytest_asyncio.fixture
async def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['token']}"}
