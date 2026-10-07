"""Tests for the health check and root endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/health returns HTTP 200 and expected payload."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert data["app_env"] == "test"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verify GET / returns HTTP 200 and metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data
