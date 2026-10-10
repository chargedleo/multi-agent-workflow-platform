"""Tests for evaluation dataset loading, validation, and fixture integrity."""

import json
import pytest
from pathlib import Path

from backend.app.evaluation.dataset import (
    DatasetValidationError,
    load_dataset,
    list_available_datasets,
    validate_dataset_structure,
)
from backend.app.evaluation.schemas import BenchmarkCategory, EvaluationDataset


def test_load_default_benchmark_v1():
    """Verify that the official benchmark_v1 fixture loads cleanly with 35 cases."""
    ds = load_dataset()
    assert isinstance(ds, EvaluationDataset)
    assert ds.name == "enterprise_workflow_benchmark"
    assert ds.version == "1.0.0"
    assert len(ds.cases) == 35
    assert ds.checksum is not None
    assert len(ds.checksum) == 64  # Valid SHA256 hex string

    # Verify categories presence across all 7 categories (A through G)
    categories_found = {c.category for c in ds.cases}
    expected_categories = {
        BenchmarkCategory.ANSWERABLE,
        BenchmarkCategory.MULTI_HOP,
        BenchmarkCategory.UNANSWERABLE,
        BenchmarkCategory.AMBIGUOUS,
        BenchmarkCategory.CITATION_SENSITIVE,
        BenchmarkCategory.UNSUPPORTED_PREMISE,
        BenchmarkCategory.RETRIEVAL_EDGE_CASE,
    }
    assert categories_found == expected_categories


def test_validation_missing_root_fields():
    """Verify error when name or version or cases are missing."""
    with pytest.raises(DatasetValidationError, match="name"):
        validate_errors = validate_dataset_structure({"version": "1.0.0", "cases": []})
        if validate_errors:
            raise DatasetValidationError("; ".join(validate_errors))

    with pytest.raises(DatasetValidationError, match="version"):
        validate_errors = validate_dataset_structure({"name": "test", "cases": []})
        if validate_errors:
            raise DatasetValidationError("; ".join(validate_errors))


def test_validation_empty_cases():
    """Verify error on empty cases list."""
    errors = validate_dataset_structure({"name": "test", "version": "1.0.0", "cases": []})
    assert any("non-empty list" in e for e in errors)


def test_validation_duplicate_case_id():
    """Verify error on duplicate case IDs."""
    data = {
        "name": "dup_test",
        "version": "1.0.0",
        "cases": [
            {
                "case_id": "CASE-01",
                "dataset_version": "1.0.0",
                "category": "answerable",
                "question": "Question 1",
            },
            {
                "case_id": "CASE-01",
                "dataset_version": "1.0.0",
                "category": "answerable",
                "question": "Question 2 with same ID",
            },
        ],
    }
    errors = validate_dataset_structure(data)
    assert any("Duplicate case_id 'CASE-01'" in e for e in errors)


def test_validation_invalid_category():
    """Verify error when case specifies an unknown category."""
    data = {
        "name": "cat_test",
        "version": "1.0.0",
        "cases": [
            {
                "case_id": "CASE-INVALID-CAT",
                "dataset_version": "1.0.0",
                "category": "unsupported_magic_category",
                "question": "Valid question?",
            }
        ],
    }
    errors = validate_dataset_structure(data)
    assert any("category 'unsupported_magic_category' is invalid" in e for e in errors)


def test_validation_malformed_citations():
    """Verify error when citations field is not a list or elements are not dicts."""
    data = {
        "name": "cit_test",
        "version": "1.0.0",
        "cases": [
            {
                "case_id": "CASE-BAD-CIT",
                "dataset_version": "1.0.0",
                "category": "answerable",
                "question": "Valid question?",
                "expected_citations": "not a list",
            }
        ],
    }
    errors = validate_dataset_structure(data)
    assert any("expected_citations' must be a list" in e for e in errors)


def test_validation_invalid_validation_behavior():
    """Verify error when expected_validation_behavior is invalid."""
    data = {
        "name": "behav_test",
        "version": "1.0.0",
        "cases": [
            {
                "case_id": "CASE-BAD-BEHAV",
                "dataset_version": "1.0.0",
                "category": "answerable",
                "question": "Valid question?",
                "expected_validation_behavior": "UNKNOWN_ACTION",
            }
        ],
    }
    errors = validate_dataset_structure(data)
    assert any("invalid expected_validation_behavior" in e for e in errors)


def test_load_dataset_file_not_found():
    """Verify FileNotFoundError on non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_dataset(filepath="non_existent_dataset.json")


def test_list_available_datasets():
    """Verify dataset discovery returns benchmark_v1."""
    datasets = list_available_datasets()
    assert len(datasets) >= 1
    found = next((d for d in datasets if d["name"] == "enterprise_workflow_benchmark"), None)
    assert found is not None
    assert found["version"] == "1.0.0"
    assert found["case_count"] == 35
