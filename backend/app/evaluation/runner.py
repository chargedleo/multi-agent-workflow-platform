"""Controlled benchmark evaluation runner (Milestone 9A).

Supports:
- METRIC_ONLY mode (offline, fast, deterministic testing using known fixtures)
- INTEGRATION mode (calls real RetrievalService and workflow pipeline)
- Concurrency limiting via asyncio.Semaphore
- Per-case timeout isolation and failure preservation
- Detailed aggregation and category breakdown reporting
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Set

from backend.app.core.config import get_settings
from backend.app.core.logging import format_log_msg, get_logger
from backend.app.evaluation.answer_metrics import compute_answer_metrics
from backend.app.evaluation.citation_metrics import compute_citation_metrics
from backend.app.evaluation.guardrail_metrics import (
    compute_aggregate_guardrail_metrics,
    evaluate_state_guardrails,
)
from backend.app.evaluation.retrieval_adapter import execute_evaluation_retrieval
from backend.app.evaluation.retrieval_metrics import compute_retrieval_metrics
from backend.app.evaluation.schemas import (
    BenchmarkCategory,
    CaseEvaluationResult,
    EvaluationCase,
    EvaluationDataset,
    EvaluationMode,
    EvaluationRunReport,
    EvaluationSummaryMetrics,
    GuardrailMetrics,
)

logger = get_logger(__name__)


class EvaluationRunner:
    """Orchestrates controlled execution of benchmark evaluation cases."""

    def __init__(
        self,
        concurrency_limit: int = 4,
        case_timeout_seconds: float = 30.0,
    ) -> None:
        self.concurrency_limit = max(1, min(16, concurrency_limit))
        self.case_timeout_seconds = max(1.0, min(120.0, case_timeout_seconds))

    async def run(
        self,
        dataset: EvaluationDataset,
        mode: EvaluationMode = EvaluationMode.METRIC_ONLY,
        case_ids: Optional[List[str]] = None,
        max_cases: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> EvaluationRunReport:
        """Execute selected benchmark cases and compile full report."""
        eval_run_id = run_id or str(uuid.uuid4())
        start_wall_time = time.perf_counter()

        # 1. Filter and validate target benchmark cases
        all_cases_map: Dict[str, EvaluationCase] = {c.case_id: c for c in dataset.cases}
        target_cases: List[EvaluationCase] = []

        if case_ids:
            for cid in case_ids:
                if cid not in all_cases_map:
                    raise ValueError(f"Requested case_id '{cid}' not found in dataset '{dataset.name}'.")
                target_cases.append(all_cases_map[cid])
        else:
            target_cases = list(dataset.cases)

        if max_cases and max_cases > 0:
            target_cases = target_cases[:max_cases]

        logger.info(
            format_log_msg(
                f"Starting evaluation run '{eval_run_id}' ({mode.value}) for {len(target_cases)} cases "
                f"from '{dataset.name}' v{dataset.version}...",
                request_id=eval_run_id,
            )
        )

        semaphore = asyncio.Semaphore(self.concurrency_limit)

        async def evaluate_single_case(case: EvaluationCase) -> CaseEvaluationResult:
            async with semaphore:
                case_start = time.perf_counter()
                try:
                    return await asyncio.wait_for(
                        self._execute_case(case=case, mode=mode, eval_run_id=eval_run_id),
                        timeout=self.case_timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    duration_ms = (time.perf_counter() - case_start) * 1000.0
                    timeout_msg = f"Case execution timed out after {self.case_timeout_seconds}s"
                    logger.warning(format_log_msg(f"Case '{case.case_id}' timed out.", eval_run_id))
                    return CaseEvaluationResult(
                        case_id=case.case_id,
                        category=case.category,
                        status="FAILED",
                        duration_ms=round(duration_ms, 2),
                        error=timeout_msg,
                    )
                except Exception as exc:
                    duration_ms = (time.perf_counter() - case_start) * 1000.0
                    err_msg = f"Unhandled error: {str(exc)}"
                    logger.error(
                        format_log_msg(f"Case '{case.case_id}' failed: {exc}", eval_run_id),
                        exc_info=True,
                    )
                    return CaseEvaluationResult(
                        case_id=case.case_id,
                        category=case.category,
                        status="FAILED",
                        duration_ms=round(duration_ms, 2),
                        error=err_msg,
                    )

        # 2. Execute cases concurrently with bounded semaphore
        case_results = await asyncio.gather(*(evaluate_single_case(c) for c in target_cases))

        # 3. Aggregate summary metrics and breakdown
        total_duration_ms = (time.perf_counter() - start_wall_time) * 1000.0
        summary, category_breakdown, failures = self._aggregate_results(case_results)
        summary.avg_duration_ms = round(total_duration_ms / max(1, len(case_results)), 2)

        settings = get_settings()
        config_snapshot = {
            "mode": mode.value,
            "concurrency_limit": self.concurrency_limit,
            "case_timeout_seconds": self.case_timeout_seconds,
            "llm_provider": settings.LLM_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "validation_enabled": settings.VALIDATION_ENABLED,
        }

        report = EvaluationRunReport(
            evaluation_run_id=eval_run_id,
            dataset_name=dataset.name,
            dataset_version=dataset.version,
            dataset_checksum=dataset.checksum,
            application_version="0.1.0",
            mode=mode,
            configuration_snapshot=config_snapshot,
            summary=summary,
            category_breakdown=category_breakdown,
            case_results=case_results,
            failures=failures,
            known_limitations=[
                "Answer evaluation uses deterministic n-gram and regex term matching; semantic nuance requires M9B.",
                "Retrieval scores reflect the active FAISS index and embedding provider (mock vs native).",
                "Guardrail evaluations assume configured validation rules in ValidationService.",
            ],
        )

        logger.info(
            format_log_msg(
                f"Evaluation run '{eval_run_id}' complete in {round(total_duration_ms, 2)}ms. "
                f"Completed: {summary.completed_cases}/{summary.total_cases}, Failed: {summary.failed_cases}",
                request_id=eval_run_id,
            )
        )
        return report

    async def _execute_case(
        self,
        case: EvaluationCase,
        mode: EvaluationMode,
        eval_run_id: str,
    ) -> CaseEvaluationResult:
        """Execute evaluation logic for an individual benchmark case."""
        case_start = time.perf_counter()

        if mode == EvaluationMode.METRIC_ONLY:
            # 1. Deterministic synthetic fixture generation based on case ground truth
            retrieved_items: List[Dict[str, Any]] = []
            for cid in case.relevant_chunk_ids:
                retrieved_items.append(
                    {
                        "chunk_id": cid,
                        "document_id": case.relevant_document_ids[0] if case.relevant_document_ids else "doc-1",
                        "filename": (
                            case.expected_citations[0].filename if case.expected_citations else "enterprise_arch.txt"
                        ),
                        "page_number": 1,
                        "similarity_score": 0.95,
                    }
                )

            # Compute retrieval metrics
            ret_metrics = compute_retrieval_metrics(
                retrieved_items=retrieved_items,
                relevant_chunk_ids=case.relevant_chunk_ids,
                relevant_document_ids=case.relevant_document_ids,
                latency_ms=2.5,
            )

            # Answer and Citation evaluation
            if case.answerable:
                # Synthetic answer incorporating expected facts
                joined_facts = ". ".join(case.expected_answer_facts) if case.expected_answer_facts else "Answer text."
                answer_text = f"According to the documentation: {joined_facts}."
                citations = [
                    {
                        "document_id": case.relevant_document_ids[0] if case.relevant_document_ids else "doc-1",
                        "filename": (
                            case.expected_citations[0].filename if case.expected_citations else "enterprise_arch.txt"
                        ),
                        "chunk_id": case.relevant_chunk_ids[0] if case.relevant_chunk_ids else "chunk-1",
                        "page_number": 1,
                    }
                ] if case.expected_citations else []
            else:
                answer_text = "This information is not mentioned in the documentation or specification."
                citations = []

            cit_metrics = compute_citation_metrics(
                citations=citations,
                retrieved_documents=retrieved_items,
                expected_citations=case.expected_citations,
                answerable=case.answerable,
            )

            ans_metrics = compute_answer_metrics(
                answer=answer_text,
                expected_facts=case.expected_answer_facts,
                answerable=case.answerable,
                key_points=["Executive key point."],
            )

            # Guardrail evaluation
            guardrail_state = {
                "user_query": case.question,
                "final_answer": {
                    "request_id": f"req-{case.case_id}",
                    "answer": answer_text,
                    "key_points": ["Verified key point."],
                    "confidence": 0.95,
                    "sources": citations,
                },
                "retrieved_documents": retrieved_items,
            }
            guard_metrics, _ = evaluate_state_guardrails(
                state=guardrail_state,
                expected_status=case.expected_validation_behavior,
            )

            duration_ms = (time.perf_counter() - case_start) * 1000.0
            return CaseEvaluationResult(
                case_id=case.case_id,
                category=case.category,
                status="COMPLETED",
                retrieval=ret_metrics,
                citation=cit_metrics,
                answer=ans_metrics,
                guardrail=guard_metrics,
                duration_ms=round(duration_ms, 2),
            )

        else:
            # 2. INTEGRATION mode: Invoke real RetrievalService and workflow agent pipeline
            norm_retrieved, latency_ms = execute_evaluation_retrieval(query=case.question, top_k=5)

            ret_metrics = compute_retrieval_metrics(
                retrieved_items=norm_retrieved,
                relevant_chunk_ids=case.relevant_chunk_ids,
                relevant_document_ids=case.relevant_document_ids,
                latency_ms=latency_ms,
            )

            from backend.app.graph.workflow import run_workflow

            wf_state = await run_workflow(query=case.question)
            wf_run_id = wf_state.get("run_id")
            final_ans = wf_state.get("final_answer") or {}
            answer_text = final_ans.get("answer") or ""
            citations = final_ans.get("sources") or []
            key_points = final_ans.get("key_points") or []

            cit_metrics = compute_citation_metrics(
                citations=citations,
                retrieved_documents=norm_retrieved,
                expected_citations=case.expected_citations,
                answerable=case.answerable,
            )

            ans_metrics = compute_answer_metrics(
                answer=answer_text,
                expected_facts=case.expected_answer_facts,
                answerable=case.answerable,
                key_points=key_points,
            )

            guard_metrics, _ = evaluate_state_guardrails(
                state=wf_state,
                expected_status=case.expected_validation_behavior,
            )

            duration_ms = (time.perf_counter() - case_start) * 1000.0
            return CaseEvaluationResult(
                case_id=case.case_id,
                category=case.category,
                status="COMPLETED",
                retrieval=ret_metrics,
                citation=cit_metrics,
                answer=ans_metrics,
                guardrail=guard_metrics,
                associated_workflow_run_id=wf_run_id,
                duration_ms=round(duration_ms, 2),
            )

    def _aggregate_results(
        self,
        results: List[CaseEvaluationResult],
    ) -> (EvaluationSummaryMetrics, Dict[str, Dict[str, Any]], List[Dict[str, Any]]):
        """Compute macro-averages and category aggregations across completed cases."""
        total = len(results)
        completed = sum(1 for r in results if r.status == "COMPLETED")
        failed = sum(1 for r in results if r.status == "FAILED")
        skipped = sum(1 for r in results if r.status == "SKIPPED")

        failures: List[Dict[str, Any]] = [
            {"case_id": r.case_id, "category": r.category.value, "error": r.error}
            for r in results
            if r.status == "FAILED"
        ]

        # Valid cases for metric aggregation
        valid_cases = [r for r in results if r.status == "COMPLETED"]

        if not valid_cases:
            return (
                EvaluationSummaryMetrics(
                    total_cases=total,
                    completed_cases=completed,
                    failed_cases=failed,
                    skipped_cases=skipped,
                ),
                {},
                failures,
            )

        # Retrieval aggregates
        rec1_vals = [r.retrieval.recall_at_1 for r in valid_cases if r.retrieval and r.retrieval.recall_at_1 is not None]
        rec3_vals = [r.retrieval.recall_at_3 for r in valid_cases if r.retrieval and r.retrieval.recall_at_3 is not None]
        rec5_vals = [r.retrieval.recall_at_5 for r in valid_cases if r.retrieval and r.retrieval.recall_at_5 is not None]

        mean_rec1 = round(sum(rec1_vals) / len(rec1_vals), 4) if rec1_vals else None
        mean_rec3 = round(sum(rec3_vals) / len(rec3_vals), 4) if rec3_vals else None
        mean_rec5 = round(sum(rec5_vals) / len(rec5_vals), 4) if rec5_vals else None

        mean_p1 = round(sum(r.retrieval.precision_at_1 for r in valid_cases if r.retrieval) / len(valid_cases), 4)
        mean_p3 = round(sum(r.retrieval.precision_at_3 for r in valid_cases if r.retrieval) / len(valid_cases), 4)
        mean_p5 = round(sum(r.retrieval.precision_at_5 for r in valid_cases if r.retrieval) / len(valid_cases), 4)

        mean_hr1 = round(sum(r.retrieval.hit_rate_at_1 for r in valid_cases if r.retrieval) / len(valid_cases), 4)
        mean_hr3 = round(sum(r.retrieval.hit_rate_at_3 for r in valid_cases if r.retrieval) / len(valid_cases), 4)
        mean_hr5 = round(sum(r.retrieval.hit_rate_at_5 for r in valid_cases if r.retrieval) / len(valid_cases), 4)

        mean_mrr = round(sum(r.retrieval.mrr for r in valid_cases if r.retrieval) / len(valid_cases), 4)
        mean_map = round(sum(r.retrieval.map_score for r in valid_cases if r.retrieval) / len(valid_cases), 4)
        avg_ret_lat = round(sum(r.retrieval.latency_ms for r in valid_cases if r.retrieval) / len(valid_cases), 2)

        # Citation aggregates
        cit_presence = round(sum(r.citation.citation_presence for r in valid_cases if r.citation) / len(valid_cases), 4)
        id_validity = round(sum(r.citation.identifier_validity for r in valid_cases if r.citation) / len(valid_cases), 4)
        src_validity = round(sum(r.citation.source_reference_validity for r in valid_cases if r.citation) / len(valid_cases), 4)
        page_validity = round(sum(r.citation.page_reference_validity for r in valid_cases if r.citation) / len(valid_cases), 4)
        attrib_match = round(sum(r.citation.attribution_match for r in valid_cases if r.citation) / len(valid_cases), 4)

        # Answer aggregates
        mean_fact_cov = round(sum(r.answer.fact_coverage for r in valid_cases if r.answer) / len(valid_cases), 4)
        abst_cases = [r.answer.correct_abstention for r in valid_cases if r.answer and r.answer.correct_abstention is not None]
        abst_acc = round(sum(1 for a in abst_cases if a is True) / len(abst_cases), 4) if abst_cases else None

        # Guardrail aggregates
        guard_cases = [r.guardrail for r in valid_cases if r.guardrail]
        guard_agg = compute_aggregate_guardrail_metrics(guard_cases)

        summary = EvaluationSummaryMetrics(
            mean_recall_at_1=mean_rec1,
            mean_recall_at_3=mean_rec3,
            mean_recall_at_5=mean_rec5,
            mean_precision_at_1=mean_p1,
            mean_precision_at_3=mean_p3,
            mean_precision_at_5=mean_p5,
            mean_hit_rate_at_1=mean_hr1,
            mean_hit_rate_at_3=mean_hr3,
            mean_hit_rate_at_5=mean_hr5,
            mrr=mean_mrr,
            map_score=mean_map,
            avg_retrieval_latency_ms=avg_ret_lat,
            citation_presence_rate=cit_presence,
            identifier_validity_rate=id_validity,
            source_validity_rate=src_validity,
            page_validity_rate=page_validity,
            attribution_match_rate=attrib_match,
            mean_fact_coverage=mean_fact_cov,
            abstention_accuracy=abst_acc,
            guardrail_accuracy=guard_agg.get("guardrail_accuracy", 0.0),
            true_positive_rate=guard_agg.get("true_positive_rate"),
            false_positive_rate=guard_agg.get("false_positive_rate"),
            false_negative_rate=guard_agg.get("false_negative_rate"),
            total_cases=total,
            completed_cases=completed,
            failed_cases=failed,
            skipped_cases=skipped,
        )

        # Category Breakdown
        category_breakdown: Dict[str, Dict[str, Any]] = {}
        for cat in BenchmarkCategory:
            cat_cases = [r for r in valid_cases if r.category == cat]
            if not cat_cases:
                continue

            c_rec3 = [r.retrieval.recall_at_3 for r in cat_cases if r.retrieval and r.retrieval.recall_at_3 is not None]
            c_p3 = [r.retrieval.precision_at_3 for r in cat_cases if r.retrieval]
            c_mrr = [r.retrieval.mrr for r in cat_cases if r.retrieval]
            c_fact = [r.answer.fact_coverage for r in cat_cases if r.answer]
            c_guard = [1.0 if (r.guardrail and r.guardrail.status_match) else 0.0 for r in cat_cases]

            category_breakdown[cat.value] = {
                "case_count": len(cat_cases),
                "mean_recall_at_3": round(sum(c_rec3) / len(c_rec3), 4) if c_rec3 else None,
                "mean_precision_at_3": round(sum(c_p3) / len(c_p3), 4) if c_p3 else 0.0,
                "mean_mrr": round(sum(c_mrr) / len(c_mrr), 4) if c_mrr else 0.0,
                "mean_fact_coverage": round(sum(c_fact) / len(c_fact), 4) if c_fact else 0.0,
                "guardrail_match_rate": round(sum(c_guard) / len(c_guard), 4) if c_guard else 0.0,
            }

        return summary, category_breakdown, failures
