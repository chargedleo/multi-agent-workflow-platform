"""Validation Agent for Multi-Agent Workflow Guardrails.

Executes deterministic validation checks across agent outputs, citations,
numerical calculations, and claims. Governs the correction loop when recoverable
errors are detected and enforces hard limits.
"""

import time
from typing import Any, Dict
from backend.app.core.config import get_settings
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.session import get_db_context
from backend.app.graph.state import WorkflowState
from backend.app.services.workflow_runs import (
    complete_workflow_step,
    create_workflow_step,
    fail_workflow_step,
)
from backend.app.validation.schemas import ValidationResult, ValidationStatus
from backend.app.validation.service import ValidationService

logger = get_logger(__name__)


async def validation_agent(state: WorkflowState) -> Dict[str, Any]:
    """Execute the Validation Agent node.

    Args:
        state: Current WorkflowState.

    Returns:
        State update dictionary containing validation_results, attempt count, and feedback.
    """
    request_id = state.get("request_id", "unknown")
    run_id = state.get("run_id")
    settings = get_settings()

    current_attempt = (state.get("validation_attempt") or 0) + 1
    step_order = 5 + (2 * current_attempt - 1)  # Attempt 1 -> Step 6, Attempt 2 -> Step 8

    logger.info(
        format_log_msg(
            f"VALIDATION_STARTED: Attempt {current_attempt}/{settings.MAX_VALIDATION_ATTEMPTS} (run_id: {run_id or 'none'})",
            request_id,
        )
    )

    step_id = None
    if run_id:
        try:
            async with get_db_context() as session:
                step = await create_workflow_step(
                    session=session,
                    run_id=run_id,
                    agent_name="validation",
                    step_order=step_order,
                    input_data={
                        "attempt": current_attempt,
                        "has_final_answer": bool(state.get("final_answer")),
                        "sources_count": len(state.get("retrieved_documents") or []),
                        "has_analysis": bool(state.get("analysis_results")),
                    },
                )
                step_id = step.id
        except Exception as db_err:
            logger.warning(format_log_msg(f"Could not persist validation step start: {db_err}", request_id))

    try:
        # Check if validation is disabled in settings
        if not settings.VALIDATION_ENABLED:
            logger.info(format_log_msg("VALIDATION_SKIPPED: Validation is disabled in settings.", request_id))
            result = ValidationResult(
                status=ValidationStatus.PASS,
                score=1.0,
                issues=[],
                checked_items=0,
                failed_items=0,
                validator_name="disabled_guardrails",
                attempt=current_attempt,
            )
        else:
            result = ValidationService.validate_workflow_state(dict(state), attempt=current_attempt)

        result_dict = result.model_dump()

        # Structured observability logging
        if result.status == ValidationStatus.PASS:
            logger.info(
                format_log_msg(
                    f"VALIDATION_PASSED: Score {result.score:.2f} ({result.checked_items} checks passed, attempt {current_attempt})",
                    request_id,
                )
            )
        elif result.status == ValidationStatus.RECOVERABLE:
            logger.warning(
                format_log_msg(
                    f"VALIDATION_RECOVERY_ATTEMPT: Triggering correction attempt {current_attempt} with {len(result.issues)} issue(s)",
                    request_id,
                )
            )
        elif result.status == ValidationStatus.BLOCKED:
            logger.error(
                format_log_msg(
                    f"VALIDATION_BLOCKED: Security or critical violation detected with {len(result.issues)} issue(s)",
                    request_id,
                )
            )
        else:
            logger.error(
                format_log_msg(
                    f"VALIDATION_FAILED: Workflow validation failed with {len(result.issues)} issue(s) (attempt {current_attempt})",
                    request_id,
                )
            )

        # Persist step outcome
        if step_id:
            try:
                async with get_db_context() as session:
                    if result.status in (ValidationStatus.PASS, ValidationStatus.RECOVERABLE):
                        await complete_workflow_step(session=session, step_id=step_id, output_data=result_dict)
                    else:
                        first_err = result.issues[0].message if result.issues else "Validation checks failed"
                        await fail_workflow_step(session=session, step_id=step_id, error_message=first_err)
            except Exception as db_err:
                logger.warning(format_log_msg(f"Could not persist validation step outcome: {db_err}", request_id))

        history = list(state.get("validation_history") or [])
        history.append(result_dict)

        state_update: Dict[str, Any] = {
            "validation_results": result_dict,
            "validation_attempt": current_attempt,
            "validation_issues": [i.model_dump() for i in result.issues if i.recoverable],
            "validation_history": history,
            "intermediate_results": [
                {
                    "agent": "validation",
                    "status": result.status.value,
                    "attempt": current_attempt,
                    "output": result_dict,
                }
            ],
        }

        # If permanent failure, record to errors list
        if result.status in (ValidationStatus.FAIL, ValidationStatus.BLOCKED):
            fail_reasons = [f"[{i.code}] {i.message}" for i in result.issues if i.severity.value in ("ERROR", "CRITICAL")]
            state_update["errors"] = [f"Validation Guardrail Failure: {', '.join(fail_reasons) if fail_reasons else 'Failed checks'}"]

        return state_update

    except Exception as exc:
        err_msg = f"Validation Agent crashed with unhandled exception: {str(exc)}"
        logger.error(format_log_msg(err_msg, request_id), exc_info=True)

        if step_id:
            try:
                async with get_db_context() as session:
                    await fail_workflow_step(session=session, step_id=step_id, error_message=err_msg)
            except Exception as db_err:
                logger.warning(format_log_msg(f"Could not persist validation step crash: {db_err}", request_id))

        crash_result = ValidationResult(
            status=ValidationStatus.FAIL,
            score=0.0,
            issues=[],
            checked_items=0,
            failed_items=1,
            validator_name="guardrails_error_fallback",
            attempt=current_attempt,
        )

        return {
            "validation_results": crash_result.model_dump(),
            "validation_attempt": current_attempt,
            "errors": [err_msg],
            "intermediate_results": [
                {
                    "agent": "validation",
                    "status": "FAIL",
                    "attempt": current_attempt,
                    "error": err_msg,
                }
            ],
        }
