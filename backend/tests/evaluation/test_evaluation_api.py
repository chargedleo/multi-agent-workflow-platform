"""Integration tests for Evaluation Engine REST API endpoints (Milestone 9A)."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.evaluation.schemas import EvaluationMode, StartEvaluationRequest
from backend.app.evaluation.service import EvaluationService


@pytest.mark.asyncio
async def test_list_datasets_endpoint(async_client: AsyncClient):
    """GET /api/v1/evaluations/datasets returns registered benchmark metadata."""
    resp = await async_client.get("/api/v1/evaluations/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    found = any(d["name"] == "enterprise_workflow_benchmark" for d in data)
    assert found


@pytest.mark.asyncio
async def test_start_evaluation_and_get_details(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/evaluations creates run and GET /api/v1/evaluations/{id} retrieves it."""
    payload = {
        "dataset_name": "benchmark_v1",
        "mode": "metric_only",
        "max_concurrency": 2,
        "timeout_per_case_seconds": 15.0,
    }
    create_resp = await async_client.post("/api/v1/evaluations", json=payload)
    assert create_resp.status_code == 201
    run_data = create_resp.json()
    run_id = run_data["id"]
    assert run_data["dataset_name"] == "enterprise_workflow_benchmark"
    assert run_data["mode"] == "metric_only"
    assert run_data["status"] in {"PENDING", "RUNNING", "COMPLETED"}

    # Fetch by ID
    get_resp = await async_client.get(f"/api/v1/evaluations/{run_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == run_id


@pytest.mark.asyncio
async def test_start_evaluation_invalid_dataset(async_client: AsyncClient):
    """POST /api/v1/evaluations with invalid dataset returns 400 Bad Request."""
    payload = {
        "dataset_name": "non_existent_dataset_123",
        "mode": "metric_only",
    }
    resp = await async_client.post("/api/v1/evaluations", json=payload)
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_evaluation_not_found(async_client: AsyncClient):
    """GET /api/v1/evaluations/{id} for nonexistent run returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/evaluations/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_evaluation_invalid_uuid(async_client: AsyncClient):
    """GET /api/v1/evaluations/{id} for non-UUID string returns 400."""
    resp = await async_client.get("/api/v1/evaluations/not-a-valid-uuid")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_evaluations_endpoint(async_client: AsyncClient):
    """GET /api/v1/evaluations returns paginated list of runs."""
    resp = await async_client.get("/api/v1/evaluations?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_case_results_and_report_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """Verify results and report endpoints after executing an evaluation run."""
    # Create and synchronously run an evaluation
    run_record = await EvaluationService.create_evaluation_run(
        session=db_session,
        dataset_name="benchmark_v1",
        mode=EvaluationMode.METRIC_ONLY,
    )
    run_id = str(run_record.id)

    # Execute synchronous task
    req = StartEvaluationRequest(
        dataset_name="benchmark_v1",
        mode=EvaluationMode.METRIC_ONLY,
        max_concurrency=4,
        timeout_per_case_seconds=10.0,
    )
    await EvaluationService.execute_run_task(run_id, req)

    # Check results endpoint
    results_resp = await async_client.get(f"/api/v1/evaluations/{run_id}/results?page=1&page_size=50")
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert "items" in results_data
    assert results_data["total"] > 0
    assert len(results_data["items"]) > 0

    # Check report endpoint
    report_resp = await async_client.get(f"/api/v1/evaluations/{run_id}/report")
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert report_data["evaluation_run_id"] == run_id
    assert "summary" in report_data
    assert "case_results" in report_data


@pytest.mark.asyncio
async def test_compare_evaluations_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/evaluations/compare computes deltas between two runs."""
    # Create two runs
    run1 = await EvaluationService.create_evaluation_run(
        session=db_session,
        dataset_name="benchmark_v1",
        mode=EvaluationMode.METRIC_ONLY,
    )
    run2 = await EvaluationService.create_evaluation_run(
        session=db_session,
        dataset_name="benchmark_v1",
        mode=EvaluationMode.METRIC_ONLY,
    )

    req = StartEvaluationRequest(
        dataset_name="benchmark_v1",
        mode=EvaluationMode.METRIC_ONLY,
    )
    await EvaluationService.execute_run_task(str(run1.id), req)
    await EvaluationService.execute_run_task(str(run2.id), req)

    compare_payload = {
        "baseline_run_id": str(run1.id),
        "comparison_run_id": str(run2.id),
    }
    resp = await async_client.post("/api/v1/evaluations/compare", json=compare_payload)
    assert resp.status_code == 200
    comp_data = resp.json()
    assert comp_data["baseline_run_id"] == str(run1.id)
    assert comp_data["comparison_run_id"] == str(run2.id)
    assert "metric_deltas" in comp_data
    assert "summary_verdict" in comp_data


@pytest.mark.asyncio
async def test_compare_evaluations_not_found(async_client: AsyncClient):
    """POST /api/v1/evaluations/compare with nonexistent run returns 404."""
    payload = {
        "baseline_run_id": str(uuid.uuid4()),
        "comparison_run_id": str(uuid.uuid4()),
    }
    resp = await async_client.post("/api/v1/evaluations/compare", json=payload)
    assert resp.status_code == 404
