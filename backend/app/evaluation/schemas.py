"""Pydantic schemas and data contracts for the Evaluation Engine (Milestone 9A).

Defines:
- Benchmark categories and case structures
- Expected evidence and citation contracts
- Deterministic retrieval, citation, answer, and guardrail metric results
- Evaluation runner configuration and structured report schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class BenchmarkCategory(str, Enum):
    """Standardized benchmark question and evaluation categories."""

    ANSWERABLE = "answerable"                      # Category A: Direct fact retrieval & answerable
    MULTI_HOP = "multi_hop"                        # Category B: Requires reasoning across multiple chunks/sources
    UNANSWERABLE = "unanswerable"                  # Category C: Facts missing from corpus; expects abstention
    AMBIGUOUS = "ambiguous"                        # Category D: Underspecified or ambiguous query
    CITATION_SENSITIVE = "citation_sensitive"      # Category E: Strict citation integrity & provenance required
    UNSUPPORTED_PREMISE = "unsupported_premise"    # Category F: Misleading premise or false assumption
    RETRIEVAL_EDGE_CASE = "retrieval_edge_case"    # Category G: Typos, punctuation, empty query, extreme length


class EvaluationMode(str, Enum):
    """Operational mode for evaluation execution."""

    METRIC_ONLY = "metric_only"  # Offline, deterministic computation using fixture outputs
    INTEGRATION = "integration"  # Live integration calling existing retrieval and workflow agents


class ExpectedCitation(BaseModel):
    """Contract for expected citation provenance."""

    document_id: Optional[str] = Field(default=None, description="Expected source document UUID if stable")
    filename: Optional[str] = Field(default=None, description="Expected source filename (e.g., enterprise_arch.txt)")
    chunk_id: Optional[str] = Field(default=None, description="Expected source chunk UUID if stable")
    page_number: Optional[int] = Field(default=None, description="Expected page number")


class EvaluationCase(BaseModel):
    """Individual benchmark test case."""

    case_id: str = Field(..., min_length=1, description="Unique identifier for the benchmark case")
    dataset_version: str = Field(..., description="Dataset release version (e.g., '1.0.0')")
    category: BenchmarkCategory = Field(..., description="Benchmark classification category")
    question: str = Field(..., min_length=2, description="Natural language prompt or query")
    expected_answer_facts: List[str] = Field(default_factory=list, description="List of required atomic facts")
    relevant_document_ids: List[str] = Field(default_factory=list, description="IDs of ground-truth documents")
    relevant_chunk_ids: List[str] = Field(default_factory=list, description="IDs of ground-truth chunks")
    expected_citations: List[ExpectedCitation] = Field(default_factory=list, description="Expected citation metadata")
    answerable: bool = Field(default=True, description="Whether the question is answerable given the corpus")
    expected_validation_behavior: str = Field(
        default="PASS",
        description="Expected validation outcome: PASS, FAIL, RECOVERABLE, or BLOCKED",
    )
    evaluation_notes: Optional[str] = Field(default=None, description="Rationale or test case documentation")

    @field_validator("expected_validation_behavior")
    @classmethod
    def validate_expected_status(cls, v: str) -> str:
        valid_statuses = {"PASS", "FAIL", "RECOVERABLE", "BLOCKED"}
        upper_v = v.upper().strip()
        if upper_v not in valid_statuses:
            raise ValueError(f"Invalid expected_validation_behavior '{v}'. Must be one of {valid_statuses}")
        return upper_v


class EvaluationDataset(BaseModel):
    """Versioned collection of benchmark cases."""

    name: str = Field(..., description="Dataset name identifier")
    version: str = Field(..., description="Semantic version string")
    description: str = Field(default="", description="Description of the benchmark scope and corpus")
    cases: List[EvaluationCase] = Field(..., min_length=1, description="Non-empty list of benchmark cases")
    checksum: Optional[str] = Field(default=None, description="SHA256 checksum of raw dataset payload")


# -----------------------------------------------------------------------------
# Metric Computation Schemas
# -----------------------------------------------------------------------------

class RetrievalMetrics(BaseModel):
    """Deterministic retrieval metrics calculated for a single query."""

    recall_at_1: Optional[float] = Field(default=None, description="Recall@1 (None if no relevant items defined)")
    recall_at_3: Optional[float] = Field(default=None, description="Recall@3 (None if no relevant items defined)")
    recall_at_5: Optional[float] = Field(default=None, description="Recall@5 (None if no relevant items defined)")
    precision_at_1: float = Field(default=0.0, description="Precision@1")
    precision_at_3: float = Field(default=0.0, description="Precision@3")
    precision_at_5: float = Field(default=0.0, description="Precision@5")
    hit_rate_at_1: float = Field(default=0.0, description="Hit Rate@1: 1.0 if any relevant in top 1 else 0.0")
    hit_rate_at_3: float = Field(default=0.0, description="Hit Rate@3: 1.0 if any relevant in top 3 else 0.0")
    hit_rate_at_5: float = Field(default=0.0, description="Hit Rate@5: 1.0 if any relevant in top 5 else 0.0")
    mrr: float = Field(default=0.0, description="Mean Reciprocal Rank (1/rank of first relevant item)")
    map_score: float = Field(default=0.0, description="Mean Average Precision score")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Retrieval latency in milliseconds")
    retrieved_count: int = Field(default=0, ge=0, description="Total chunks returned by retriever")
    relevant_count: int = Field(default=0, ge=0, description="Ground truth relevant items count")


class CitationMetrics(BaseModel):
    """Deterministic citation-integrity metrics."""

    citation_presence: float = Field(
        default=1.0,
        description="1.0 if citations are provided when required (or absent when unanswerable), else 0.0",
    )
    identifier_validity: float = Field(
        default=1.0,
        description="Fraction of citations containing non-empty valid document/chunk IDs (1.0 if none required)",
    )
    source_reference_validity: float = Field(
        default=1.0,
        description="Fraction of cited document IDs that match actual retrieved documents (1.0 if none required)",
    )
    page_reference_validity: float = Field(
        default=1.0,
        description="Fraction of citations where cited page matches retrieved page metadata (1.0 if page NA)",
    )
    attribution_match: float = Field(
        default=1.0,
        description="Fraction of citations matching expected ground-truth evidence (1.0 if none expected)",
    )
    duplicate_citations_count: int = Field(default=0, ge=0, description="Count of duplicate citation references")
    malformed_citations_count: int = Field(default=0, ge=0, description="Count of malformed citation dictionaries")
    total_citations: int = Field(default=0, ge=0, description="Total citations present in answer")


class AnswerMetrics(BaseModel):
    """Deterministic reference-based answer quality metrics."""

    fact_coverage: float = Field(
        default=1.0,
        description="Fraction of expected facts matched in the response (0.0 to 1.0)",
    )
    missing_facts: List[str] = Field(default_factory=list, description="List of expected facts not detected")
    matched_facts: List[str] = Field(default_factory=list, description="List of expected facts detected")
    correct_abstention: Optional[bool] = Field(
        default=None,
        description="True if unanswerable question correctly abstained; False if hallucinated; None if answerable",
    )
    completeness_score: float = Field(
        default=1.0,
        description="Heuristic measure of response substance and structured completeness",
    )
    deterministic_grade_note: Optional[str] = Field(
        default=None,
        description="Documentation of deterministic evaluation limitations for this answer",
    )


class GuardrailMetrics(BaseModel):
    """Evaluation of system guardrail and validation behavior."""

    actual_status: str = Field(..., description="Observed ValidationStatus (PASS, FAIL, RECOVERABLE, BLOCKED)")
    expected_status: str = Field(..., description="Expected validation outcome from benchmark label")
    status_match: bool = Field(..., description="Whether observed status matches expected benchmark label")
    validation_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Calculated guardrail score")
    issues_detected_count: int = Field(default=0, ge=0, description="Number of issues identified by validators")
    recovery_attempted: bool = Field(default=False, description="Whether correction loop was triggered")


class CaseEvaluationResult(BaseModel):
    """Outcome for a single evaluated benchmark case."""

    case_id: str = Field(..., description="Benchmark case ID")
    category: BenchmarkCategory = Field(..., description="Benchmark case category")
    status: str = Field(default="COMPLETED", description="Case status: COMPLETED, FAILED, or SKIPPED")
    retrieval: Optional[RetrievalMetrics] = Field(default=None, description="Retrieval metrics if evaluated")
    citation: Optional[CitationMetrics] = Field(default=None, description="Citation integrity metrics")
    answer: Optional[AnswerMetrics] = Field(default=None, description="Answer evaluation metrics")
    guardrail: Optional[GuardrailMetrics] = Field(default=None, description="Guardrail evaluation metrics")
    associated_workflow_run_id: Optional[str] = Field(default=None, description="Correlated workflow run UUID")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Total execution duration for this case")
    error: Optional[str] = Field(default=None, description="Failure details if case execution encountered error")


class EvaluationSummaryMetrics(BaseModel):
    """Aggregated metrics across all evaluated benchmark cases."""

    # Retrieval aggregates
    mean_recall_at_1: Optional[float] = None
    mean_recall_at_3: Optional[float] = None
    mean_recall_at_5: Optional[float] = None
    mean_precision_at_1: float = 0.0
    mean_precision_at_3: float = 0.0
    mean_precision_at_5: float = 0.0
    mean_hit_rate_at_1: float = 0.0
    mean_hit_rate_at_3: float = 0.0
    mean_hit_rate_at_5: float = 0.0
    mrr: float = 0.0
    map_score: float = 0.0
    avg_retrieval_latency_ms: float = 0.0

    # Citation aggregates
    citation_presence_rate: float = 0.0
    identifier_validity_rate: float = 0.0
    source_validity_rate: float = 0.0
    page_validity_rate: float = 0.0
    attribution_match_rate: float = 0.0

    # Answer aggregates
    mean_fact_coverage: float = 0.0
    abstention_accuracy: Optional[float] = None  # None if no unanswerable cases tested

    # Guardrail aggregates
    guardrail_accuracy: float = 0.0
    true_positive_rate: Optional[float] = None   # Correctly flagged violations
    false_positive_rate: Optional[float] = None  # Wrongly flagged valid outputs
    false_negative_rate: Optional[float] = None  # Missed violations

    # Overall stats
    total_cases: int = 0
    completed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    avg_duration_ms: float = 0.0


class EvaluationRunReport(BaseModel):
    """Machine-readable, standalone JSON evaluation report."""

    report_version: str = Field(default="1.0.0", description="Report format schema version")
    evaluation_run_id: str = Field(..., description="Unique evaluation run ID")
    dataset_name: str = Field(..., description="Dataset identifier")
    dataset_version: str = Field(..., description="Dataset version string")
    dataset_checksum: Optional[str] = Field(default=None, description="SHA256 hash of dataset")
    application_version: str = Field(default="0.1.0", description="Backend application version")
    mode: EvaluationMode = Field(..., description="Evaluation mode (metric_only or integration)")
    configuration_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Runtime settings snapshot")
    summary: EvaluationSummaryMetrics = Field(..., description="Aggregated metric summary")
    category_breakdown: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-category aggregated metrics",
    )
    case_results: List[CaseEvaluationResult] = Field(default_factory=list, description="Per-case evaluation details")
    failures: List[Dict[str, Any]] = Field(default_factory=list, description="Isolated execution failure details")
    known_limitations: List[str] = Field(default_factory=list, description="Documented grading limitations")


# -----------------------------------------------------------------------------
# REST API Schemas
# -----------------------------------------------------------------------------

class StartEvaluationRequest(BaseModel):
    """Payload to trigger a new evaluation benchmark run."""

    dataset_name: str = Field(default="benchmark_v1", description="Dataset identifier or filename")
    mode: EvaluationMode = Field(default=EvaluationMode.METRIC_ONLY, description="Execution mode: metric_only or integration")
    max_concurrency: int = Field(default=4, ge=1, le=16, description="Concurrency limit")
    timeout_per_case_seconds: float = Field(default=30.0, ge=1.0, le=120.0, description="Per-case timeout")


class EvaluationRunResponse(BaseModel):
    """Summary of an evaluation run returned by the API."""

    id: str
    dataset_name: str
    dataset_version: str
    dataset_checksum: Optional[str] = None
    mode: str
    application_version: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    configuration_snapshot: Dict[str, Any] = Field(default_factory=dict)
    aggregate_metrics: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: Optional[datetime] = None


class EvaluationRunListResponse(BaseModel):
    """Paginated list of evaluation runs."""

    items: List[EvaluationRunResponse]
    total: int
    page: int = 1
    page_size: int = 20


class MetricDelta(BaseModel):
    """Delta calculation for a single metric between two runs."""

    baseline: Optional[float] = None
    comparison: Optional[float] = None
    delta: Optional[float] = None
    status: str = Field(default="UNCHANGED", description="IMPROVED, REGRESSED, UNCHANGED, or NA")


class EvaluationComparisonRequest(BaseModel):
    """Request to compare two evaluation runs."""

    baseline_run_id: str = Field(..., description="UUID of baseline evaluation run")
    comparison_run_id: str = Field(..., description="UUID of comparison evaluation run")


class EvaluationComparisonReport(BaseModel):
    """Comparison report highlighting deltas, improvements, and regressions."""

    baseline_run_id: str
    comparison_run_id: str
    baseline_mode: str
    comparison_mode: str
    metric_deltas: Dict[str, MetricDelta]
    regressions: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    summary_verdict: str = Field(default="NEUTRAL")


class DatasetMetadataResponse(BaseModel):
    """Summary metadata for an available benchmark dataset."""

    name: str
    version: str
    description: str
    case_count: int
    categories: List[str]
    checksum: Optional[str] = None


class CaseResultsListResponse(BaseModel):
    """Paginated list of individual benchmark case outcomes."""

    items: List[Dict[str, Any]]
    total: int
    page: int = 1
    page_size: int = 50
