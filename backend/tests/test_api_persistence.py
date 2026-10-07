"""Tests for Workflow API endpoints with database persistence and history retrieval."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_workflow_returns_run_id_and_persists(async_client: AsyncClient):
    """Verify POST /api/v1/workflows returns run_id and creates persistent record."""
    payload = {"query": "Compare PostgreSQL and MongoDB for a SaaS startup."}
    response = await async_client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "request_id" in data
    assert "run_id" in data
    assert data["run_id"] is not None
    assert data["status"] == "completed"
    assert "answer" in data
    assert len(data["key_points"]) > 0

    run_id = data["run_id"]

    # Verify run detail can be retrieved
    detail_res = await async_client.get(f"/api/v1/workflows/{run_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["run_id"] == run_id
    assert len(detail_data["steps"]) == 5
    agent_names = [s["agent_name"] for s in detail_data["steps"]]
    assert "planner" in agent_names
    assert "document_retrieval" in agent_names
    assert "data_analysis" in agent_names
    assert "researcher" in agent_names
    assert "responder" in agent_names


@pytest.mark.asyncio
async def test_get_workflow_runs_paginated(async_client: AsyncClient):
    """Verify GET /api/v1/workflows returns paginated list."""
    # Execute a run first
    await async_client.post("/api/v1/workflows", json={"query": "Test listing runs 1"})
    await async_client.post("/api/v1/workflows", json={"query": "Test listing runs 2"})

    response = await async_client.get("/api/v1/workflows?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) >= 2
    assert "run_id" in data["items"][0]
    assert "status" in data["items"][0]


@pytest.mark.asyncio
async def test_get_workflow_run_404_for_unknown_id(async_client: AsyncClient):
    """Verify GET /api/v1/workflows/{run_id} returns 404 for non-existent UUID."""
    random_uuid = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/workflows/{random_uuid}")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
