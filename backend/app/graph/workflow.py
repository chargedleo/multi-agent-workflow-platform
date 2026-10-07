"""LangGraph workflow definition and orchestration.

Constructs, compiles, and executes the StateGraph multi-agent pipeline:
START -> Planner -> Researcher -> Responder -> END.
"""

from typing import Any, Dict, Optional
import uuid
import logging
from langgraph.graph import StateGraph, START, END

from backend.app.agents.planner import plan_agent
from backend.app.agents.researcher import research_agent
from backend.app.agents.responder import response_agent
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.graph.state import WorkflowState, create_initial_state

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
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkflowState:
    """Execute the multi-agent workflow for a given user query.

    Args:
        query: User input query
        request_id: Optional request identifier (generates UUIDv4 if omitted)
        metadata: Optional metadata dictionary

    Returns:
        WorkflowState containing the execution outputs and final response.
    """
    req_id = request_id or str(uuid.uuid4())
    logger.info(format_log_msg(f"Request received: '{query[:80]}...'", req_id))
    logger.info(format_log_msg("Workflow started", req_id))

    initial_state = create_initial_state(query=query, request_id=req_id, metadata=metadata)

    try:
        final_state: WorkflowState = await compiled_workflow.ainvoke(initial_state)

        errors = final_state.get("errors", [])
        if errors:
            logger.warning(
                format_log_msg(
                    f"Workflow completed with {len(errors)} error(s): {', '.join(errors)}",
                    req_id,
                )
            )
        else:
            logger.info(format_log_msg("Workflow completed successfully", req_id))

        return final_state

    except Exception as exc:
        err_msg = f"Workflow failed with unhandled exception: {str(exc)}"
        logger.error(format_log_msg(err_msg, req_id), exc_info=True)

        # Ensure state contains error details
        fallback_state = dict(initial_state)
        fallback_state["errors"] = [err_msg]
        return fallback_state
