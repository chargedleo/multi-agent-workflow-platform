"""End-to-end tests for Milestone 4: Data Analysis Agent and LangGraph workflow."""

import pytest
from backend.app.graph.workflow import run_workflow
from backend.app.services.workflow_runs import get_workflow_run


@pytest.mark.asyncio
async def test_workflow_non_analytical_skips_analysis(db_session):
    """Verify that conceptual/architectural queries skip data analysis cleanly."""
    query = "Compare PostgreSQL and MongoDB architecture for high-volume SaaS applications."
    state = await run_workflow(query=query)

    assert state.get("status") == "COMPLETED"
    assert state.get("final_answer") is not None
    analysis = state.get("analysis_results")
    assert analysis is not None
    assert analysis.get("status") == "not_required"

    # Verify run persistence in DB
    run_id = state.get("run_id")
    assert run_id is not None
    run_record = await get_workflow_run(db_session, run_id=run_id)
    assert run_record is not None
    step_names = [s.agent_name for s in run_record.steps]
    assert "data_analysis" in step_names
    da_step = next(s for s in run_record.steps if s.agent_name == "data_analysis")
    assert da_step.status == "COMPLETED"
    assert da_step.output_data.get("analysis_required") is False


@pytest.mark.asyncio
async def test_workflow_simple_analytical_query(db_session):
    """Verify that analytical query executes data analysis agent and returns exact figures."""
    query = "How many orders are in the dataset?"
    state = await run_workflow(query=query)

    assert state.get("status") == "COMPLETED"
    analysis = state.get("analysis_results")
    assert analysis is not None
    assert analysis.get("status") == "completed"
    assert analysis.get("tool_name") == "analyze_dataset"
    assert analysis.get("metrics", {}).get("count") == 20

    # Ensure final answer contains data analysis findings
    final_ans = state.get("final_answer", {})
    assert "analysis_results" in final_ans
    assert "20" in final_ans.get("answer", "") or "orders" in final_ans.get("answer", "").lower()

    # Verify step persistence
    run_id = state.get("run_id")
    run_record = await get_workflow_run(db_session, run_id=run_id)
    da_step = next(s for s in run_record.steps if s.agent_name == "data_analysis")
    assert da_step.status == "COMPLETED"
    assert da_step.output_data.get("tool_name") == "analyze_dataset"


@pytest.mark.asyncio
async def test_workflow_aggregation_query(db_session):
    """Verify regional aggregation query via workflow."""
    query = "What is the total revenue by region?"
    state = await run_workflow(query=query)

    assert state.get("status") == "COMPLETED"
    analysis = state.get("analysis_results")
    assert analysis is not None
    assert analysis.get("status") == "completed"
    assert len(analysis.get("rows", [])) == 4
    assert analysis.get("metrics", {}).get("total_revenue_sum") == 177650.0


@pytest.mark.asyncio
async def test_workflow_top_n_query(db_session):
    """Verify top products query via workflow."""
    query = "What are the top 5 products by revenue?"
    state = await run_workflow(query=query)

    assert state.get("status") == "COMPLETED"
    analysis = state.get("analysis_results")
    assert analysis is not None
    assert analysis.get("status") == "completed"
    assert len(analysis.get("rows", [])) == 5


@pytest.mark.asyncio
async def test_workflow_combined_document_and_analysis_query(db_session):
    """Verify combined document retrieval and analytical query."""
    query = "What does the architecture document say about Section 2, and what is the total revenue by region in our dataset?"
    state = await run_workflow(query=query)

    assert state.get("status") == "COMPLETED"
    # Should have both retrieved documents (or retrieval attempted) and completed analysis
    analysis = state.get("analysis_results")
    assert analysis is not None
    assert analysis.get("status") == "completed"


@pytest.mark.asyncio
async def test_workflow_invalid_analysis_column_graceful(db_session):
    """Verify that an invalid column query produces a structured error without crashing workflow."""
    query = "What is the total profit by region in our orders dataset?"
    state = await run_workflow(query=query)

    # Workflow handles the error gracefully
    analysis = state.get("analysis_results")
    assert analysis is not None
    assert analysis.get("status") == "failed"
    assert "profit" in str(analysis.get("error", ""))

    run_id = state.get("run_id")
    run_record = await get_workflow_run(db_session, run_id=run_id)
    da_step = next(s for s in run_record.steps if s.agent_name == "data_analysis")
    assert da_step.status == "FAILED"
    assert "profit" in str(da_step.error or "")
