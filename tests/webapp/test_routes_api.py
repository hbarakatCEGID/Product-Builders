"""Tests for API endpoints."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from product_builders.webapp.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_post_analyze_missing_fields(client):
    resp = await client.post("/api/analyze", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_generate_missing_fields(client):
    resp = await client.post("/api/generate", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_feedback_missing_fields(client):
    resp = await client.post("/api/feedback", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_recent_paths(client):
    resp = await client.get("/api/recent-paths")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_metrics_missing_product(client):
    resp = await client.get("/api/metrics/nonexistent-product-xyz")
    assert resp.status_code == 200
    assert resp.json() == []
