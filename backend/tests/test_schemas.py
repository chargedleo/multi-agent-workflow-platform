"""Tests for Pydantic schema validation and rejection of invalid outputs."""

import pytest
from pydantic import ValidationError
from backend.app.models.schemas import (
    Plan,
    ResearchResult,
    WorkflowResponse,
    WorkflowRequest,
    WorkflowAPIResponse,
)


def test_valid_plan_schema():
    """Verify a valid Plan object parses properly."""
    plan = Plan(
        goal="Compare PostgreSQL and MongoDB",
        steps=["Step 1: Check ACID", "Step 2: Check sharding"],
    )
    assert plan.goal == "Compare PostgreSQL and MongoDB"
    assert len(plan.steps) == 2


def test_invalid_plan_schema_rejection():
    """Verify invalid plans are rejected."""
    # Empty goal
    with pytest.raises(ValidationError):
        Plan(goal="a", steps=["Step 1"])

    # Empty steps list
    with pytest.raises(ValidationError):
        Plan(goal="Valid Goal", steps=[])


def test_valid_research_result_schema():
    """Verify a valid ResearchResult object."""
    res = ResearchResult(
        findings=["PostgreSQL has strong relational integrity."],
        assumptions=["Cloud environment."],
        unanswered_questions=["What is the schema evolution rate?"],
    )
    assert len(res.findings) == 1
    assert len(res.assumptions) == 1
    assert len(res.unanswered_questions) == 1


def test_invalid_research_result_schema_rejection():
    """Verify research results missing findings are rejected."""
    with pytest.raises(ValidationError):
        ResearchResult(findings=[])


def test_valid_workflow_response_schema():
    """Verify valid WorkflowResponse object."""
    resp = WorkflowResponse(
        request_id="req-123",
        answer="PostgreSQL is recommended for SaaS transactional data.",
        key_points=["ACID compliance", "Mature ecosystem"],
        confidence=0.92,
    )
    assert resp.request_id == "req-123"
    assert resp.confidence == 0.92


def test_invalid_workflow_response_confidence_bounds():
    """Verify confidence must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        WorkflowResponse(
            request_id="req-123",
            answer="Valid answer text.",
            key_points=["Point 1"],
            confidence=1.5,  # Out of range > 1.0
        )

    with pytest.raises(ValidationError):
        WorkflowResponse(
            request_id="req-123",
            answer="Valid answer text.",
            key_points=["Point 1"],
            confidence=-0.1,  # Out of range < 0.0
        )


def test_workflow_request_validation():
    """Verify WorkflowRequest constraints."""
    valid_req = WorkflowRequest(query="Explain database sharding.")
    assert valid_req.query == "Explain database sharding."

    with pytest.raises(ValidationError):
        WorkflowRequest(query="")  # Empty query
