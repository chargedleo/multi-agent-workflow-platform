"""Unit tests for Data Analysis Agent."""

import pytest
from backend.app.agents.data_analysis import data_analysis_agent
from backend.app.graph.state import create_initial_state


@pytest.mark.asyncio
async def test_data_analysis_not_required():
    state = create_initial_state(
        query="Compare PostgreSQL and MongoDB architecture for SaaS startups.",
        request_id="test-req-001",
    )
    res = await data_analysis_agent(state)
    assert "analysis_results" in res
    assert res["analysis_results"]["status"] == "not_required"


@pytest.mark.asyncio
async def test_data_analysis_required_count_orders():
    state = create_initial_state(
        query="How many orders are in the dataset?",
        request_id="test-req-002",
    )
    res = await data_analysis_agent(state)
    assert "analysis_results" in res
    analysis = res["analysis_results"]
    assert analysis["status"] == "completed"
    assert analysis["tool_name"] == "analyze_dataset"
    assert analysis["metrics"]["count"] == 20


@pytest.mark.asyncio
async def test_data_analysis_required_revenue_by_region():
    state = create_initial_state(
        query="What is the total revenue by region?",
        request_id="test-req-003",
    )
    res = await data_analysis_agent(state)
    assert "analysis_results" in res
    analysis = res["analysis_results"]
    assert analysis["status"] == "completed"
    assert len(analysis["rows"]) == 4
    assert analysis["metrics"]["total_revenue_sum"] == 177650.0


@pytest.mark.asyncio
async def test_data_analysis_required_top_products():
    state = create_initial_state(
        query="What are the top 5 products by revenue?",
        request_id="test-req-004",
    )
    res = await data_analysis_agent(state)
    assert "analysis_results" in res
    analysis = res["analysis_results"]
    assert analysis["status"] == "completed"
    assert len(analysis["rows"]) == 5


@pytest.mark.asyncio
async def test_data_analysis_tool_error_graceful_handling():
    # Query mentions profit which is not in dataset
    state = create_initial_state(
        query="What is the total profit by region?",
        request_id="test-req-005",
    )
    res = await data_analysis_agent(state)
    assert "analysis_results" in res
    analysis = res["analysis_results"]
    assert analysis["status"] == "failed"
    assert "profit" in str(analysis["error"])
    assert len(res["errors"]) > 0
