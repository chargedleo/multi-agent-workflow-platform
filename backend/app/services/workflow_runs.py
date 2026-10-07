"""Workflow Run and Step Persistence Service Layer.

Handles database transactions for workflow run lifecycles, individual agent
execution steps, status transitions, and run history queries.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.models.workflow_run import WorkflowRun
from backend.app.db.models.workflow_step import WorkflowStep

logger = get_logger(__name__)


def _to_uuid(val: Union[str, uuid.UUID]) -> uuid.UUID:
    """Ensure value is a UUID instance."""
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


async def create_workflow_run(
    session: AsyncSession,
    request_id: Union[str, uuid.UUID],
    user_query: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkflowRun:
    """Create a new workflow run record with PENDING status."""
    req_uuid = _to_uuid(request_id)
    run = WorkflowRun(
        id=uuid.uuid4(),
        request_id=req_uuid,
        user_query=user_query,
        status="PENDING",
        metadata_json=metadata or {},
        errors=[],
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    logger.info(format_log_msg(f"Persisted workflow run {run.id} (status: PENDING)", str(req_uuid)))
    return run


async def start_workflow_run(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
) -> Optional[WorkflowRun]:
    """Transition a workflow run to RUNNING and record started_at timestamp."""
    run_uuid = _to_uuid(run_id)
    run = await session.get(WorkflowRun, run_uuid)
    if not run:
        return None

    run.status = "RUNNING"
    run.started_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(run)
    logger.info(format_log_msg(f"Updated workflow run {run.id} status to RUNNING", str(run.request_id)))
    return run


async def complete_workflow_run(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
    final_answer: str,
    key_points: List[str],
    confidence: float,
    plan: Optional[Dict[str, Any]] = None,
    research_results: Optional[Dict[str, Any]] = None,
    errors: Optional[List[str]] = None,
) -> Optional[WorkflowRun]:
    """Transition a workflow run to COMPLETED and record outputs and duration."""
    run_uuid = _to_uuid(run_id)
    run = await session.get(WorkflowRun, run_uuid)
    if not run:
        return None

    now = datetime.now(timezone.utc)
    run.completed_at = now
    if run.started_at:
        delta = now - run.started_at
        run.duration_ms = int(delta.total_seconds() * 1000)

    run.status = "COMPLETED"
    run.final_answer = final_answer
    run.key_points = key_points
    run.confidence = confidence
    if plan:
        run.plan = plan
    if research_results:
        run.research_results = research_results
    if errors is not None:
        run.errors = errors

    await session.commit()
    await session.refresh(run)
    logger.info(
        format_log_msg(
            f"Completed workflow run {run.id} in {run.duration_ms}ms (confidence: {confidence})",
            str(run.request_id),
        )
    )
    return run


async def fail_workflow_run(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
    errors: List[str],
    final_answer: Optional[str] = None,
    plan: Optional[Dict[str, Any]] = None,
    research_results: Optional[Dict[str, Any]] = None,
) -> Optional[WorkflowRun]:
    """Transition a workflow run to FAILED and record error details."""
    run_uuid = _to_uuid(run_id)
    run = await session.get(WorkflowRun, run_uuid)
    if not run:
        return None

    now = datetime.now(timezone.utc)
    run.completed_at = now
    if run.started_at:
        delta = now - run.started_at
        run.duration_ms = int(delta.total_seconds() * 1000)

    run.status = "FAILED"
    run.errors = errors
    if final_answer:
        run.final_answer = final_answer
    if plan:
        run.plan = plan
    if research_results:
        run.research_results = research_results

    await session.commit()
    await session.refresh(run)
    logger.error(
        format_log_msg(
            f"Marked workflow run {run.id} as FAILED after {run.duration_ms}ms: {errors}",
            str(run.request_id),
        )
    )
    return run


async def create_workflow_step(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
    agent_name: str,
    step_order: int,
    input_data: Optional[Dict[str, Any]] = None,
) -> WorkflowStep:
    """Create and start a workflow agent step record with RUNNING status."""
    run_uuid = _to_uuid(run_id)
    step = WorkflowStep(
        id=uuid.uuid4(),
        run_id=run_uuid,
        agent_name=agent_name,
        step_order=step_order,
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
        input_data=input_data,
    )
    session.add(step)
    await session.commit()
    await session.refresh(step)
    return step


async def complete_workflow_step(
    session: AsyncSession,
    step_id: Union[str, uuid.UUID],
    output_data: Dict[str, Any],
) -> Optional[WorkflowStep]:
    """Transition a workflow step to COMPLETED, recording output data and duration."""
    step_uuid = _to_uuid(step_id)
    step = await session.get(WorkflowStep, step_uuid)
    if not step:
        return None

    now = datetime.now(timezone.utc)
    step.completed_at = now
    if step.started_at:
        delta = now - step.started_at
        step.duration_ms = int(delta.total_seconds() * 1000)

    step.status = "COMPLETED"
    step.output_data = output_data
    await session.commit()
    await session.refresh(step)
    return step


async def fail_workflow_step(
    session: AsyncSession,
    step_id: Union[str, uuid.UUID],
    error_message: str,
) -> Optional[WorkflowStep]:
    """Transition a workflow step to FAILED, recording error and duration."""
    step_uuid = _to_uuid(step_id)
    step = await session.get(WorkflowStep, step_uuid)
    if not step:
        return None

    now = datetime.now(timezone.utc)
    step.completed_at = now
    if step.started_at:
        delta = now - step.started_at
        step.duration_ms = int(delta.total_seconds() * 1000)

    step.status = "FAILED"
    step.error = error_message
    await session.commit()
    await session.refresh(step)
    return step


async def get_workflow_run(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
) -> Optional[WorkflowRun]:
    """Retrieve a workflow run by run_id with all its steps eagerly loaded."""
    try:
        run_uuid = _to_uuid(run_id)
    except (ValueError, TypeError):
        return None

    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.id == run_uuid)
        .options(selectinload(WorkflowRun.steps))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_workflow_run_by_request_id(
    session: AsyncSession,
    request_id: Union[str, uuid.UUID],
) -> Optional[WorkflowRun]:
    """Retrieve a workflow run by request_id."""
    try:
        req_uuid = _to_uuid(request_id)
    except (ValueError, TypeError):
        return None

    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.request_id == req_uuid)
        .options(selectinload(WorkflowRun.steps))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_workflow_runs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[WorkflowRun], int]:
    """Return paginated list of workflow runs and total count."""
    safe_page = max(1, page)
    safe_limit = max(1, min(100, page_size))
    offset = (safe_page - 1) * safe_limit

    # Count query
    count_stmt = select(func.count(WorkflowRun.id))
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Query items without loading all steps for optimal list performance
    stmt = (
        select(WorkflowRun)
        .order_by(desc(WorkflowRun.created_at))
        .offset(offset)
        .limit(safe_limit)
    )
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    return items, total
