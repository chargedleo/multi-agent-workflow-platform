"""Tests for analytics datasets API endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_analytics_datasets(async_client: AsyncClient):
    response = await async_client.get("/api/v1/analytics/datasets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    orders_meta = next(d for d in data if d["dataset_name"] == "orders")
    assert orders_meta["row_count"] == 20
    col_names = [c["name"] for c in orders_meta["columns"]]
    assert "revenue" in col_names
    assert "region" in col_names
