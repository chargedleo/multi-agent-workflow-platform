"""Guardrail and validation evaluation engine (Milestone 9A).

Evaluates the existing ValidationService against labeled test cases covering:
- Clean/supported answers (PASS)
- Unsupported factual claims (FAIL)
- Missing required citations (ERROR / FAIL)
- Recoverable validation failures (RECOVERABLE)
- Blocked outputs (BLOCKED, e.g. SQL injection / unapproved tools)

Computes per-case GuardrailMetrics and aggregate TPR, FPR, FNR, and Accuracy.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.evaluation.schemas import GuardrailMetrics
from backend.app.validation.schemas import ValidationResult
from backend.app.validation.service import ValidationService


def evaluate_state_guardrails(
    state: Dict[str, Any],
    expected_status: str = "PASS",
    attempt: int = 1,
) -> Tuple[GuardrailMetrics, ValidationResult]:
    """Evaluate current workflow state using existing ValidationService and compare with expectation.

    Args:
        state: Workflow state dictionary.
        expected_status: Expected outcome ('PASS', 'FAIL', 'RECOVERABLE', 'BLOCKED').
        attempt: Iteration index for bounded correction loop.

    Returns:
        Tuple of (GuardrailMetrics, raw ValidationResult).
    """
    clean_expected = str(expected_status).upper().strip()
    val_result: ValidationResult = ValidationService.validate_workflow_state(state, attempt=attempt)
    actual_status = val_result.status.value

    status_match = actual_status == clean_expected

    recovery_attempted = actual_status == "RECOVERABLE" or attempt > 1

    metrics = GuardrailMetrics(
        actual_status=actual_status,
        expected_status=clean_expected,
        status_match=status_match,
        validation_score=val_result.score,
        issues_detected_count=len(val_result.issues),
        recovery_attempted=recovery_attempted,
    )

    return metrics, val_result


def compute_aggregate_guardrail_metrics(
    guardrail_results: List[GuardrailMetrics],
) -> Dict[str, Optional[float]]:
    """Compute aggregate confusion matrix metrics across labeled guardrail cases.

    Ground-Truth Definitions:
    - Positive Case (Violation Expected): expected_status in {'FAIL', 'RECOVERABLE', 'BLOCKED'}
    - Negative Case (Valid / Clean Expected): expected_status == 'PASS'

    Outcome Classifications:
    - True Positive (TP): Violation expected, and actual_status is NOT PASS
    - False Positive (FP): Clean expected (PASS), but actual_status is NOT PASS
    - True Negative (TN): Clean expected (PASS), and actual_status is PASS
    - False Negative (FN): Violation expected, but actual_status is PASS

    Denominator Conventions:
    - If total positives (TP + FN) == 0: TPR and FNR are None (undefined).
    - If total negatives (FP + TN) == 0: FPR is None (undefined).

    Returns:
        Dictionary with accuracy, TPR, FPR, FNR.
    """
    if not guardrail_results:
        return {
            "guardrail_accuracy": 0.0,
            "true_positive_rate": None,
            "false_positive_rate": None,
            "false_negative_rate": None,
        }

    tp = 0
    fp = 0
    tn = 0
    fn = 0

    for res in guardrail_results:
        expected_positive = res.expected_status != "PASS"
        actual_positive = res.actual_status != "PASS"

        if expected_positive and actual_positive:
            tp += 1
        elif not expected_positive and actual_positive:
            fp += 1
        elif not expected_positive and not actual_positive:
            tn += 1
        elif expected_positive and not actual_positive:
            fn += 1

    total = len(guardrail_results)
    exact_matches = sum(1 for r in guardrail_results if r.status_match)
    accuracy = round(exact_matches / total, 4)

    total_positives = tp + fn
    total_negatives = fp + tn

    tpr = round(tp / total_positives, 4) if total_positives > 0 else None
    fpr = round(fp / total_negatives, 4) if total_negatives > 0 else None
    fnr = round(fn / total_positives, 4) if total_positives > 0 else None

    return {
        "guardrail_accuracy": accuracy,
        "true_positive_rate": tpr,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
    }
