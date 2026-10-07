"""Data Analysis Agent.

Determines whether structured data analysis is required for a user query,
invokes approved MCP tools (analyze_dataset, get_dataset_schema, query_postgres),
and stores validated analytical results into the shared WorkflowState.
Guarantees:
- Zero numerical hallucination.
- Zero arbitrary code or SQL execution.
- Strict step lifecycle persistence in PostgreSQL.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.app.core.logging import format_log_msg, get_logger
from backend.app.db.session import get_db_context
from backend.app.graph.state import WorkflowState
from backend.app.mcp.server import invoke_mcp_tool
from backend.app.services.llm import get_llm, invoke_structured
from backend.app.services.workflow_runs import complete_workflow_step, create_workflow_step, fail_workflow_step

logger = get_logger(__name__)


class AnalysisDecision(BaseModel):
    """Structured decision made by the Data Analysis Agent."""

    analysis_required: bool = Field(..., description="Whether structured data analysis is required")
    reasoning: str = Field(..., description="Strategic rationale for deciding whether to invoke analysis tools")
    tool_name: Optional[str] = Field(default="analyze_dataset", description="Approved MCP tool: 'analyze_dataset', 'get_dataset_schema', or 'query_postgres'")
    dataset: Optional[str] = Field(default="orders", description="Target approved dataset name or PostgreSQL table")
    operation: Optional[str] = Field(default="count", description="Analytical operation: count, sum, mean, min, max, group_by, top_n, sort, descriptive_stats")
    columns: Optional[List[str]] = Field(default=None, description="Target column(s) for the operation")
    group_by: Optional[List[str]] = Field(default=None, description="Columns to group by")
    filters: Optional[List[Dict[str, Any]]] = Field(default=None, description="Filter predicates")
    sort_by: Optional[str] = Field(default=None, description="Column to sort by")
    sort_order: Optional[str] = Field(default="desc", description="Sort order: 'asc' or 'desc'")
    limit: Optional[int] = Field(default=None, description="Max rows to return")


DATA_ANALYSIS_SYSTEM_PROMPT = """You are an expert Data Analysis Agent in a Multi-Agent AI system.
Your job is to determine whether the user query requires structured quantitative or tabular analysis,
and if so, formulate a structured tool call using only approved MCP tools and datasets.

Available MCP tools:
1. 'analyze_dataset': In-memory safe analysis on approved datasets ('orders').
   Operations: 'count', 'sum', 'mean', 'min', 'max', 'group_by', 'top_n', 'sort', 'descriptive_stats'.
   Columns in 'orders': order_id, order_date, customer, region, product, category, quantity, unit_price, revenue.
2. 'get_dataset_schema': Inspect columns, types, and record count of dataset ('orders').
3. 'query_postgres': Parameterized SQL query on approved PostgreSQL table 'analytics_orders'.

Guidelines:
- If the query is conceptual, architectural, or purely document-based with no request for numbers/metrics/orders/sales, set analysis_required=False.
- If the query asks about orders, revenue, sales, averages, top products, or regional breakdowns, set analysis_required=True.
- Select the exact approved tool, operation, and columns. Never invent table or column names.
- Do not fabricate numbers or computational results; the tool will compute them deterministically.
"""


async def data_analysis_agent(state: WorkflowState) -> Dict[str, Any]:
    """Execute Data Analysis Agent node in LangGraph pipeline."""
    request_id = state.get("request_id", "unknown")
    run_id_val = state.get("run_id")
    run_uuid = uuid.UUID(run_id_val) if run_id_val else None
    user_query = state.get("user_query", "")
    plan = state.get("plan") or {}

    logger.info(format_log_msg(f"Data Analysis agent started (run_id: {run_id_val or 'none'})", request_id))

    step_id = None
    start_time = time.perf_counter()

    if run_uuid:
        try:
            async with get_db_context() as db:
                step = await create_workflow_step(
                    db,
                    run_id=run_uuid,
                    agent_name="data_analysis",
                    step_order=3,
                    input_data={
                        "user_query": user_query,
                        "plan_goal": plan.get("goal", ""),
                    },
                )
                step_id = step.id
        except Exception as exc:
            logger.warning(format_log_msg(f"Could not persist data_analysis step start: {exc}", request_id))

    try:
        llm = get_llm()
        messages = [
            SystemMessage(content=DATA_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"User Query:\n{user_query}\n\n"
                    f"Strategic Plan Goal:\n{plan.get('goal', 'N/A')}\n\n"
                    "Determine whether structured data analysis is required and formulate the decision."
                )
            ),
        ]

        decision: AnalysisDecision = await invoke_structured(llm, messages, AnalysisDecision)

        if not decision.analysis_required:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_data = {
                "analysis_required": False,
                "reasoning": decision.reasoning,
                "status": "not_required",
            }

            if step_id and run_uuid:
                try:
                    async with get_db_context() as db:
                        await complete_workflow_step(db, step_id=step_id, output_data=output_data)
                except Exception as exc:
                    logger.warning(format_log_msg(f"Could not persist data_analysis completion: {exc}", request_id))

            logger.info(format_log_msg("Data analysis not required for query", request_id))
            return {
                "analysis_results": {"status": "not_required", "reasoning": decision.reasoning},
                "intermediate_results": [
                    {
                        "agent": "data_analysis",
                        "status": "not_required",
                        "duration_ms": duration_ms,
                        "output": output_data,
                    }
                ],
            }

        # Formulate MCP tool arguments
        tool_name = decision.tool_name or "analyze_dataset"
        tool_args: Dict[str, Any] = {}

        if tool_name == "analyze_dataset":
            tool_args = {
                "dataset": decision.dataset or "orders",
                "operation": decision.operation or "count",
            }
            if decision.columns:
                tool_args["columns"] = decision.columns
            if decision.group_by:
                tool_args["group_by"] = decision.group_by
            if decision.filters:
                tool_args["filters"] = decision.filters
            if decision.sort_by:
                tool_args["sort_by"] = decision.sort_by
            if decision.sort_order:
                tool_args["sort_order"] = decision.sort_order
            if decision.limit:
                tool_args["limit"] = decision.limit

        elif tool_name == "get_dataset_schema":
            tool_args = {"dataset": decision.dataset or "orders"}

        elif tool_name == "query_postgres":
            tool_args = {
                "table": decision.dataset or "analytics_orders",
                "limit": decision.limit or 100,
            }
            if decision.columns:
                tool_args["columns"] = decision.columns
            if decision.filters:
                tool_args["filters"] = decision.filters
            if decision.group_by:
                tool_args["group_by"] = decision.group_by
            if decision.sort_by:
                tool_args["order_by"] = decision.sort_by
                tool_args["sort_order"] = decision.sort_order or "asc"

        logger.info(format_log_msg(f"Invoking MCP tool '{tool_name}' with args: {tool_args}", request_id))
        tool_result = await invoke_mcp_tool(tool_name, tool_args)
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        step_output = {
            "analysis_required": True,
            "tool_name": tool_name,
            "tool_arguments": tool_args,
            "tool_success": tool_result.success,
            "tool_error": tool_result.error,
            "duration_ms": tool_result.duration_ms,
            "result_summary": tool_result.result.get("summary") if isinstance(tool_result.result, dict) else str(tool_result.result),
            "metrics": tool_result.result.get("metrics", {}) if isinstance(tool_result.result, dict) else {},
            "rows_count": len(tool_result.result.get("rows", [])) if isinstance(tool_result.result, dict) else 0,
        }

        # Store analysis results dictionary for state
        analysis_state_res: Dict[str, Any] = {
            "status": "completed" if tool_result.success else "failed",
            "tool_name": tool_name,
            "dataset": decision.dataset or "orders",
            "operation": decision.operation or "query",
            "success": tool_result.success,
            "summary": tool_result.result.get("summary", "") if isinstance(tool_result.result, dict) else "",
            "metrics": tool_result.result.get("metrics", {}) if isinstance(tool_result.result, dict) else {},
            "columns": tool_result.result.get("columns", []) if isinstance(tool_result.result, dict) else [],
            "rows": tool_result.result.get("rows", [])[:10] if isinstance(tool_result.result, dict) else [],
            "execution_time_ms": tool_result.duration_ms,
            "error": tool_result.error,
        }

        if step_id and run_uuid:
            try:
                async with get_db_context() as db:
                    if tool_result.success:
                        await complete_workflow_step(db, step_id=step_id, output_data=step_output)
                    else:
                        await fail_workflow_step(db, step_id=step_id, error_message=tool_result.error or "Analysis tool failed")
            except Exception as exc:
                logger.warning(format_log_msg(f"Could not persist data_analysis step completion: {exc}", request_id))

        res_update: Dict[str, Any] = {
            "analysis_results": analysis_state_res,
            "intermediate_results": [
                {
                    "agent": "data_analysis",
                    "status": "success" if tool_result.success else "failed",
                    "duration_ms": duration_ms,
                    "output": step_output,
                }
            ],
        }

        if not tool_result.success and tool_result.error:
            res_update["errors"] = [f"Data Analysis error: {tool_result.error}"]

        return res_update

    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        err_msg = f"Data Analysis Agent failed: {str(exc)}"
        logger.error(format_log_msg(err_msg, request_id), exc_info=True)

        if step_id and run_uuid:
            try:
                async with get_db_context() as db:
                    await fail_workflow_step(db, step_id=step_id, error_message=err_msg)
            except Exception as db_exc:
                logger.warning(format_log_msg(f"Could not persist data_analysis failure: {db_exc}", request_id))

        return {
            "analysis_results": {
                "status": "failed",
                "error": err_msg,
            },
            "errors": [err_msg],
            "intermediate_results": [
                {
                    "agent": "data_analysis",
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "error": str(exc),
                }
            ],
        }
