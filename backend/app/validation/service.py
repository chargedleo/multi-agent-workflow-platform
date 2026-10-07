"""Validation Service.

Coordinates modular validators across schema integrity, citation provenance,
mathematical consistency, tool outputs, and claim verification. Produces a
structured ValidationResult guiding workflow routing and agent correction.
"""

import time
from typing import Any, Dict, List
from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.validation.schemas import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from backend.app.validation.validators import (
    validate_analysis_results,
    validate_citations,
    validate_claims_and_numbers,
    validate_response_schema,
    validate_tool_outputs,
)

logger = get_logger(__name__)


class ValidationService:
    """Service orchestrating guardrail checks and computing workflow validation status."""

    @classmethod
    def validate_workflow_state(
        cls,
        state: Dict[str, Any],
        attempt: int = 1,
    ) -> ValidationResult:
        """Execute all validation checks against the current workflow state.

        Args:
            state: The current WorkflowState dictionary.
            attempt: Current correction loop iteration index (1-based).

        Returns:
            Structured ValidationResult with status, score, and recorded issues.
        """
        start_time = time.perf_counter()
        settings = get_settings()

        final_answer = state.get("final_answer")
        analysis_results = state.get("analysis_results") or (final_answer.get("analysis_results") if isinstance(final_answer, dict) else None)
        intermediate_results = state.get("intermediate_results") or []

        all_issues: List[ValidationIssue] = []
        total_checks = 0

        # 1. Response Schema Validation
        schema_issues, schema_checks = validate_response_schema(final_answer, state)
        all_issues.extend(schema_issues)
        total_checks += schema_checks

        # 2. Citation Provenance Validation
        citation_issues, citation_checks = validate_citations(final_answer, state)
        all_issues.extend(citation_issues)
        total_checks += citation_checks

        # 3. Numerical & Analysis Results Validation
        analysis_issues, analysis_checks = validate_analysis_results(analysis_results, state)
        all_issues.extend(analysis_issues)
        total_checks += analysis_checks

        # 4. Tool Output & Invocation Validation
        tool_issues, tool_checks = validate_tool_outputs(intermediate_results, state)
        all_issues.extend(tool_issues)
        total_checks += tool_checks

        # 5. Unsupported Claims & Figures Validation
        claim_issues, claim_checks = validate_claims_and_numbers(final_answer, state)
        all_issues.extend(claim_issues)
        total_checks += claim_checks

        # Categorize issue severities
        critical_issues = [i for i in all_issues if i.severity == ValidationSeverity.CRITICAL]
        error_issues = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
        warning_issues = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]

        failed_items = len(critical_issues) + len(error_issues) + len(warning_issues)

        # Determine overall status
        status: ValidationStatus
        max_attempts = settings.MAX_VALIDATION_ATTEMPTS

        if critical_issues:
            # Check if any issue is a safety/injection blocker
            is_blocked = any(i.code in ("UNAPPROVED_TOOL_NAME", "SQL_INJECTION") for i in critical_issues)
            status = ValidationStatus.BLOCKED if is_blocked else ValidationStatus.FAIL

        elif error_issues:
            # All errors must be recoverable and within attempt budget for a retry
            all_errors_recoverable = all(i.recoverable for i in error_issues)
            if all_errors_recoverable and attempt < max_attempts:
                status = ValidationStatus.RECOVERABLE
            else:
                status = ValidationStatus.FAIL

        else:
            status = ValidationStatus.PASS

        # Calculate calibrated validation score
        error_penalty = len(critical_issues) * 0.4 + len(error_issues) * 0.2
        warning_penalty = len(warning_issues) * 0.05
        raw_score = 1.0 - (error_penalty + warning_penalty)
        final_score = max(0.0, min(1.0, round(raw_score, 2)))

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ValidationResult(
            status=status,
            score=final_score,
            issues=all_issues,
            checked_items=total_checks,
            failed_items=failed_items,
            validator_name="comprehensive_workflow_guardrails",
            validation_duration_ms=duration_ms,
            attempt=attempt,
        )
