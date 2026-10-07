"""Tests for workflow persistence service layer operations."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.workflow_runs import (
    complete_workflow_run,
    complete_workflow_step,
    create_workflow_run,
    create_workflow_step,
    fail_workflow_run,
    fail_workflow_step,
    get_workflow_run,
    get_workflow_run_by_request_id,
    list_workflow_runs,
    start_workflow_run,
)


@pytest.mark.asyncio
async def test_workflow_run_lifecycle_service(db_session: AsyncSession):
    """Verify complete run lifecycle: create -> start -> complete."""
    req_id = uuid.uuid4()
    query = "Compare Kafka and RabbitMQ messaging systems."

    # 1. Create run
    run = await create_workflow_run(db_session, request_id=req_id, user_query=query)
    assert run.status == "PENDING"
    assert run.request_id == req_id
    assert run.started_at is None

    # 2. Start run
    started = await start_workflow_run(db_session, run_id=run.id)
    assert started.status == "RUNNING"
    assert started.started_at is not None

    # 3. Create & complete steps
    step = await create_workflow_step(
        db_session,
        run_id=run.id,
        agent_name="planner",
        step_order=1,
        input_data={"user_query": query},
    )
    assert step.status == "RUNNING"
    completed_step = await complete_workflow_step(
        db_session,
        step_id=step.id,
        output_data={"goal": "Compare brokers", "steps": ["Identify pros", "Identify cons"]},
    )
    assert completed_step.status == "COMPLETED"
    assert completed_step.duration_ms is not None

    # 4. Complete run
    completed_run = await complete_workflow_run(
        db_session,
        run_id=run.id,
        final_answer="Kafka is designed for high-throughput stream retention, RabbitMQ for complex AMQP routing.",
        key_points=["Kafka retains logs", "RabbitMQ routes with exchanges"],
        confidence=0.96,
        plan={"goal": "Compare brokers"},
        research_results={"findings": ["Stream processing vs queuing"]},
    )
    assert completed_run.status == "COMPLETED"
    assert completed_run.duration_ms is not None
    assert completed_run.confidence == 0.96
    assert completed_run.completed_at is not None


@pytest.mark.asyncio
async def test_workflow_run_failure_service(db_session: AsyncSession):
    """Verify failure lifecycle: create -> start -> fail step -> fail run."""
    req_id = uuid.uuid4()
    run = await create_workflow_run(db_session, request_id=req_id, user_query="Fault tolerance test")
    await start_workflow_run(db_session, run_id=run.id)

    step = await create_workflow_step(db_session, run_id=run.id, agent_name="planner", step_order=1)
    failed_step = await fail_workflow_step(db_session, step_id=step.id, error_message="LLM timeout")
    assert failed_step.status == "FAILED"
    assert failed_step.error == "LLM timeout"

    failed_run = await fail_workflow_run(
        db_session,
        run_id=run.id,
        errors=["Planner step failed: LLM timeout"],
    )
    assert failed_run.status == "FAILED"
    assert failed_run.errors == ["Planner step failed: LLM timeout"]
    assert failed_run.duration_ms is not None


@pytest.mark.asyncio
async def test_list_and_get_workflow_runs(db_session: AsyncSession):
    """Verify paginated listing and fetching run details with steps."""
    for i in range(3):
        r = await create_workflow_run(
            db_session,
            request_id=uuid.uuid4(),
            user_query=f"Query {i+1}",
        )
        await start_workflow_run(db_session, run_id=r.id)
        await complete_workflow_run(
            db_session,
            run_id=r.id,
            final_answer=f"Answer {i+1}",
            key_points=[f"Key Point {i+1}"],
            confidence=0.9,
        )

    items, total = await list_workflow_runs(db_session, page=1, page_size=2)
    assert len(items) == 2
    assert total >= 3

    # Test single fetch with steps
    fetched = await get_workflow_run(db_session, run_id=items[0].id)
    assert fetched is not None
    assert fetched.id == items[0].id
