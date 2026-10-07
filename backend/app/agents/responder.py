"""Response Agent for Multi-Agent Workflow.

Responsible for synthesizing the user query, strategic plan, and research findings
into an authoritative, structured final response with key executive takeaways
and a calibrated confidence score.
"""

from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.core.logging import format_log_msg, get_logger
from backend.app.graph.state import WorkflowState
from backend.app.models.schemas import WorkflowResponse
from backend.app.services.llm import get_llm, invoke_structured

logger = get_logger(__name__)

RESPONDER_SYSTEM_PROMPT = """You are an expert Executive Response Agent in a Multi-Agent AI system.
Your job is to synthesize all research findings, execution plans, and the initial user query
into an authoritative, polished, and structured final response.

Guidelines:
- Provide an articulate, comprehensive answer that directly addresses the user query.
- Extract 3 to 5 high-impact, executive key points summarizing core takeaways.
- Provide a calibrated confidence score (between 0.0 and 1.0) indicating how complete and reliable the answer is given the research.
- Retain technical accuracy, nuance, and actionable trade-offs.
"""


async def response_agent(state: WorkflowState) -> Dict[str, Any]:
    """Execute the Response Agent node.

    Args:
        state: Current WorkflowState.

    Returns:
        State update dictionary containing the final_answer and intermediate step.
    """
    request_id = state.get("request_id", "unknown")
    user_query = state.get("user_query", "")
    plan_data = state.get("plan") or {}
    research_data = state.get("research_results") or {}

    logger.info(format_log_msg("Response agent started", request_id))

    try:
        llm = get_llm()

        # Build synthesis prompt
        findings_str = "\n".join(f"- {f}" for f in research_data.get("findings", [])) or "None"
        assumptions_str = "\n".join(f"- {a}" for a in research_data.get("assumptions", [])) or "None"
        unanswered_str = "\n".join(f"- {u}" for u in research_data.get("unanswered_questions", [])) or "None"
        steps_str = "\n".join(f"- {s}" for s in plan_data.get("steps", [])) or "None"

        prompt_content = (
            f"User Query:\n{user_query}\n\n"
            f"Strategic Plan Goal:\n{plan_data.get('goal', 'N/A')}\n"
            f"Steps Planned:\n{steps_str}\n\n"
            f"Research Findings:\n{findings_str}\n\n"
            f"Assumptions:\n{assumptions_str}\n\n"
            f"Unanswered Questions / Nuances:\n{unanswered_str}\n\n"
            f"Workflow Request ID:\n{request_id}\n\n"
            f"Synthesize this into a final response matching the WorkflowResponse schema. "
            f"Include the exact request_id: '{request_id}'."
        )

        messages = [
            SystemMessage(content=RESPONDER_SYSTEM_PROMPT),
            HumanMessage(content=prompt_content),
        ]

        # Produce validated structured output
        workflow_response: WorkflowResponse = await invoke_structured(llm, messages, WorkflowResponse)

        # Ensure request_id matches state
        if workflow_response.request_id != request_id:
            workflow_response = workflow_response.model_copy(update={"request_id": request_id})

        logger.info(
            format_log_msg(
                f"Responder completed with confidence {workflow_response.confidence:.2f} "
                f"and {len(workflow_response.key_points)} key points.",
                request_id,
            )
        )

        return {
            "final_answer": workflow_response.model_dump(),
            "intermediate_results": [
                {
                    "agent": "responder",
                    "output": workflow_response.model_dump(),
                }
            ],
        }

    except Exception as exc:
        err_msg = f"Response Agent failed: {str(exc)}"
        logger.error(format_log_msg(err_msg, request_id))
        return {
            "errors": [err_msg],
            "intermediate_results": [{"agent": "responder", "error": err_msg}],
        }
