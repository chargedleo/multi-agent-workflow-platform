"""Tests for Document REST API endpoints."""

import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_document_endpoint_success(async_client: AsyncClient):
    """Verify POST /api/v1/documents successfully uploads and indexes a text file."""
    content = b"LangGraph enables complex agentic loops with shared state graph execution."
    files = {"file": ("langgraph_guide.txt", io.BytesIO(content), "text/plain")}

    response = await async_client.post("/api/v1/documents", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "langgraph_guide.txt"
    assert data["status"] == "COMPLETED"
    assert data["chunk_count"] > 0
    doc_id = data["document_id"]

    # Verify GET /api/v1/documents contains uploaded document
    list_res = await async_client.get("/api/v1/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["document_id"] == doc_id for item in list_data["items"])

    # Verify GET /api/v1/documents/{id} returns details
    detail_res = await async_client.get(f"/api/v1/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["document_id"] == doc_id
    assert detail_data["chunk_count"] > 0

    # Verify DELETE /api/v1/documents/{id} removes it
    del_res = await async_client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "deleted"

    # Confirm 404 after deletion
    check_res = await async_client.get(f"/api/v1/documents/{doc_id}")
    assert check_res.status_code == 404


@pytest.mark.asyncio
async def test_upload_document_unsupported_format(async_client: AsyncClient):
    """Verify POST /api/v1/documents rejects unsupported file extensions."""
    files = {"file": ("malicious.exe", io.BytesIO(b"binary data"), "application/octet-stream")}
    response = await async_client.post("/api/v1/documents", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_document_404_not_found(async_client: AsyncClient):
    """Verify GET /api/v1/documents/{id} returns 404 for unknown UUID."""
    unknown_uuid = "00000000-0000-0000-0000-000000000000"
    response = await async_client.get(f"/api/v1/documents/{unknown_uuid}")
    assert response.status_code == 404
