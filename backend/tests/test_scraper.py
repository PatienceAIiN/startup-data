import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_trigger_scrape_requires_auth(client: AsyncClient):
    resp = await client.post("/scraper/trigger")
    assert resp.status_code in (401, 403)


async def test_trigger_scrape_requires_admin(client: AsyncClient, auth_headers):
    resp = await client.post("/scraper/trigger", headers=auth_headers)
    assert resp.status_code == 403


async def test_job_status_invalid_id(client: AsyncClient, auth_headers):
    resp = await client.get(
        "/scraper/status/00000000-0000-0000-0000-000000000000",
        headers=auth_headers
    )
    assert resp.status_code == 404


async def test_list_jobs(client: AsyncClient, auth_headers):
    resp = await client.get("/scraper/jobs", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
