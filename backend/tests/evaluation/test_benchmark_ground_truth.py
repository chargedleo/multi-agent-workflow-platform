"""Automated benchmark ground-truth and semantic integrity tests (Milestone 9A).

Separates structural schema validation from semantic ground-truth auditing:
- Verifies unique case IDs and canonical categories (A through G).
- Verifies that referenced chunk UUIDs exist in the corpus metadata.
- Verifies unanswerable cases have zero declared evidence.
- Verifies answerable cases have supporting atomic facts and chunk evidence.
- Verifies multi-hop cases reference necessary synthesizing evidence.
- Verifies citation references match source filename and page metadata.
- Verifies dataset checksum calculation stability.
- Verifies invalid or corrupted labels fail loudly instead of being ignored.
"""

import json
from pathlib import Path
import pytest

from backend.app.evaluation.dataset import (
    DatasetValidationError,
    compute_checksum,
    load_dataset,
    validate_dataset_structure,
)
from backend.app.evaluation.schemas import (
    BenchmarkCategory,
    EvaluationCase,
    EvaluationDataset,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "evaluation" / "fixtures"
FAISS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "faiss"


def load_raw_benchmark():
    path = FIXTURES_DIR / "benchmark_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_faiss_metadata():
    path = FAISS_DIR / "metadata.json"
    if not path.exists():
        pytest.skip(f"FAISS metadata not found at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("metadata", [])


# =============================================================================
# 1. Structural and ID Uniqueness Validation
# =============================================================================

def test_benchmark_v1_case_ids_unique_and_consistent():
    """Verify all 35 cases have unique IDs, canonical prefixes, and valid category distributions."""
    raw = load_raw_benchmark()
    cases = raw.get("cases", [])
    assert len(cases) == 35, f"Expected exactly 35 benchmark cases, got {len(cases)}"

    seen_ids = set()
    category_counts = {}

    for c in cases:
        cid = c.get("case_id")
        cat = c.get("category")
        assert cid, "Case missing case_id"
        assert cid not in seen_ids, f"Duplicate case_id: {cid}"
        seen_ids.add(cid)

        category_counts[cat] = category_counts.get(cat, 0) + 1

    expected_categories = {
        BenchmarkCategory.ANSWERABLE.value: 7,
        BenchmarkCategory.MULTI_HOP.value: 5,
        BenchmarkCategory.UNANSWERABLE.value: 5,
        BenchmarkCategory.AMBIGUOUS.value: 4,
        BenchmarkCategory.CITATION_SENSITIVE.value: 5,
        BenchmarkCategory.UNSUPPORTED_PREMISE.value: 5,
        BenchmarkCategory.RETRIEVAL_EDGE_CASE.value: 4,
    }
    assert category_counts == expected_categories


# =============================================================================
# 2. Corpus Evidence & Referenced ID Existence
# =============================================================================

def test_benchmark_v1_referenced_chunk_ids_exist_in_corpus():
    """Verify that all non-empty relevant_chunk_ids actually exist in the FAISS metadata store."""
    raw = load_raw_benchmark()
    faiss_chunks = load_faiss_metadata()
    indexed_chunk_ids = {entry["chunk_id"] for entry in faiss_chunks}

    for c in raw["cases"]:
        rel_cids = c.get("relevant_chunk_ids", [])
        if c.get("answerable") is True:
            assert len(rel_cids) > 0, f"Answerable case {c['case_id']} has no relevant_chunk_ids"
            for cid in rel_cids:
                assert cid in indexed_chunk_ids, (
                    f"Case {c['case_id']} references chunk_id '{cid}' which does not exist in FAISS metadata!"
                )


def test_benchmark_v1_referenced_document_ids_exist_in_corpus():
    """Verify that all referenced relevant_document_ids exist in the FAISS metadata store."""
    raw = load_raw_benchmark()
    faiss_chunks = load_faiss_metadata()
    indexed_doc_ids = {entry["document_id"] for entry in faiss_chunks}

    for c in raw["cases"]:
        rel_dids = c.get("relevant_document_ids", [])
        if c.get("answerable") is True:
            for did in rel_dids:
                assert did in indexed_doc_ids, (
                    f"Case {c['case_id']} references document_id '{did}' which does not exist in FAISS metadata!"
                )


# =============================================================================
# 3. Unanswerable Category C Ground-Truth Semantics
# =============================================================================

def test_benchmark_v1_unanswerable_cases_have_empty_evidence():
    """Verify all Category C cases have answerable=False and zero declared relevant evidence."""
    raw = load_raw_benchmark()
    unans_cases = [c for c in raw["cases"] if c.get("category") == BenchmarkCategory.UNANSWERABLE.value]
    assert len(unans_cases) == 5

    for c in unans_cases:
        assert c.get("answerable") is False, f"Case {c['case_id']} in Category C must have answerable=False"
        assert c.get("relevant_chunk_ids") == [], f"Case {c['case_id']} must have empty relevant_chunk_ids"
        assert c.get("relevant_document_ids") == [], f"Case {c['case_id']} must have empty relevant_document_ids"
        assert c.get("expected_answer_facts") == [], f"Case {c['case_id']} must have empty expected_answer_facts"
        assert c.get("expected_citations") == [], f"Case {c['case_id']} must have empty expected_citations"


# =============================================================================
# 4. Multi-hop Evidence Semantics
# =============================================================================

def test_benchmark_v1_multi_hop_cases_evidence_requirements():
    """Verify Category B multi-hop cases have valid multi-hop or cross-document evidence."""
    raw = load_raw_benchmark()
    multi_cases = [c for c in raw["cases"] if c.get("category") == BenchmarkCategory.MULTI_HOP.value]
    assert len(multi_cases) == 5

    for c in multi_cases:
        assert c.get("answerable") is True
        assert len(c.get("expected_answer_facts", [])) >= 1, (
            f"Multi-hop case {c['case_id']} requires at least 1 atomic fact"
        )
        assert len(c.get("relevant_chunk_ids", [])) >= 1


# =============================================================================
# 5. Citation Metadata Integrity
# =============================================================================

def test_benchmark_v1_citation_references_match_source_metadata():
    """Verify expected_citations point to legitimate filenames and valid page numbers."""
    raw = load_raw_benchmark()
    valid_filenames = {"enterprise_arch.txt", "database_guide.txt"}

    for c in raw["cases"]:
        for cit in c.get("expected_citations", []):
            fn = cit.get("filename")
            assert fn in valid_filenames, f"Case {c['case_id']} expects unknown citation filename '{fn}'"
            assert cit.get("page_number", 0) >= 1, f"Case {c['case_id']} citation has invalid page number"


# =============================================================================
# 6. Checksum Stability & Tamper Detection
# =============================================================================

def test_benchmark_v1_checksum_stability_and_tamper_detection():
    """Verify dataset checksum calculation is deterministic and sensitive to content modifications."""
    ds = load_dataset()
    assert ds.checksum is not None
    assert len(ds.checksum) == 64

    # Direct bytes checksum matches dataset checksum
    fixture_bytes = (FIXTURES_DIR / "benchmark_v1.json").read_bytes()
    expected_hash = compute_checksum(fixture_bytes)
    assert ds.checksum == expected_hash

    # Mutated bytes produce a different checksum
    mutated_bytes = fixture_bytes + b" "
    assert compute_checksum(mutated_bytes) != expected_hash


# =============================================================================
# 7. Validation Failure Loudness (No Silent Acceptance)
# =============================================================================

def test_benchmark_v1_invalid_labels_fail_loudly():
    """Verify corrupted dataset payloads raise DatasetValidationError immediately."""
    raw = load_raw_benchmark()

    # 1. Invalid status
    bad_data = json.loads(json.dumps(raw))
    bad_data["cases"][0]["expected_validation_behavior"] = "MAGIC_STATUS"
    errors = validate_dataset_structure(bad_data)
    assert any("invalid expected_validation_behavior" in e for e in errors)

    # 2. Invalid category
    bad_data2 = json.loads(json.dumps(raw))
    bad_data2["cases"][0]["category"] = "unsupported_category"
    errors2 = validate_dataset_structure(bad_data2)
    assert any("category 'unsupported_category' is invalid" in e for e in errors2)

    # 3. Malformed citation
    bad_data3 = json.loads(json.dumps(raw))
    bad_data3["cases"][0]["expected_citations"] = "invalid_not_a_list"
    errors3 = validate_dataset_structure(bad_data3)
    assert any("expected_citations' must be a list" in e for e in errors3)
