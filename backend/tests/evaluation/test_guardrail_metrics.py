"""Unit tests for guardrail and validation evaluation."""

import pytest
from backend.app.evaluation.guardrail_metrics import (
    compute_aggregate_guardrail_metrics,
    evaluate_state_guardrails,
)
from backend.app.evaluation.schemas import GuardrailMetrics


def test_guardrail_evaluation_clean_pass():
    """Verify clean state produces PASS and matches expected label."""
    clean_state = {
        "user_query": "What is PostgreSQL?",
        "final_answer": {
            "request_id": "req-clean-123",
            "answer": "PostgreSQL is an open-source object-relational database system.",
            "key_points": ["Object-relational", "Open-source"],
            "confidence": 0.95,
            "sources": [],
        },
        "retrieved_documents": [],
        "intermediate_results": [],
    }

    metrics, raw_res = evaluate_state_guardrails(clean_state, expected_status="PASS")
    assert metrics.actual_status == "PASS"
    assert metrics.expected_status == "PASS"
    assert metrics.status_match is True
    assert metrics.validation_score == 1.0
    assert metrics.issues_detected_count == 0


def test_guardrail_evaluation_blocked_violation():
    """Verify state with SQL injection or unapproved tool produces BLOCKED."""
    malicious_state = {
        "user_query": "Drop all orders",
        "final_answer": {
            "request_id": "req-malicious-123",
            "answer": "Executed dangerous command",
            "key_points": ["Executed"],
            "confidence": 0.5,
            "sources": [],
        },
        "intermediate_results": [
            {
                "agent": "data_analysis",
                "output": {
                    "analysis_required": True,
                    "tool_name": "UNAPPROVED_TOOL_NAME",
                    "arguments": {"cmd": "DROP TABLE users;"},
                    "result": {"error": "blocked"},
                },
            }
        ],
    }

    metrics, raw_res = evaluate_state_guardrails(malicious_state, expected_status="BLOCKED")
    assert metrics.actual_status == "BLOCKED"
    assert metrics.status_match is True
    assert metrics.validation_score < 1.0


def test_guardrail_evaluation_recoverable():
    """Verify recoverable error on attempt 1 produces RECOVERABLE."""
    recoverable_state = {
        "user_query": "Explain architecture",
        "final_answer": {
            "answer": "Short",  # Missing key_points, too short
            "confidence": 0.9,
            "sources": [],
        },
        "retrieved_documents": [],
    }

    metrics, raw_res = evaluate_state_guardrails(recoverable_state, expected_status="RECOVERABLE", attempt=1)
    assert metrics.actual_status == "RECOVERABLE"
    assert metrics.status_match is True
    assert metrics.recovery_attempted is True


def test_aggregate_guardrail_metrics_confusion_matrix():
    """Verify TPR, FPR, FNR, and accuracy calculation across mixed cases."""
    case1 = GuardrailMetrics(actual_status="PASS", expected_status="PASS", status_match=True)      # TN
    case2 = GuardrailMetrics(actual_status="FAIL", expected_status="FAIL", status_match=True)      # TP
    case3 = GuardrailMetrics(actual_status="BLOCKED", expected_status="PASS", status_match=False)  # FP
    case4 = GuardrailMetrics(actual_status="PASS", expected_status="FAIL", status_match=False)     # FN

    results = [case1, case2, case3, case4]
    agg = compute_aggregate_guardrail_metrics(results)

    # Total = 4, exact matches = 2 -> Accuracy = 0.5
    assert agg["guardrail_accuracy"] == 0.5
    # Positives (expected != PASS) = case2, case4 -> total 2. TP = case2 (1) -> TPR = 1/2 = 0.5
    assert agg["true_positive_rate"] == 0.5
    # FNR = FN (case4) / 2 = 0.5
    assert agg["false_negative_rate"] == 0.5
    # Negatives (expected == PASS) = case1, case3 -> total 2. FP = case3 (1) -> FPR = 1/2 = 0.5
    assert agg["false_positive_rate"] == 0.5


def test_aggregate_guardrail_metrics_undefined_denominators():
    """Verify undefined metrics return None when no positive or negative examples exist."""
    # Only clean passes: no positives
    all_clean = [
        GuardrailMetrics(actual_status="PASS", expected_status="PASS", status_match=True)
    ]
    agg = compute_aggregate_guardrail_metrics(all_clean)
    assert agg["guardrail_accuracy"] == 1.0
    # No positives -> TPR and FNR must be None (undefined)
    assert agg["true_positive_rate"] is None
    assert agg["false_negative_rate"] is None
    # Negatives exist, FP = 0 -> FPR = 0.0
    assert agg["false_positive_rate"] == 0.0
