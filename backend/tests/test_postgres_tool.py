"""Unit tests for PostgreSQL parameterized analytical query tool."""

import pytest
from backend.app.analysis.schemas import FilterCondition, FilterOperator, PostgresQueryRequest, SortOrder
from backend.app.mcp.tools.postgres import PostgresAnalyticsTool


@pytest.mark.asyncio
async def test_postgres_tool_simple_query():
    req = PostgresQueryRequest(
        table="analytics_orders",
        columns=["order_id", "region", "revenue"],
        limit=5,
    )
    result = await PostgresAnalyticsTool.query(req)
    assert result["success"] is True
    assert result["table"] == "analytics_orders"
    assert len(result["rows"]) <= 5
    assert "revenue" in result["columns"]


@pytest.mark.asyncio
async def test_postgres_tool_aggregations():
    req = PostgresQueryRequest(
        table="analytics_orders",
        group_by=["region"],
        aggregations={"revenue": "sum", "quantity": "sum"},
        order_by="revenue_sum",
        sort_order=SortOrder.DESC,
    )
    result = await PostgresAnalyticsTool.query(req)
    assert result["success"] is True
    assert len(result["rows"]) == 4
    regions = [r["region"] for r in result["rows"]]
    assert "West" in regions
    assert "North" in regions


@pytest.mark.asyncio
async def test_postgres_tool_filter_equality():
    req = PostgresQueryRequest(
        table="analytics_orders",
        columns=["order_id", "region", "customer"],
        filters=[
            FilterCondition(column="region", operator=FilterOperator.EQ, value="West")
        ],
    )
    result = await PostgresAnalyticsTool.query(req)
    assert result["success"] is True
    assert len(result["rows"]) == 6
    for row in result["rows"]:
        assert row["region"] == "West"


@pytest.mark.asyncio
async def test_postgres_tool_invalid_table_rejected():
    req = PostgresQueryRequest(
        table="users_passwords",
        columns=["password"],
    )
    result = await PostgresAnalyticsTool.query(req)
    assert result["success"] is False
    assert "not permitted" in result["error"]


@pytest.mark.asyncio
async def test_postgres_tool_invalid_column_rejected():
    req = PostgresQueryRequest(
        table="analytics_orders",
        columns=["secret_token"],
    )
    result = await PostgresAnalyticsTool.query(req)
    assert result["success"] is False
    assert "not allowed" in result["error"]


@pytest.mark.asyncio
async def test_postgres_tool_sql_injection_attempt_rejected():
    # Attempting SQL injection in column name
    req = PostgresQueryRequest(
        table="analytics_orders",
        columns=["revenue; DROP TABLE analytics_orders; --"],
    )
    result = await PostgresAnalyticsTool.query(req)
    assert result["success"] is False
    assert "not allowed" in result["error"]
