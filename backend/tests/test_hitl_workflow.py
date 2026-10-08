"""Milestone 6 Tests: Human-in-the-Loop Approval, Interrupt/Resume, and Durable Workflow Control."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.db.models.workflow_run import WorkflowRun
from backend.app.db.models.workflow_approval import WorkflowApproval
from backend.app.graph.checkpointer import init_checkpointer, set_checkpointer, close_checkpointer
from backend.app.graph.workflow import get_compiled_workflow, reset_compiled_workflow, resume_workflow, run_workflow
from backend.app.services.workflow_runs import _to_uuid, get_workflow_run


@pytest.fixture
async def enable_hitl(monkeypatch):
    """Fixture ensuring human approval gate is active for M6 tests."""
    settings = get_settings()
    monkeypatch.setattr(settings, "APPROVAL_ENABLED", True)
    monkeypatch.setattr(settings, "MAX_APPROVAL_REVISIONS", 3)
    await init_checkpointer()
    reset_compiled_workflow()
    yield
    reset_compiled_workflow()


@pytest.mark.asyncio
async def test_hitl_workflow_suspends_at_approval_gate(enable_hitl, db_session: AsyncSession):
    """Verify workflow executes through validation and suspends at Human Approval Gate."""
    query = "Compare PostgreSQL and MongoDB connection pooling architectures."
    req_id = str(uuid.uuid4())

    state = await run_workflow(query=query, request_id=req_id)

    # 1. Workflow state inspection
    assert state.get("status") == "WAITING_FOR_APPROVAL"
    assert state.get("approval_status") == "PENDING"
    assert "__interrupt__" in state
    assert state.get("final_answer") is not None
    assert len(state["final_answer"].get("answer", "")) > 10
    assert state.get("approval_revision", 0) == 0

    run_id = state.get("run_id")
    assert run_id is not None

    # 2. Database persistence inspection
    run_record = await get_workflow_run(db_session, run_id=run_id)
    assert run_record is not None
    assert run_record.status == "WAITING_FOR_APPROVAL"
    assert run_record.approval_status == "PENDING"
    assert run_record.final_answer is not None

    # 3. Dedicated workflow_approvals table inspection
    assert len(run_record.approvals) == 1
    approval = run_record.approvals[0]
    assert approval.status == "PENDING"
    assert approval.revision_count == 0
    assert approval.decision is None
    assert approval.decided_at is None


@pytest.mark.asyncio
async def test_hitl_workflow_resume_approve(enable_hitl, db_session: AsyncSession):
    """Verify that approving a suspended workflow transitions it to COMPLETED with APPROVED status."""
    query = "Evaluate PostgreSQL read replicas vs distributed CockroachDB."
    req_id = str(uuid.uuid4())

    init_state = await run_workflow(query=query, request_id=req_id)
    run_id = init_state.get("run_id")
    assert init_state.get("status") == "WAITING_FOR_APPROVAL"

    # Resume with approval decision
    resumed_state = await resume_workflow(
        run_id=run_id,
        decision="APPROVE",
        feedback="Verified technical accuracy. Approved for publishing.",
        decided_by="senior_architect",
    )

    # 1. State assertions
    assert resumed_state.get("status") == "COMPLETED"
    assert resumed_state.get("approval_status") == "APPROVED"
    assert "__interrupt__" not in resumed_state or not resumed_state["__interrupt__"]

    # 2. Database assertions
    run_record = await get_workflow_run(db_session, run_id=run_id)
    assert run_record is not None
    assert run_record.status == "COMPLETED"
    assert run_record.approval_status == "APPROVED"
    assert run_record.completed_at is not None

    # 3. Approval record audit trail
    assert len(run_record.approvals) >= 1
    last_app = run_record.approvals[-1]
    assert last_app.status == "APPROVED"
    assert last_app.decision == "APPROVE"
    assert last_app.decided_by == "senior_architect"
    assert "Approved for publishing" in (last_app.feedback or "")
    assert last_app.decided_at is not None


@pytest.mark.asyncio
async def test_hitl_workflow_resume_reject(enable_hitl, db_session: AsyncSession):
    """Verify that rejecting a suspended workflow terminates it as FAILED with REJECTED status."""
    query = "Provide recommendations on legacy database deprecation."
    req_id = str(uuid.uuid4())

    init_state = await run_workflow(query=query, request_id=req_id)
    run_id = init_state.get("run_id")
    assert init_state.get("status") == "WAITING_FOR_APPROVAL"

    # Resume with rejection decision
    resumed_state = await resume_workflow(
        run_id=run_id,
        decision="REJECT",
        feedback="Recommendations violate corporate compliance standards.",
        decided_by="compliance_officer",
    )

    # 1. State assertions
    assert resumed_state.get("status") == "FAILED"
    assert resumed_state.get("approval_status") == "REJECTED"

    # 2. Database assertions
    run_record = await get_workflow_run(db_session, run_id=run_id)
    assert run_record is not None
    assert run_record.status == "FAILED"
    assert run_record.approval_status == "REJECTED"

    # 3. Approval record audit trail
    assert len(run_record.approvals) >= 1
    last_app = run_record.approvals[-1]
    assert last_app.status == "REJECTED"
    assert last_app.decision == "REJECT"
    assert last_app.decided_by == "compliance_officer"
    assert "corporate compliance" in (last_app.feedback or "")


@pytest.mark.asyncio
async def test_hitl_workflow_revision_loop(enable_hitl, db_session: AsyncSession):
    """Verify CHANGES_REQUESTED cycles through responder with feedback and re-suspends at gate."""
    query = "Summarize total sales revenue metrics for the current quarter."
    req_id = str(uuid.uuid4())

    init_state = await run_workflow(query=query, request_id=req_id)
    run_id = init_state.get("run_id")
    assert init_state.get("status") == "WAITING_FOR_APPROVAL"
    first_answer = init_state["final_answer"]["answer"]

    # Turn 1: Reviewer requests changes with specific instructions
    revised_state = await resume_workflow(
        run_id=run_id,
        decision="CHANGES_REQUESTED",
        feedback="Please include exact revenue figures and breakdown by category.",
        decided_by="finance_director",
    )

    # Must re-suspend at approval gate with revision 1
    assert revised_state.get("status") == "WAITING_FOR_APPROVAL"
    assert revised_state.get("approval_status") == "PENDING"
    assert revised_state.get("approval_revision") == 1
    second_answer = revised_state["final_answer"]["answer"]
    assert second_answer is not None

    # Verify database has 2 approval records: turn 1 decided, turn 2 pending
    run_record = await get_workflow_run(db_session, run_id=run_id)
    assert len(run_record.approvals) == 2
    assert run_record.approvals[0].status == "CHANGES_REQUESTED"
    assert run_record.approvals[0].decision == "CHANGES_REQUESTED"
    assert run_record.approvals[1].status == "PENDING"
    assert run_record.approvals[1].revision_count == 1

    # Turn 2: Reviewer is now satisfied and approves revision
    final_state = await resume_workflow(
        run_id=run_id,
        decision="APPROVE",
        feedback="Breakdown is clear and accurate.",
        decided_by="finance_director",
    )

    assert final_state.get("status") == "COMPLETED"
    assert final_state.get("approval_status") == "APPROVED"

    db_session.expire_all()
    updated_run = await get_workflow_run(db_session, run_id=run_id)
    assert updated_run.status == "COMPLETED"
    assert updated_run.approval_status == "APPROVED"
    assert len(updated_run.approvals) == 2
    assert updated_run.approvals[1].status == "APPROVED"


@pytest.mark.asyncio
async def test_hitl_workflow_max_revisions_bounded(enable_hitl, monkeypatch, db_session: AsyncSession):
    """Verify that exceeding MAX_APPROVAL_REVISIONS automatically finalizes workflow as REJECTED."""
    settings = get_settings()
    monkeypatch.setattr(settings, "MAX_APPROVAL_REVISIONS", 2)

    query = "Generate quarterly enterprise strategy report."
    req_id = str(uuid.uuid4())

    state = await run_workflow(query=query, request_id=req_id)
    run_id = state.get("run_id")

    # Revision 1
    s1 = await resume_workflow(run_id=run_id, decision="CHANGES_REQUESTED", feedback="Needs revision 1")
    assert s1.get("status") == "WAITING_FOR_APPROVAL"
    assert s1.get("approval_revision") == 1

    # Revision 2
    s2 = await resume_workflow(run_id=run_id, decision="CHANGES_REQUESTED", feedback="Needs revision 2")
    assert s2.get("status") == "WAITING_FOR_APPROVAL"
    assert s2.get("approval_revision") == 2

    # Revision 3: Exceeds max revisions (limit is 2)
    s3 = await resume_workflow(run_id=run_id, decision="CHANGES_REQUESTED", feedback="Needs revision 3")
    assert s3.get("status") == "FAILED"
    assert s3.get("approval_status") == "REJECTED"

    run_record = await get_workflow_run(db_session, run_id=run_id)
    assert run_record.status == "FAILED"
    assert run_record.approval_status == "REJECTED"


@pytest.mark.asyncio
async def test_hitl_api_pending_approvals_endpoint(enable_hitl, async_client: AsyncClient):
    """Verify GET /api/v1/approvals/pending returns active pending approvals."""
    query = "Analyze PostgreSQL indexing performance."
    resp = await async_client.post("/api/v1/workflows", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "waiting_for_approval"
    run_id = data["run_id"]

    # Call pending approvals endpoint
    list_resp = await async_client.get("/api/v1/approvals/pending")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    pending_items = list_data["items"]
    matching = [item for item in pending_items if item["run_id"] == run_id]
    assert len(matching) == 1
    assert matching[0]["status"] == "PENDING"
    assert matching[0]["query"] == query


@pytest.mark.asyncio
async def test_hitl_api_get_and_post_approval_decision(enable_hitl, async_client: AsyncClient):
    """Verify GET /api/v1/workflows/{run_id}/approval and POST decision endpoint."""
    query = "Assess data warehouse partitioning options."
    post_res = await async_client.post("/api/v1/workflows", json={"query": query})
    run_id = post_res.json()["run_id"]

    # GET approval inspection endpoint
    get_res = await async_client.get(f"/api/v1/workflows/{run_id}/approval")
    assert get_res.status_code == 200
    approval_detail = get_res.json()
    assert approval_detail["run_id"] == run_id
    assert approval_detail["approval_status"] == "PENDING"
    assert approval_detail["current_approval"] is not None
    assert approval_detail["answer"] is not None
    assert approval_detail["max_revisions"] == 3

    # POST approval decision
    decision_payload = {
        "decision": "APPROVE",
        "feedback": "Architecture assessment meets requirements.",
        "decided_by": "lead_engineer",
    }
    decision_res = await async_client.post(f"/api/v1/workflows/{run_id}/approval", json=decision_payload)
    assert decision_res.status_code == 200
    updated_run = decision_res.json()
    assert updated_run["status"] == "COMPLETED"
    assert updated_run["approval_status"] == "APPROVED"
    assert len(updated_run["approvals"]) >= 1


@pytest.mark.asyncio
async def test_hitl_api_conflict_on_already_decided_run(enable_hitl, async_client: AsyncClient):
    """Verify submitting a decision on a run not waiting for approval returns 409 Conflict."""
    query = "Quick validation query."
    post_res = await async_client.post("/api/v1/workflows", json={"query": query})
    run_id = post_res.json()["run_id"]

    # First approve
    await async_client.post(
        f"/api/v1/workflows/{run_id}/approval",
        json={"decision": "APPROVE", "feedback": "Approved"},
    )

    # Second decision should return 409 Conflict
    conflict_res = await async_client.post(
        f"/api/v1/workflows/{run_id}/approval",
        json={"decision": "REJECT", "feedback": "Too late"},
    )
    assert conflict_res.status_code == 409
    assert "not awaiting approval" in conflict_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hitl_api_invalid_decision_returns_400(enable_hitl, async_client: AsyncClient):
    """Verify submitting an invalid decision value returns 400 Bad Request."""
    query = "Validation query for bad decision."
    post_res = await async_client.post("/api/v1/workflows", json={"query": query})
    run_id = post_res.json()["run_id"]

    bad_res = await async_client.post(
        f"/api/v1/workflows/{run_id}/approval",
        json={"decision": "MAYBE", "feedback": "Undecided"},
    )
    assert bad_res.status_code == 400
    assert "invalid decision" in bad_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hitl_durable_checkpoint_survives_restart(enable_hitl, db_session: AsyncSession):
    """Verify workflow state checkpoint survives connection reset / simulated restart."""
    query = "Durable restart test: compare database transaction isolation levels."
    req_id = str(uuid.uuid4())

    # Step 1: Run until interrupt
    state1 = await run_workflow(query=query, request_id=req_id)
    run_id = state1.get("run_id")
    assert state1.get("status") == "WAITING_FOR_APPROVAL"

    # Step 2: Simulate process / connection restart
    # Reset cached workflow and checkpointer pool
    reset_compiled_workflow()
    await close_checkpointer()

    # Re-initialize checkpointer (simulating clean boot of backend server)
    await init_checkpointer()
    reset_compiled_workflow()

    # Step 3: Resume workflow from durable database checkpoint
    resumed = await resume_workflow(
        run_id=run_id,
        decision="APPROVE",
        feedback="Verified after clean restart.",
        decided_by="ops_lead",
    )

    assert resumed.get("status") == "COMPLETED"
    assert resumed.get("approval_status") == "APPROVED"

    db_session.expire_all()
    run_record = await get_workflow_run(db_session, run_id=run_id)
    assert run_record.status == "COMPLETED"
    assert run_record.approval_status == "APPROVED"
