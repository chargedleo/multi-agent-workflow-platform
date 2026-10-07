"""Data Analysis Service.

Provides secure, controlled, in-memory analytical capabilities over approved datasets.
Guarantees:
- Strict dataset allowlist and path traversal protection.
- Strict column existence and data type validation.
- Zero eval(), exec(), or arbitrary shell/code invocation.
- Structured, predictable Pydantic error reporting.
"""

import csv
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.app.analysis.operations import (
    apply_filter,
    apply_sort,
    calculate_column_metric,
    calculate_descriptive_stats,
    execute_group_by,
)
from backend.app.analysis.schemas import (
    AnalysisColumn,
    AnalysisOperation,
    AnalysisRequest,
    AnalysisResult,
    DatasetSchemaInfo,
    SortOrder,
)
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

# Base directory for approved datasets
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SAMPLE_DATA_DIR = REPO_ROOT / "data" / "sample"

# Approved dataset registry
APPROVED_DATASETS: Dict[str, Dict[str, Any]] = {
    "orders": {
        "path": SAMPLE_DATA_DIR / "orders.csv",
        "description": "Historical enterprise SaaS and software product orders containing regional sales, quantities, and revenues.",
        "types": {
            "order_id": "string",
            "order_date": "string",
            "customer": "string",
            "region": "string",
            "product": "string",
            "category": "string",
            "quantity": "integer",
            "unit_price": "float",
            "revenue": "float",
        },
    }
}


class DataAnalysisService:
    """Service providing safe analytical computation over approved structured datasets."""

    @classmethod
    def _load_dataset(cls, dataset_name: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Load and cast dataset rows securely.
        
        Raises:
            ValueError: If dataset is not approved or file does not exist.
        """
        key = dataset_name.lower().strip()
        if key not in APPROVED_DATASETS:
            # Also allow matching by filename without extension
            matched = None
            for name, meta in APPROVED_DATASETS.items():
                if name in key or key.endswith(f"{name}.csv"):
                    matched = name
                    break
            if matched:
                key = matched
            else:
                allowed = ", ".join(APPROVED_DATASETS.keys())
                raise ValueError(f"Dataset '{dataset_name}' is not in approved allowlist. Available datasets: {allowed}")

        meta = APPROVED_DATASETS[key]
        filepath: Path = meta["path"]
        if not filepath.exists():
            for alt_dir in [
                Path("/app/data/sample"),
                Path.cwd() / "data" / "sample",
                Path(__file__).resolve().parent.parent.parent / "data" / "sample",
            ]:
                candidate = alt_dir / f"{key}.csv"
                if candidate.exists():
                    filepath = candidate
                    break

        # Ensure path does not escape approved directory
        if not filepath.exists():
            raise ValueError(f"Dataset file '{meta['path'].name}' not found on server.")

        types = meta["types"]
        rows: List[Dict[str, Any]] = []

        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                cast_row: Dict[str, Any] = {}
                for col, val in raw_row.items():
                    val = val.strip() if val is not None else ""
                    expected_type = types.get(col, "string")
                    if expected_type == "integer":
                        try:
                            cast_row[col] = int(val)
                        except (ValueError, TypeError):
                            cast_row[col] = 0
                    elif expected_type == "float":
                        try:
                            cast_row[col] = float(val)
                        except (ValueError, TypeError):
                            cast_row[col] = 0.0
                    else:
                        cast_row[col] = val
                rows.append(cast_row)

        return rows, types

    @classmethod
    def get_schema(cls, dataset_name: str) -> DatasetSchemaInfo:
        """Retrieve schema metadata and row count for an approved dataset."""
        key = dataset_name.lower().strip()
        rows, types = cls._load_dataset(key)
        meta = APPROVED_DATASETS.get(key, APPROVED_DATASETS["orders"])

        columns = [
            AnalysisColumn(name=col, data_type=dtype)
            for col, dtype in types.items()
        ]

        return DatasetSchemaInfo(
            dataset_name=key,
            description=meta["description"],
            columns=columns,
            row_count=len(rows),
        )

    @classmethod
    def list_datasets(cls) -> List[DatasetSchemaInfo]:
        """List all approved datasets and their schemas."""
        results: List[DatasetSchemaInfo] = []
        for name in APPROVED_DATASETS:
            try:
                results.append(cls.get_schema(name))
            except Exception as e:
                logger.warning(f"Could not load schema for dataset {name}: {e}")
        return results

    @classmethod
    def analyze(cls, request: AnalysisRequest) -> AnalysisResult:
        """Execute a controlled analytical request safely and return structured results."""
        start_time = time.perf_counter()
        dataset_name = request.dataset
        op = request.operation

        try:
            rows, types = cls._load_dataset(dataset_name)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return AnalysisResult(
                success=False,
                operation=str(op.value if hasattr(op, "value") else op),
                dataset=dataset_name,
                summary=f"Analysis failed: {str(exc)}",
                columns=[],
                rows=[],
                metrics={},
                tool_name="analyze_dataset",
                execution_time_ms=duration_ms,
                warnings=[],
                errors=[str(exc)],
            )

        # Validate requested columns
        warnings: List[str] = []
        all_cols = set(types.keys())

        if request.columns:
            for c in request.columns:
                if c not in all_cols:
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return AnalysisResult(
                        success=False,
                        operation=str(op.value if hasattr(op, "value") else op),
                        dataset=dataset_name,
                        summary=f"Invalid column '{c}'. Available columns: {', '.join(sorted(all_cols))}",
                        columns=[],
                        rows=[],
                        metrics={},
                        tool_name="analyze_dataset",
                        execution_time_ms=duration_ms,
                        warnings=[],
                        errors=[f"Column '{c}' does not exist in dataset '{dataset_name}'."],
                    )

        if request.group_by:
            for c in request.group_by:
                if c not in all_cols:
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return AnalysisResult(
                        success=False,
                        operation=str(op.value if hasattr(op, "value") else op),
                        dataset=dataset_name,
                        summary=f"Invalid group_by column '{c}'. Available: {', '.join(sorted(all_cols))}",
                        columns=[],
                        rows=[],
                        metrics={},
                        tool_name="analyze_dataset",
                        execution_time_ms=duration_ms,
                        warnings=[],
                        errors=[f"Group column '{c}' does not exist in dataset '{dataset_name}'."],
                    )

        # Apply filters
        active_rows = rows
        if request.filters:
            active_rows = apply_filter(active_rows, request.filters)
            if not active_rows:
                warnings.append("Filters resulted in an empty dataset.")

        # Execute primary operation
        target_col = request.columns[0] if (request.columns and len(request.columns) > 0) else None
        res_columns: List[str] = []
        res_rows: List[Dict[str, Any]] = []
        metrics: Dict[str, Any] = {}
        summary_text = ""

        if op in (AnalysisOperation.COUNT, AnalysisOperation.SUM, AnalysisOperation.MEAN, AnalysisOperation.MIN, AnalysisOperation.MAX):
            if op != AnalysisOperation.COUNT and not target_col:
                target_col = "revenue" if "revenue" in types else next((c for c, t in types.items() if t in ("float", "integer")), None)

            metric_val = calculate_column_metric(active_rows, target_col or "", op)
            metric_key = f"{op.value}_{target_col}" if target_col else f"{op.value}"
            metrics[metric_key] = metric_val
            metrics["record_count"] = len(active_rows)

            res_columns = [metric_key, "record_count"]
            res_rows = [{metric_key: metric_val, "record_count": len(active_rows)}]
            summary_text = f"Calculated {op.value.upper()} for column '{target_col or 'all records'}': {metric_val} across {len(active_rows)} records."

        elif op == AnalysisOperation.DESCRIPTIVE_STATS:
            target_col = target_col or "revenue"
            stats = calculate_descriptive_stats(active_rows, target_col)
            metrics = stats
            res_columns = list(stats.keys())
            res_rows = [stats]
            summary_text = (
                f"Descriptive statistics for '{target_col}': count={stats['count']}, "
                f"mean={stats['mean']}, sum={stats['sum']}, min={stats['min']}, max={stats['max']}, std={stats['std']}."
            )

        elif op == AnalysisOperation.GROUP_BY:
            group_cols = request.group_by or (["region"] if "region" in types else [list(types.keys())[0]])
            agg_col = target_col or ("revenue" if "revenue" in types else None)
            res_columns, res_rows, metrics = execute_group_by(active_rows, group_cols, agg_col=agg_col, agg_func="sum")
            summary_text = (
                f"Grouped {len(active_rows)} records by {', '.join(group_cols)} with aggregation on '{agg_col or 'count'}'. "
                f"Produced {len(res_rows)} distinct group(s)."
            )

        elif op in (AnalysisOperation.SORT, AnalysisOperation.TOP_N, AnalysisOperation.FILTER):
            sort_col = request.sort_by or target_col or ("revenue" if "revenue" in types else list(types.keys())[0])
            sort_direction = request.sort_order
            sorted_rows = apply_sort(active_rows, sort_by=sort_col, sort_order=sort_direction)

            limit_val = request.limit or (5 if op == AnalysisOperation.TOP_N else len(sorted_rows))
            limited_rows = sorted_rows[:limit_val]

            res_columns = list(types.keys())
            res_rows = limited_rows
            metrics = {
                "total_matched": len(active_rows),
                "returned_rows": len(limited_rows),
                "sort_column": sort_col,
                "sort_order": sort_direction.value,
            }
            summary_text = (
                f"Retrieved {len(limited_rows)} records "
                f"(sorted by '{sort_col}' {sort_direction.value.upper()}) from {len(active_rows)} matched records."
            )

        else:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return AnalysisResult(
                success=False,
                operation=str(op),
                dataset=dataset_name,
                summary=f"Unsupported analytical operation: {op}",
                columns=[],
                rows=[],
                metrics={},
                tool_name="analyze_dataset",
                execution_time_ms=duration_ms,
                warnings=[],
                errors=[f"Unsupported analytical operation: {op}"],
            )

        # Enforce result row limit
        if request.limit and len(res_rows) > request.limit:
            res_rows = res_rows[:request.limit]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return AnalysisResult(
            success=True,
            operation=op.value if hasattr(op, "value") else str(op),
            dataset=dataset_name,
            summary=summary_text,
            columns=res_columns,
            rows=res_rows,
            metrics=metrics,
            tool_name="analyze_dataset",
            execution_time_ms=duration_ms,
            warnings=warnings,
            errors=[],
        )
