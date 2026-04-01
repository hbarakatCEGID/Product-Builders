"""Smoke tests for the FastAPI webapp (uses httpx from default dev deps)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from product_builders.webapp.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_home_html(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Product Builders" in r.text


def test_download_html(client: TestClient) -> None:
    r = client.get("/download")
    assert r.status_code == 200
    assert "pip install" in r.text.lower() or "install" in r.text.lower()


def test_docs_index(client: TestClient) -> None:
    r = client.get("/docs")
    assert r.status_code == 200
    assert "Documentation" in r.text
    assert "/docs/getting-started" in r.text


def test_docs_getting_started_renders(client: TestClient) -> None:
    r = client.get("/docs/getting-started")
    assert r.status_code == 200
    assert "Getting started" in r.text or "Analyze" in r.text


def test_docs_unknown_slug_404(client: TestClient) -> None:
    r = client.get("/docs/does-not-exist-xyz")
    assert r.status_code == 404


def test_catalog_page(client: TestClient) -> None:
    r = client.get("/products")
    assert r.status_code == 200
    assert "Product catalog" in r.text


def test_api_products_json(client: TestClient) -> None:
    r = client.get("/api/products")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "name" in data[0]


def test_product_detail_when_profile_exists(client: TestClient) -> None:
    r = client.get("/products/product-builders")
    if r.status_code == 404:
        pytest.skip("No product-builders profile in PB_PROFILES_DIR")
    assert r.status_code == 200
    assert "product-builders" in r.text


def test_onboarding_engineer_when_present(client: TestClient) -> None:
    r = client.get("/products/product-builders/onboarding/engineer")
    if r.status_code == 404:
        pytest.skip("No engineer onboarding for product-builders")
    assert r.status_code == 200
    assert "markdown-body" in r.text


def test_product_unknown_404(client: TestClient) -> None:
    r = client.get("/products/__invalid__name__")
    assert r.status_code == 404
