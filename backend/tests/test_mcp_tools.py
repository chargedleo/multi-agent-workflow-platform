"""Unit tests for MCP server tool registration, schemas, and invocation."""

import pytest
from backend.app.mcp.server import (
    invoke_mcp_tool,
    list_registered_mcp_tools,
    mcp_server,
)


@pytest.mark.asyncio
async def test_mcp_tool_registration():
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    assert "analyze_dataset" in tool_names
    assert "get_dataset_schema" in tool_names
    assert "query_postgres" in tool_names


@pytest.mark.asyncio
async def test_list_registered_mcp_tools_metadata():
    metadata = await list_registered_mcp_tools()
    assert len(metadata) == 3
    tool_map = {m["name"]: m for m in metadata}

    assert "analyze_dataset" in tool_map
    assert "parameters" in tool_map["analyze_dataset"]
    assert "description" in tool_map["analyze_dataset"]


@pytest.mark.asyncio
async def test_invoke_mcp_get_dataset_schema():
    res = await invoke_mcp_tool("get_dataset_schema", {"dataset": "orders"})
    assert res.success is True
    assert res.tool_name == "get_dataset_schema"
    assert res.result["dataset"] == "orders"
    assert res.result["row_count"] == 20


@pytest.mark.asyncio
async def test_invoke_mcp_analyze_dataset():
    args = {
        "dataset": "orders",
        "operation": "sum",
        "columns": ["revenue"],
    }
    res = await invoke_mcp_tool("analyze_dataset", args)
    assert res.success is True
    assert res.tool_name == "analyze_dataset"
    assert res.result["success"] is True
    assert res.result["metrics"]["sum_revenue"] == 177650.0


@pytest.mark.asyncio
async def test_invoke_mcp_query_postgres():
    args = {
        "table": "analytics_orders",
        "columns": ["region", "revenue"],
        "limit": 5,
    }
    res = await invoke_mcp_tool("query_postgres", args)
    assert res.success is True
    assert res.tool_name == "query_postgres"
    assert res.result["success"] is True
    assert len(res.result["rows"]) <= 5


@pytest.mark.asyncio
async def test_invoke_mcp_invalid_tool_name():
    res = await invoke_mcp_tool("unregistered_malicious_tool", {})
    assert res.success is False
    assert res.error is not None
