"""Workflow execution and history API routes."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.session import get_db
from backend.app.graph.workflow import run_workflow
from backend.app.models.schemas import (
    WorkflowAPIResponse,
    WorkflowRequest,
    WorkflowRunDetailResponse,
    WorkflowRunListResponse,
    WorkflowRunSummary,
    WorkflowStepDetail,
)
from backend.app.services.workflow_runs import get_workflow_run, list_workflow_runs

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post(
    "",
    response_model=WorkflowAPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute multi-agent workflow",
    description="Submits a query through the Planner -> Researcher -> Responder LangGraph workflow, persisting run records in PostgreSQL.",
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

        if not final_answer:
            error_details = "; ".join(errors) if errors else "Workflow did not yield a valid final answer"
            logger.error(format_log_msg(f"Workflow execution produced no answer: {error_details}", request_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow failed to complete: {error_details}",
            )

        return WorkflowAPIResponse(
            request_id=request_id,
            run_id=run_id,
            status=run_status.lower(),
            answer=final_answer.get("answer", ""),
            key_points=final_answer.get("key_points", []),
            confidence=final_answer.get("confidence", 0.0),
            sources=final_answer.get("sources", []),
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
    "",
    response_model=WorkflowRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workflow runs",
    description="Returns a paginated list of recent workflow runs from PostgreSQL.",
)
async def list_runs_endpoint(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunListResponse:
    """Retrieve paginated workflow runs."""
    items, total = await list_workflow_runs(session, page=page, page_size=page_size)

    summaries = [
        WorkflowRunSummary(
            run_id=str(r.id),
            request_id=str(r.request_id),
            query=r.user_query,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            duration_ms=r.duration_ms,
        )
        for r in items
    ]

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
    description="Returns detailed execution information, final outputs, and all agent steps for a specific run ID.",
)
async def get_run_detail_endpoint(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunDetailResponse:
    """Retrieve detailed workflow execution run including all agent steps."""
    run = await get_workflow_run(session, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )

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
        for step in run.steps
    ]

    sources = (run.metadata_json or {}).get("sources", [])

    return WorkflowRunDetailResponse(
        run_id=str(run.id),
        request_id=str(run.request_id),
        status=run.status,
        query=run.user_query,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        plan=run.plan,
        research_results=run.research_results,
        answer=run.final_answer,
        key_points=run.key_points,
        confidence=run.confidence,
        sources=sources,
        errors=run.errors or [],
        metadata=run.metadata_json or {},
        steps=steps,
    )
