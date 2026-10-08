"""Tests for Milestone 7 Dashboard API endpoints: aggregated statistics, status filtering, and search."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from backend.app.db.models.workflow_run import WorkflowRun
from backend.app.db.session import get_session_factory


@pytest.mark.asyncio
async def test_get_workflow_stats_baseline(async_client: AsyncClient):
    """Verify GET /api/v1/workflows/stats returns aggregated metrics structure."""
    response = await async_client.get("/api/v1/workflows/stats")
    assert response.status_code == 200

    data = response.json()
    assert "total_runs" in data
    assert "active_runs" in data
    assert "awaiting_approval" in data
    assert "completed_runs" in data
    assert "failed_runs" in data
    assert "rejected_runs" in data
    assert "avg_duration_ms" in data
    assert isinstance(data["total_runs"], int)
    assert data["total_runs"] >= 0


@pytest.mark.asyncio
async def test_workflow_stats_aggregation_and_averages(async_client: AsyncClient):
    """Verify that get_workflow_stats calculates correct totals and average duration."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:6]

    async with session_factory() as session:
        # 1. Completed run
        run_comp = WorkflowRun(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            user_query=f"Completed query {suffix}",
            status="COMPLETED",
            duration_ms=2000,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            validation_status="PASS",
        )
        # 2. Waiting for approval run
        run_await = WorkflowRun(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            user_query=f"Approval query {suffix}",
            status="WAITING_FOR_APPROVAL",
            approval_status="PENDING",
            started_at=datetime.now(timezone.utc),
        )
        # 3. Failed run
        run_fail = WorkflowRun(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            user_query=f"Failed query {suffix}",
            status="FAILED",
            errors=["Network timeout"],
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        # 4. Running (active) run
        run_active = WorkflowRun(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            user_query=f"Active query {suffix}",
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
        )
        # 5. Rejected run
        run_rej = WorkflowRun(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            user_query=f"Rejected query {suffix}",
            status="CANCELLED",
            approval_status="REJECTED",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

        session.add_all([run_comp, run_await, run_fail, run_active, run_rej])
        await session.commit()

    # Query stats endpoint
    response = await async_client.get("/api/v1/workflows/stats")
    assert response.status_code == 200
    stats = response.json()

    assert stats["total_runs"] >= 5
    assert stats["active_runs"] >= 1
    assert stats["awaiting_approval"] >= 1
    assert stats["completed_runs"] >= 1
    assert stats["failed_runs"] >= 1
    assert stats["rejected_runs"] >= 1
    assert stats["avg_duration_ms"] is not None
    assert stats["avg_duration_ms"] > 0


@pytest.mark.asyncio
async def test_list_workflows_filtering_by_status(async_client: AsyncClient):
    """Verify that status filter query parameter filters runs appropriately."""
    session_factory = get_session_factory()
    tag = uuid.uuid4().hex[:6]

    async with session_factory() as session:
        r1 = WorkflowRun(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            user_query=f"Status test completed {tag}",
            status="COMPLETED",
        )
        r2 = WorkflowRun(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            user_query=f"Status test approval {tag}",
            status="WAITING_FOR_APPROVAL",
        )
        session.add_all([r1, r2])
        await session.commit()

    # Filter by COMPLETED
    res_comp = await async_client.get(f"/api/v1/workflows?status=COMPLETED&search={tag}")
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    assert data_comp["total"] == 1
    assert data_comp["items"][0]["status"] == "COMPLETED"
    assert data_comp["items"][0]["current_stage"] == "completed"

    # Filter by WAITING_FOR_APPROVAL
    res_appr = await async_client.get(f"/api/v1/workflows?status=WAITING_FOR_APPROVAL&search={tag}")
    assert res_appr.status_code == 200
    data_appr = res_appr.json()
    assert data_appr["total"] == 1
    assert data_appr["items"][0]["status"] == "WAITING_FOR_APPROVAL"
    assert data_appr["items"][0]["current_stage"] == "human_approval"


@pytest.mark.asyncio
async def test_list_workflows_search_by_query_text_and_id(async_client: AsyncClient):
    """Verify that search query parameter matches query string or run ID."""
    session_factory = get_session_factory()
    unique_keyword = f"telemetry_{uuid.uuid4().hex[:8]}"
    run_uuid = uuid.uuid4()

    async with session_factory() as session:
        run = WorkflowRun(
            id=run_uuid,
            request_id=uuid.uuid4(),
            user_query=f"Perform deep analysis on {unique_keyword} dataset",
            status="COMPLETED",
        )
        session.add(run)
        await session.commit()

    # Search by keyword
    res = await async_client.get(f"/api/v1/workflows?search={unique_keyword}")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    assert unique_keyword in items[0]["query"]
    assert items[0]["run_id"] == str(run_uuid)

    # Search by UUID prefix
    uuid_prefix = str(run_uuid)[:8]
    res_id = await async_client.get(f"/api/v1/workflows?search={uuid_prefix}")
    assert res_id.status_code == 200
    assert any(it["run_id"] == str(run_uuid) for it in res_id.json()["items"])


@pytest.mark.asyncio
async def test_dashboard_route_no_uuid_conflict(async_client: AsyncClient):
    """Ensure /api/v1/workflows/stats does not conflict with /api/v1/workflows/{run_id}."""
    stats_res = await async_client.get("/api/v1/workflows/stats")
    assert stats_res.status_code == 200
    assert "total_runs" in stats_res.json()

    not_found_res = await async_client.get(f"/api/v1/workflows/{uuid.uuid4()}")
    assert not_found_res.status_code == 404
