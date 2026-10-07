"""Unit tests for ValidationService and modular validators."""

import pytest
from backend.app.validation.schemas import (
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from backend.app.validation.service import ValidationService
from backend.app.validation.validators.analysis import validate_analysis_results
from backend.app.validation.validators.citation import validate_citations
from backend.app.validation.validators.claim import validate_claims_and_numbers
from backend.app.validation.validators.response_schema import validate_response_schema
from backend.app.validation.validators.tool_output import validate_tool_outputs


# =============================================================================
# 1. Response Schema Validator Tests
# =============================================================================

def test_response_schema_valid():
    """Verify that a well-structured final answer passes schema validation."""
    state = {
        "request_id": "req-123",
        "final_answer": {
            "request_id": "req-123",
            "answer": "PostgreSQL is an advanced open-source relational database.",
            "key_points": ["ACID compliant", "Extensible data types", "Rich ecosystem"],
            "confidence": 0.95,
            "sources": [],
        },
    }
    issues, count = validate_response_schema(state["final_answer"], state)
    assert count > 0
    errors = [i for i in issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]
    assert len(errors) == 0


def test_response_schema_missing_answer():
    """Verify that an empty or missing answer is flagged as critical."""
    state = {
        "request_id": "req-123",
        "final_answer": {
            "request_id": "req-123",
            "answer": "",
            "key_points": ["Point 1"],
            "confidence": 0.9,
            "sources": [],
        },
    }
    issues, count = validate_response_schema(state["final_answer"], state)
    assert any(i.code == "EMPTY_ANSWER_BODY" for i in issues)


def test_response_schema_invalid_confidence():
    """Verify that out-of-range confidence values are flagged."""
    state = {
        "request_id": "req-123",
        "final_answer": {
            "request_id": "req-123",
            "answer": "Valid text here.",
            "key_points": ["Point 1"],
            "confidence": 1.5,
            "sources": [],
        },
    }
    issues, _ = validate_response_schema(state["final_answer"], state)
    assert any(i.code == "OUT_OF_BOUNDS_CONFIDENCE" for i in issues)


def test_response_schema_empty_key_points():
    """Verify that empty key points list is flagged as an error."""
    state = {
        "request_id": "req-123",
        "final_answer": {
            "request_id": "req-123",
            "answer": "Valid text here.",
            "key_points": [],
            "confidence": 0.85,
            "sources": [],
        },
    }
    issues, _ = validate_response_schema(state["final_answer"], state)
    assert any(i.code == "MISSING_KEY_POINTS" for i in issues)


# =============================================================================
# 2. Citation Provenance Validator Tests
# =============================================================================

def test_citations_valid_provenance():
    """Verify that cited sources matching retrieved documents pass."""
    state = {
        "retrieved_documents": [
            {
                "document_id": "doc-uuid-1",
                "chunk_id": "chunk-uuid-1",
                "filename": "quarterly_report.pdf",
                "content": "Q3 Revenue reached 1.2M USD.",
            }
        ],
        "final_answer": {
            "sources": [
                {
                    "document_id": "doc-uuid-1",
                    "chunk_id": "chunk-uuid-1",
                    "filename": "quarterly_report.pdf",
                    "snippet": "Q3 Revenue reached 1.2M USD.",
                }
            ]
        },
    }
    issues, count = validate_citations(state["final_answer"], state)
    assert count > 0
    errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
    assert len(errors) == 0


def test_citations_fabricated_document_detected():
    """Verify that fabricated document references not in retrieved set are flagged."""
    state = {
        "retrieved_documents": [
            {
                "document_id": "doc-uuid-1",
                "chunk_id": "chunk-uuid-1",
                "filename": "verified_doc.pdf",
                "content": "Real content.",
            }
        ],
        "final_answer": {
            "sources": [
                {
                    "document_id": "fake-doc-999",
                    "chunk_id": "fake-chunk-999",
                    "filename": "hallucinated_file.pdf",
                    "snippet": "Fabricated facts.",
                }
            ]
        },
    }
    issues, _ = validate_citations(state["final_answer"], state)
    assert any(i.code == "FABRICATED_DOCUMENT_CITATION" for i in issues)


def test_citations_duplicate_detection():
    """Verify that duplicate identical citations generate a warning/info."""
    state = {
        "retrieved_documents": [
            {
                "document_id": "doc-uuid-1",
                "chunk_id": "chunk-uuid-1",
                "filename": "doc.pdf",
                "content": "Same chunk content.",
            }
        ],
        "final_answer": {
            "sources": [
                {
                    "document_id": "doc-uuid-1",
                    "chunk_id": "chunk-uuid-1",
                    "filename": "doc.pdf",
                },
                {
                    "document_id": "doc-uuid-1",
                    "chunk_id": "chunk-uuid-1",
                    "filename": "doc.pdf",
                },
            ]
        },
    }
    issues, _ = validate_citations(state["final_answer"], state)
    assert any(i.code == "DUPLICATE_CITATION" for i in issues)


# =============================================================================
# 3. Numerical Consistency Validator Tests
# =============================================================================

def test_analysis_numerical_valid():
    """Verify that consistent descriptive statistics pass validation."""
    analysis_results = {
        "status": "completed",
        "success": True,
        "metrics": {
            "count": 100,
            "sum": 5000.0,
            "mean": 50.0,
            "min": 10.0,
            "max": 90.0,
        },
    }
    issues, count = validate_analysis_results(analysis_results, {})
    assert count > 0
    errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
    assert len(errors) == 0


def test_analysis_inconsistent_mean_detected():
    """Verify that mathematical mismatch between sum/count and mean is caught."""
    analysis_results = {
        "status": "completed",
        "success": True,
        "metrics": {
            "count": 100,
            "sum": 5000.0,
            "mean": 99.0,  # Should be 50.0
            "min": 10.0,
            "max": 100.0,
        },
    }
    issues, _ = validate_analysis_results(analysis_results, {})
    assert any(i.code == "INCONSISTENT_MEAN_SUM_COUNT" for i in issues)


def test_analysis_min_greater_than_max():
    """Verify that min > max triggers a numerical bounds error."""
    analysis_results = {
        "status": "completed",
        "success": True,
        "metrics": {
            "count": 10,
            "sum": 500.0,
            "mean": 50.0,
            "min": 80.0,
            "max": 20.0,  # Impossible: min > max
        },
    }
    issues, _ = validate_analysis_results(analysis_results, {})
    assert any(i.code == "MIN_EXCEEDS_MAX" for i in issues)


def test_analysis_group_sum_mismatch():
    """Verify that discrepancy between group rows sum and total sum metric is flagged."""
    analysis_results = {
        "status": "completed",
        "success": True,
        "operation": "group_by",
        "metrics": {
            "total_revenue": 1000.0,
        },
        "rows": [
            {"region": "North", "sum_revenue": 400.0},
            {"region": "South", "sum_revenue": 400.0},  # Sum is 800, but total_revenue is 1000
        ],
    }
    issues, _ = validate_analysis_results(analysis_results, {})
    assert any(i.code == "GROUP_SUM_MISMATCH" for i in issues)


# =============================================================================
# 4. Tool Output Validator Tests
# =============================================================================

def test_tool_outputs_approved_tools():
    """Verify that registered MCP tools pass tool output validation."""
    intermediate_results = [
        {
            "agent": "data_analysis",
            "output": {
                "analysis_required": True,
                "tool_name": "analyze_dataset",
                "tool_arguments": {"dataset": "orders", "operation": "summary"},
                "tool_success": True,
                "tool_error": None,
            },
        }
    ]
    issues, count = validate_tool_outputs(intermediate_results, {})
    assert count > 0
    errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
    assert len(errors) == 0


def test_tool_outputs_unapproved_tool_detected():
    """Verify that arbitrary or unapproved tool invocations are blocked."""
    intermediate_results = [
        {
            "agent": "data_analysis",
            "output": {
                "analysis_required": True,
                "tool_name": "run_arbitrary_shell_command",
                "tool_arguments": {"command": "rm -rf /"},
                "tool_success": True,
            },
        }
    ]
    issues, _ = validate_tool_outputs(intermediate_results, {})
    assert any(i.code == "UNAPPROVED_TOOL_NAME" for i in issues)


def test_tool_outputs_masked_failure_detected():
    """Verify that tools reporting failure inside result are caught."""
    intermediate_results = [
        {
            "agent": "data_analysis",
            "output": {
                "analysis_required": True,
                "tool_name": "analyze_dataset",
                "tool_arguments": {"dataset": "orders"},
                "tool_success": True,
                "tool_error": "Database connection timed out",
            },
        }
    ]
    issues, _ = validate_tool_outputs(intermediate_results, {})
    assert any(i.code == "MASKED_TOOL_ERROR" for i in issues)


# =============================================================================
# 5. Unsupported Claims & Numbers Validator Tests
# =============================================================================

def test_claims_supported_numbers():
    """Verify that stated figures matching analysis metrics pass claim check."""
    state = {
        "analysis_results": {
            "status": "completed",
            "metrics": {"total_revenue": 177650.0, "total_orders": 120},
            "rows": [],
        },
        "retrieved_documents": [],
    }
    final_answer = {
        "answer": "Total revenue calculated across 120 orders is $177,650.",
        "key_points": ["Revenue stands at $177,650 across 120 transactions."],
    }
    issues, count = validate_claims_and_numbers(final_answer, state)
    assert count > 0
    errors = [i for i in issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]
    assert len(errors) == 0


def test_claims_unsupported_figure_detected():
    """Verify that hallucinated figures (e.g. $190,000 when verified is $177,650) are flagged as recoverable."""
    state = {
        "analysis_results": {
            "status": "completed",
            "metrics": {"total_revenue": 177650.0, "total_orders": 120},
            "rows": [],
        },
        "retrieved_documents": [],
    }
    final_answer = {
        "answer": "The platform generated $190,000 in Q4 revenue.",
        "key_points": ["Record revenue of $190,000."],
    }
    issues, _ = validate_claims_and_numbers(final_answer, state)
    claim_issues = [i for i in issues if i.code == "UNSUPPORTED_NUMERICAL_CLAIM"]
    assert len(claim_issues) > 0
    assert any(i.recoverable for i in claim_issues)


# =============================================================================
# 6. Full ValidationService Coordination Tests
# =============================================================================

def test_validation_service_all_pass():
    """Verify that a complete, clean workflow state yields PASS status and 1.0 score."""
    state = {
        "request_id": "req-complete-1",
        "user_query": "What is the total revenue?",
        "analysis_results": {
            "status": "completed",
            "success": True,
            "metrics": {"sum_revenue": 177650.0, "record_count": 120},
            "rows": [],
        },
        "retrieved_documents": [
            {
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "filename": "sales.pdf",
                "content": "Sales documentation",
            }
        ],
        "intermediate_results": [
            {
                "agent": "data_analysis",
                "output": {
                    "analysis_required": True,
                    "tool_name": "analyze_dataset",
                    "tool_arguments": {"dataset": "orders", "operation": "sum"},
                    "tool_success": True,
                    "tool_error": None,
                },
            }
        ],
        "final_answer": {
            "request_id": "req-complete-1",
            "answer": "Total revenue is $177,650 across 120 records.",
            "key_points": ["Revenue reached $177,650."],
            "confidence": 0.95,
            "sources": [
                {
                    "document_id": "doc-1",
                    "chunk_id": "chunk-1",
                    "filename": "sales.pdf",
                }
            ],
        },
    }

    result = ValidationService.validate_workflow_state(state, attempt=1)
    assert result.status == ValidationStatus.PASS
    assert result.score >= 0.8
    assert result.failed_items == 0
    assert result.validation_duration_ms > 0
