"""Workflow execution API routes."""

import uuid
from fastapi import APIRouter, HTTPException, status
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.graph.workflow import run_workflow
from backend.app.models.schemas import WorkflowAPIResponse, WorkflowRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post(
    "",
    response_model=WorkflowAPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute multi-agent workflow",
    description="Submits a query through the Planner -> Researcher -> Responder LangGraph workflow.",
)
async def create_workflow_run(payload: WorkflowRequest) -> WorkflowAPIResponse:
    """Submit a query to the multi-agent workflow pipeline."""
    request_id = str(uuid.uuid4())
    logger.info(format_log_msg(f"Initiating workflow execution via API: '{payload.query[:60]}...'", request_id))

    try:
        final_state = await run_workflow(query=payload.query, request_id=request_id)
        final_answer = final_state.get("final_answer")
        errors = final_state.get("errors", [])

        if not final_answer:
            error_details = "; ".join(errors) if errors else "Workflow did not yield a valid final answer"
            logger.error(format_log_msg(f"Workflow execution produced no answer: {error_details}", request_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow failed to complete: {error_details}",
            )

        return WorkflowAPIResponse(
            request_id=request_id,
            answer=final_answer.get("answer", ""),
            key_points=final_answer.get("key_points", []),
            confidence=final_answer.get("confidence", 0.0),
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
