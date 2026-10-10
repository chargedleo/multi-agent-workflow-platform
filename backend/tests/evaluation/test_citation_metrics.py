"""Unit tests for deterministic citation integrity metrics."""

import pytest
from backend.app.evaluation.citation_metrics import compute_citation_metrics
from backend.app.evaluation.schemas import ExpectedCitation


def test_valid_citation_matching_retrieved():
    """Verify metrics when citations match retrieved documents perfectly."""
    retrieved = [
        {"document_id": "doc-1", "filename": "database_guide.txt", "page_number": 1, "chunk_id": "chk-1"}
    ]
    citations = [
        {"document_id": "doc-1", "filename": "database_guide.txt", "page_number": 1, "chunk_id": "chk-1"}
    ]
    expected = [
        ExpectedCitation(filename="database_guide.txt", page_number=1)
    ]

    metrics = compute_citation_metrics(
        citations=citations,
        retrieved_documents=retrieved,
        expected_citations=expected,
        answerable=True,
    )

    assert metrics.citation_presence == 1.0
    assert metrics.identifier_validity == 1.0
    assert metrics.source_reference_validity == 1.0
    assert metrics.page_reference_validity == 1.0
    assert metrics.attribution_match == 1.0
    assert metrics.duplicate_citations_count == 0
    assert metrics.malformed_citations_count == 0
    assert metrics.total_citations == 1


def test_missing_citation_when_expected():
    """Verify metrics when citations are expected but none provided."""
    retrieved = [{"document_id": "doc-1", "filename": "guide.txt"}]
    expected = [ExpectedCitation(filename="guide.txt")]

    metrics = compute_citation_metrics(
        citations=[],
        retrieved_documents=retrieved,
        expected_citations=expected,
        answerable=True,
    )

    assert metrics.citation_presence == 0.0
    assert metrics.source_reference_validity == 0.0
    assert metrics.attribution_match == 0.0
    assert metrics.total_citations == 0


def test_fabricated_citation_not_retrieved():
    """Verify source_reference_validity flags citations to unretrieved documents."""
    retrieved = [{"document_id": "doc-1", "filename": "doc1.txt"}]
    # Cites doc-999 which was never retrieved
    citations = [{"document_id": "doc-999", "filename": "fabricated.txt"}]

    metrics = compute_citation_metrics(
        citations=citations,
        retrieved_documents=retrieved,
        expected_citations=[],
        answerable=True,
    )

    assert metrics.citation_presence == 1.0
    assert metrics.identifier_validity == 1.0
    assert metrics.source_reference_validity == 0.0  # Fabricated!


def test_duplicate_citations_detected():
    """Verify duplicate citations are counted."""
    retrieved = [{"document_id": "doc-1", "filename": "doc1.txt"}]
    citations = [
        {"document_id": "doc-1", "filename": "doc1.txt", "chunk_id": "c1"},
        {"document_id": "doc-1", "filename": "doc1.txt", "chunk_id": "c1"},  # Duplicate
    ]
    metrics = compute_citation_metrics(
        citations=citations,
        retrieved_documents=retrieved,
    )
    assert metrics.duplicate_citations_count == 1
    assert metrics.total_citations == 2


def test_unanswerable_query_citation_handling():
    """Verify unanswerable queries should not include citations."""
    retrieved = []
    # 1. Correct abstention: 0 citations
    m_clean = compute_citation_metrics(
        citations=[],
        retrieved_documents=retrieved,
        answerable=False,
    )
    assert m_clean.citation_presence == 1.0

    # 2. Hallucinated citation on unanswerable query
    m_bad = compute_citation_metrics(
        citations=[{"document_id": "hallucinated", "filename": "secret.txt"}],
        retrieved_documents=retrieved,
        answerable=False,
    )
    assert m_bad.citation_presence == 0.0
    assert m_bad.source_reference_validity == 0.0
