"""Parameterized, secure PostgreSQL Analytical Query Tool.

Security guarantees:
- Strict table allowlist (only 'analytics_orders').
- Strict column allowlist (attributes of AnalyticsOrder).
- Fully parameterized SQLAlchemy expressions (no raw SQL strings or concatenation).
- Whitelisted aggregation functions and comparison operators.
- Enforced row limits.
"""

import time
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute

from backend.app.analysis.schemas import FilterOperator, PostgresQueryRequest, SortOrder
from backend.app.core.logging import get_logger
from backend.app.db.models.analytics_order import AnalyticsOrder
from backend.app.db.session import get_db_context

logger = get_logger(__name__)

# Strict Table Allowlist
ALLOWED_TABLES: Dict[str, Any] = {
    "analytics_orders": AnalyticsOrder,
}

# Strict Column Allowlist for analytics_orders
ALLOWED_COLUMNS = {
    "order_id",
    "order_date",
    "customer",
    "region",
    "product",
    "category",
    "quantity",
    "unit_price",
    "revenue",
}

# Whitelisted SQL aggregations
ALLOWED_AGGS = {
    "count": func.count,
    "sum": func.sum,
    "avg": func.avg,
    "mean": func.avg,
    "min": func.min,
    "max": func.max,
}


class PostgresAnalyticsTool:
    """Executes safe, parameterized structured queries against approved analytical PostgreSQL tables."""

    @classmethod
    async def query(cls, request: PostgresQueryRequest) -> Dict[str, Any]:
        """Execute a safe, parameterized analytical query."""
        start_time = time.perf_counter()
        tbl_name = request.table.lower().strip()

        # 1. Table allowlist check
        if tbl_name not in ALLOWED_TABLES:
            allowed = ", ".join(ALLOWED_TABLES.keys())
            return {
                "success": False,
                "error": f"Table '{request.table}' is not permitted. Allowed tables: {allowed}",
                "columns": [],
                "rows": [],
                "metrics": {},
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }

        model = ALLOWED_TABLES[tbl_name]

        # 2. Column validation
        requested_cols = request.columns or []
        for col in requested_cols:
            if col not in ALLOWED_COLUMNS:
                return {
                    "success": False,
                    "error": f"Column '{col}' is not allowed on table '{tbl_name}'. Allowed: {', '.join(sorted(ALLOWED_COLUMNS))}",
                    "columns": [],
                    "rows": [],
                    "metrics": {},
                    "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                }

        if request.group_by:
            for col in request.group_by:
                if col not in ALLOWED_COLUMNS:
                    return {
                        "success": False,
                        "error": f"Group-by column '{col}' is not allowed.",
                        "columns": [],
                        "rows": [],
                        "metrics": {},
                        "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    }

        if request.order_by and request.order_by not in ALLOWED_COLUMNS:
            # Check if order_by refers to an aggregation alias like revenue_sum
            pass

        # 3. Build Select query using SQLAlchemy model attributes
        select_targets = []
        output_column_names: List[str] = []

        if request.group_by:
            for g_col in request.group_by:
                col_attr: InstrumentedAttribute = getattr(model, g_col)
                select_targets.append(col_attr)
                output_column_names.append(g_col)

        if request.aggregations:
            for col, agg_name in request.aggregations.items():
                agg_fn = ALLOWED_AGGS.get(agg_name.lower())
                if not agg_fn:
                    allowed_aggs_str = ", ".join(ALLOWED_AGGS.keys())
                    return {
                        "success": False,
                        "error": f"Aggregation '{agg_name}' is not supported. Allowed: {allowed_aggs_str}",
                        "columns": [],
                        "rows": [],
                        "metrics": {},
                        "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    }
                if col not in ALLOWED_COLUMNS and col != "*":
                    return {
                        "success": False,
                        "error": f"Aggregation column '{col}' is not allowed.",
                        "columns": [],
                        "rows": [],
                        "metrics": {},
                        "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    }
                target_attr = getattr(model, col) if col != "*" else model.id
                alias_name = f"{col}_{agg_name.lower()}"
                select_targets.append(agg_fn(target_attr).label(alias_name))
                output_column_names.append(alias_name)
        elif not request.group_by:
            # Projection without grouping
            if requested_cols:
                for c in requested_cols:
                    select_targets.append(getattr(model, c))
                    output_column_names.append(c)
            else:
                for c in sorted(ALLOWED_COLUMNS):
                    select_targets.append(getattr(model, c))
                    output_column_names.append(c)

        stmt = select(*select_targets)

        # 4. Parameterized Filters
        if request.filters:
            for f in request.filters:
                col_name = f.column
                if col_name not in ALLOWED_COLUMNS:
                    return {
                        "success": False,
                        "error": f"Filter column '{col_name}' is not allowed.",
                        "columns": [],
                        "rows": [],
                        "metrics": {},
                        "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    }
                col_attr = getattr(model, col_name)
                val = f.value
                op = f.operator

                if op == FilterOperator.EQ:
                    stmt = stmt.where(col_attr == val)
                elif op == FilterOperator.NEQ:
                    stmt = stmt.where(col_attr != val)
                elif op == FilterOperator.GT:
                    stmt = stmt.where(col_attr > val)
                elif op == FilterOperator.LT:
                    stmt = stmt.where(col_attr < val)
                elif op == FilterOperator.GTE:
                    stmt = stmt.where(col_attr >= val)
                elif op == FilterOperator.LTE:
                    stmt = stmt.where(col_attr <= val)
                elif op == FilterOperator.IN:
                    if isinstance(val, list):
                        stmt = stmt.where(col_attr.in_(val))
                    else:
                        stmt = stmt.where(col_attr == val)
                elif op == FilterOperator.CONTAINS:
                    stmt = stmt.where(col_attr.ilike(f"%{val}%"))

        # 5. Group by
        if request.group_by:
            group_attrs = [getattr(model, c) for c in request.group_by]
            stmt = stmt.group_by(*group_attrs)

        # 6. Order by
        if request.order_by:
            if request.order_by in ALLOWED_COLUMNS:
                order_attr = getattr(model, request.order_by)
                stmt = stmt.order_by(order_attr.desc() if request.sort_order == SortOrder.DESC else order_attr.asc())
            elif request.aggregations:
                # Ordering by aggregate alias
                for col, agg_name in request.aggregations.items():
                    alias_name = f"{col}_{agg_name.lower()}"
                    if request.order_by in (alias_name, col):
                        agg_fn = ALLOWED_AGGS[agg_name.lower()]
                        target_attr = getattr(model, col) if col != "*" else model.id
                        expr = agg_fn(target_attr)
                        stmt = stmt.order_by(expr.desc() if request.sort_order == SortOrder.DESC else expr.asc())
                        break

        # 7. Limit (cap at 1000)
        limit_val = min(request.limit or 100, 1000)
        stmt = stmt.limit(limit_val)

        # 8. Execute asynchronously
        try:
            async with get_db_context() as session:
                db_res = await session.execute(stmt)
                raw_rows = db_res.all()

            rows: List[Dict[str, Any]] = []
            for row in raw_rows:
                row_dict: Dict[str, Any] = {}
                for idx, col_name in enumerate(output_column_names):
                    val = row[idx]
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif isinstance(val, float):
                        val = round(val, 2)
                    row_dict[col_name] = val
                rows.append(row_dict)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metrics = {
                "rows_returned": len(rows),
                "table": tbl_name,
            }

            return {
                "success": True,
                "table": tbl_name,
                "columns": output_column_names,
                "rows": rows,
                "metrics": metrics,
                "execution_time_ms": duration_ms,
            }

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"PostgreSQL query execution failed: {exc}", exc_info=True)
            return {
                "success": False,
                "error": f"Database query failed: {str(exc)}",
                "columns": [],
                "rows": [],
                "metrics": {},
                "execution_time_ms": duration_ms,
            }
