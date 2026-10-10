"""Unit tests for deterministic retrieval metrics (Recall@k, Precision@k, MRR, MAP, HitRate)."""

import pytest
from backend.app.evaluation.retrieval_metrics import (
    compute_retrieval_metrics,
    deduplicate_ranked_results,
)


def test_perfect_retrieval_metrics():
    """Verify metrics when top 2 items are exactly the 2 relevant items."""
    retrieved = [
        {"chunk_id": "c1", "document_id": "d1"},
        {"chunk_id": "c2", "document_id": "d1"},
        {"chunk_id": "c3", "document_id": "d2"},
    ]
    relevant_chunks = ["c1", "c2"]

    metrics = compute_retrieval_metrics(
        retrieved_items=retrieved,
        relevant_chunk_ids=relevant_chunks,
        latency_ms=15.4,
    )

    assert metrics.retrieved_count == 3
    assert metrics.relevant_count == 2
    assert metrics.recall_at_1 == 0.5   # 1 of 2
    assert metrics.recall_at_3 == 1.0   # 2 of 2
    assert metrics.recall_at_5 == 1.0   # 2 of 2

    assert metrics.precision_at_1 == 1.0       # 1 / 1
    assert metrics.precision_at_3 == round(2 / 3, 4)  # 2 / 3
    assert metrics.precision_at_5 == round(2 / 5, 4)  # 2 / 5

    assert metrics.hit_rate_at_1 == 1.0
    assert metrics.hit_rate_at_3 == 1.0
    assert metrics.hit_rate_at_5 == 1.0

    assert metrics.mrr == 1.0           # First relevant hit at rank 1
    # MAP = ((1/1) + (2/2)) / 2 = 1.0
    assert metrics.map_score == 1.0
    assert metrics.latency_ms == 15.4


def test_first_hit_at_rank_two():
    """Verify MRR and Precision when first relevant item is at rank 2."""
    retrieved = [
        {"chunk_id": "irrelevant_1"},
        {"chunk_id": "relevant_target"},
        {"chunk_id": "irrelevant_2"},
    ]
    metrics = compute_retrieval_metrics(
        retrieved_items=retrieved,
        relevant_chunk_ids=["relevant_target"],
    )

    assert metrics.recall_at_1 == 0.0
    assert metrics.recall_at_3 == 1.0
    assert metrics.precision_at_1 == 0.0
    assert metrics.precision_at_3 == round(1 / 3, 4)
    assert metrics.hit_rate_at_1 == 0.0
    assert metrics.hit_rate_at_3 == 1.0
    assert metrics.mrr == 0.5           # 1 / 2


def test_empty_retrieval_results():
    """Verify metrics when retriever returns 0 items."""
    metrics = compute_retrieval_metrics(
        retrieved_items=[],
        relevant_chunk_ids=["c1", "c2"],
    )
    assert metrics.retrieved_count == 0
    assert metrics.relevant_count == 2
    assert metrics.recall_at_1 == 0.0
    assert metrics.recall_at_3 == 0.0
    assert metrics.recall_at_5 == 0.0
    assert metrics.precision_at_1 == 0.0
    assert metrics.precision_at_3 == 0.0
    assert metrics.precision_at_5 == 0.0
    assert metrics.hit_rate_at_1 == 0.0
    assert metrics.mrr == 0.0
    assert metrics.map_score == 0.0


def test_unanswerable_no_relevant_documents():
    """Verify undefined Recall behavior when no relevant documents exist (Category C)."""
    retrieved = [
        {"chunk_id": "c1"},
        {"chunk_id": "c2"},
    ]
    # No relevant chunks specified
    metrics = compute_retrieval_metrics(
        retrieved_items=retrieved,
        relevant_chunk_ids=[],
        relevant_document_ids=[],
    )
    assert metrics.relevant_count == 0
    # Recall must be None (undefined), not 0.0 or 1.0
    assert metrics.recall_at_1 is None
    assert metrics.recall_at_3 is None
    assert metrics.recall_at_5 is None
    assert metrics.hit_rate_at_1 == 0.0
    assert metrics.mrr == 0.0
    assert metrics.map_score == 0.0


def test_deduplication_preserves_order():
    """Verify deduplication removes duplicate chunk_ids while preserving rank."""
    raw = [
        {"chunk_id": "c1", "score": 0.9},
        {"chunk_id": "c2", "score": 0.8},
        {"chunk_id": "c1", "score": 0.7},  # Duplicate
        {"chunk_id": "c3", "score": 0.6},
    ]
    deduped = deduplicate_ranked_results(raw)
    assert len(deduped) == 3
    assert [d["chunk_id"] for d in deduped] == ["c1", "c2", "c3"]


def test_hit_beyond_top_five():
    """Verify item at rank 6 yields 0 for top 5, but non-zero MRR."""
    retrieved = [
        {"chunk_id": "x1"},
        {"chunk_id": "x2"},
        {"chunk_id": "x3"},
        {"chunk_id": "x4"},
        {"chunk_id": "x5"},
        {"chunk_id": "target"},
    ]
    metrics = compute_retrieval_metrics(
        retrieved_items=retrieved,
        relevant_chunk_ids=["target"],
    )
    assert metrics.hit_rate_at_5 == 0.0
    assert metrics.recall_at_5 == 0.0
    assert metrics.precision_at_5 == 0.0
    assert metrics.mrr == round(1 / 6, 4)
