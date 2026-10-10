"""Evaluation Engine API routes (Milestone 9A).

Endpoints:
- POST /api/v1/evaluations: Start benchmark evaluation
- GET /api/v1/evaluations: List past evaluation runs
- GET /api/v1/evaluations/datasets: List available benchmark datasets
- GET /api/v1/evaluations/{evaluation_id}: Get run status and summary
- GET /api/v1/evaluations/{evaluation_id}/results: Get per-case results
- GET /api/v1/evaluations/{evaluation_id}/report: Download full JSON report
- POST /api/v1/evaluations/compare: Compare two evaluation runs
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.db.models.evaluation import EvaluationRun
from backend.app.db.session import get_db
from backend.app.evaluation.dataset import DatasetValidationError
from backend.app.evaluation.schemas import (
    CaseResultsListResponse,
    DatasetMetadataResponse,
    EvaluationComparisonReport,
    EvaluationComparisonRequest,
    EvaluationRunListResponse,
    EvaluationRunReport,
    EvaluationRunResponse,
    StartEvaluationRequest,
)
from backend.app.evaluation.service import EvaluationService

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


def _to_run_response(run: EvaluationRun) -> EvaluationRunResponse:
    """Map SQLAlchemy EvaluationRun model to Pydantic response."""
    return EvaluationRunResponse(
        id=str(run.id),
        dataset_name=run.dataset_name,
        dataset_version=run.dataset_version,
        dataset_checksum=run.dataset_checksum,
        mode=run.mode,
        application_version=run.application_version,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        configuration_snapshot=run.configuration_snapshot or {},
        aggregate_metrics=run.aggregate_metrics or {},
        summary=run.summary or {},
        error=run.error,
        created_at=run.created_at,
    )


def _validate_uuid(val: str, field_name: str = "id") -> uuid.UUID:
    """Validate string as UUID or raise 400 Bad Request."""
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format for {field_name}: '{val}'",
        )


@router.post(
    "",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start evaluation benchmark run",
    description="Initializes a new benchmark evaluation execution against a versioned dataset.",
)
async def start_evaluation_endpoint(
    request: StartEvaluationRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    """Trigger an evaluation run and schedule its execution in the background."""
    try:
        run_record = await EvaluationService.create_evaluation_run(
            session=session,
            dataset_name=request.dataset_name,
            mode=request.mode,
            max_concurrency=request.max_concurrency,
            timeout_per_case_seconds=request.timeout_per_case_seconds,
        )
    except (DatasetValidationError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot initialize evaluation run: {exc}",
        )
    except Exception as exc:
        logger.error(f"Failed to create evaluation run: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize evaluation benchmark run",
        )

    # Schedule background execution
    background_tasks.add_task(
        EvaluationService.execute_run_task,
        run_id=str(run_record.id),
        request=request,
    )

    return _to_run_response(run_record)


@router.get(
    "/datasets",
    response_model=List[DatasetMetadataResponse],
    status_code=status.HTTP_200_OK,
    summary="List available benchmark datasets",
    description="Returns metadata for all registered benchmark fixtures.",
)
async def list_datasets_endpoint() -> List[DatasetMetadataResponse]:
    """Retrieve metadata for available benchmark datasets."""
    return EvaluationService.get_available_datasets_metadata()


@router.get(
    "",
    response_model=EvaluationRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List past evaluation runs",
    description="Returns a paginated list of evaluation runs.",
)
async def list_evaluations_endpoint(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    dataset_name: Optional[str] = Query(default=None, description="Optional filter by dataset name"),
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunListResponse:
    """Retrieve paginated evaluation runs."""
    runs, total = await EvaluationService.list_evaluation_runs(
        session=session,
        page=page,
        page_size=page_size,
        dataset_name=dataset_name,
    )
    items = [_to_run_response(r) for r in runs]
    return EvaluationRunListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get evaluation run status and summary",
    description="Fetches an evaluation run by its unique identifier.",
)
async def get_evaluation_endpoint(
    evaluation_id: str,
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    """Fetch an evaluation run record."""
    run_uuid = _validate_uuid(evaluation_id, "evaluation_id")
    run = await EvaluationService.get_evaluation_run(session, run_uuid)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run with ID '{evaluation_id}' not found",
        )
    return _to_run_response(run)


@router.get(
    "/{evaluation_id}/results",
    response_model=CaseResultsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get per-case evaluation results",
    description="Returns individual case outcomes for a specific evaluation run.",
)
async def get_case_results_endpoint(
    evaluation_id: str,
    category: Optional[str] = Query(default=None, description="Filter by case category"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_db),
) -> CaseResultsListResponse:
    """Fetch individual case results for an evaluation run."""
    run_uuid = _validate_uuid(evaluation_id, "evaluation_id")
    run = await EvaluationService.get_evaluation_run(session, run_uuid)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run with ID '{evaluation_id}' not found",
        )

    records, total = await EvaluationService.get_case_results(
        session=session,
        run_id=run_uuid,
        category=category,
        page=page,
        page_size=page_size,
    )

    items: List[Dict[str, Any]] = [
        {
            "id": str(r.id),
            "case_id": r.case_id,
            "category": r.category,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "associated_workflow_run_id": r.associated_workflow_run_id,
            "metric_results": r.metric_results,
            "safe_error_summary": r.safe_error_summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]

    return CaseResultsListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{evaluation_id}/report",
    response_model=EvaluationRunReport,
    status_code=status.HTTP_200_OK,
    summary="Download full JSON evaluation report",
    description="Returns a full standalone machine-readable evaluation report with case results and metrics.",
)
async def get_report_endpoint(
    evaluation_id: str,
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunReport:
    """Generate and return complete EvaluationRunReport."""
    run_uuid = _validate_uuid(evaluation_id, "evaluation_id")
    report = await EvaluationService.get_evaluation_report(session, run_uuid)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run with ID '{evaluation_id}' not found",
        )
    return report


@router.post(
    "/compare",
    response_model=EvaluationComparisonReport,
    status_code=status.HTTP_200_OK,
    summary="Compare two evaluation runs",
    description="Computes per-metric deltas, regressions, and improvements between a baseline and target run.",
)
async def compare_evaluations_endpoint(
    request: EvaluationComparisonRequest,
    session: AsyncSession = Depends(get_db),
) -> EvaluationComparisonReport:
    """Compare baseline and comparison evaluation runs."""
    base_uuid = _validate_uuid(request.baseline_run_id, "baseline_run_id")
    comp_uuid = _validate_uuid(request.comparison_run_id, "comparison_run_id")

    comparison_report = await EvaluationService.compare_runs(
        session=session,
        baseline_run_id=base_uuid,
        comparison_run_id=comp_uuid,
    )
    if not comparison_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both evaluation runs were not found",
        )
    return comparison_report
