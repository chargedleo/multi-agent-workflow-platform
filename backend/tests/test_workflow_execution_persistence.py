"""Tests verifying that LangGraph execution genuinely writes run and step records to PostgreSQL."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.graph.workflow import run_workflow
from backend.app.services.workflow_runs import get_workflow_run


@pytest.mark.asyncio
async def test_langgraph_execution_creates_durable_records(db_session: AsyncSession):
    """Verify that a full LangGraph run creates workflow_run and 3 workflow_steps records."""
    query = "Compare PostgreSQL and MongoDB for a SaaS startup."
    req_id = str(uuid.uuid4())

    state = await run_workflow(query=query, request_id=req_id)
    run_id = state.get("run_id")

    assert run_id is not None
    assert state.get("status") == "COMPLETED"

    # Query the database directly to confirm persistence
    run = await get_workflow_run(db_session, run_id=run_id)
    assert run is not None
    assert str(run.request_id) == req_id
    assert run.status == "COMPLETED"
    assert run.user_query == query
    assert run.final_answer is not None
    assert len(run.key_points) >= 1
    assert run.confidence is not None
    assert run.duration_ms is not None and run.duration_ms >= 0
    assert run.started_at is not None
    assert run.completed_at is not None

    # Verify all 3 agent steps persisted
    step_agents = [step.agent_name for step in run.steps]
    assert "planner" in step_agents
    assert "researcher" in step_agents
    assert "responder" in step_agents

    for step in run.steps:
        assert step.status == "COMPLETED"
        assert step.duration_ms is not None
        assert step.output_data is not None


@pytest.mark.asyncio
async def test_langgraph_agent_failure_persists_failed_status(db_session: AsyncSession, monkeypatch):
    """Verify that an agent failure persists status=FAILED on run and records step error."""
    import backend.app.graph.workflow as workflow_module

    async def failing_researcher(state):
        return {
            "errors": ["External API rate limit exceeded in researcher"],
            "intermediate_results": [{"agent": "researcher", "error": "Rate limit exceeded"}],
        }

    monkeypatch.setattr(workflow_module, "research_agent", failing_researcher)

    # Rebuild graph to bind monkeypatched node
    test_graph = workflow_module.build_workflow_graph()
    monkeypatch.setattr(workflow_module, "compiled_workflow", test_graph)

    req_id = str(uuid.uuid4())
    state = await run_workflow(query="Will fail in research step", request_id=req_id)
    run_id = state.get("run_id")

    assert run_id is not None
    assert state.get("status") == "FAILED"

    # Check database status
    run = await get_workflow_run(db_session, run_id=run_id)
    assert run is not None
    assert run.status == "FAILED"
    assert any("rate limit exceeded" in err.lower() for err in run.errors)
