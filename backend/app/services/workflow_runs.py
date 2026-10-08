"""Workflow Run and Step Persistence Service Layer.

Handles database transactions for workflow run lifecycles, individual agent
execution steps, status transitions, and run history queries.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from sqlalchemy import and_, case, cast, desc, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.models.workflow_approval import WorkflowApproval
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
    sources: Optional[List[Dict[str, Any]]] = None,
    analysis_results: Optional[Dict[str, Any]] = None,
    validation_results: Optional[Dict[str, Any]] = None,
    approval_status: Optional[str] = None,
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
    if approval_status:
        run.approval_status = approval_status
    run.final_answer = final_answer
    run.key_points = key_points
    run.confidence = confidence
    if plan:
        run.plan = plan
    if research_results:
        run.research_results = research_results
    if errors is not None:
        run.errors = errors

    if validation_results is not None:
        run.validation_status = validation_results.get("status")
        run.validation_score = validation_results.get("score")

    if sources is not None or analysis_results is not None or validation_results is not None:
        meta = dict(run.metadata_json or {})
        if sources is not None:
            meta["sources"] = sources
        if analysis_results is not None:
            meta["analysis_results"] = analysis_results
        if validation_results is not None:
            meta["validation"] = validation_results
            meta["validation_results"] = validation_results
        run.metadata_json = meta

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
    validation_results: Optional[Dict[str, Any]] = None,
    approval_status: Optional[str] = None,
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
    if approval_status:
        run.approval_status = approval_status
    run.errors = errors
    if final_answer:
        run.final_answer = final_answer
    if plan:
        run.plan = plan
    if research_results:
        run.research_results = research_results

    if validation_results is not None:
        run.validation_status = validation_results.get("status")
        run.validation_score = validation_results.get("score")
        meta = dict(run.metadata_json or {})
        meta["validation"] = validation_results
        meta["validation_results"] = validation_results
        run.metadata_json = meta

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
    """Retrieve a workflow run by run_id with all its steps and approvals eagerly loaded."""
    try:
        run_uuid = _to_uuid(run_id)
    except (ValueError, TypeError):
        return None

    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.id == run_uuid)
        .options(
            selectinload(WorkflowRun.steps),
            selectinload(WorkflowRun.approvals),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_workflow_run_by_request_id(
    session: AsyncSession,
    request_id: Union[str, uuid.UUID],
) -> Optional[WorkflowRun]:
    """Retrieve a workflow run by request_id with steps and approvals."""
    try:
        req_uuid = _to_uuid(request_id)
    except (ValueError, TypeError):
        return None

    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.request_id == req_uuid)
        .options(
            selectinload(WorkflowRun.steps),
            selectinload(WorkflowRun.approvals),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_workflow_runs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[WorkflowRun], int]:
    """Return paginated list of workflow runs and total count with optional filtering."""
    safe_page = max(1, page)
    safe_limit = max(1, min(100, page_size))
    offset = (safe_page - 1) * safe_limit

    filters = []
    if status and status.strip():
        norm_status = status.strip().upper()
        if norm_status != "ALL":
            if norm_status == "ACTIVE":
                filters.append(WorkflowRun.status.in_(["RUNNING", "PENDING"]))
            elif norm_status in ("WAITING_FOR_APPROVAL", "AWAITING_APPROVAL"):
                filters.append(WorkflowRun.status == "WAITING_FOR_APPROVAL")
            elif norm_status == "REJECTED":
                filters.append(or_(WorkflowRun.approval_status == "REJECTED", WorkflowRun.status == "CANCELLED"))
            else:
                filters.append(or_(WorkflowRun.status == norm_status, WorkflowRun.approval_status == norm_status))

    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                WorkflowRun.user_query.ilike(term),
                cast(WorkflowRun.id, String).ilike(term),
                cast(WorkflowRun.request_id, String).ilike(term),
            )
        )

    # Count query
    count_stmt = select(func.count(WorkflowRun.id))
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Query items without loading all steps for optimal list performance
    stmt = (
        select(WorkflowRun)
        .order_by(desc(WorkflowRun.created_at))
        .offset(offset)
        .limit(safe_limit)
    )
    if filters:
        stmt = stmt.where(and_(*filters))
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    return items, total


async def get_workflow_stats(session: AsyncSession) -> Dict[str, Any]:
    """Calculate aggregated workflow metrics across all persisted runs."""
    stmt = select(
        func.count(WorkflowRun.id).label("total_runs"),
        func.count(case((WorkflowRun.status.in_(["RUNNING", "PENDING"]), 1))).label("active_runs"),
        func.count(case((WorkflowRun.status == "WAITING_FOR_APPROVAL", 1))).label("awaiting_approval"),
        func.count(case((WorkflowRun.status == "COMPLETED", 1))).label("completed_runs"),
        func.count(case((WorkflowRun.status == "FAILED", 1))).label("failed_runs"),
        func.count(
            case((or_(WorkflowRun.approval_status == "REJECTED", WorkflowRun.status == "CANCELLED"), 1))
        ).label("rejected_runs"),
        func.avg(case((WorkflowRun.status == "COMPLETED", WorkflowRun.duration_ms))).label("avg_duration_ms"),
    )
    res = await session.execute(stmt)
    row = res.one()
    avg_dur = float(row.avg_duration_ms) if row.avg_duration_ms is not None else None
    return {
        "total_runs": int(row.total_runs or 0),
        "active_runs": int(row.active_runs or 0),
        "awaiting_approval": int(row.awaiting_approval or 0),
        "completed_runs": int(row.completed_runs or 0),
        "failed_runs": int(row.failed_runs or 0),
        "rejected_runs": int(row.rejected_runs or 0),
        "avg_duration_ms": round(avg_dur, 1) if avg_dur is not None else None,
    }


async def update_workflow_run_approval_status(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
    status: str,
    approval_status: str,
) -> Optional[WorkflowRun]:
    """Update workflow run execution status and approval_status."""
    run_uuid = _to_uuid(run_id)
    run = await session.get(WorkflowRun, run_uuid)
    if not run:
        return None
    run.status = status
    run.approval_status = approval_status
    await session.commit()
    await session.refresh(run)
    return run


async def create_approval_request(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
    revision_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkflowApproval:
    """Create a new human approval request for a workflow run and update run status."""
    run_uuid = _to_uuid(run_id)
    approval = WorkflowApproval(
        id=uuid.uuid4(),
        workflow_run_id=run_uuid,
        status="PENDING",
        requested_at=datetime.now(timezone.utc),
        revision_count=revision_count,
        metadata_json=metadata or {},
    )
    session.add(approval)

    run = await session.get(WorkflowRun, run_uuid)
    if run:
        run.status = "WAITING_FOR_APPROVAL"
        run.approval_status = "PENDING"

    await session.commit()
    await session.refresh(approval)
    logger.info(
        format_log_msg(
            f"Created approval request {approval.id} for run {run_uuid} (revision: {revision_count})",
            str(run.request_id) if run else "unknown",
        )
    )
    return approval


async def record_approval_decision(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
    decision: str,
    feedback: Optional[str] = None,
    decided_by: Optional[str] = "human_reviewer",
) -> Optional[WorkflowApproval]:
    """Record a human decision on the pending approval request for a workflow run."""
    run_uuid = _to_uuid(run_id)
    stmt = (
        select(WorkflowApproval)
        .where(
            WorkflowApproval.workflow_run_id == run_uuid,
            WorkflowApproval.status == "PENDING",
        )
        .order_by(desc(WorkflowApproval.requested_at))
    )
    result = await session.execute(stmt)
    approval = result.scalars().first()
    if not approval:
        return None

    dec_upper = decision.upper()
    now = datetime.now(timezone.utc)
    status_map = {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "CHANGES_REQUESTED": "CHANGES_REQUESTED",
    }
    app_status = status_map.get(dec_upper, dec_upper)
    approval.status = app_status
    approval.decision = dec_upper
    approval.feedback = feedback
    approval.decided_by = decided_by
    approval.decided_at = now

    run = await session.get(WorkflowRun, run_uuid)
    if run:
        run.approval_status = app_status
        if dec_upper == "REJECT":
            run.status = "FAILED"
        elif dec_upper == "CHANGES_REQUESTED":
            run.status = "RUNNING"
        elif dec_upper == "APPROVE":
            run.status = "RUNNING"

    await session.commit()
    await session.refresh(approval)
    return approval


async def get_pending_approvals(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve all workflow runs currently awaiting human approval."""
    safe_page = max(1, page)
    safe_limit = max(1, min(100, page_size))
    offset = (safe_page - 1) * safe_limit

    count_stmt = select(func.count(WorkflowApproval.id)).where(WorkflowApproval.status == "PENDING")
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        select(WorkflowApproval, WorkflowRun)
        .join(WorkflowRun, WorkflowApproval.workflow_run_id == WorkflowRun.id)
        .where(WorkflowApproval.status == "PENDING")
        .order_by(desc(WorkflowApproval.requested_at))
        .offset(offset)
        .limit(safe_limit)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = []
    for app_row, run_row in rows:
        items.append({
            "approval_id": str(app_row.id),
            "run_id": str(run_row.id),
            "request_id": str(run_row.request_id),
            "query": run_row.user_query,
            "status": app_row.status,
            "requested_at": app_row.requested_at,
            "revision_count": app_row.revision_count,
            "validation_status": run_row.validation_status,
            "validation_score": run_row.validation_score,
        })

    return items, total


async def get_workflow_approvals_for_run(
    session: AsyncSession,
    run_id: Union[str, uuid.UUID],
) -> List[WorkflowApproval]:
    """Retrieve all approval records for a given workflow run."""
    run_uuid = _to_uuid(run_id)
    stmt = (
        select(WorkflowApproval)
        .where(WorkflowApproval.workflow_run_id == run_uuid)
        .order_by(WorkflowApproval.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
