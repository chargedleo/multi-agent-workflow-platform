"""Planner Agent for Multi-Agent Workflow.

Responsible for analyzing user queries, deconstructing complex tasks into
sequential logical steps, and producing a structured execution plan.
"""

from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.core.logging import format_log_msg, get_logger
from backend.app.graph.state import WorkflowState
from backend.app.models.schemas import Plan
from backend.app.services.llm import get_llm, invoke_structured

logger = get_logger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an expert Strategic Planner Agent in a Multi-Agent AI system.
Your job is to deconstruct complex business and technical queries into a coherent, high-level goal
and a sequential list of actionable, logical execution steps.

Guidelines:
- Define a clear, targeted goal summarizing what must be achieved.
- Break the execution into 3 to 6 structured, chronological steps.
- Ensure each step is concrete and verifiable.
- Focus on comparative analysis, trade-offs, architecture, and actionable recommendations where applicable.
"""


async def plan_agent(state: WorkflowState) -> Dict[str, Any]:
    """Execute the Planner Agent node.

    Args:
        state: Current WorkflowState.

    Returns:
        State update dictionary containing the generated plan and intermediate step.
    """
    request_id = state.get("request_id", "unknown")
    user_query = state.get("user_query", "")
    logger.info(format_log_msg("Planner agent started", request_id))

    try:
        llm = get_llm()
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"User Query:\n{user_query}"),
        ]

        # Produce validated structured output
        plan_result: Plan = await invoke_structured(llm, messages, Plan)

        # Log completion
        logger.info(
            format_log_msg(
                f"Planner completed with {len(plan_result.steps)} steps for goal: '{plan_result.goal}'",
                request_id,
            )
        )

        return {
            "plan": plan_result.model_dump(),
            "intermediate_results": [
                {
                    "agent": "planner",
                    "output": plan_result.model_dump(),
                }
            ],
        }

    except Exception as exc:
        err_msg = f"Planner Agent failed: {str(exc)}"
        logger.error(format_log_msg(err_msg, request_id))
        return {
            "errors": [err_msg],
            "intermediate_results": [
                {
                    "agent": "planner",
                    "error": err_msg,
                }
            ],
        }
