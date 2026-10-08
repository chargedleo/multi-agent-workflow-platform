"""Human-in-the-Loop Approval Agent Node for LangGraph Workflow.

Implements the Human Approval Gate using LangGraph interrupt() semantics.
Suspends workflow execution to await human reviewer feedback or approval.
"""

from typing import Any, Dict
from langgraph.types import interrupt

from backend.app.core.config import get_settings
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.graph.state import WorkflowState

logger = get_logger(__name__)


async def human_approval_node(state: WorkflowState) -> Dict[str, Any]:
    """Execute the Human Approval Gate node.

    If approvals are enabled, pauses workflow execution using interrupt()
    and yields state for human inspection. When resumed with Command(resume=...),
    processes the reviewer decision.

    Args:
        state: Current WorkflowState.

    Returns:
        State update dictionary containing approval_status, approval_decision,
        approval_feedback, and updated approval_revision count.
    """
    request_id = state.get("request_id", "unknown")
    run_id = state.get("run_id")
    settings = get_settings()

    # If approval is disabled globally or explicitly not required
    if not settings.APPROVAL_ENABLED or state.get("approval_required") is False:
        logger.info(
            format_log_msg(
                "Approval is disabled or not required; auto-approving workflow.",
                request_id,
            )
        )
        return {
            "approval_status": "APPROVED",
            "approval_decision": "AUTO_APPROVED",
        }

    current_revision = state.get("approval_revision", 0)
    logger.info(
        format_log_msg(
            f"Human Approval Gate reached (run_id: {run_id or 'none'}, revision: {current_revision}). Suspending via interrupt()...",
            request_id,
        )
    )

    # Interrupt execution and persist checkpoint for reviewer review
    decision_payload = interrupt({
        "type": "human_approval",
        "run_id": run_id,
        "request_id": request_id,
        "user_query": state.get("user_query"),
        "final_answer": state.get("final_answer"),
        "retrieved_documents": state.get("retrieved_documents"),
        "analysis_results": state.get("analysis_results"),
        "validation_results": state.get("validation_results"),
        "revision_count": current_revision,
        "max_revisions": settings.MAX_APPROVAL_REVISIONS,
    })

    if not isinstance(decision_payload, dict):
        decision_payload = {"decision": str(decision_payload)}

    decision = str(decision_payload.get("decision", "APPROVE")).upper().strip()
    feedback = decision_payload.get("feedback")
    decided_by = decision_payload.get("decided_by", "human_reviewer")

    logger.info(
        format_log_msg(
            f"Human approval resumed: decision='{decision}', reviewer='{decided_by}', revision={current_revision}",
            request_id,
        )
    )

    if decision == "APPROVE":
        return {
            "approval_status": "APPROVED",
            "approval_decision": "APPROVE",
            "approval_feedback": feedback,
        }

    if decision == "REJECT":
        return {
            "approval_status": "REJECTED",
            "approval_decision": "REJECT",
            "approval_feedback": feedback,
        }

    if decision == "CHANGES_REQUESTED":
        max_revisions = settings.MAX_APPROVAL_REVISIONS
        if current_revision >= max_revisions:
            logger.warning(
                format_log_msg(
                    f"Maximum approval revision limit ({max_revisions}) exceeded. Finalizing as REJECTED.",
                    request_id,
                )
            )
            return {
                "approval_status": "REJECTED",
                "approval_decision": "REJECT",
                "approval_feedback": f"Maximum revisions ({max_revisions}) exceeded: {feedback or ''}".strip(),
            }

        return {
            "approval_status": "CHANGES_REQUESTED",
            "approval_decision": "CHANGES_REQUESTED",
            "approval_feedback": feedback,
            "approval_revision": current_revision + 1,
            "validation_attempt": 0,
            "validation_issues": [],
        }

    # Fallback for unrecognized decisions
    logger.warning(
        format_log_msg(
            f"Unrecognized approval decision '{decision}'. Defaulting to REJECTED.",
            request_id,
        )
    )
    return {
        "approval_status": "REJECTED",
        "approval_decision": "REJECT",
        "approval_feedback": f"Unrecognized decision: {decision}",
    }
