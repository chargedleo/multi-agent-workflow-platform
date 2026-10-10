"""Evaluation dataset loader and validator (Milestone 9A).

Responsible for:
- Loading versioned benchmark fixtures from disk (JSON / JSONL)
- Calculating deterministic SHA256 checksums
- Enforcing structural and semantic dataset validation (no silent drops)
- Listing available registered benchmark datasets
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from backend.app.core.logging import get_logger
from backend.app.evaluation.schemas import (
    BenchmarkCategory,
    EvaluationCase,
    EvaluationDataset,
)

logger = get_logger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class DatasetValidationError(ValueError):
    """Raised when an evaluation benchmark dataset violates schema or semantic integrity."""
    pass


def compute_checksum(raw_bytes: bytes) -> str:
    """Compute standard SHA256 checksum of raw dataset content."""
    return hashlib.sha256(raw_bytes).hexdigest()


def validate_dataset_structure(data: Dict[str, Any]) -> List[str]:
    """Inspect raw dictionary representation of a dataset and return validation errors."""
    errors: List[str] = []

    if not isinstance(data, dict):
        return ["Dataset root must be a JSON object/dictionary."]

    if not data.get("name") or not isinstance(data.get("name"), str):
        errors.append("Dataset 'name' is required and must be a non-empty string.")

    if not data.get("version") or not isinstance(data.get("version"), str):
        errors.append("Dataset 'version' is required and must be a non-empty string.")

    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) == 0:
        errors.append("Dataset 'cases' must be a non-empty list of benchmark cases.")
        return errors

    seen_ids: Set[str] = set()
    for idx, c in enumerate(cases):
        prefix = f"Case at index {idx}"
        if not isinstance(c, dict):
            errors.append(f"{prefix} must be a dictionary object.")
            continue

        case_id = c.get("case_id")
        if not case_id or not isinstance(case_id, str):
            errors.append(f"{prefix} is missing a valid 'case_id' string.")
        elif case_id in seen_ids:
            errors.append(f"Duplicate case_id '{case_id}' detected at index {idx}.")
        else:
            seen_ids.add(case_id)
            prefix = f"Case '{case_id}'"

        cat = c.get("category")
        valid_cats = {item.value for item in BenchmarkCategory}
        if not cat or cat not in valid_cats:
            errors.append(f"{prefix}: category '{cat}' is invalid. Allowed: {sorted(list(valid_cats))}")

        question = c.get("question")
        if not question or not isinstance(question, str) or len(question.strip()) < 2:
            errors.append(f"{prefix}: 'question' is missing or too short.")

        # Validate citation objects if present
        citations = c.get("expected_citations")
        if citations is not None:
            if not isinstance(citations, list):
                errors.append(f"{prefix}: 'expected_citations' must be a list.")
            else:
                for c_idx, cit in enumerate(citations):
                    if not isinstance(cit, dict):
                        errors.append(f"{prefix} expected_citation[{c_idx}] must be a dict.")

        # Validate validation status label
        expected_status = c.get("expected_validation_behavior", "PASS")
        if str(expected_status).upper() not in {"PASS", "FAIL", "RECOVERABLE", "BLOCKED"}:
            errors.append(f"{prefix}: invalid expected_validation_behavior '{expected_status}'.")

    return errors


def load_dataset(
    filepath: Optional[str] = None,
    name: str = "enterprise_workflow_benchmark",
    version: str = "1.0.0",
) -> EvaluationDataset:
    """Load, validate, and return an EvaluationDataset.

    Args:
        filepath: Optional direct path to JSON/JSONL benchmark fixture.
        name: Registered dataset name if filepath is not provided.
        version: Dataset version to resolve if filepath is not provided.

    Returns:
        Validated EvaluationDataset instance.

    Raises:
        DatasetValidationError: If dataset format, fields, or constraints are invalid.
        FileNotFoundError: If the target file does not exist.
    """
    target_path: Optional[Path] = None
    if filepath:
        target_path = Path(filepath).resolve()
    else:
        # Resolve from standard fixtures directory
        dataset_name = name or "enterprise_workflow_benchmark"
        candidates = [
            FIXTURES_DIR / f"{dataset_name}.json",
            FIXTURES_DIR / dataset_name,
            FIXTURES_DIR / f"{dataset_name}_v{version}.json",
            FIXTURES_DIR / f"{dataset_name}_v{version.split('.')[0]}.json",
        ]
        if dataset_name in {"enterprise_workflow_benchmark", "benchmark", "benchmark_v1", "benchmark_v1.json"}:
            candidates.append(FIXTURES_DIR / "benchmark_v1.json")

        for cand in candidates:
            if cand.is_file():
                target_path = cand
                break

    if not target_path or not target_path.exists():
        raise FileNotFoundError(f"Benchmark dataset fixture not found for '{filepath or name}' in {FIXTURES_DIR}")

    raw_bytes = target_path.read_bytes()
    checksum = compute_checksum(raw_bytes)

    try:
        raw_text = raw_bytes.decode("utf-8")
        if target_path.suffix == ".jsonl":
            lines = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
            raw_data = {
                "name": name,
                "version": version,
                "description": f"Loaded from {target_path.name}",
                "cases": lines,
            }
        else:
            raw_data = json.loads(raw_text)
    except Exception as exc:
        raise DatasetValidationError(f"Malformed JSON in dataset file '{target_path.name}': {exc}") from exc

    # Perform thorough structural validation
    errors = validate_dataset_structure(raw_data)
    if errors:
        msg = f"Dataset validation failed for '{target_path.name}' with {len(errors)} error(s):\n" + "\n".join(
            f" - {e}" for e in errors
        )
        logger.error(msg)
        raise DatasetValidationError(msg)

    dataset = EvaluationDataset.model_validate(raw_data)
    dataset.checksum = checksum
    logger.info(
        f"Loaded evaluation dataset '{dataset.name}' (v{dataset.version}) with "
        f"{len(dataset.cases)} cases. SHA256: {checksum[:12]}..."
    )
    return dataset


def list_available_datasets() -> List[Dict[str, Any]]:
    """Scan registered fixtures directory and return metadata for available benchmarks."""
    results: List[Dict[str, Any]] = []
    if not FIXTURES_DIR.exists():
        return results

    for file in sorted(FIXTURES_DIR.glob("*.json")):
        if file.name.endswith("_corpus.json"):
            continue
        try:
            ds = load_dataset(filepath=str(file))
            results.append(
                {
                    "name": ds.name,
                    "version": ds.version,
                    "description": ds.description,
                    "case_count": len(ds.cases),
                    "checksum": ds.checksum,
                    "filename": file.name,
                }
            )
        except Exception as exc:
            logger.warning(f"Could not load fixture metadata for '{file.name}': {exc}")
    return results
