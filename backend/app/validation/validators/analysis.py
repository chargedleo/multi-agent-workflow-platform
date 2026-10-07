"""Numerical and analytical consistency validator.

Validates structured analytical calculations, aggregations, mathematical relationships,
and bounds produced by the Data Analysis Agent and MCP tools.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.validation.schemas import (
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)


def validate_analysis_results(
    analysis_results: Optional[Dict[str, Any]],
    state: Dict[str, Any],
) -> Tuple[List[ValidationIssue], int]:
    """Validate data analysis results for mathematical and structural integrity.

    Returns:
        Tuple of (recorded_issues, checked_count)
    """
    issues: List[ValidationIssue] = []
    checks = 0

    if not analysis_results:
        return issues, checks

    checks += 1
    status = analysis_results.get("status")
    if status == "not_required":
        return issues, checks

    if status == "failed":
        # Controlled failure is acceptable if error is clearly identified
        checks += 1
        if analysis_results.get("success") is True:
            issues.append(
                ValidationIssue(
                    code="TOOL_ERROR_REPORTED_AS_SUCCESS",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.NUMERICAL_CONSISTENCY,
                    message="Analysis status is 'failed' but success flag is marked True.",
                    recoverable=False,
                    source="data_analysis",
                )
            )
        return issues, checks

    # 1. Structure validation
    checks += 1
    metrics = analysis_results.get("metrics")
    if metrics is None or not isinstance(metrics, dict):
        issues.append(
            ValidationIssue(
                code="MALFORMED_ANALYSIS_METRICS",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.NUMERICAL_CONSISTENCY,
                message="Analysis completed but 'metrics' dictionary is missing or malformed.",
                recoverable=True,
                source="data_analysis",
            )
        )
        return issues, checks

    # 2. Type validation for metrics
    count_val: Optional[float] = None
    sum_val: Optional[float] = None
    mean_val: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None

    KNOWN_METADATA_METRIC_KEYS = {"sort_column", "sort_order", "group_by", "aggregation", "column", "status", "dataset"}

    for m_key, m_val in metrics.items():
        checks += 1
        if m_key.lower() in KNOWN_METADATA_METRIC_KEYS:
            continue

        if m_val is not None and not isinstance(m_val, (int, float)):
            issues.append(
                ValidationIssue(
                    code="NON_NUMERIC_METRIC_VALUE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.NUMERICAL_CONSISTENCY,
                    message=f"Metric '{m_key}' has non-numeric value '{m_val}' of type {type(m_val).__name__}.",
                    evidence=f"{m_key}={m_val}",
                    recoverable=True,
                    source="data_analysis",
                )
            )
            continue

        if m_val is None:
            continue

        num = float(m_val)
        k_lower = m_key.lower()

        # Capture key variables for mathematical verification
        if "count" in k_lower:
            count_val = num
            checks += 1
            if num < 0:
                issues.append(
                    ValidationIssue(
                        code="NEGATIVE_COUNT_VALUE",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.NUMERICAL_CONSISTENCY,
                        message=f"Count metric '{m_key}' is negative ({num}).",
                        evidence=f"{m_key}={num}",
                        recoverable=False,
                        source="data_analysis",
                    )
                )
        elif "sum" in k_lower or "total" in k_lower:
            sum_val = num
        elif "mean" in k_lower or "avg" in k_lower or "average" in k_lower:
            mean_val = num
        elif "min" in k_lower:
            min_val = num
        elif "max" in k_lower:
            max_val = num

    # 3. Mathematical reconciliation: count, sum, mean
    # If count, sum, and mean are all provided, verify sum / count == mean (within floating point delta)
    if count_val is not None and sum_val is not None and mean_val is not None and count_val > 0:
        checks += 1
        expected_mean = sum_val / count_val
        diff = abs(expected_mean - mean_val)
        if diff > 0.05:
            issues.append(
                ValidationIssue(
                    code="INCONSISTENT_MEAN_SUM_COUNT",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.NUMERICAL_CONSISTENCY,
                    message=(
                        f"Mathematical inconsistency: sum ({sum_val}) divided by count ({count_val}) "
                        f"yields {expected_mean:.2f}, but reported mean is {mean_val:.2f}."
                    ),
                    evidence=f"sum={sum_val}, count={count_val}, reported_mean={mean_val}, calculated_mean={expected_mean:.2f}",
                    recoverable=True,
                    source="data_analysis",
                )
            )

    # 4. Bounds verification: min <= mean <= max
    if min_val is not None and max_val is not None:
        checks += 1
        if min_val > max_val:
            issues.append(
                ValidationIssue(
                    code="MIN_EXCEEDS_MAX",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.NUMERICAL_CONSISTENCY,
                    message=f"Minimum value ({min_val}) is strictly greater than maximum value ({max_val}).",
                    evidence=f"min={min_val}, max={max_val}",
                    recoverable=False,
                    source="data_analysis",
                )
            )
        if mean_val is not None:
            checks += 1
            if mean_val < min_val or mean_val > max_val:
                issues.append(
                    ValidationIssue(
                        code="MEAN_OUTSIDE_MIN_MAX_BOUNDS",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.NUMERICAL_CONSISTENCY,
                        message=f"Mean value ({mean_val}) lies outside [min: {min_val}, max: {max_val}] interval.",
                        evidence=f"min={min_val}, mean={mean_val}, max={max_val}",
                        recoverable=False,
                        source="data_analysis",
                    )
                )

    # 5. Group reconciliation: check group rows sum matches total if total is given
    rows = analysis_results.get("rows") or []
    operation = analysis_results.get("operation")
    if operation == "group_by" and rows and sum_val is not None:
        checks += 1
        # Extract row sum values
        row_sums: List[float] = []
        for r in rows:
            for k, v in r.items():
                if ("sum" in k.lower() or "revenue" in k.lower() or "total" in k.lower()) and isinstance(v, (int, float)):
                    row_sums.append(float(v))
                    break

        if row_sums and len(row_sums) == len(rows):
            reconciled_sum = sum(row_sums)
            if abs(reconciled_sum - sum_val) > 0.05:
                issues.append(
                    ValidationIssue(
                        code="GROUP_SUM_MISMATCH",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.NUMERICAL_CONSISTENCY,
                        message=f"Sum of group rows ({reconciled_sum:.2f}) does not match total sum metric ({sum_val:.2f}).",
                        evidence=f"row_sum={reconciled_sum}, total_sum={sum_val}",
                        recoverable=True,
                        source="data_analysis",
                    )
                )

    # 6. Top-N length verification
    if operation == "top_n":
        checks += 1
        # If user query requested top N (e.g. 5), verify rows length <= N
        query = (state.get("user_query") or "").lower()
        import re
        top_match = re.search(r"top\s+(\d+)", query)
        if top_match:
            requested_n = int(top_match.group(1))
            if len(rows) > requested_n:
                issues.append(
                    ValidationIssue(
                        code="TOP_N_EXCEEDED_LIMIT",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.NUMERICAL_CONSISTENCY,
                        message=f"Returned {len(rows)} records for top-{requested_n} request.",
                        evidence=f"returned={len(rows)}, requested={requested_n}",
                        recoverable=True,
                        source="data_analysis",
                    )
                )

    return issues, checks
