"""Tool implementations for dataset analysis and schema inspection."""

from typing import Any, Dict, List, Optional
from backend.app.analysis.schemas import (
    AnalysisOperation,
    AnalysisRequest,
    FilterCondition,
    FilterOperator,
    PostgresQueryRequest,
    SortOrder,
)
from backend.app.analysis.service import DataAnalysisService
from backend.app.mcp.tools.postgres import PostgresAnalyticsTool


def parse_filters(raw_filters: Optional[List[Dict[str, Any]]]) -> Optional[List[FilterCondition]]:
    """Safely convert list of raw dict filters to validated FilterConditions."""
    if not raw_filters:
        return None
    parsed: List[FilterCondition] = []
    for f in raw_filters:
        if isinstance(f, FilterCondition):
            parsed.append(f)
        elif isinstance(f, dict) and "column" in f and "value" in f:
            op_str = f.get("operator", "==")
            # Find matching enum
            matched_op = FilterOperator.EQ
            for op_enum in FilterOperator:
                if op_enum.value == op_str:
                    matched_op = op_enum
                    break
            parsed.append(FilterCondition(
                column=f["column"],
                operator=matched_op,
                value=f["value"],
            ))
    return parsed


def analyze_dataset_tool(
    dataset: str,
    operation: str,
    columns: Optional[List[str]] = None,
    group_by: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute safe analytical operations (count, sum, mean, min, max, group_by, top_n, sort, descriptive_stats)."""
    # Parse operation
    op_clean = operation.lower().strip()
    matched_op = None
    for op_enum in AnalysisOperation:
        if op_enum.value == op_clean:
            matched_op = op_enum
            break
    if not matched_op:
        matched_op = AnalysisOperation.COUNT

    order_enum = SortOrder.DESC if sort_order.lower() == "desc" else SortOrder.ASC
    parsed_filter_list = parse_filters(filters)

    req = AnalysisRequest(
        dataset=dataset,
        operation=matched_op,
        columns=columns,
        group_by=group_by,
        filters=parsed_filter_list,
        sort_by=sort_by,
        sort_order=order_enum,
        limit=limit,
    )
    result = DataAnalysisService.analyze(req)
    return result.model_dump()


def get_dataset_schema_tool(dataset: str) -> Dict[str, Any]:
    """Inspect columns, types, and record count of an approved dataset."""
    try:
        schema_info = DataAnalysisService.get_schema(dataset)
        return {
            "success": True,
            "dataset": schema_info.dataset_name,
            "description": schema_info.description,
            "columns": [col.model_dump() for col in schema_info.columns],
            "row_count": schema_info.row_count,
        }
    except Exception as exc:
        return {
            "success": False,
            "dataset": dataset,
            "error": str(exc),
        }


async def query_postgres_tool(
    table: str = "analytics_orders",
    columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    group_by: Optional[List[str]] = None,
    aggregations: Optional[Dict[str, str]] = None,
    order_by: Optional[str] = None,
    sort_order: str = "asc",
    limit: Optional[int] = 100,
) -> Dict[str, Any]:
    """Query approved PostgreSQL analytical tables using safe, parameterized structured requests."""
    order_enum = SortOrder.DESC if sort_order.lower() == "desc" else SortOrder.ASC
    parsed_filter_list = parse_filters(filters)

    req = PostgresQueryRequest(
        table=table,
        columns=columns,
        filters=parsed_filter_list,
        group_by=group_by,
        aggregations=aggregations,
        order_by=order_by,
        sort_order=order_enum,
        limit=limit,
    )
    return await PostgresAnalyticsTool.query(req)
