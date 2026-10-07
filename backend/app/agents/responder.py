"""Response Agent for Multi-Agent Workflow.

Responsible for synthesizing the user query, strategic plan, and research findings
into an authoritative, structured final response with key executive takeaways
and a calibrated confidence score.
Persists execution step lifecycle in PostgreSQL when run_id is provided.
"""

from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.session import get_db_context
from backend.app.graph.state import WorkflowState
from backend.app.models.schemas import WorkflowResponse
from backend.app.services.llm import get_llm, invoke_structured
from backend.app.services.workflow_runs import complete_workflow_step, create_workflow_step, fail_workflow_step

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
    run_id = state.get("run_id")
    user_query = state.get("user_query", "")
    plan_data = state.get("plan") or {}
    research_data = state.get("research_results") or {}
    retrieved_docs = state.get("retrieved_documents") or []

    # Format structured source citations from retrieved document chunks
    sources = [
        {
            "document_id": d.get("document_id", ""),
            "chunk_id": d.get("chunk_id", ""),
            "filename": d.get("metadata", {}).get("filename") if isinstance(d.get("metadata"), dict) else d.get("filename", ""),
            "page_number": (d.get("metadata", {}).get("page_number", 1) if isinstance(d.get("metadata"), dict) else d.get("page_number", 1)),
            "snippet": ((d.get("content") or d.get("text") or "")[:200] + ("..." if len(d.get("content") or d.get("text") or "") > 200 else "")),
            "similarity_score": d.get("score") if d.get("score") is not None else d.get("similarity_score"),
        }
        for d in retrieved_docs
    ]

    logger.info(format_log_msg(f"Response agent started (run_id: {run_id or 'none'}, citations: {len(sources)})", request_id))

    step_id = None
    if run_id:
        try:
            async with get_db_context() as session:
                step = await create_workflow_step(
                    session=session,
                    run_id=run_id,
                    agent_name="responder",
                    step_order=4,
                    input_data={
                        "user_query": user_query,
                        "plan": plan_data,
                        "research_results": research_data,
                        "retrieved_sources_count": len(sources),
                    },
                )
                step_id = step.id
        except Exception as db_err:
            logger.warning(format_log_msg(f"Could not persist responder step start: {db_err}", request_id))

    try:
        llm = get_llm()

        # Build synthesis prompt
        findings_str = "\n".join(f"- {f}" for f in research_data.get("findings", [])) or "None"
        assumptions_str = "\n".join(f"- {a}" for a in research_data.get("assumptions", [])) or "None"
        unanswered_str = "\n".join(f"- {u}" for u in research_data.get("unanswered_questions", [])) or "None"
        steps_str = "\n".join(f"- {s}" for s in plan_data.get("steps", [])) or "None"

        sources_prompt = ""
        if sources:
            sources_details = "\n".join(
                f"- [{s['filename']} p.{s['page_number']}]: {s['snippet']}"
                for s in sources
            )
            sources_prompt = f"\n\nRetrieved Reference Sources:\n{sources_details}\nEnsure the answer is accurately grounded in these sources where relevant."

        prompt_content = (
            f"User Query:\n{user_query}\n\n"
            f"Strategic Plan Goal:\n{plan_data.get('goal', 'N/A')}\n"
            f"Steps Planned:\n{steps_str}\n\n"
            f"Research Findings:\n{findings_str}\n\n"
            f"Assumptions:\n{assumptions_str}\n\n"
            f"Unanswered Questions / Nuances:\n{unanswered_str}"
            f"{sources_prompt}\n\n"
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

        # Ensure request_id matches state and sources are populated
        update_fields = {"request_id": request_id}
        if sources and not workflow_response.sources:
            update_fields["sources"] = sources
        workflow_response = workflow_response.model_copy(update=update_fields)

        response_dict = workflow_response.model_dump()

        if step_id:
            try:
                async with get_db_context() as session:
                    await complete_workflow_step(session=session, step_id=step_id, output_data=response_dict)
            except Exception as db_err:
                logger.warning(format_log_msg(f"Could not persist responder step completion: {db_err}", request_id))

        logger.info(
            format_log_msg(
                f"Responder completed with confidence {workflow_response.confidence:.2f} "
                f"and {len(workflow_response.key_points)} key points.",
                request_id,
            )
        )

        return {
            "final_answer": response_dict,
            "intermediate_results": [
                {
                    "agent": "responder",
                    "output": response_dict,
                }
            ],
        }

    except Exception as exc:
        err_msg = f"Response Agent failed: {str(exc)}"
        logger.error(format_log_msg(err_msg, request_id))

        if step_id:
            try:
                async with get_db_context() as session:
                    await fail_workflow_step(session=session, step_id=step_id, error_message=err_msg)
            except Exception as db_err:
                logger.warning(format_log_msg(f"Could not persist responder step failure: {db_err}", request_id))

        return {
            "errors": [err_msg],
            "intermediate_results": [{"agent": "responder", "error": err_msg}],
        }
