"""Tests for Workflow API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_workflow_success(async_client: AsyncClient):
    """Verify POST /api/v1/workflows succeeds and returns structured payload."""
    payload = {
        "query": "Compare PostgreSQL and MongoDB for a startup SaaS application."
    }
    response = await async_client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "request_id" in data
    assert len(data["request_id"]) > 0
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert "key_points" in data
    assert isinstance(data["key_points"], list)
    assert len(data["key_points"]) > 0
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0
    assert "errors" in data
    assert isinstance(data["errors"], list)


@pytest.mark.asyncio
async def test_create_workflow_invalid_payload(async_client: AsyncClient):
    """Verify POST /api/v1/workflows rejects invalid or empty queries."""
    # Query too short / empty
    response = await async_client.post("/api/v1/workflows", json={"query": ""})
    assert response.status_code == 422

    # Missing query field
    response_missing = await async_client.post("/api/v1/workflows", json={})
    assert response_missing.status_code == 422
