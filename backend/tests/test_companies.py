import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_companies_requires_auth(client: AsyncClient):
    resp = await client.get("/companies")
    assert resp.status_code in (401, 403)


async def test_list_companies_authenticated(client: AsyncClient, auth_headers):
    resp = await client.get("/companies", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data


async def test_list_companies_pagination(client: AsyncClient, auth_headers):
    resp = await client.get("/companies?page=1&page_size=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


async def test_list_companies_search(client: AsyncClient, auth_headers):
    resp = await client.get("/companies?search=tech", headers=auth_headers)
    assert resp.status_code == 200


async def test_list_companies_date_filter(client: AsyncClient, auth_headers):
    resp = await client.get("/companies?date_from=2020-01-01&date_to=2024-12-31", headers=auth_headers)
    assert resp.status_code == 200


async def test_stats_requires_auth(client: AsyncClient):
    resp = await client.get("/companies/stats")
    assert resp.status_code in (401, 403)


async def test_stats_authenticated(client: AsyncClient, auth_headers):
    resp = await client.get("/companies/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_companies" in data
    assert "startups" in data
    assert "by_state" in data
    assert "by_year" in data
