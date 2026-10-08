"""Workflow execution and history API routes."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.session import get_db
from backend.app.graph.workflow import resume_workflow, run_workflow
from backend.app.models.schemas import (
    ApprovalDecisionRequest,
    ApprovalRecordResponse,
    WorkflowAPIResponse,
    WorkflowApprovalDetailResponse,
    WorkflowRequest,
    WorkflowRunDetailResponse,
    WorkflowRunListResponse,
    WorkflowRunSummary,
    WorkflowStatsResponse,
    WorkflowStepDetail,
)
from backend.app.services.workflow_runs import (
    get_workflow_run,
    get_workflow_stats,
    list_workflow_runs,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


def _format_approval_record(app) -> ApprovalRecordResponse:
    """Helper to convert WorkflowApproval ORM entity to ApprovalRecordResponse schema."""
    return ApprovalRecordResponse(
        id=str(app.id),
        workflow_run_id=str(app.workflow_run_id),
        status=app.status,
        requested_at=app.requested_at,
        decided_at=app.decided_at,
        decided_by=app.decided_by,
        decision=app.decision,
        feedback=app.feedback,
        revision_count=app.revision_count,
        metadata=app.metadata_json or {},
    )


def _build_run_detail_response(run) -> WorkflowRunDetailResponse:
    """Helper to convert WorkflowRun ORM entity to WorkflowRunDetailResponse schema."""
    steps = [
        WorkflowStepDetail(
            id=str(step.id),
            agent_name=step.agent_name,
            step_order=step.step_order,
            status=step.status,
            started_at=step.started_at,
            completed_at=step.completed_at,
            duration_ms=step.duration_ms,
            input_data=step.input_data,
            output_data=step.output_data,
            error=step.error,
        )
        for step in (run.steps or [])
    ]

    approvals = [_format_approval_record(a) for a in (run.approvals or [])]

    sources = (run.metadata_json or {}).get("sources", [])
    analysis_results = (run.metadata_json or {}).get("analysis_results")
    validation_data = (run.metadata_json or {}).get("validation")

    return WorkflowRunDetailResponse(
        run_id=str(run.id),
        request_id=str(run.request_id),
        status=run.status,
        approval_status=run.approval_status,
        query=run.user_query,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        plan=run.plan,
        research_results=run.research_results,
        answer=run.final_answer,
        key_points=run.key_points or [],
        confidence=run.confidence,
        sources=sources,
        analysis_results=analysis_results,
        validation=validation_data,
        validation_status=run.validation_status,
        validation_score=run.validation_score,
        errors=run.errors or [],
        metadata=run.metadata_json or {},
        steps=steps,
        approvals=approvals,
    )


@router.post(
    "",
    response_model=WorkflowAPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute multi-agent workflow",
    description="Submits a query through the Planner -> Document Retrieval -> Data Analysis -> Researcher -> Responder -> Validation -> Human Approval workflow, persisting run records in PostgreSQL.",
)
async def create_workflow_run_endpoint(payload: WorkflowRequest) -> WorkflowAPIResponse:
    """Submit a query to the multi-agent workflow pipeline with durable persistence."""
    request_id = str(uuid.uuid4())
    logger.info(format_log_msg(f"Initiating workflow execution via API: '{payload.query[:60]}...'", request_id))

    try:
        final_state = await run_workflow(query=payload.query, request_id=request_id)
        final_answer = final_state.get("final_answer")
        errors = final_state.get("errors", [])
        run_id = final_state.get("run_id")
        run_status = final_state.get("status", "completed" if final_answer else "failed")
        app_status = final_state.get("approval_status")

        if not final_answer:
            error_details = "; ".join(errors) if errors else "Workflow did not yield a valid final answer"
            logger.error(format_log_msg(f"Workflow execution produced no answer: {error_details}", request_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow failed to complete: {error_details}",
            )

        analysis_data = final_state.get("analysis_results") or final_answer.get("analysis_results")
        validation_data = final_state.get("validation_results")
        val_status = validation_data.get("status") if isinstance(validation_data, dict) else None
        val_score = validation_data.get("score") if isinstance(validation_data, dict) else None

        return WorkflowAPIResponse(
            request_id=request_id,
            run_id=run_id,
            status=run_status.lower(),
            answer=final_answer.get("answer", ""),
            key_points=final_answer.get("key_points", []),
            confidence=final_answer.get("confidence", 0.0),
            sources=final_answer.get("sources", []),
            analysis_results=analysis_data,
            validation=validation_data,
            validation_status=val_status,
            validation_score=val_score,
            approval_status=app_status,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as exc:
        err_str = f"Unexpected failure while processing workflow: {str(exc)}"
        logger.error(format_log_msg(err_str, request_id), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while executing the multi-agent workflow.",
        )


@router.get(
    "/stats",
    response_model=WorkflowStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated workflow metrics",
    description="Returns high-level statistics across all workflow runs: total, active, awaiting approval, completed, failed, rejected, and average execution duration.",
)
async def get_workflow_stats_endpoint(
    session: AsyncSession = Depends(get_db),
) -> WorkflowStatsResponse:
    """Retrieve aggregated execution statistics for the monitoring dashboard."""
    stats_data = await get_workflow_stats(session)
    return WorkflowStatsResponse(**stats_data)


@router.get(
    "",
    response_model=WorkflowRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workflow runs",
    description="Returns a paginated list of recent workflow runs from PostgreSQL with optional status and search filtering.",
)
async def list_runs_endpoint(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (e.g. COMPLETED, FAILED, WAITING_FOR_APPROVAL, ACTIVE, REJECTED)"),
    search: Optional[str] = Query(default=None, description="Search query string matching query text or run ID"),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunListResponse:
    """Retrieve paginated workflow runs with optional status and search filtering."""
    items, total = await list_workflow_runs(
        session, page=page, page_size=page_size, status=status_filter, search=search
    )

    summaries = []
    for r in items:
        current_stage = "completed" if r.status == "COMPLETED" else (
            "human_approval" if r.status == "WAITING_FOR_APPROVAL" else (
                "failed" if r.status == "FAILED" else (
                    "planner" if r.status == "PENDING" else "processing"
                )
            )
        )
        summaries.append(
            WorkflowRunSummary(
                run_id=str(r.id),
                request_id=str(r.request_id),
                query=r.user_query,
                status=r.status,
                approval_status=r.approval_status,
                started_at=r.started_at,
                completed_at=r.completed_at,
                duration_ms=r.duration_ms,
                current_stage=current_stage,
                validation_status=r.validation_status,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

    return WorkflowRunListResponse(
        items=summaries,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/{run_id}",
    response_model=WorkflowRunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workflow run details",
    description="Returns detailed execution information, final outputs, and all agent steps and approvals for a specific run ID.",
)
async def get_run_detail_endpoint(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunDetailResponse:
    """Retrieve detailed workflow execution run including all agent steps and approval history."""
    run = await get_workflow_run(session, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )

    return _build_run_detail_response(run)


@router.get(
    "/{run_id}/approval",
    response_model=WorkflowApprovalDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get approval state for workflow run",
    description="Returns the current approval status, draft synthesized response, sources, analytics, and decision history.",
)
async def get_run_approval_endpoint(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> WorkflowApprovalDetailResponse:
    """Retrieve human approval status, review assets, and decision history for a run."""
    run = await get_workflow_run(session, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )

    approvals = [_format_approval_record(a) for a in (run.approvals or [])]
    current_approval = next((a for a in approvals if a.status == "PENDING"), None)
    revision_count = current_approval.revision_count if current_approval else (len(approvals) - 1 if approvals else 0)

    sources = (run.metadata_json or {}).get("sources", [])
    analysis_results = (run.metadata_json or {}).get("analysis_results")
    validation_data = (run.metadata_json or {}).get("validation")
    settings = get_settings()

    return WorkflowApprovalDetailResponse(
        run_id=str(run.id),
        request_id=str(run.request_id),
        status=run.status,
        approval_status=run.approval_status or ("PENDING" if run.status == "WAITING_FOR_APPROVAL" else "NONE"),
        query=run.user_query,
        answer=run.final_answer,
        key_points=run.key_points or [],
        confidence=run.confidence,
        sources=sources,
        analysis_results=analysis_results,
        validation=validation_data,
        validation_status=run.validation_status,
        validation_score=run.validation_score,
        revision_count=max(0, revision_count),
        max_revisions=settings.MAX_APPROVAL_REVISIONS,
        current_approval=current_approval,
        approval_history=approvals,
    )


@router.post(
    "/{run_id}/approval",
    response_model=WorkflowRunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit human approval decision",
    description="Submit an approval decision (APPROVE, REJECT, or CHANGES_REQUESTED) to resume the workflow from its LangGraph checkpoint.",
)
async def submit_approval_decision_endpoint(
    run_id: str,
    payload: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunDetailResponse:
    """Process human decision and resume durable workflow execution."""
    decision_clean = payload.decision.upper().strip()
    if decision_clean not in ("APPROVE", "REJECT", "CHANGES_REQUESTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{payload.decision}'. Allowed values are APPROVE, REJECT, CHANGES_REQUESTED.",
        )

    run = await get_workflow_run(session, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )

    if run.status != "WAITING_FOR_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow run '{run_id}' is not awaiting approval (current status: '{run.status}').",
        )

    try:
        await resume_workflow(
            run_id=run_id,
            decision=decision_clean,
            feedback=payload.feedback,
            decided_by=payload.decided_by or "human_reviewer",
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"Error resuming workflow run {run_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume workflow: {str(exc)}",
        )

    # Refresh and return full updated run details
    session.expire_all()
    updated_run = await get_workflow_run(session, run_id=run_id)
    return _build_run_detail_response(updated_run)
