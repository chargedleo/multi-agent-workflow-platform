"""LangGraph workflow definition and orchestration.

Constructs, compiles, and executes the StateGraph multi-agent pipeline:
START -> Planner -> Researcher -> Responder -> END.
Integrates durable lifecycle persistence in PostgreSQL.
"""

from typing import Any, Dict, Optional
import uuid
from langgraph.graph import StateGraph, START, END

from backend.app.agents.planner import plan_agent
from backend.app.agents.researcher import research_agent
from backend.app.agents.responder import response_agent
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.session import get_db_context
from backend.app.graph.state import WorkflowState, create_initial_state
from backend.app.services.workflow_runs import (
    complete_workflow_run,
    create_workflow_run,
    fail_workflow_run,
    start_workflow_run,
)

logger = get_logger(__name__)


def build_workflow_graph() -> Any:
    """Build and compile the LangGraph multi-agent StateGraph."""
    graph_builder = StateGraph(WorkflowState)

    # Register agent nodes
    graph_builder.add_node("planner", plan_agent)
    graph_builder.add_node("researcher", research_agent)
    graph_builder.add_node("responder", response_agent)

    # Define linear execution edges
    graph_builder.add_edge(START, "planner")
    graph_builder.add_edge("planner", "researcher")
    graph_builder.add_edge("researcher", "responder")
    graph_builder.add_edge("responder", END)

    # Compile the graph
    return graph_builder.compile()


# Singleton compiled graph instance
compiled_workflow = build_workflow_graph()


async def run_workflow(
    query: str,
    request_id: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkflowState:
    """Execute the multi-agent workflow for a given user query with database persistence.

    Args:
        query: User input query
        request_id: Optional request identifier (generates UUIDv4 if omitted)
        run_id: Optional existing run_id (creates a new run record if omitted)
        metadata: Optional metadata dictionary

    Returns:
        WorkflowState containing the execution outputs, final response, and run identifiers.
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

    try:
        final_state: WorkflowState = await compiled_workflow.ainvoke(initial_state)

        # Ensure run_id is attached to final state
        if active_run_id and not final_state.get("run_id"):
            final_state["run_id"] = active_run_id

        final_answer = final_state.get("final_answer")
        errors = final_state.get("errors", [])

        if errors or not final_answer:
            final_state["status"] = "FAILED"
            logger.warning(
                format_log_msg(
                    f"Workflow completed with {len(errors)} error(s): {', '.join(errors)}",
                    req_id,
                )
            )
            if active_run_id:
                try:
                    async with get_db_context() as session:
                        await fail_workflow_run(
                            session=session,
                            run_id=active_run_id,
                            errors=errors,
                            final_answer=final_answer.get("answer") if final_answer else None,
                            plan=final_state.get("plan"),
                            research_results=final_state.get("research_results"),
                        )
                except Exception as db_err:
                    logger.warning(format_log_msg(f"Could not persist failed run status: {db_err}", req_id))
        else:
            final_state["status"] = "COMPLETED"
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
