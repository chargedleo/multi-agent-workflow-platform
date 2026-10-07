"""MCP Server and Tool Invocation Layer.

Provides the official Model Context Protocol (MCP) tool boundary between
autonomous agents and backend analytical capabilities.
"""

import inspect
import json
import time
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

from backend.app.analysis.schemas import ToolResult
from backend.app.core.logging import get_logger
from backend.app.mcp.tools.analysis import (
    analyze_dataset_tool,
    get_dataset_schema_tool,
    query_postgres_tool,
)

logger = get_logger(__name__)

# Initialize MCP Server instance
mcp_server = MCPServer("workflow-data-analysis")

# Register approved MCP tools
mcp_server.tool(
    name="analyze_dataset",
    description="Analyze an approved structured dataset (e.g. 'orders') with safe operations: count, sum, mean, min, max, group_by, top_n, sort, descriptive_stats.",
)(analyze_dataset_tool)

mcp_server.tool(
    name="get_dataset_schema",
    description="Inspect the schema, available columns, data types, and total row count of an approved dataset.",
)(get_dataset_schema_tool)

mcp_server.tool(
    name="query_postgres",
    description="Execute structured, parameterized analytical queries against approved PostgreSQL tables (e.g. 'analytics_orders').",
)(query_postgres_tool)


async def invoke_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
    """Invoke an approved MCP tool by name with arguments.
    
    Guarantees:
    - Only registered tools can be executed.
    - Parameter validation against tool schema.
    - Captures timing and returns structured ToolResult.
    """
    start_time = time.perf_counter()
    clean_name = tool_name.strip()

    try:
        call_res = await mcp_server.call_tool(clean_name, arguments)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Extract structured content if provided, or parse text content
        structured_data = getattr(call_res, "structured_content", None)
        if isinstance(structured_data, dict) and "result" in structured_data and isinstance(structured_data["result"], dict):
            structured_data = structured_data["result"]

        if not structured_data and getattr(call_res, "content", None):
            for block in call_res.content:
                text_val = getattr(block, "text", "")
                if text_val:
                    try:
                        parsed_text = json.loads(text_val)
                        if isinstance(parsed_text, dict):
                            structured_data = parsed_text
                        break
                    except Exception:
                        structured_data = {"raw_text": text_val}

        is_error = getattr(call_res, "is_error", False)
        error_msg = None
        if is_error:
            error_msg = str(structured_data.get("error", "Tool execution failed")) if isinstance(structured_data, dict) else "Tool error"
        elif isinstance(structured_data, dict) and structured_data.get("success") is False:
            is_error = True
            error_msg = str(structured_data.get("error") or (structured_data.get("errors") and structured_data["errors"][0]) or "Tool failed")

        return ToolResult(
            tool_name=clean_name,
            success=not is_error,
            result=structured_data if isinstance(structured_data, dict) else {"result": structured_data},
            error=error_msg,
            duration_ms=duration_ms,
        )

    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"MCP tool invocation error for '{clean_name}': {exc}", exc_info=True)
        return ToolResult(
            tool_name=clean_name,
            success=False,
            result={},
            error=str(exc),
            duration_ms=duration_ms,
        )


async def list_registered_mcp_tools() -> List[Dict[str, Any]]:
    """List all registered MCP tools and their schemas."""
    tools = await mcp_server.list_tools()
    results: List[Dict[str, Any]] = []
    for t in tools:
        results.append({
            "name": t.name,
            "description": t.description,
            "parameters": getattr(t, "input_schema", getattr(t, "inputSchema", {})),
        })
    return results
