"""Unit tests for evaluation report generation and run comparison (Milestone 9A)."""

import pytest

from backend.app.evaluation.report import (
    compare_evaluation_metrics,
    compare_evaluation_runs,
)
from backend.app.evaluation.schemas import EvaluationComparisonReport


def test_compare_identical_metrics():
    """Comparing identical summaries should result in zero deltas and UNCHANGED status."""
    baseline = {
        "mean_recall_at_3": 0.85,
        "mean_fact_coverage": 0.90,
        "guardrail_accuracy": 0.95,
        "false_positive_rate": 0.05,
        "avg_retrieval_latency_ms": 25.0,
    }
    comparison = {
        "mean_recall_at_3": 0.85,
        "mean_fact_coverage": 0.90,
        "guardrail_accuracy": 0.95,
        "false_positive_rate": 0.05,
        "avg_retrieval_latency_ms": 25.0,
    }

    deltas = compare_evaluation_metrics(baseline, comparison)
    assert len(deltas) == 5
    for key, delta in deltas.items():
        assert delta.status == "UNCHANGED"
        assert delta.delta == 0.0


def test_compare_improved_run():
    """Higher quality metrics and lower latency should be classified as IMPROVED."""
    baseline_run = {
        "id": "run-001",
        "mode": "metric_only",
        "summary": {
            "mean_recall_at_3": 0.75,
            "mean_fact_coverage": 0.70,
            "guardrail_accuracy": 0.80,
            "avg_retrieval_latency_ms": 50.0,
        },
    }
    comparison_run = {
        "id": "run-002",
        "mode": "metric_only",
        "summary": {
            "mean_recall_at_3": 0.90,  # Improved
            "mean_fact_coverage": 0.85,  # Improved
            "guardrail_accuracy": 0.95,  # Improved
            "avg_retrieval_latency_ms": 20.0,  # Improved (lower)
        },
    }

    report = compare_evaluation_runs(baseline_run, comparison_run)
    assert isinstance(report, EvaluationComparisonReport)
    assert report.summary_verdict == "IMPROVED"
    assert len(report.improvements) == 4
    assert len(report.regressions) == 0


def test_compare_regressed_run():
    """Lower quality metrics and higher error rate should be classified as REGRESSED."""
    baseline_run = {
        "id": "run-001",
        "mode": "metric_only",
        "summary": {
            "mean_recall_at_3": 0.90,
            "guardrail_accuracy": 0.95,
            "false_positive_rate": 0.02,
        },
    }
    comparison_run = {
        "id": "run-002",
        "mode": "metric_only",
        "summary": {
            "mean_recall_at_3": 0.60,  # Regressed
            "guardrail_accuracy": 0.75,  # Regressed
            "false_positive_rate": 0.15,  # Regressed (higher)
        },
    }

    report = compare_evaluation_runs(baseline_run, comparison_run)
    assert report.summary_verdict == "REGRESSED"
    assert len(report.regressions) == 3
    assert len(report.improvements) == 0


def test_compare_missing_metrics_handled():
    """Metrics missing from one run should be assigned NA status without crashing."""
    baseline = {"mean_recall_at_1": 0.8}
    comparison = {"guardrail_accuracy": 0.9}

    deltas = compare_evaluation_metrics(baseline, comparison)
    assert "mean_recall_at_1" in deltas
    assert deltas["mean_recall_at_1"].status == "NA"
    assert "guardrail_accuracy" in deltas
    assert deltas["guardrail_accuracy"].status == "NA"
