# Evaluation Engine & Deterministic Benchmarking (Milestone 9A)

## 1. Overview & Objectives

Milestone 9A introduces a reproducible, offline-capable **Evaluation Engine and Deterministic Benchmarking Harness** for the Multi-Agent AI Workflow Automation Platform.

The evaluation engine is designed to:
1. Provide a rigorous, repeatable ground-truth benchmark across retrieval, citation integrity, reference-based fact matching, and guardrail decisions.
2. Run fully deterministically in CI and local test suites without requiring external paid LLM APIs or LLM-as-judge heuristics.
3. Support both `metric_only` (fast offline simulation against fixture responses) and `integration` (live invocation of existing `RetrievalService` and workflow agents) modes.
4. Persist all benchmark runs and per-case results into PostgreSQL (`evaluation_runs` and `evaluation_case_results`).
5. Provide REST APIs for triggering runs, polling execution status, inspecting per-case outcomes, exporting standalone JSON reports, and comparing two runs with automated regression detection.
6. Establish the reliable testing foundation required for Milestone 9B (React Evaluation Console & Advanced Model-Assisted Grading).

---

## 2. Architecture & Components

The evaluation module is located in `backend/app/evaluation/` with tests in `backend/tests/evaluation/`:

```
backend/app/evaluation/
├── fixtures/
│   └── benchmark_v1.json         # 35 Grounded benchmark test cases across 7 categories
├── schemas.py                    # Pydantic data contracts and schemas
├── dataset.py                    # Dataset loader, structural validator, and checksum calculation
├── retrieval_metrics.py          # Deterministic Recall@k, Precision@k, HitRate@k, MRR, MAP
├── citation_metrics.py           # Citation presence, identifier/source/page validity, attribution
├── answer_metrics.py             # Normalized key-term matching, fact coverage, abstention accuracy
├── guardrail_metrics.py          # Evaluation against existing ValidationService outcomes
├── retrieval_adapter.py          # Non-destructive adapter to existing RetrievalService
├── runner.py                     # Controlled EvaluationRunner with bounded concurrency & timeouts
├── report.py                     # Run comparison engine & metric delta calculator
├── service.py                    # Service layer for execution & PostgreSQL persistence
└── routes/evaluation.py          # REST API endpoints mounted at /api/v1/evaluations
```

---

## 3. Benchmark Dataset Schema & Categories

Benchmark fixtures are versioned JSON/JSONL documents stored in `backend/app/evaluation/fixtures/`. Each dataset is verified with SHA256 checksumming upon load.

### Benchmark Categories (A–G)

The benchmark fixture `benchmark_v1.json` provides 35 ground-truth test cases covering 7 core operational categories:

| Category Code | Enum Value | Description | Cases |
| :--- | :--- | :--- | :--- |
| **Category A** | `answerable` | Direct factual queries answerable from the grounded corpus. | 7 |
| **Category B** | `multi_hop` | Requires synthesizing information across multiple chunks or sections. | 5 |
| **Category C** | `unanswerable` | Information missing from corpus; expects the model to abstain. | 5 |
| **Category D** | `ambiguous` | Underspecified prompts testing clarification and cautious bounds. | 4 |
| **Category E** | `citation_sensitive` | Queries demanding exact document, chunk, and page attribution. | 5 |
| **Category F** | `unsupported_premise`| Questions based on false assumptions (e.g., non-existent features). | 5 |
| **Category G** | `retrieval_edge_case`| Extreme lengths, punctuation, typographical errors, noise. | 4 |

### Case Structure Contract

```json
{
  "case_id": "TC-ANS-001",
  "dataset_version": "1.0.0",
  "category": "answerable",
  "question": "What are the four architectural tiers defined in the platform blueprint?",
  "expected_answer_facts": [
    "Presentation tier (React frontend)",
    "API and Orchestration tier (FastAPI and LangGraph)",
    "Persistence tier (PostgreSQL and FAISS)",
    "Infrastructure tier (Docker Compose)"
  ],
  "relevant_document_ids": ["doc-arch-001"],
  "relevant_chunk_ids": ["chunk-arch-001", "chunk-arch-002"],
  "expected_citations": [
    {
      "filename": "enterprise_architecture_blueprint.txt",
      "chunk_id": "chunk-arch-001",
      "page_number": 1
    }
  ],
  "answerable": true,
  "expected_validation_behavior": "PASS",
  "evaluation_notes": "Verifies basic four-tier architecture retrieval."
}
```

---

## 4. Metric Definitions & Formulas

### 4.1 Retrieval Metrics (`retrieval_metrics.py`)
- **Recall@k**: Fraction of distinct relevant concepts retrieved in top-k:
  $$\text{Recall@k} = \frac{|\text{Retrieved}_{\le k} \cap \text{Relevant}|}{|\text{Relevant}|}$$
  *Undefined convention*: Returns `None` when $|\text{Relevant}| = 0$ (e.g. unanswerable Category C cases), preventing skew in macro averages.
- **Precision@k**:
  $$\text{Precision@k} = \frac{|\text{Retrieved}_{\le k} \cap \text{Relevant}|}{k}$$
- **Hit Rate@k**: Binary indicator ($1.0$ if $|\text{Retrieved}_{\le k} \cap \text{Relevant}| > 0$, else $0.0$).
- **MRR (Mean Reciprocal Rank)**:
  $$\text{MRR} = \frac{1}{\text{rank of first relevant chunk}} \quad (\text{or } 0.0 \text{ if no hit})$$
- **MAP (Mean Average Precision)**: Standard average precision computed across newly satisfied target ranks $1..k$.
- **Retrieval Latency**: Measured via high-resolution `time.perf_counter()` in milliseconds.
- **Chunk Equivalence Groups & Duplicate Handling**: When multiple chunks in the index represent the same underlying content (e.g. from repeated uploads), explicit alias groups defined in `relevant_chunk_aliases` ensure any equivalent chunk satisfies the target concept without inflating recall or precision beyond the concept's single unit of relevance. Filename-only matching is strictly rejected to prevent false positives across unrelated chunks of identical files.
- **Robust Error Handling**: Unexpected retrieval pipeline exceptions raise typed `RetrievalAdapterError` and are marked with `status="FAILED"` in `CaseEvaluationResult`, preventing retrieval crashes from falsely passing unanswerable cases.

### 4.2 Citation Integrity Metrics (`citation_metrics.py`)
- **Citation Presence**: $1.0$ if citations are provided when expected (or absent when unanswerable); $0.0$ otherwise.
- **Identifier Validity**: Proportion of citations with non-empty, syntactically valid chunk or document IDs.
- **Source Reference Validity**: Proportion of cited documents that actually exist in the retrieved document pool (detects fabricated citations).
- **Page Reference Validity**: Proportion of cited page numbers matching retrieved metadata.
- **Attribution Match**: Proportion of citations that match the ground-truth expected source evidence.
- **Duplicate & Malformed Counts**: Exact count of duplicate and unparseable citation objects.

### 4.3 Answer Quality Metrics (`answer_metrics.py`)
- **Fact Coverage**: Normalized key-term matching for expected atomic facts. Evaluates whether ground-truth technical terms appear in the answer.
- **Abstention Accuracy**: For `unanswerable` queries, checks whether the response abstained (e.g. "not mentioned", "insufficient information") or hallucinated an answer. Returns `None` for answerable queries.
- **Completeness Score**: Structured length and substance heuristic ($0.0$ to $1.0$).

### 4.4 Guardrail Metrics (`guardrail_metrics.py`)
- Directly executes `ValidationService.validate_workflow_state` on agent outputs.
- **Status Match**: Whether observed validation status matches benchmark expectation (`PASS`, `FAIL`, `RECOVERABLE`, `BLOCKED`).
- **Confusion Matrix & Rates**:
  - Positive Case = Violation expected (`FAIL`, `RECOVERABLE`, `BLOCKED`).
  - Negative Case = Clean expected (`PASS`).
  - **TPR (Sensitivity)**: Correctly flagged violations.
  - **FPR (Fall-out)**: False alarms on clean outputs.
  - **FNR (Miss rate)**: Undetected violations.
  - Handles undefined rates gracefully when denominator is 0.

---

## 5. Execution Modes & Concurrency

The runner supports two execution modes:
1. **`METRIC_ONLY`**:
   - Zero network or database dependencies for retrieval.
   - Computes deterministic scores using pre-computed fixture answers and simulated retrieval.
   - Ideal for sub-second CI validation and smoke tests.
2. **`INTEGRATION`**:
   - Calls live `RetrievalService.retrieve()` against native FAISS index and PostgreSQL chunks.
   - Evaluates real retrieval quality, latency, citations, and validation guardrails.

Execution is constrained by an `asyncio.Semaphore(max_concurrency)` (default 4) and protected by per-case `asyncio.wait_for` timeouts (default 30s). Case failures are captured cleanly in the report without halting the evaluation run.

---

## 6. Persistence & Database Schema

Evaluations are persisted using SQLAlchemy models in PostgreSQL:
- **`evaluation_runs`**:
  - `id`: UUID primary key
  - `dataset_name`, `dataset_version`, `dataset_checksum`
  - `mode`: `metric_only` or `integration`
  - `status`: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`
  - `started_at`, `completed_at`, `duration_ms`
  - `configuration_snapshot`: JSONB
  - `aggregate_metrics`: JSONB (all summary metrics)
  - `summary`: JSONB
  - `error`: Text (safe failure details)
- **`evaluation_case_results`**:
  - `id`: UUID primary key
  - `evaluation_run_id`: Foreign key with `ON DELETE CASCADE`
  - `case_id`, `category`
  - `status`: `COMPLETED`, `FAILED`
  - `duration_ms`: Float
  - `metric_results`: JSONB (`retrieval`, `citation`, `answer`, `guardrail`)
  - `safe_error_summary`: Text

Managed via Alembic migration `006_evaluation_engine.py`.

---

## 7. REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/evaluations` | Starts a new evaluation run in the background (returns 201 Created). |
| `GET` | `/api/v1/evaluations` | Lists past evaluation runs (paginated). |
| `GET` | `/api/v1/evaluations/datasets` | Lists registered benchmark datasets and metadata. |
| `GET` | `/api/v1/evaluations/{id}` | Retrieves execution status, metadata, and summary metrics. |
| `GET` | `/api/v1/evaluations/{id}/results` | Retrieves paginated per-case evaluation results. |
| `GET` | `/api/v1/evaluations/{id}/report` | Downloads complete standalone JSON evaluation report. |
| `POST` | `/api/v1/evaluations/compare` | Compares two runs and computes metric deltas, regressions, and improvements. |

### Comparison Report Example

```json
{
  "baseline_run_id": "a1b2c3d4-...",
  "comparison_run_id": "e5f6g7h8-...",
  "baseline_mode": "metric_only",
  "comparison_mode": "metric_only",
  "metric_deltas": {
    "mean_recall_at_3": {
      "baseline": 0.85,
      "comparison": 0.92,
      "delta": 0.07,
      "status": "IMPROVED"
    },
    "guardrail_accuracy": {
      "baseline": 0.95,
      "comparison": 0.95,
      "delta": 0.0,
      "status": "UNCHANGED"
    }
  },
  "improvements": ["mean_recall_at_3"],
  "regressions": [],
  "summary_verdict": "IMPROVED"
}
```

---

---

## 8. Isolated Benchmark Corpus & Automated Integration Regression Tests

An isolated benchmark corpus fixture (`isolated_benchmark_corpus.json`) provides stable document and chunk UUIDs for deterministic testing without mutating or depending on production index state.

The automated integration regression suite in `backend/tests/evaluation/test_evaluation_integration.py` verifies:
- **Test A (Positive Control)**: Verifies real FAISS search returns ground-truth chunk at rank 1 with Recall@1=1.0 and MRR=1.0.
- **Test B (Empty-Result Control)**: Valid query returning 0 chunks returns `status="COMPLETED"` with Recall=None (for unanswerable queries) and Recall=0.0 (for answerable queries), not an execution failure.
- **Test C (Perturbation Control)**: Removing a target chunk from the index drops Recall and Hit Rate to 0.0.
- **Test D (Ranking Shift Control)**: Placing target chunk at rank 2 yields MRR=0.5 and Recall@1=0.0.
- **Test E (Retrieval Exception Handling)**: Unexpected exceptions in `RetrievalService.retrieve` raise `RetrievalAdapterError`, record `status="FAILED"` with sanitized error messages, and do not falsely pass unanswerable cases.
- **Test F (Timeout Control)**: Queries exceeding execution timeout are isolated and marked `status="FAILED"`.
- **Test G (Metric-Only Isolation)**: Metric-only mode operates strictly offline without calling `RetrievalService` or external systems.
- **Test H (Persistence & Failure Reporting)**: Failed cases are persisted to PostgreSQL and serialized into the report's `failures` array.
- **Test I (Equivalence Groups & Duplicates)**: Validates alias groups satisfy target concepts and rejects filename-only matching.

---

## 9. Verification & Running Tests

To run the complete evaluation test suite:

```bash
# Host environment (57 evaluation tests)
python -m pytest backend/tests/evaluation -v

# Docker container
docker exec workflow_backend pytest /app/backend/tests/evaluation -v
```

To run full project regression tests:

```bash
# Complete suite (181 passed tests across M1–M9A)
docker exec workflow_backend pytest /app/backend/tests -q
```
