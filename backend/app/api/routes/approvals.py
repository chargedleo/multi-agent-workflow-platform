"""Pending Approvals API routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.db.session import get_db
from backend.app.models.schemas import (
    PendingApprovalSummary,
    PendingApprovalsListResponse,
)
from backend.app.services.workflow_runs import get_pending_approvals

logger = get_logger(__name__)

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get(
    "/pending",
    response_model=PendingApprovalsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List pending approval requests",
    description="Returns a paginated list of workflow runs currently suspended waiting for human approval.",
)
async def list_pending_approvals_endpoint(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db),
) -> PendingApprovalsListResponse:
    """Retrieve all workflows currently awaiting human approval."""
    items_data, total = await get_pending_approvals(session, page=page, page_size=page_size)

    items = [
        PendingApprovalSummary(
            approval_id=item["approval_id"],
            run_id=item["run_id"],
            request_id=item["request_id"],
            query=item["query"],
            status=item["status"],
            requested_at=item["requested_at"],
            revision_count=item["revision_count"],
            validation_status=item["validation_status"],
            validation_score=item["validation_score"],
        )
        for item in items_data
    ]

    return PendingApprovalsListResponse(
        items=items,
        total=total,
    )
