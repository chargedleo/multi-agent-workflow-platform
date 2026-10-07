"""Pure Python & NumPy safe analytical operations implementation.

Guaranteed safe execution:
- No eval() or exec()
- Strict column allowlists
- Strict operation definitions
- Graceful handling of nulls, zeroes, and type mismatches
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.app.analysis.schemas import (
    AnalysisOperation,
    FilterCondition,
    FilterOperator,
    SortOrder,
)


def apply_filter(
    rows: List[Dict[str, Any]],
    filters: List[FilterCondition],
) -> List[Dict[str, Any]]:
    """Filter rows matching all given FilterConditions safely without dynamic execution."""
    if not filters:
        return rows

    filtered: List[Dict[str, Any]] = []
    for row in rows:
        matches_all = True
        for cond in filters:
            col = cond.column
            if col not in row:
                matches_all = False
                break

            actual = row[col]
            expected = cond.value
            op = cond.operator

            if actual is None:
                matches_all = False
                break

            try:
                # Handle numeric comparisons when types differ (e.g. float vs int)
                if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                    actual_val = float(actual)
                    expected_val = float(expected)
                elif isinstance(expected, str) and isinstance(actual, str):
                    actual_val = actual.lower()
                    expected_val = expected.lower()
                else:
                    actual_val = str(actual)
                    expected_val = str(expected)

                if op == FilterOperator.EQ:
                    matches = actual_val == expected_val
                elif op == FilterOperator.NEQ:
                    matches = actual_val != expected_val
                elif op == FilterOperator.GT:
                    matches = actual_val > expected_val
                elif op == FilterOperator.LT:
                    matches = actual_val < expected_val
                elif op == FilterOperator.GTE:
                    matches = actual_val >= expected_val
                elif op == FilterOperator.LTE:
                    matches = actual_val <= expected_val
                elif op == FilterOperator.IN:
                    if isinstance(expected, list):
                        exp_list = [str(x).lower() for x in expected]
                        matches = str(actual).lower() in exp_list
                    else:
                        matches = str(actual).lower() == str(expected).lower()
                elif op == FilterOperator.CONTAINS:
                    matches = str(expected).lower() in str(actual).lower()
                else:
                    matches = False

                if not matches:
                    matches_all = False
                    break
            except Exception:
                matches_all = False
                break

        if matches_all:
            filtered.append(row)

    return filtered


def apply_sort(
    rows: List[Dict[str, Any]],
    sort_by: str,
    sort_order: SortOrder = SortOrder.ASC,
) -> List[Dict[str, Any]]:
    """Safely sort rows by a given column name."""
    if not rows or not sort_by:
        return rows

    def sort_key(row: Dict[str, Any]) -> Any:
        val = row.get(sort_by)
        if val is None:
            return (0, "")
        if isinstance(val, (int, float)):
            return (1, float(val))
        return (2, str(val))

    reverse = (sort_order == SortOrder.DESC)
    return sorted(rows, key=sort_key, reverse=reverse)


def calculate_column_metric(
    rows: List[Dict[str, Any]],
    column: str,
    operation: AnalysisOperation,
) -> Union[int, float]:
    """Calculate single column metric: count, sum, mean, min, max."""
    if operation == AnalysisOperation.COUNT:
        if column:
            return sum(1 for r in rows if r.get(column) is not None)
        return len(rows)

    values = [float(r[column]) for r in rows if r.get(column) is not None and isinstance(r[column], (int, float))]
    if not values:
        return 0.0

    arr = np.array(values, dtype=np.float64)
    if operation == AnalysisOperation.SUM:
        return round(float(np.sum(arr)), 4)
    elif operation == AnalysisOperation.MEAN:
        return round(float(np.mean(arr)), 4)
    elif operation == AnalysisOperation.MIN:
        return round(float(np.min(arr)), 4)
    elif operation == AnalysisOperation.MAX:
        return round(float(np.max(arr)), 4)
    else:
        raise ValueError(f"Unsupported metric operation: {operation}")


def calculate_descriptive_stats(
    rows: List[Dict[str, Any]],
    column: str,
) -> Dict[str, Any]:
    """Compute complete statistical summary for a numeric column."""
    values = [float(r[column]) for r in rows if r.get(column) is not None and isinstance(r[column], (int, float))]
    if not values:
        return {
            "count": len(rows),
            "valid_count": 0,
            "sum": 0.0,
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std": 0.0,
            "median": 0.0,
        }

    arr = np.array(values, dtype=np.float64)
    return {
        "count": len(rows),
        "valid_count": len(values),
        "sum": round(float(np.sum(arr)), 4),
        "mean": round(float(np.mean(arr)), 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "std": round(float(np.std(arr)), 4),
        "median": round(float(np.median(arr)), 4),
    }


def execute_group_by(
    rows: List[Dict[str, Any]],
    group_cols: List[str],
    agg_col: Optional[str] = None,
    agg_func: str = "sum",
) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
    """Group rows by specified columns and compute aggregation."""
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    for r in rows:
        key = tuple(r.get(c, "Unknown") for c in group_cols)
        groups.setdefault(key, []).append(r)

    result_rows: List[Dict[str, Any]] = []
    overall_total = 0.0

    agg_col_name = f"{agg_col}_{agg_func}" if agg_col else f"count"

    for key, items in groups.items():
        row_dict: Dict[str, Any] = {}
        for c, k_val in zip(group_cols, key):
            row_dict[c] = k_val

        if agg_col:
            nums = [float(item[agg_col]) for item in items if item.get(agg_col) is not None and isinstance(item[agg_col], (int, float))]
            if not nums:
                val = 0.0
            else:
                arr = np.array(nums, dtype=np.float64)
                if agg_func.lower() == "sum":
                    val = round(float(np.sum(arr)), 2)
                elif agg_func.lower() in ("mean", "avg"):
                    val = round(float(np.mean(arr)), 2)
                elif agg_func.lower() == "min":
                    val = round(float(np.min(arr)), 2)
                elif agg_func.lower() == "max":
                    val = round(float(np.max(arr)), 2)
                elif agg_func.lower() == "count":
                    val = len(items)
                else:
                    val = round(float(np.sum(arr)), 2)
            row_dict[agg_col_name] = val
            overall_total += float(val) if isinstance(val, (int, float)) else 0.0
        else:
            row_dict[agg_col_name] = len(items)
            overall_total += len(items)

        result_rows.append(row_dict)

    # Sort descending by aggregated column by default
    result_rows.sort(key=lambda x: x.get(agg_col_name, 0), reverse=True)

    output_columns = list(group_cols) + [agg_col_name]
    metrics = {
        "groups_count": len(groups),
        f"total_{agg_col_name}": round(overall_total, 2),
    }

    return output_columns, result_rows, metrics
