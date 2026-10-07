"""Response schema validator.

Validates that the final agent response strictly adheres to the required structure,
contains non-empty answers and key points, has calibrated confidence bounds,
and maintains well-formed structured fields.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.validation.schemas import (
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)


def validate_response_schema(
    final_answer: Optional[Dict[str, Any]],
    state: Dict[str, Any],
) -> Tuple[List[ValidationIssue], int]:
    """Validate final response schema structure and completeness.

    Returns:
        Tuple of (recorded_issues, checked_count)
    """
    issues: List[ValidationIssue] = []
    checks = 0

    checks += 1
    if not final_answer or not isinstance(final_answer, dict):
        issues.append(
            ValidationIssue(
                code="MISSING_FINAL_ANSWER",
                severity=ValidationSeverity.CRITICAL,
                category=ValidationCategory.RESPONSE_SCHEMA,
                message="Workflow did not produce a valid structured final_answer object.",
                recoverable=True,
                source="responder",
            )
        )
        return issues, checks

    # 1. Answer body validation
    checks += 1
    answer = final_answer.get("answer")
    if not answer or not isinstance(answer, str) or not answer.strip():
        issues.append(
            ValidationIssue(
                code="EMPTY_ANSWER_BODY",
                severity=ValidationSeverity.CRITICAL,
                category=ValidationCategory.RESPONSE_SCHEMA,
                message="The response answer field is empty or whitespace only.",
                recoverable=True,
                source="responder",
            )
        )

    # 2. Key points validation
    checks += 1
    key_points = final_answer.get("key_points")
    if not isinstance(key_points, list) or len(key_points) == 0:
        issues.append(
            ValidationIssue(
                code="MISSING_KEY_POINTS",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.RESPONSE_SCHEMA,
                message="Response must include at least one executive key takeaway point.",
                recoverable=True,
                source="responder",
            )
        )
    else:
        checks += 1
        empty_pts = [p for p in key_points if not isinstance(p, str) or not p.strip()]
        if empty_pts:
            issues.append(
                ValidationIssue(
                    code="EMPTY_KEY_POINT_ITEM",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.RESPONSE_SCHEMA,
                    message=f"Found {len(empty_pts)} blank key point(s).",
                    recoverable=True,
                    source="responder",
                )
            )

    # 3. Confidence score validation
    checks += 1
    confidence = final_answer.get("confidence")
    if confidence is None or not isinstance(confidence, (int, float)):
        issues.append(
            ValidationIssue(
                code="INVALID_CONFIDENCE_TYPE",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.RESPONSE_SCHEMA,
                message="Confidence score is missing or not a numerical value.",
                recoverable=True,
                source="responder",
            )
        )
    else:
        checks += 1
        if confidence < 0.0 or confidence > 1.0:
            issues.append(
                ValidationIssue(
                    code="OUT_OF_BOUNDS_CONFIDENCE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.RESPONSE_SCHEMA,
                    message=f"Confidence score {confidence} is outside valid bounds [0.0, 1.0].",
                    evidence=f"confidence={confidence}",
                    recoverable=True,
                    source="responder",
                )
            )

    # 4. Request ID validation
    checks += 1
    request_id = final_answer.get("request_id")
    expected_req_id = state.get("request_id")
    if not request_id:
        issues.append(
            ValidationIssue(
                code="MISSING_REQUEST_ID",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.RESPONSE_SCHEMA,
                message="Response does not contain request_id attribute.",
                recoverable=True,
                source="responder",
            )
        )
    elif expected_req_id and request_id != expected_req_id:
        issues.append(
            ValidationIssue(
                code="MISMATCHED_REQUEST_ID",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.RESPONSE_SCHEMA,
                message=f"Response request_id '{request_id}' does not match workflow request_id '{expected_req_id}'.",
                evidence=f"expected={expected_req_id}, actual={request_id}",
                recoverable=True,
                source="responder",
            )
        )

    # 5. Analysis section presence when analysis was completed
    analysis_results = state.get("analysis_results") or final_answer.get("analysis_results")
    if analysis_results and analysis_results.get("status") == "completed":
        checks += 1
        summary = analysis_results.get("summary", "")
        # If analysis completed successfully, answer should contain reference to analysis or summary
        if answer and summary and summary not in answer and "analysis" not in answer.lower():
            issues.append(
                ValidationIssue(
                    code="MISSING_ANALYSIS_IN_ANSWER",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.RESPONSE_SCHEMA,
                    message="Quantitative analysis completed but findings are omitted from the synthesized answer.",
                    evidence=f"analysis_summary='{summary}'",
                    recoverable=True,
                    source="responder",
                )
            )

    return issues, checks
