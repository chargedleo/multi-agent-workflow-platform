"""Unit tests for deterministic answer quality metrics."""

import pytest
from backend.app.evaluation.answer_metrics import compute_answer_metrics, is_fact_matched, is_abstaining


def test_fact_matching_exact_and_partial():
    """Verify keyword and term matching on facts."""
    answer = (
        "PostgreSQL is an open-source object-relational database system that provides "
        "durable state persistence for high-throughput messaging."
    )
    fact1 = "PostgreSQL is an open-source object-relational database system"
    fact2 = "Redis cluster manages pub-sub streaming"

    assert is_fact_matched(fact1, answer) is True
    assert is_fact_matched(fact2, answer) is False


def test_answer_metrics_full_coverage():
    """Verify 100% fact coverage when all expected facts are present."""
    answer = (
        "LangGraph is used for coordinating Planner, Retrieval, Researcher, and Responder agents. "
        "PostgreSQL manages high throughput messaging via durable state persistence."
    )
    expected_facts = [
        "LangGraph coordinates Planner, Retrieval, Researcher, and Responder agents",
        "PostgreSQL manages high throughput messaging",
    ]
    metrics = compute_answer_metrics(
        answer=answer,
        expected_facts=expected_facts,
        answerable=True,
        key_points=["LangGraph agent coordination", "PostgreSQL persistence"],
    )

    assert metrics.fact_coverage == 1.0
    assert len(metrics.matched_facts) == 2
    assert len(metrics.missing_facts) == 0
    assert metrics.correct_abstention is None
    assert metrics.completeness_score == 1.0


def test_answer_metrics_partial_coverage():
    """Verify 50% fact coverage when 1 of 2 expected facts is missing."""
    answer = "LangGraph coordinates the agents across the workflow pipeline."
    expected_facts = [
        "LangGraph coordinates the agents",
        "PostgreSQL manages high throughput messaging",
    ]
    metrics = compute_answer_metrics(
        answer=answer,
        expected_facts=expected_facts,
        answerable=True,
    )

    assert metrics.fact_coverage == 0.5
    assert len(metrics.matched_facts) == 1
    assert len(metrics.missing_facts) == 1
    assert "PostgreSQL manages high throughput messaging" in metrics.missing_facts


def test_unanswerable_proper_abstention():
    """Verify correct_abstention is True when unanswerable query meets abstention phrases."""
    answer = "This information is not mentioned in the provided documentation or corpus."
    metrics = compute_answer_metrics(
        answer=answer,
        expected_facts=[],
        answerable=False,
    )

    assert metrics.correct_abstention is True
    assert metrics.fact_coverage == 1.0
    assert len(metrics.missing_facts) == 0


def test_unanswerable_failed_abstention():
    """Verify correct_abstention is False when unanswerable query hallucinates an answer."""
    answer = "The secret quantum encryption key is alpha-beta-gamma-999."
    metrics = compute_answer_metrics(
        answer=answer,
        expected_facts=[],
        answerable=False,
    )

    assert metrics.correct_abstention is False
    assert metrics.fact_coverage == 0.0
    assert len(metrics.missing_facts) > 0
