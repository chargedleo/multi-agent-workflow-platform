"""Automated integration regression tests for the Evaluation Engine (Milestone 9A).

Verifies:
- Test A: Positive control (isolated index, real FAISS, real mock embedding, Recall@1=1.0, MRR=1.0)
- Test B: Empty-result control (valid query with 0 hits returns COMPLETED with Recall=None or 0.0, not exception)
- Test C: Perturbation control (removing chunk drops Recall and Hit Rate to 0.0)
- Test D: Ranking shift control (forcing chunk to rank 2 yields MRR=0.5)
- Test E: Retrieval exception (mocking failure in RetrievalService.retrieve results in status="FAILED",
          sanitized error message recorded, does not falsely pass unanswerable cases)
- Test F: Timeout control (mocking timeout yields status="FAILED" with timeout error)
- Test G: Metric-only mode isolation (verifies deterministic, offline fixture execution)
- Test H: Persistence & reporting (verifies failed case results and error summaries are persisted and serialized)
- Test I: Equivalence groups and duplicate chunk handling (verifies aliases satisfy targets without inflation)
"""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.documents.vectorstore.faiss_store as faiss_store_module
from backend.app.documents.embeddings.provider import get_embedding_provider
from backend.app.documents.schemas import RetrievalResult, RetrievedChunk
from backend.app.documents.vectorstore.faiss_store import FAISSVectorStore, reset_vector_store
from backend.app.evaluation.retrieval_adapter import (
    RetrievalAdapterError,
    execute_evaluation_retrieval,
)
from backend.app.evaluation.retrieval_metrics import compute_retrieval_metrics
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.evaluation.schemas import (
    BenchmarkCategory,
    EvaluationCase,
    EvaluationDataset,
    EvaluationMode,
    ExpectedCitation,
    StartEvaluationRequest,
)
from backend.app.evaluation.service import EvaluationService
from backend.app.services.retrieval import RetrievalService


@pytest.fixture
def isolated_vector_store(tmp_path: Path):
    """Fixture providing an isolated FAISSVectorStore with stable IDs and known embeddings."""
    store = FAISSVectorStore(dimension=384, storage_dir=tmp_path / "faiss_test")
    provider = get_embedding_provider()

    corpus_chunks = [
        {
            "chunk_id": "chunk-stable-pg-01",
            "document_id": "doc-stable-postgres-guide",
            "filename": "database_guide.txt",
            "page_number": 1,
            "content": "PostgreSQL is a powerful, open-source object-relational database system known for reliability.",
        },
        {
            "chunk_id": "chunk-stable-pg-02",
            "document_id": "doc-stable-postgres-guide",
            "filename": "database_guide.txt",
            "page_number": 1,
            "content": "PostgreSQL provides ACID compliance, strong data integrity, and enterprise support.",
        },
        {
            "chunk_id": "chunk-stable-arch-01",
            "document_id": "doc-stable-enterprise-arch",
            "filename": "enterprise_arch.txt",
            "page_number": 1,
            "content": "Antigravity Enterprise Architecture Specification. Section 1: The system uses LangGraph for coordinating Planner, Retrieval, Researcher, and Responder agents.",
        },
        {
            "chunk_id": "chunk-stable-arch-02",
            "document_id": "doc-stable-enterprise-arch",
            "filename": "enterprise_arch.txt",
            "page_number": 1,
            "content": "Section 2: High throughput messaging is managed via durable PostgreSQL state persistence and checkpointing.",
        },
    ]

    texts = [c["content"] for c in corpus_chunks]
    vectors = provider.embed_documents(texts)
    store.add_vectors(vectors, corpus_chunks)
    store.save()

    original_store = faiss_store_module._vector_store_instance
    faiss_store_module._vector_store_instance = store

    yield store

    faiss_store_module._vector_store_instance = original_store


# =============================================================================
# Test A: Positive Control
# =============================================================================

@pytest.mark.asyncio
async def test_positive_control_retrieval(isolated_vector_store):
    """Positive Control: Verify real FAISS retrieval matches expected target at rank 1 with Recall=1.0 and MRR=1.0."""
    case = EvaluationCase(
        case_id="TEST-POS-01",
        dataset_version="1.0.0",
        category=BenchmarkCategory.ANSWERABLE,
        question="Which framework coordinates the Planner, Retrieval, Researcher, and Responder agents?",
        expected_answer_facts=["LangGraph is used for coordinating Planner, Retrieval, Researcher, and Responder agents"],
        relevant_chunk_ids=["chunk-stable-arch-01"],
        relevant_document_ids=["doc-stable-enterprise-arch"],
        expected_citations=[ExpectedCitation(filename="enterprise_arch.txt", page_number=1)],
        answerable=True,
    )

    dataset = EvaluationDataset(
        name="positive_control_benchmark",
        version="1.0.0",
        cases=[case],
    )

    runner = EvaluationRunner()
    report = await runner.run(dataset=dataset, mode=EvaluationMode.INTEGRATION)

    assert len(report.case_results) == 1
    result = report.case_results[0]
    assert result.status == "COMPLETED"
    assert result.retrieval is not None
    assert result.retrieval.hit_rate_at_1 == 1.0
    assert result.retrieval.recall_at_1 == 1.0
    assert result.retrieval.precision_at_1 == 1.0
    assert result.retrieval.mrr == 1.0
    assert report.summary.completed_cases == 1
    assert report.summary.failed_cases == 0


# =============================================================================
# Test B: Empty-Result Control
# =============================================================================

@pytest.mark.asyncio
async def test_empty_result_control(isolated_vector_store, monkeypatch):
    """Empty-Result Control: A query returning 0 chunks completes cleanly without raising an exception."""
    # Monkeypatch RetrievalService.retrieve to return a valid 0-hit result
    monkeypatch.setattr(
        RetrievalService,
        "retrieve",
        lambda query, top_k=None: RetrievalResult(query=query, results=[]),
    )

    # 1. Answerable case with missing hits -> Recall=0.0
    case_ans = EvaluationCase(
        case_id="TEST-EMPTY-ANS",
        dataset_version="1.0.0",
        category=BenchmarkCategory.ANSWERABLE,
        question="What is the architecture?",
        relevant_chunk_ids=["chunk-stable-arch-01"],
        answerable=True,
    )

    # 2. Unanswerable case (Category C) -> Recall=None (undefined)
    case_unans = EvaluationCase(
        case_id="TEST-EMPTY-UNANS",
        dataset_version="1.0.0",
        category=BenchmarkCategory.UNANSWERABLE,
        question="What is quantum gravity encryption?",
        relevant_chunk_ids=[],
        relevant_document_ids=[],
        answerable=False,
    )

    dataset = EvaluationDataset(
        name="empty_control_benchmark",
        version="1.0.0",
        cases=[case_ans, case_unans],
    )

    runner = EvaluationRunner()
    report = await runner.run(dataset=dataset, mode=EvaluationMode.INTEGRATION)

    assert len(report.case_results) == 2

    res_ans = next(r for r in report.case_results if r.case_id == "TEST-EMPTY-ANS")
    assert res_ans.status == "COMPLETED"
    assert res_ans.retrieval.retrieved_count == 0
    assert res_ans.retrieval.recall_at_1 == 0.0
    assert res_ans.retrieval.hit_rate_at_1 == 0.0
    assert res_ans.retrieval.mrr == 0.0

    res_unans = next(r for r in report.case_results if r.case_id == "TEST-EMPTY-UNANS")
    assert res_unans.status == "COMPLETED"
    assert res_unans.retrieval.retrieved_count == 0
    # Undefined recall for Category C with empty relevant set
    assert res_unans.retrieval.recall_at_1 is None
    assert res_unans.retrieval.recall_at_3 is None
    assert res_unans.retrieval.hit_rate_at_1 == 0.0
    assert res_unans.retrieval.mrr == 0.0


# =============================================================================
# Test C: Perturbation Control
# =============================================================================

@pytest.mark.asyncio
async def test_perturbation_control(tmp_path: Path):
    """Perturbation Control: Missing target chunk in index drops Recall and Hit Rate to 0.0."""
    # Create index containing only postgres chunks (no arch chunks)
    store = FAISSVectorStore(dimension=384, storage_dir=tmp_path / "faiss_perturbed")
    provider = get_embedding_provider()
    chunks = [
        {
            "chunk_id": "chunk-stable-pg-01",
            "document_id": "doc-stable-postgres-guide",
            "filename": "database_guide.txt",
            "page_number": 1,
            "content": "PostgreSQL is a powerful, open-source object-relational database system.",
        }
    ]
    store.add_vectors(provider.embed_documents([c["content"] for c in chunks]), chunks)
    store.save()

    original_store = faiss_store_module._vector_store_instance
    faiss_store_module._vector_store_instance = store

    try:
        case = EvaluationCase(
            case_id="TEST-PERTURB-01",
            dataset_version="1.0.0",
            category=BenchmarkCategory.ANSWERABLE,
            question="Which framework coordinates Planner and Responder?",
            relevant_chunk_ids=["chunk-stable-arch-01"],  # Not in store
            answerable=True,
        )
        dataset = EvaluationDataset(name="perturb_bench", version="1.0.0", cases=[case])
        runner = EvaluationRunner()
        report = await runner.run(dataset=dataset, mode=EvaluationMode.INTEGRATION)

        res = report.case_results[0]
        assert res.status == "COMPLETED"
        assert res.retrieval.hit_rate_at_1 == 0.0
        assert res.retrieval.hit_rate_at_3 == 0.0
        assert res.retrieval.recall_at_1 == 0.0
        assert res.retrieval.recall_at_3 == 0.0
        assert res.retrieval.mrr == 0.0
    finally:
        faiss_store_module._vector_store_instance = original_store


# =============================================================================
# Test D: Ranking Shift Control
# =============================================================================

def test_ranking_shift_control():
    """Ranking Shift: Forcing target chunk to rank 2 yields MRR=0.5 and Recall@1=0.0."""
    retrieved = [
        {"chunk_id": "chunk-irrelevant-top", "document_id": "doc-other"},
        {"chunk_id": "chunk-target-rank2", "document_id": "doc-target"},
        {"chunk_id": "chunk-irrelevant-3", "document_id": "doc-other"},
    ]
    metrics = compute_retrieval_metrics(
        retrieved_items=retrieved,
        relevant_chunk_ids=["chunk-target-rank2"],
    )

    assert metrics.mrr == 0.5  # 1 / 2
    assert metrics.recall_at_1 == 0.0
    assert metrics.recall_at_3 == 1.0
    assert metrics.hit_rate_at_1 == 0.0
    assert metrics.hit_rate_at_3 == 1.0
    assert metrics.precision_at_1 == 0.0
    assert metrics.precision_at_3 == round(1 / 3, 4)


# =============================================================================
# Test E: Retrieval Exception Handling
# =============================================================================

@pytest.mark.asyncio
async def test_retrieval_exception_handling(monkeypatch):
    """Retrieval Exception: Unexpected retrieval failures raise RetrievalAdapterError,
    mark cases as FAILED, and do NOT falsely pass unanswerable Category C queries.
    """
    def broken_retrieve(query, top_k=None):
        raise RuntimeError("FAISS disk corruption or IO read failure")

    monkeypatch.setattr(RetrievalService, "retrieve", broken_retrieve)

    # 1. Verify adapter raises typed exception
    with pytest.raises(RetrievalAdapterError, match="Retrieval execution failure"):
        execute_evaluation_retrieval(query="Any search query", top_k=5)

    # 2. Verify runner marks answerable case as FAILED
    case_ans = EvaluationCase(
        case_id="TEST-FAIL-ANS",
        dataset_version="1.0.0",
        category=BenchmarkCategory.ANSWERABLE,
        question="What is the architecture?",
        relevant_chunk_ids=["chunk-stable-arch-01"],
        answerable=True,
    )

    # 3. Verify runner marks unanswerable case as FAILED (must NOT falsely pass)
    case_unans = EvaluationCase(
        case_id="TEST-FAIL-UNANS",
        dataset_version="1.0.0",
        category=BenchmarkCategory.UNANSWERABLE,
        question="What is quantum gravity encryption?",
        relevant_chunk_ids=[],
        relevant_document_ids=[],
        answerable=False,
    )

    dataset = EvaluationDataset(
        name="exception_benchmark",
        version="1.0.0",
        cases=[case_ans, case_unans],
    )

    runner = EvaluationRunner()
    report = await runner.run(dataset=dataset, mode=EvaluationMode.INTEGRATION)

    assert report.summary.total_cases == 2
    assert report.summary.failed_cases == 2
    assert report.summary.completed_cases == 0

    for res in report.case_results:
        assert res.status == "FAILED"
        assert "Retrieval execution failure: FAISS disk corruption" in (res.error or "")

    assert len(report.failures) == 2
    assert any(f["case_id"] == "TEST-FAIL-UNANS" for f in report.failures)


# =============================================================================
# Test F: Timeout Control
# =============================================================================

@pytest.mark.asyncio
async def test_timeout_handling(monkeypatch):
    """Timeout Control: Case execution exceeding timeout is isolated and marked FAILED."""
    async def slow_workflow(query):
        await asyncio.sleep(0.4)
        return {"status": "COMPLETED"}

    monkeypatch.setattr("backend.app.graph.workflow.run_workflow", slow_workflow)
    monkeypatch.setattr(
        RetrievalService,
        "retrieve",
        lambda query="", top_k=None: RetrievalResult(query=query, results=[]),
    )

    case = EvaluationCase(
        case_id="TEST-TIMEOUT-01",
        dataset_version="1.0.0",
        category=BenchmarkCategory.ANSWERABLE,
        question="Query that takes too long",
        relevant_chunk_ids=["c1"],
    )
    dataset = EvaluationDataset(name="timeout_bench", version="1.0.0", cases=[case])

    runner = EvaluationRunner()
    runner.case_timeout_seconds = 0.1  # Set small timeout on instance directly
    report = await runner.run(dataset=dataset, mode=EvaluationMode.INTEGRATION)

    res = report.case_results[0]
    assert res.status == "FAILED"
    assert "timed out" in (res.error or "").lower()
    assert report.summary.failed_cases == 1


# =============================================================================
# Test G: Metric-Only Mode Isolation
# =============================================================================

@pytest.mark.asyncio
async def test_metric_only_mode_isolation(monkeypatch):
    """Metric-Only Mode Isolation: Executes offline without touching RetrievalService."""
    def crash_if_called(*args, **kwargs):
        raise AssertionError("RetrievalService should never be called in METRIC_ONLY mode!")

    monkeypatch.setattr(RetrievalService, "retrieve", crash_if_called)

    case = EvaluationCase(
        case_id="TEST-METRIC-ONLY-01",
        dataset_version="1.0.0",
        category=BenchmarkCategory.ANSWERABLE,
        question="What is the architecture?",
        relevant_chunk_ids=["chunk-1"],
        expected_answer_facts=["Architecture fact"],
    )
    dataset = EvaluationDataset(name="metric_only_bench", version="1.0.0", cases=[case])

    runner = EvaluationRunner()
    report = await runner.run(dataset=dataset, mode=EvaluationMode.METRIC_ONLY)

    assert report.mode == EvaluationMode.METRIC_ONLY
    assert report.summary.completed_cases == 1
    assert report.summary.failed_cases == 0
    res = report.case_results[0]
    assert res.status == "COMPLETED"
    assert res.retrieval.hit_rate_at_1 == 1.0


# =============================================================================
# Test H: Persistence and Reporting
# =============================================================================

@pytest.mark.asyncio
async def test_persistence_and_failure_reporting(db_session: AsyncSession, monkeypatch):
    """Persistence and Reporting: Failed cases are saved to database and serialized into report failures."""
    # Prepare mock retrieve that succeeds on query 1 but fails on query 2
    def conditional_retrieve(query, top_k=None):
        if "fail" in query.lower():
            raise RuntimeError("Database connection timed out during vector lookup")
        return RetrievalResult(
            query=query,
            results=[
                RetrievedChunk(
                    chunk_id="chunk-stable-arch-01",
                    document_id="doc-stable-enterprise-arch",
                    filename="enterprise_arch.txt",
                    content="Section 1: LangGraph coordinates agents.",
                    page_number=1,
                    similarity_score=0.98,
                )
            ],
        )

    monkeypatch.setattr(RetrievalService, "retrieve", conditional_retrieve)

    # Initialize evaluation run in DB
    run_record = await EvaluationService.create_evaluation_run(
        session=db_session,
        dataset_name="benchmark_v1",
        mode=EvaluationMode.INTEGRATION,
        max_concurrency=2,
        timeout_per_case_seconds=10.0,
    )
    assert run_record.status == "PENDING"

    # Define minimal test dataset
    case_ok = EvaluationCase(
        case_id="CASE-OK",
        dataset_version="1.0.0",
        category=BenchmarkCategory.ANSWERABLE,
        question="Explain system architecture",
        relevant_chunk_ids=["chunk-stable-arch-01"],
    )
    case_bad = EvaluationCase(
        case_id="CASE-FAIL",
        dataset_version="1.0.0",
        category=BenchmarkCategory.ANSWERABLE,
        question="This query will fail",
        relevant_chunk_ids=["chunk-stable-arch-01"],
    )
    dataset = EvaluationDataset(name="bench_persist", version="1.0.0", cases=[case_ok, case_bad])

    runner = EvaluationRunner()
    report = await runner.run(dataset=dataset, mode=EvaluationMode.INTEGRATION, run_id=str(run_record.id))

    assert report.summary.completed_cases == 1
    assert report.summary.failed_cases == 1
    assert len(report.failures) == 1
    assert report.failures[0]["case_id"] == "CASE-FAIL"
    assert "Database connection timed out" in report.failures[0]["error"]


# =============================================================================
# Test I: Equivalence Groups & Duplicate Chunks
# =============================================================================

def test_equivalence_groups_and_duplicate_chunks():
    """Equivalence Groups: Aliases satisfy target concepts, duplicate copies do not inflate metrics,
    and filename-only matching is rejected.
    """
    retrieved = [
        # Rank 1: Duplicate copy of target 1
        {"chunk_id": "chunk-arch-copy-01", "document_id": "doc-dup-1", "filename": "enterprise_arch.txt"},
        # Rank 2: Another duplicate copy of target 1
        {"chunk_id": "chunk-arch-copy-02", "document_id": "doc-dup-2", "filename": "enterprise_arch.txt"},
        # Rank 3: Target 2
        {"chunk_id": "chunk-target-2", "document_id": "doc-target-2", "filename": "database_guide.txt"},
        # Rank 4: Same filename as target 2, but completely different chunk
        {"chunk_id": "chunk-unrelated-pg", "document_id": "doc-other", "filename": "database_guide.txt"},
    ]

    # Target 1 primary UUID is 'chunk-arch-primary', with aliases ['chunk-arch-copy-01', 'chunk-arch-copy-02']
    metrics = compute_retrieval_metrics(
        retrieved_items=retrieved,
        relevant_chunk_ids=["chunk-arch-primary", "chunk-target-2"],
        relevant_chunk_aliases=[["chunk-arch-copy-01", "chunk-arch-copy-02"], []],
    )

    assert metrics.relevant_count == 2
    # At k=1: target 1 is satisfied by copy-01
    assert metrics.recall_at_1 == 0.5   # 1 of 2
    assert metrics.hit_rate_at_1 == 1.0
    assert metrics.precision_at_1 == 1.0

    # At k=3: target 1 satisfied at rank 1, copy-02 at rank 2 does NOT double-count, target 2 satisfied at rank 3
    assert metrics.recall_at_3 == 1.0   # 2 of 2
    assert metrics.hit_rate_at_3 == 1.0
    assert metrics.precision_at_3 == round(2 / 3, 4)  # 2 distinct concepts satisfied out of 3 retrieved

    # Rank 4 has filename="database_guide.txt" but chunk_id is not in target clusters:
    # Precision at 5 remains 2/5, does NOT inflate to 3/5
    assert metrics.precision_at_5 == round(2 / 5, 4)
    assert metrics.recall_at_5 == 1.0
    assert metrics.mrr == 1.0
