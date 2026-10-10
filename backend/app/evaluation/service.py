"""Evaluation service orchestrating benchmark runs and persistence (Milestone 9A).

Responsible for:
- Creating, updating, and querying EvaluationRun and EvaluationCaseResultRecord in PostgreSQL
- Executing benchmarks in background or synchronously via EvaluationRunner
- Generating full machine-readable evaluation reports
- Comparing runs using report comparison engine
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import get_logger
from backend.app.db.models.evaluation import EvaluationCaseResultRecord, EvaluationRun
from backend.app.db.session import get_db_context
from backend.app.evaluation.dataset import list_available_datasets, load_dataset
from backend.app.evaluation.report import compare_evaluation_runs
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.evaluation.schemas import (
    BenchmarkCategory,
    CaseEvaluationResult,
    DatasetMetadataResponse,
    EvaluationComparisonReport,
    EvaluationMode,
    EvaluationRunReport,
    EvaluationRunResponse,
    EvaluationSummaryMetrics,
    StartEvaluationRequest,
)

logger = get_logger(__name__)


class EvaluationService:
    """Service layer for evaluation benchmarking and persistence."""

    @staticmethod
    async def create_evaluation_run(
        session: AsyncSession,
        dataset_name: str,
        mode: EvaluationMode,
        max_concurrency: int = 4,
        timeout_per_case_seconds: float = 30.0,
    ) -> EvaluationRun:
        """Initialize an evaluation run record in the database."""
        # Load dataset metadata to capture version and checksum
        dataset = load_dataset(name=dataset_name)

        run_record = EvaluationRun(
            id=uuid.uuid4(),
            dataset_name=dataset.name,
            dataset_version=dataset.version,
            dataset_checksum=dataset.checksum,
            mode=mode.value if isinstance(mode, EvaluationMode) else str(mode),
            status="PENDING",
            configuration_snapshot={
                "max_concurrency": max_concurrency,
                "timeout_per_case_seconds": timeout_per_case_seconds,
                "dataset_name": dataset.name,
                "dataset_version": dataset.version,
                "mode": mode.value if isinstance(mode, EvaluationMode) else str(mode),
            },
        )
        session.add(run_record)
        await session.commit()
        await session.refresh(run_record)
        return run_record

    @staticmethod
    async def get_evaluation_run(
        session: AsyncSession,
        run_id: str | uuid.UUID,
    ) -> Optional[EvaluationRun]:
        """Fetch an EvaluationRun by ID."""
        run_uuid = uuid.UUID(str(run_id))
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.id == run_uuid)
            .options(selectinload(EvaluationRun.case_results))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_evaluation_runs(
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        dataset_name: Optional[str] = None,
    ) -> Tuple[List[EvaluationRun], int]:
        """Fetch a paginated list of evaluation runs and total count."""
        stmt = select(EvaluationRun)
        count_stmt = select(func.count(EvaluationRun.id))

        if dataset_name:
            stmt = stmt.where(EvaluationRun.dataset_name == dataset_name)
            count_stmt = count_stmt.where(EvaluationRun.dataset_name == dataset_name)

        stmt = stmt.order_by(desc(EvaluationRun.created_at)).offset((page - 1) * page_size).limit(page_size)

        total_res = await session.execute(count_stmt)
        total = total_res.scalar_one()

        result = await session.execute(stmt)
        runs = list(result.scalars().all())
        return runs, total

    @staticmethod
    async def get_case_results(
        session: AsyncSession,
        run_id: str | uuid.UUID,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[EvaluationCaseResultRecord], int]:
        """Fetch paginated case results for a specific evaluation run."""
        run_uuid = uuid.UUID(str(run_id))
        stmt = select(EvaluationCaseResultRecord).where(EvaluationCaseResultRecord.evaluation_run_id == run_uuid)
        count_stmt = select(func.count(EvaluationCaseResultRecord.id)).where(
            EvaluationCaseResultRecord.evaluation_run_id == run_uuid
        )

        if category:
            stmt = stmt.where(EvaluationCaseResultRecord.category == category)
            count_stmt = count_stmt.where(EvaluationCaseResultRecord.category == category)

        stmt = stmt.order_by(EvaluationCaseResultRecord.created_at).offset((page - 1) * page_size).limit(page_size)

        total_res = await session.execute(count_stmt)
        total = total_res.scalar_one()

        result = await session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def execute_run_task(
        run_id: str | uuid.UUID,
        request: StartEvaluationRequest,
    ) -> None:
        """Background worker that executes the benchmark and persists outcomes."""
        run_uuid = uuid.UUID(str(run_id))
        start_time = time.perf_counter()

        async with get_db_context() as session:
            run_record = await session.get(EvaluationRun, run_uuid)
            if not run_record:
                logger.error(f"Cannot execute background evaluation task: run {run_uuid} not found")
                return

            run_record.status = "RUNNING"
            run_record.started_at = datetime.now(timezone.utc)
            await session.commit()

        try:
            # 1. Load dataset
            dataset = load_dataset(name=request.dataset_name)

            # 2. Run benchmark
            runner = EvaluationRunner(
                concurrency_limit=request.max_concurrency,
                case_timeout_seconds=request.timeout_per_case_seconds,
            )
            report: EvaluationRunReport = await runner.run(
                dataset=dataset,
                mode=request.mode,
                run_id=str(run_uuid),
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            # 3. Persist results and complete
            async with get_db_context() as session:
                target_run = await session.get(EvaluationRun, run_uuid)
                if target_run:
                    target_run.status = "COMPLETED"
                    target_run.completed_at = datetime.now(timezone.utc)
                    target_run.duration_ms = duration_ms
                    target_run.aggregate_metrics = report.summary.model_dump()
                    target_run.summary = report.summary.model_dump()
                    target_run.configuration_snapshot = report.configuration_snapshot

                    # Persist individual case result entities
                    for case_res in report.case_results:
                        metric_data = {
                            "retrieval": case_res.retrieval.model_dump() if case_res.retrieval else None,
                            "citation": case_res.citation.model_dump() if case_res.citation else None,
                            "answer": case_res.answer.model_dump() if case_res.answer else None,
                            "guardrail": case_res.guardrail.model_dump() if case_res.guardrail else None,
                        }
                        case_record = EvaluationCaseResultRecord(
                            id=uuid.uuid4(),
                            evaluation_run_id=run_uuid,
                            case_id=case_res.case_id,
                            category=case_res.category.value if hasattr(case_res.category, "value") else str(case_res.category),
                            associated_workflow_run_id=case_res.associated_workflow_run_id,
                            status=case_res.status,
                            duration_ms=case_res.duration_ms,
                            metric_results=metric_data,
                            safe_error_summary=case_res.error,
                        )
                        session.add(case_record)

                    await session.commit()
                    logger.info(f"Evaluation run {run_uuid} completed successfully in {duration_ms:.1f}ms")

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Evaluation run {run_uuid} failed: {exc}", exc_info=True)
            async with get_db_context() as session:
                target_run = await session.get(EvaluationRun, run_uuid)
                if target_run:
                    target_run.status = "FAILED"
                    target_run.completed_at = datetime.now(timezone.utc)
                    target_run.duration_ms = duration_ms
                    target_run.error = str(exc)
                    await session.commit()

    @staticmethod
    async def get_evaluation_report(
        session: AsyncSession,
        run_id: str | uuid.UUID,
    ) -> Optional[EvaluationRunReport]:
        """Construct full EvaluationRunReport from persisted database entities."""
        run = await EvaluationService.get_evaluation_run(session, run_id)
        if not run:
            return None

        # Reconstruct case results
        case_results: List[CaseEvaluationResult] = []
        for c in run.case_results:
            metric_data = c.metric_results or {}
            case_results.append(
                CaseEvaluationResult(
                    case_id=c.case_id,
                    category=c.category,
                    status=c.status,
                    retrieval=metric_data.get("retrieval"),
                    citation=metric_data.get("citation"),
                    answer=metric_data.get("answer"),
                    guardrail=metric_data.get("guardrail"),
                    associated_workflow_run_id=c.associated_workflow_run_id,
                    duration_ms=c.duration_ms,
                    error=c.safe_error_summary,
                )
            )

        summary_data = run.summary or run.aggregate_metrics or {}
        summary_model = EvaluationSummaryMetrics.model_validate(summary_data) if summary_data else EvaluationSummaryMetrics()

        return EvaluationRunReport(
            report_version="1.0.0",
            evaluation_run_id=str(run.id),
            dataset_name=run.dataset_name,
            dataset_version=run.dataset_version,
            dataset_checksum=run.dataset_checksum,
            application_version=run.application_version,
            mode=EvaluationMode(run.mode) if run.mode in [m.value for m in EvaluationMode] else EvaluationMode.METRIC_ONLY,
            configuration_snapshot=run.configuration_snapshot or {},
            summary=summary_model,
            category_breakdown=run.configuration_snapshot.get("category_breakdown", {}),
            case_results=case_results,
            failures=[],
            known_limitations=[
                "Deterministic evaluation uses normalized term matching and heuristic fact coverage",
                "Integration mode relies on existing FAISS index state and mock/local LLM configuration",
                "Advanced model-assisted grading is reserved for Milestone 9B",
            ],
        )

    @staticmethod
    async def compare_runs(
        session: AsyncSession,
        baseline_run_id: str | uuid.UUID,
        comparison_run_id: str | uuid.UUID,
    ) -> Optional[EvaluationComparisonReport]:
        """Compare two evaluation runs and return the comparison report."""
        baseline = await EvaluationService.get_evaluation_run(session, baseline_run_id)
        comparison = await EvaluationService.get_evaluation_run(session, comparison_run_id)

        if not baseline or not comparison:
            return None

        baseline_dict = {
            "id": str(baseline.id),
            "mode": baseline.mode,
            "summary": baseline.summary or baseline.aggregate_metrics or {},
        }
        comparison_dict = {
            "id": str(comparison.id),
            "mode": comparison.mode,
            "summary": comparison.summary or comparison.aggregate_metrics or {},
        }

        return compare_evaluation_runs(baseline_dict, comparison_dict)

    @staticmethod
    def get_available_datasets_metadata() -> List[DatasetMetadataResponse]:
        """Return metadata list of available benchmark datasets."""
        raw_items = list_available_datasets()
        results: List[DatasetMetadataResponse] = []
        for item in raw_items:
            results.append(
                DatasetMetadataResponse(
                    name=item["name"],
                    version=item["version"],
                    description=item.get("description", ""),
                    case_count=item.get("case_count", 0),
                    categories=[c.value for c in BenchmarkCategory],
                    checksum=item.get("checksum"),
                )
            )
        return results
