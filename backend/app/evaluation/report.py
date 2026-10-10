"""Evaluation report generation and run comparison (Milestone 9A).

Provides:
- Serialization and formatting of EvaluationRunReport
- Metric-by-metric delta comparison between baseline and target runs
- Regression and improvement classification
"""

import json
from typing import Any, Dict, List, Optional

from backend.app.evaluation.schemas import (
    EvaluationComparisonReport,
    EvaluationRunReport,
    MetricDelta,
)

# Higher is better for all quality, coverage, and accuracy metrics
HIGHER_IS_BETTER = {
    "mean_recall_at_1",
    "mean_recall_at_3",
    "mean_recall_at_5",
    "mean_precision_at_1",
    "mean_precision_at_3",
    "mean_precision_at_5",
    "mean_hit_rate_at_1",
    "mean_hit_rate_at_3",
    "mean_hit_rate_at_5",
    "mrr",
    "map_score",
    "citation_presence_rate",
    "identifier_validity_rate",
    "source_validity_rate",
    "page_validity_rate",
    "attribution_match_rate",
    "mean_fact_coverage",
    "abstention_accuracy",
    "guardrail_accuracy",
    "true_positive_rate",
}

# Lower is better for error rates and latency
LOWER_IS_BETTER = {
    "false_positive_rate",
    "false_negative_rate",
    "avg_retrieval_latency_ms",
}

DEFAULT_DELTA_THRESHOLD = 0.005  # 0.5% threshold for significant change


def compare_evaluation_metrics(
    baseline_summary: Dict[str, Any],
    comparison_summary: Dict[str, Any],
    threshold: float = DEFAULT_DELTA_THRESHOLD,
) -> Dict[str, MetricDelta]:
    """Compute per-metric deltas and classify them as IMPROVED, REGRESSED, or UNCHANGED."""
    all_keys = set(baseline_summary.keys()) | set(comparison_summary.keys())
    metric_deltas: Dict[str, MetricDelta] = {}

    for key in sorted(all_keys):
        # Skip non-numeric or count fields
        if key in {"total_cases", "completed_cases", "failed_cases", "skipped_cases"}:
            continue

        b_val = baseline_summary.get(key)
        c_val = comparison_summary.get(key)

        # Handle None or non-numeric values
        if b_val is None and c_val is None:
            continue
        if b_val is None or c_val is None:
            metric_deltas[key] = MetricDelta(
                baseline=float(b_val) if b_val is not None else None,
                comparison=float(c_val) if c_val is not None else None,
                delta=None,
                status="NA",
            )
            continue

        try:
            b_float = float(b_val)
            c_float = float(c_val)
        except (ValueError, TypeError):
            continue

        delta = round(c_float - b_float, 4)

        if abs(delta) < threshold:
            status = "UNCHANGED"
        elif key in HIGHER_IS_BETTER:
            status = "IMPROVED" if delta > 0 else "REGRESSED"
        elif key in LOWER_IS_BETTER:
            status = "IMPROVED" if delta < 0 else "REGRESSED"
        else:
            status = "UNCHANGED"

        metric_deltas[key] = MetricDelta(
            baseline=round(b_float, 4),
            comparison=round(c_float, 4),
            delta=delta,
            status=status,
        )

    return metric_deltas


def compare_evaluation_runs(
    baseline_run: Dict[str, Any],
    comparison_run: Dict[str, Any],
    threshold: float = DEFAULT_DELTA_THRESHOLD,
) -> EvaluationComparisonReport:
    """Compare two evaluation runs and generate an EvaluationComparisonReport."""
    baseline_id = str(baseline_run.get("id") or baseline_run.get("evaluation_run_id") or "baseline")
    comparison_id = str(comparison_run.get("id") or comparison_run.get("evaluation_run_id") or "comparison")
    baseline_mode = str(baseline_run.get("mode", "unknown"))
    comparison_mode = str(comparison_run.get("mode", "unknown"))

    baseline_summary = baseline_run.get("summary") or baseline_run.get("aggregate_metrics") or {}
    comparison_summary = comparison_run.get("summary") or comparison_run.get("aggregate_metrics") or {}

    metric_deltas = compare_evaluation_metrics(baseline_summary, comparison_summary, threshold=threshold)

    regressions = [k for k, d in metric_deltas.items() if d.status == "REGRESSED"]
    improvements = [k for k, d in metric_deltas.items() if d.status == "IMPROVED"]

    if len(regressions) > len(improvements):
        verdict = "REGRESSED"
    elif len(improvements) > len(regressions):
        verdict = "IMPROVED"
    else:
        verdict = "NEUTRAL"

    return EvaluationComparisonReport(
        baseline_run_id=baseline_id,
        comparison_run_id=comparison_id,
        baseline_mode=baseline_mode,
        comparison_mode=comparison_mode,
        metric_deltas=metric_deltas,
        regressions=regressions,
        improvements=improvements,
        summary_verdict=verdict,
    )
