"""Tests for SQLAlchemy database models and relationships."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.workflow_run import WorkflowRun
from backend.app.db.models.workflow_step import WorkflowStep


@pytest.mark.asyncio
async def test_create_workflow_run_model(db_session: AsyncSession):
    """Verify that WorkflowRun model instances persist and retrieve accurately."""
    req_id = uuid.uuid4()
    run = WorkflowRun(
        id=uuid.uuid4(),
        request_id=req_id,
        user_query="Evaluate microservices vs monolithic architecture",
        status="PENDING",
        metadata_json={"source": "unit_test"},
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    assert run.id is not None
    assert run.request_id == req_id
    assert run.status == "PENDING"
    assert run.metadata_json == {"source": "unit_test"}
    assert run.created_at is not None


@pytest.mark.asyncio
async def test_workflow_run_and_steps_relationship(db_session: AsyncSession):
    """Verify one-to-many relationship between WorkflowRun and WorkflowStep."""
    run = WorkflowRun(
        id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        user_query="Database performance benchmarks",
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.flush()

    step1 = WorkflowStep(
        id=uuid.uuid4(),
        run_id=run.id,
        agent_name="planner",
        step_order=1,
        status="COMPLETED",
        duration_ms=450,
        input_data={"user_query": run.user_query},
        output_data={"goal": "Benchmark DB", "steps": ["Step 1", "Step 2"]},
    )
    step2 = WorkflowStep(
        id=uuid.uuid4(),
        run_id=run.id,
        agent_name="researcher",
        step_order=2,
        status="COMPLETED",
        duration_ms=950,
        input_data={"plan": {"goal": "Benchmark DB"}},
        output_data={"findings": ["High throughput"]},
    )

    db_session.add_all([step1, step2])
    await db_session.commit()
    await db_session.refresh(run)

    # Check relation
    assert len(run.steps) == 2
    assert run.steps[0].agent_name == "planner"
    assert run.steps[1].agent_name == "researcher"
    assert run.steps[0].duration_ms == 450
