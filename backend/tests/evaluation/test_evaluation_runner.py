"""Unit tests for EvaluationRunner in METRIC_ONLY mode and edge-case execution."""

import pytest
from unittest.mock import patch

from backend.app.evaluation.dataset import load_dataset
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.evaluation.schemas import EvaluationMode, EvaluationRunReport


@pytest.mark.asyncio
async def test_runner_metric_only_full_dataset():
    """Verify that EvaluationRunner completes all 35 cases in METRIC_ONLY mode offline."""
    dataset = load_dataset()
    runner = EvaluationRunner(concurrency_limit=4)

    report = await runner.run(dataset=dataset, mode=EvaluationMode.METRIC_ONLY)

    assert isinstance(report, EvaluationRunReport)
    assert report.summary.total_cases == 35
    assert report.summary.completed_cases == 35
    assert report.summary.failed_cases == 0
    assert len(report.failures) == 0

    # Verify category breakdown contains all 7 categories
    assert len(report.category_breakdown) == 7
    assert "answerable" in report.category_breakdown
    assert "multi_hop" in report.category_breakdown
    assert "unanswerable" in report.category_breakdown
    assert "ambiguous" in report.category_breakdown
    assert "citation_sensitive" in report.category_breakdown
    assert "unsupported_premise" in report.category_breakdown
    assert "retrieval_edge_case" in report.category_breakdown

    # Verify summary metrics are computed cleanly
    assert report.summary.mean_precision_at_3 > 0.0
    assert report.summary.mrr > 0.0
    assert report.summary.citation_presence_rate > 0.0
    assert report.summary.mean_fact_coverage > 0.0
    assert report.summary.guardrail_accuracy > 0.0


@pytest.mark.asyncio
async def test_runner_case_id_filtering():
    """Verify runner evaluates only specifically requested case_ids."""
    dataset = load_dataset()
    runner = EvaluationRunner()

    report = await runner.run(
        dataset=dataset,
        mode=EvaluationMode.METRIC_ONLY,
        case_ids=["CASE-A01", "CASE-A02"],
    )

    assert report.summary.total_cases == 2
    assert report.summary.completed_cases == 2
    assert [c.case_id for c in report.case_results] == ["CASE-A01", "CASE-A02"]


@pytest.mark.asyncio
async def test_runner_invalid_case_id_raises_error():
    """Verify ValueError when requested case_id does not exist."""
    dataset = load_dataset()
    runner = EvaluationRunner()

    with pytest.raises(ValueError, match="Requested case_id 'NON_EXISTENT' not found"):
        await runner.run(
            dataset=dataset,
            mode=EvaluationMode.METRIC_ONLY,
            case_ids=["NON_EXISTENT"],
        )


@pytest.mark.asyncio
async def test_runner_max_cases_bounding():
    """Verify max_cases bounds the evaluation run."""
    dataset = load_dataset()
    runner = EvaluationRunner()

    report = await runner.run(
        dataset=dataset,
        mode=EvaluationMode.METRIC_ONLY,
        max_cases=5,
    )

    assert report.summary.total_cases == 5
    assert len(report.case_results) == 5


@pytest.mark.asyncio
async def test_runner_error_isolation_preserves_other_cases():
    """Verify that an individual case failure is isolated and does not abort the run."""
    dataset = load_dataset()
    runner = EvaluationRunner()

    original_execute = runner._execute_case

    async def mock_execute(case, mode, eval_run_id):
        if case.case_id == "CASE-A02":
            raise RuntimeError("Simulated failure on CASE-A02")
        return await original_execute(case, mode, eval_run_id)

    with patch.object(runner, "_execute_case", side_effect=mock_execute):
        report = await runner.run(
            dataset=dataset,
            mode=EvaluationMode.METRIC_ONLY,
            case_ids=["CASE-A01", "CASE-A02", "CASE-A03"],
        )

        assert report.summary.total_cases == 3
        assert report.summary.completed_cases == 2
        assert report.summary.failed_cases == 1
        assert len(report.failures) == 1
        assert report.failures[0]["case_id"] == "CASE-A02"
        assert "Simulated failure" in report.failures[0]["error"]
