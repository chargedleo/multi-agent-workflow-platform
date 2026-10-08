"""LangGraph workflow definition and orchestration.

Constructs, compiles, and executes the StateGraph multi-agent pipeline:
START -> Planner -> Document Retrieval -> Data Analysis -> Researcher -> Responder -> Validation -> Human Approval -> END.
Integrates durable lifecycle persistence in PostgreSQL and checkpointing.
"""

from typing import Any, Dict, Optional
import uuid
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.base import BaseCheckpointSaver

from backend.app.agents.approval import human_approval_node
from backend.app.agents.data_analysis import data_analysis_agent
from backend.app.agents.document_retrieval import document_retrieval_agent
from backend.app.agents.planner import plan_agent
from backend.app.agents.researcher import research_agent
from backend.app.agents.responder import response_agent
from backend.app.agents.validation import validation_agent
from backend.app.core.config import get_settings
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.models.workflow_run import WorkflowRun
from backend.app.db.session import get_db_context
from backend.app.graph.checkpointer import get_checkpointer
from backend.app.graph.state import WorkflowState, create_initial_state
from backend.app.services.workflow_runs import (
    _to_uuid,
    complete_workflow_run,
    create_approval_request,
    create_workflow_run,
    fail_workflow_run,
    get_workflow_run,
    record_approval_decision,
    start_workflow_run,
)

logger = get_logger(__name__)


def build_workflow_graph(checkpointer: Optional[BaseCheckpointSaver] = None) -> Any:
    """Build and compile the LangGraph multi-agent StateGraph with guardrails and human approval."""
    graph_builder = StateGraph(WorkflowState)

    # Register agent nodes
    graph_builder.add_node("planner", plan_agent)
    graph_builder.add_node("document_retrieval", document_retrieval_agent)
    graph_builder.add_node("data_analysis", data_analysis_agent)
    graph_builder.add_node("researcher", research_agent)
    graph_builder.add_node("responder", response_agent)
    graph_builder.add_node("validation", validation_agent)
    graph_builder.add_node("human_approval", human_approval_node)

    # Define linear execution edges leading to validation
    graph_builder.add_edge(START, "planner")
    graph_builder.add_edge("planner", "document_retrieval")
    graph_builder.add_edge("document_retrieval", "data_analysis")
    graph_builder.add_edge("data_analysis", "researcher")
    graph_builder.add_edge("researcher", "responder")
    graph_builder.add_edge("responder", "validation")

    # Conditional router from validation: recoverable failures cycle back to responder
    def validation_router(state: WorkflowState) -> str:
        settings = get_settings()
        errors = state.get("errors") or []
        if errors:
            return END

        if not settings.VALIDATION_ENABLED:
            return "human_approval"

        val_res = state.get("validation_results") or {}
        status = val_res.get("status")
        attempt = state.get("validation_attempt", 1)
        max_attempts = settings.MAX_VALIDATION_ATTEMPTS

        if status == "RECOVERABLE" and attempt < max_attempts:
            logger.info(
                format_log_msg(
                    f"Validation router directing state to responder for correction (attempt {attempt}/{max_attempts})",
                    state.get("request_id", "unknown"),
                )
            )
            return "responder"
        elif status in ("FAIL", "BLOCKED"):
            logger.warning(
                format_log_msg(
                    f"Validation terminal status {status}, terminating without approval gate",
                    state.get("request_id", "unknown"),
                )
            )
            return END

        return "human_approval"

    graph_builder.add_conditional_edges(
        "validation",
        validation_router,
        {
            "responder": "responder",
            "human_approval": "human_approval",
            END: END,
        },
    )

    # Conditional router from human approval gate
    def approval_router(state: WorkflowState) -> str:
        status = state.get("approval_status")
        if status == "CHANGES_REQUESTED":
            logger.info(
                format_log_msg(
                    "Approval router: revisions requested, cycling back to responder",
                    state.get("request_id", "unknown"),
                )
            )
            return "responder"
        return END

    graph_builder.add_conditional_edges(
        "human_approval",
        approval_router,
        {
            "responder": "responder",
            END: END,
        },
    )

    return graph_builder.compile(checkpointer=checkpointer)


compiled_workflow: Optional[Any] = None


def get_compiled_workflow(checkpointer: Optional[BaseCheckpointSaver] = None) -> Any:
    """Return compiled workflow instance, caching default checkpointer graph."""
    global compiled_workflow
    if checkpointer is not None:
        return build_workflow_graph(checkpointer=checkpointer)
    if compiled_workflow is None:
        compiled_workflow = build_workflow_graph(checkpointer=get_checkpointer())
    return compiled_workflow


def reset_compiled_workflow() -> None:
    """Reset cached graph instance (e.g. for testing when checkpointer changes)."""
    global compiled_workflow
    compiled_workflow = None


async def run_workflow(
    query: str,
    request_id: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    approval_required: bool = True,
) -> WorkflowState:
    """Execute the multi-agent workflow for a given user query with database persistence.

    Args:
        query: User input query
        request_id: Optional request identifier (generates UUIDv4 if omitted)
        run_id: Optional existing run_id (creates a new run record if omitted)
        metadata: Optional metadata dictionary
        approval_required: Whether to enforce human approval if globally enabled

    Returns:
        WorkflowState containing execution outputs, final response, and run identifiers.
    """
    req_id = request_id or str(uuid.uuid4())
    logger.info(format_log_msg(f"Request received: '{query[:80]}...'", req_id))
    logger.info(format_log_msg("Workflow started", req_id))

    # Persist workflow run record in PostgreSQL
    active_run_id = run_id
    if not active_run_id:
        try:
            async with get_db_context() as session:
                run_record = await create_workflow_run(
                    session=session,
                    request_id=req_id,
                    user_query=query,
                    metadata=metadata,
                )
                active_run_id = str(run_record.id)
                await start_workflow_run(session=session, run_id=active_run_id)
        except Exception as db_err:
            logger.warning(format_log_msg(f"Could not persist initial workflow run in DB: {db_err}", req_id))

    initial_state = create_initial_state(
        query=query,
        request_id=req_id,
        run_id=active_run_id,
        metadata=metadata,
    )
    initial_state["approval_required"] = approval_required

    graph = get_compiled_workflow()
    thread_config = {"configurable": {"thread_id": str(active_run_id)}}

    try:
        final_state: WorkflowState = await graph.ainvoke(initial_state, config=thread_config)

        # Ensure run_id is attached to state
        if active_run_id and not final_state.get("run_id"):
            final_state["run_id"] = active_run_id

        final_answer = final_state.get("final_answer")
        errors = final_state.get("errors", [])
        val_res = final_state.get("validation_results") or {}
        val_status = val_res.get("status")

        is_interrupted = "__interrupt__" in final_state and bool(final_state["__interrupt__"])

        if is_interrupted:
            final_state["status"] = "WAITING_FOR_APPROVAL"
            final_state["approval_status"] = "PENDING"
            rev_count = final_state.get("approval_revision", 0)

            logger.info(
                format_log_msg(
                    f"Workflow reached Human Approval Gate and suspended (revision: {rev_count})",
                    req_id,
                )
            )

            if active_run_id:
                try:
                    async with get_db_context() as session:
                        await create_approval_request(
                            session=session,
                            run_id=active_run_id,
                            revision_count=rev_count,
                            metadata={"query": query},
                        )
                        run_row = await session.get(WorkflowRun, _to_uuid(active_run_id))
                        if run_row:
                            if final_answer:
                                run_row.final_answer = final_answer.get("answer")
                                run_row.key_points = final_answer.get("key_points", [])
                                run_row.confidence = final_answer.get("confidence")
                            run_row.plan = final_state.get("plan")
                            run_row.research_results = final_state.get("research_results")
                            if val_res:
                                run_row.validation_status = val_res.get("status")
                                run_row.validation_score = val_res.get("score")
                            meta = dict(run_row.metadata_json or {})
                            if final_answer and final_answer.get("sources"):
                                meta["sources"] = final_answer.get("sources")
                            if final_state.get("analysis_results"):
                                meta["analysis_results"] = final_state.get("analysis_results")
                            if val_res:
                                meta["validation"] = val_res
                                meta["validation_results"] = val_res
                            run_row.metadata_json = meta
                            await session.commit()
                except Exception as db_err:
                    logger.warning(format_log_msg(f"Could not persist approval request in DB: {db_err}", req_id))

            return final_state

        # Uninterrupted run: either validation failed, or approval was skipped/disabled
        if errors or not final_answer or val_status in ("FAIL", "BLOCKED"):
            final_state["status"] = "FAILED"
            fail_reasons = list(errors)
            if val_status in ("FAIL", "BLOCKED"):
                fail_reasons.append(f"Validation Guardrails: {val_status}")
            logger.warning(
                format_log_msg(
                    f"Workflow completed with failure: {', '.join(fail_reasons)}",
                    req_id,
                )
            )
            if active_run_id:
                try:
                    async with get_db_context() as session:
                        await fail_workflow_run(
                            session=session,
                            run_id=active_run_id,
                            errors=fail_reasons,
                            final_answer=final_answer.get("answer") if final_answer else None,
                            plan=final_state.get("plan"),
                            research_results=final_state.get("research_results"),
                            validation_results=val_res,
                        )
                except Exception as db_err:
                    logger.warning(format_log_msg(f"Could not persist failed run status: {db_err}", req_id))
        else:
            final_state["status"] = "COMPLETED"
            final_state["approval_status"] = final_state.get("approval_status") or "APPROVED"
            logger.info(format_log_msg("Workflow completed successfully", req_id))
            if active_run_id:
                try:
                    async with get_db_context() as session:
                        await complete_workflow_run(
                            session=session,
                            run_id=active_run_id,
                            final_answer=final_answer.get("answer", ""),
                            key_points=final_answer.get("key_points", []),
                            confidence=final_answer.get("confidence", 0.0),
                            plan=final_state.get("plan"),
                            research_results=final_state.get("research_results"),
                            errors=errors,
                            sources=final_answer.get("sources", []),
                            analysis_results=final_state.get("analysis_results") or final_answer.get("analysis_results"),
                            validation_results=val_res,
                            approval_status=final_state["approval_status"],
                        )
                except Exception as db_err:
                    logger.warning(format_log_msg(f"Could not persist completed run: {db_err}", req_id))

        return final_state

    except Exception as exc:
        err_msg = f"Workflow failed with unhandled exception: {str(exc)}"
        logger.error(format_log_msg(err_msg, req_id), exc_info=True)

        if active_run_id:
            try:
                async with get_db_context() as session:
                    await fail_workflow_run(session=session, run_id=active_run_id, errors=[err_msg])
            except Exception as db_err:
                logger.warning(format_log_msg(f"Could not persist unhandled exception run status: {db_err}", req_id))

        fallback_state = dict(initial_state)
        fallback_state["errors"] = [err_msg]
        fallback_state["status"] = "FAILED"
        if active_run_id:
            fallback_state["run_id"] = active_run_id
        return fallback_state


async def resume_workflow(
    run_id: str,
    decision: str,
    feedback: Optional[str] = None,
    decided_by: Optional[str] = "human_reviewer",
) -> WorkflowState:
    """Resume a workflow run suspended at the Human Approval Gate.

    Args:
        run_id: Workflow run UUID string.
        decision: One of APPROVE, REJECT, CHANGES_REQUESTED.
        feedback: Reviewer comments or revision instructions.
        decided_by: Reviewer identity.

    Returns:
        WorkflowState representing post-resume state (either COMPLETED, FAILED, or WAITING_FOR_APPROVAL).
    """
    run_uuid = _to_uuid(run_id)
    async with get_db_context() as session:
        run = await get_workflow_run(session, run_uuid)
        if not run:
            raise KeyError(f"Workflow run '{run_id}' not found.")
        if run.status != "WAITING_FOR_APPROVAL":
            raise ValueError(
                f"Workflow run '{run_id}' is not waiting for approval (current status: {run.status})."
            )
        req_id = str(run.request_id)

    dec_upper = decision.upper().strip()
    if dec_upper not in ("APPROVE", "REJECT", "CHANGES_REQUESTED"):
        raise ValueError(f"Invalid decision '{decision}'. Must be APPROVE, REJECT, or CHANGES_REQUESTED.")

    logger.info(format_log_msg(f"Resuming workflow run with decision '{dec_upper}'", req_id))

    # Record decision in DB
    async with get_db_context() as session:
        await record_approval_decision(
            session=session,
            run_id=run_id,
            decision=dec_upper,
            feedback=feedback,
            decided_by=decided_by,
        )

    # Resume graph execution using Command(resume=...)
    graph = get_compiled_workflow()
    thread_config = {"configurable": {"thread_id": str(run_id)}}
    resume_payload = {
        "decision": dec_upper,
        "feedback": feedback,
        "decided_by": decided_by,
    }

    try:
        resumed_state = await graph.ainvoke(Command(resume=resume_payload), config=thread_config)
        if str(run_id) and not resumed_state.get("run_id"):
            resumed_state["run_id"] = str(run_id)

        is_interrupted = "__interrupt__" in resumed_state and bool(resumed_state["__interrupt__"])

        if is_interrupted:
            # Re-interrupted after revision loop
            resumed_state["status"] = "WAITING_FOR_APPROVAL"
            resumed_state["approval_status"] = "PENDING"
            rev_count = resumed_state.get("approval_revision", 0)
            logger.info(
                format_log_msg(
                    f"Workflow revised (revision #{rev_count}) and suspended at Human Approval Gate",
                    req_id,
                )
            )
            async with get_db_context() as session:
                await create_approval_request(
                    session=session,
                    run_id=run_id,
                    revision_count=rev_count,
                    metadata={"feedback_incorporated": feedback},
                )
                final_ans = resumed_state.get("final_answer") or {}
                val_res = resumed_state.get("validation_results") or {}
                run_row = await session.get(WorkflowRun, run_uuid)
                if run_row:
                    run_row.status = "WAITING_FOR_APPROVAL"
                    run_row.approval_status = "PENDING"
                    if final_ans:
                        run_row.final_answer = final_ans.get("answer")
                        run_row.key_points = final_ans.get("key_points", [])
                        run_row.confidence = final_ans.get("confidence")
                    if val_res:
                        run_row.validation_status = val_res.get("status")
                        run_row.validation_score = val_res.get("score")
                    await session.commit()

            return resumed_state

        # Graph execution completed (no interrupts remaining)
        final_answer = resumed_state.get("final_answer")
        errors = resumed_state.get("errors", [])
        val_res = resumed_state.get("validation_results") or {}
        val_status = val_res.get("status")
        app_status = resumed_state.get("approval_status", dec_upper)

        if app_status == "REJECTED" or errors or not final_answer or val_status in ("FAIL", "BLOCKED"):
            resumed_state["status"] = "FAILED"
            resumed_state["approval_status"] = "REJECTED"
            fail_reasons = list(errors)
            if app_status == "REJECTED":
                fail_reasons.append(f"Human Approval Rejected: {feedback or 'Rejected by reviewer'}")
            elif val_status in ("FAIL", "BLOCKED"):
                fail_reasons.append(f"Validation Guardrails: {val_status}")

            logger.info(format_log_msg(f"Workflow ended with rejection/failure: {fail_reasons}", req_id))
            async with get_db_context() as session:
                await fail_workflow_run(
                    session=session,
                    run_id=run_id,
                    errors=fail_reasons,
                    final_answer=final_answer.get("answer") if final_answer else None,
                    plan=resumed_state.get("plan"),
                    research_results=resumed_state.get("research_results"),
                    validation_results=val_res,
                    approval_status="REJECTED",
                )
        else:
            resumed_state["status"] = "COMPLETED"
            resumed_state["approval_status"] = "APPROVED"
            logger.info(format_log_msg("Workflow completed and approved successfully", req_id))
            async with get_db_context() as session:
                await complete_workflow_run(
                    session=session,
                    run_id=run_id,
                    final_answer=final_answer.get("answer", "") if final_answer else "",
                    key_points=final_answer.get("key_points", []) if final_answer else [],
                    confidence=final_answer.get("confidence", 0.0) if final_answer else 0.0,
                    plan=resumed_state.get("plan"),
                    research_results=resumed_state.get("research_results"),
                    errors=errors,
                    sources=final_answer.get("sources", []) if final_answer else [],
                    analysis_results=resumed_state.get("analysis_results") or (final_answer.get("analysis_results") if final_answer else None),
                    validation_results=val_res,
                    approval_status="APPROVED",
                )

        return resumed_state

    except Exception as exc:
        err_msg = f"Resume workflow failed: {str(exc)}"
        logger.error(format_log_msg(err_msg, req_id), exc_info=True)
        async with get_db_context() as session:
            await fail_workflow_run(session=session, run_id=run_id, errors=[err_msg])
        raise
