"""Unsupported claim and numerical verification validator.

Detects fabricated, hallucinated, or unsupported quantitative claims in the final
synthesized response by comparing stated figures against validated analysis metrics
and retrieved document context.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.validation.schemas import (
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)

# Regex to capture numbers, currency amounts, and percentages
NUMBER_PATTERN = re.compile(r"(\$?\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b%?)")


def _clean_and_parse_number(token: str) -> Tuple[Optional[float], bool]:
    """Parse a number token into a float and flag if it had currency/percentage prefix/suffix."""
    token = token.strip()
    is_financial = token.startswith("$")
    is_percent = token.endswith("%")

    cleaned = token.lstrip("$").rstrip("%").replace(",", "")
    try:
        val = float(cleaned)
        return val, (is_financial or is_percent)
    except (ValueError, TypeError):
        return None, False


def validate_claims_and_numbers(
    final_answer: Optional[Dict[str, Any]],
    state: Dict[str, Any],
) -> Tuple[List[ValidationIssue], int]:
    """Verify that numerical and statistical claims in the answer are grounded in evidence.

    Returns:
        Tuple of (recorded_issues, checked_count)
    """
    issues: List[ValidationIssue] = []
    checks = 0

    if not final_answer:
        return issues, checks

    answer_text = final_answer.get("answer") or ""
    if not answer_text:
        return issues, checks

    # 1. Gather all verified numbers from analysis results and state
    verified_numbers: Set[float] = set()
    verified_evidence_summary: List[str] = []

    analysis_results = state.get("analysis_results") or final_answer.get("analysis_results")
    has_analysis = bool(analysis_results and analysis_results.get("status") == "completed")

    if has_analysis:
        metrics = analysis_results.get("metrics") or {}
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                f_val = float(v)
                verified_numbers.add(f_val)
                verified_evidence_summary.append(f"{k}={v}")

        rows = analysis_results.get("rows") or []
        for r in rows:
            for k, v in r.items():
                if isinstance(v, (int, float)):
                    verified_numbers.add(float(v))

    # Add numbers from retrieved documents
    retrieved_docs = state.get("retrieved_documents") or []
    for doc in retrieved_docs:
        text = (doc.get("content") or doc.get("text") or "")
        for m in NUMBER_PATTERN.finditer(text):
            num, _ = _clean_and_parse_number(m.group(1))
            if num is not None:
                verified_numbers.add(num)

    # Add numbers mentioned in the user query
    user_query = state.get("user_query") or ""
    for m in NUMBER_PATTERN.finditer(user_query):
        num, _ = _clean_and_parse_number(m.group(1))
        if num is not None:
            verified_numbers.add(num)

    # 2. Extract numbers from the final answer
    found_tokens = NUMBER_PATTERN.findall(answer_text)

    # Allow harmless common numbers: small integers (0..10), standard years, sections
    common_tolerated = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 100.0, 2024.0, 2025.0, 2026.0}

    for raw_token in found_tokens:
        checks += 1
        num_val, is_explicit_metric = _clean_and_parse_number(raw_token)
        if num_val is None:
            continue

        # Skip small formatting/enumeration numbers unless explicitly currency
        if not is_explicit_metric and num_val in common_tolerated:
            continue

        # Check if number matches any verified number (with floating point tolerance)
        is_supported = any(abs(num_val - v) < 0.01 for v in verified_numbers)

        if not is_supported and has_analysis:
            # Check context around token: does it look like revenue, total, count, or average?
            # Or is it an explicit currency figure (e.g. $190,000)?
            token_idx = answer_text.find(raw_token)
            window = answer_text[max(0, token_idx - 60) : min(len(answer_text), token_idx + len(raw_token) + 60)].lower()
            financial_context = any(
                term in window
                for term in ["revenue", "total", "sales", "average", "mean", "sum", "$", "dollar", "amount", "cost"]
            )

            if is_explicit_metric or (financial_context and num_val > 100):
                evidence_str = ", ".join(verified_evidence_summary[:3]) if verified_evidence_summary else "no analysis matches"
                issues.append(
                    ValidationIssue(
                        code="UNSUPPORTED_NUMERICAL_CLAIM",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.CLAIM_VERIFICATION,
                        message=(
                            f"The response states a figure of '{raw_token}', but verified analysis "
                            f"reports: {evidence_str}."
                        ),
                        evidence=f"unsupported_figure='{raw_token}', verified_metrics={evidence_str}",
                        recoverable=True,
                        source="claim",
                    )
                )

    return issues, checks
