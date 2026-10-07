"""Document Retrieval Agent.

Retrieves relevant document chunks from the FAISS vector store
based on user query and planner context, passing grounding evidence to downstream agents.
"""

import time
import uuid
from typing import Any, Dict

from backend.app.core.logging import get_logger
from backend.app.db.session import get_db_context
from backend.app.graph.state import WorkflowState
from backend.app.services.retrieval import RetrievalService
from backend.app.services.workflow_runs import complete_workflow_step, create_workflow_step, fail_workflow_step

logger = get_logger(__name__)


async def document_retrieval_agent(state: WorkflowState) -> Dict[str, Any]:
    """Execute Document Retrieval Agent node in LangGraph pipeline.

    Searches FAISS vector store for semantically relevant chunks based on user query
    and plan goals. Persists step lifecycle to PostgreSQL if run_id is active.
    """
    user_query = state.get("user_query", "")
    plan = state.get("plan") or {}
    run_id_val = state.get("run_id")
    run_uuid = uuid.UUID(run_id_val) if run_id_val else None

    # Step persistence setup
    step_id = None
    start_time = time.perf_counter()

    if run_uuid:
        try:
            async with get_db_context() as db:
                step = await create_workflow_step(
                    db,
                    run_id=run_uuid,
                    agent_name="document_retrieval",
                    step_order=2,
                    input_data={
                        "user_query": user_query,
                        "plan_goal": plan.get("goal", ""),
                    },
                )
                step_id = step.id
        except Exception as exc:
            logger.warning(f"Could not persist document_retrieval step start: {exc}")

    try:
        # Formulate query: combine user query and plan goal if distinct
        plan_goal = plan.get("goal", "")
        search_query = user_query
        if plan_goal and plan_goal != user_query and len(plan_goal) < 200:
            search_query = f"{user_query} {plan_goal}"

        # Execute semantic retrieval
        retrieval_result = RetrievalService.retrieve(search_query)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        retrieved_dicts = [chunk.model_dump() for chunk in retrieval_result.results]

        output_data = {
            "query_used": search_query,
            "chunks_retrieved": len(retrieved_dicts),
            "sources": [
                {
                    "document_id": c["document_id"],
                    "filename": c["filename"],
                    "page_number": c["page_number"],
                    "chunk_id": c["chunk_id"],
                    "similarity_score": c["similarity_score"],
                }
                for c in retrieved_dicts
            ],
        }

        # Complete step persistence
        if step_id and run_uuid:
            try:
                async with get_db_context() as db:
                    await complete_workflow_step(
                        db,
                        step_id=step_id,
                        output_data=output_data,
                    )
            except Exception as exc:
                logger.warning(f"Could not persist document_retrieval step completion: {exc}")

        return {
            "retrieved_documents": retrieved_dicts,
            "intermediate_results": [
                {
                    "agent": "document_retrieval",
                    "status": "success",
                    "duration_ms": duration_ms,
                    "chunks_count": len(retrieved_dicts),
                    "output": output_data,
                }
            ],
        }

    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        err_msg = f"Document Retrieval Agent error: {str(exc)}"
        logger.error(err_msg, exc_info=True)

        if step_id and run_uuid:
            try:
                async with get_db_context() as db:
                    await fail_workflow_step(
                        db,
                        step_id=step_id,
                        error_message=err_msg,
                    )
            except Exception as db_exc:
                logger.warning(f"Could not persist document_retrieval step failure: {db_exc}")

        return {
            "retrieved_documents": [],
            "errors": [err_msg],
            "intermediate_results": [
                {
                    "agent": "document_retrieval",
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "error": str(exc),
                }
            ],
        }
