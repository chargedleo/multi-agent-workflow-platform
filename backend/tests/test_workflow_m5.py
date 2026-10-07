"""End-to-end and integration tests for Milestone 5: Multi-Agent Validation Guardrails."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.graph.workflow import run_workflow
from backend.app.services.workflow_runs import get_workflow_run
from backend.app.validation.schemas import ValidationStatus


@pytest.mark.asyncio
async def test_workflow_m5_end_to_end_validation_pass(db_session: AsyncSession):
    """Verify that a standard query runs through all 6 agents and validation passes."""
    req_id = str(uuid.uuid4())
    query = "What is the total revenue in the orders dataset?"

    state = await run_workflow(query=query, request_id=req_id)
    run_id = state.get("run_id")

    assert run_id is not None
    assert state.get("status") == "COMPLETED"

    # Validation state verification
    val_res = state.get("validation_results")
    assert val_res is not None
    assert val_res.get("status") == ValidationStatus.PASS
    assert val_res.get("score", 0.0) >= 0.8
    assert val_res.get("failed_items") == 0

    # Persistence verification
    run = await get_workflow_run(db_session, run_id=run_id)
    assert run is not None
    assert run.status == "COMPLETED"
    assert run.validation_status == "PASS"
    assert run.validation_score is not None
    assert run.validation_score >= 0.8

    # Verify all 6 agent steps are recorded
    step_agents = [step.agent_name for step in run.steps]
    assert "planner" in step_agents
    assert "document_retrieval" in step_agents
    assert "data_analysis" in step_agents
    assert "researcher" in step_agents
    assert "responder" in step_agents
    assert "validation" in step_agents

    # Verify validation step specifically
    val_step = next(s for s in run.steps if s.agent_name == "validation")
    assert val_step.status == "COMPLETED"
    assert val_step.step_order >= 6
    assert val_step.output_data is not None
    assert val_step.output_data.get("status") == "PASS"


@pytest.mark.asyncio
async def test_workflow_m5_bounded_correction_loop(db_session: AsyncSession):
    """Verify that a recoverable claim error triggers a bounded correction loop and succeeds on attempt 2."""
    req_id = str(uuid.uuid4())
    # synthetic_incorrect_revenue hook produces $190,000 on attempt 1, and corrects to $177,650 on retry with feedback
    query = "synthetic_incorrect_revenue: Total revenue across the company"

    state = await run_workflow(query=query, request_id=req_id)
    run_id = state.get("run_id")

    assert run_id is not None
    assert state.get("status") == "COMPLETED"

    val_res = state.get("validation_results")
    assert val_res is not None
    # Corrected on attempt 2
    assert val_res.get("attempt") == 2
    assert val_res.get("status") == ValidationStatus.PASS

    # Verify execution history recorded the correction loop
    val_history = state.get("validation_history", [])
    assert len(val_history) >= 2
    # First attempt flagged recoverable issues
    assert val_history[0].get("status") == ValidationStatus.RECOVERABLE
    # Second attempt succeeded
    assert val_history[1].get("status") == ValidationStatus.PASS

    # Verify database step persistence reflects both attempts
    run = await get_workflow_run(db_session, run_id=run_id)
    assert run is not None
    steps = run.steps
    responder_steps = [s for s in steps if s.agent_name == "responder"]
    validation_steps = [s for s in steps if s.agent_name == "validation"]
    assert len(responder_steps) >= 2
    assert len(validation_steps) >= 2


@pytest.mark.asyncio
async def test_workflow_m5_unrecoverable_failure_termination(db_session: AsyncSession):
    """Verify that permanent invalid claims terminate without infinite loops and persist failure."""
    req_id = str(uuid.uuid4())
    # synthetic_permanent_invalid produces $999,000 permanently and will fail all validation attempts
    query = "synthetic_permanent_invalid: Unverifiable revenue claim"

    state = await run_workflow(query=query, request_id=req_id)
    run_id = state.get("run_id")

    assert run_id is not None
    assert state.get("status") == "FAILED"

    val_res = state.get("validation_results")
    assert val_res is not None
    assert val_res.get("status") in (ValidationStatus.FAIL, ValidationStatus.BLOCKED)

    # Database record reflects FAILED status
    run = await get_workflow_run(db_session, run_id=run_id)
    assert run is not None
    assert run.status == "FAILED"
    assert run.validation_status in ("FAIL", "BLOCKED")


@pytest.mark.asyncio
async def test_workflow_m5_validation_disabled_mode(monkeypatch):
    """Verify that when VALIDATION_ENABLED is False, validation completes immediately."""
    settings = get_settings()
    monkeypatch.setattr(settings, "VALIDATION_ENABLED", False)

    req_id = str(uuid.uuid4())
    query = "What is the revenue breakdown?"

    state = await run_workflow(query=query, request_id=req_id)
    assert state.get("status") == "COMPLETED"
    val_res = state.get("validation_results")
    assert val_res is not None
    assert val_res.get("status") == ValidationStatus.PASS


@pytest.mark.asyncio
async def test_workflow_api_returns_validation_fields(async_client: AsyncClient):
    """Verify POST and GET workflow endpoints expose validation, status, and score."""
    post_res = await async_client.post(
        "/api/v1/workflows",
        json={"query": "Calculate the total revenue from orders"},
    )
    assert post_res.status_code == 200
    data = post_res.json()

    assert "validation" in data
    assert "validation_status" in data
    assert "validation_score" in data
    assert data["validation_status"] == "PASS"
    assert data["validation_score"] is not None
    assert data["validation_score"] >= 0.8
    assert data["validation"]["checked_items"] > 0

    run_id = data["run_id"]

    # Verify detail GET endpoint
    detail_res = await async_client.get(f"/api/v1/workflows/{run_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()

    assert detail_data["validation_status"] == "PASS"
    assert detail_data["validation_score"] is not None
    assert detail_data["validation"] is not None
    assert "issues" in detail_data["validation"]

    # Verify validation is in steps list
    step_names = [s["agent_name"] for s in detail_data["steps"]]
    assert "validation" in step_names
