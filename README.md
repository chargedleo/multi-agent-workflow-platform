# Multi-Agent AI Workflow Automation Platform

[![Python](https://img.shields.io/badge/Python-3.11+-111111?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-111111?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-111111?style=flat)](https://github.com/langchain-ai/langgraph)
[![React](https://img.shields.io/badge/React-18+-111111?style=flat&logo=react&logoColor=white)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-111111?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![FAISS](https://img.shields.io/badge/FAISS-1.15.1-111111?style=flat)](https://github.com/facebookresearch/faiss)
[![Docker](https://img.shields.io/badge/Docker-Compose-111111?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-202%2F202%20Passed-111111?style=flat)](tests)
[![License](https://img.shields.io/badge/License-MIT-111111.svg)](LICENSE)

An enterprise-ready **Multi-Agent AI Workflow Automation Platform** that decomposes complex business and technical queries into collaborative, specialized AI agent workflows. Orchestrated with **LangGraph**, backed by **PostgreSQL 16** with **AsyncPostgresSaver** durable checkpointing, augmented by **native FAISS 1.15.1** vector retrieval and **Model Context Protocol (MCP)** tools, and governed by a self-correcting **Validation Guardrails** layer with **Human-in-the-Loop (HITL)** approval gates.

Features a modern, high-contrast monochrome user interface inspired by **Google Antigravity** across both the React web application and FastAPI Swagger documentation.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    User([User / Client Application]) -->|Inbound Query| Gateway[FastAPI API Gateway :8000]
    
    subgraph Frontend["React 18 Production Web Application (:5173)"]
        UI_Runner[⚡ Query Runner]
        UI_Dash[📊 Monitoring Dashboard]
        UI_HITL[⏳ Approvals Queue]
        UI_Docs[📁 Knowledge Base]
        UI_Eval[🧪 Evaluation Console]
    end
    
    User <-->|HTTP / JSON| Frontend
    Frontend <-->|REST API / JSON| Gateway
    
    subgraph LangGraph["LangGraph Multi-Agent StateGraph"]
        Planner[Planner Agent]
        Retrieval[Document Retrieval Agent]
        Analysis[Data Analysis Agent]
        Researcher[Research Agent]
        Responder[Response Agent]
        Validator[Validation & Guardrails Agent]
    end
    
    Gateway --> Planner
    Planner --> Retrieval
    Retrieval --> Analysis
    Analysis --> Researcher
    Researcher --> Responder
    Responder --> Validator
    
    subgraph Integrations["Platform Infrastructure & Tooling"]
        FAISS[(Native FAISS 1.15.1 Store<br/>IndexFlatIP Cosine Similarity)]
        MCP[MCP Server : Tools<br/>Read-only Analytical SQL]
        PG[(PostgreSQL 16 Database<br/>Runs, Steps, History)]
        Saver[(AsyncPostgresSaver<br/>Durable Thread Checkpoints)]
    end
    
    Retrieval <-->|Semantic Search| FAISS
    Analysis <-->|Tool Calling| MCP
    MCP <-->|Analytical SQL| PG
    Gateway <-->|Persistence| PG
    
    Validator --> GuardrailCheck{Validation Passed?}
    GuardrailCheck -- Recoverable Error &lt; 2 Retries --> Planner
    GuardrailCheck -- Passed --> ApprovalCheck{Requires Approval?}
    
    ApprovalCheck -- Yes --> Interrupt[LangGraph Interrupt Gate]
    Interrupt <-->|Checkpoint / Resume| Saver
    Interrupt <-->|Pending Action| UI_HITL
    
    ApprovalCheck -- No --> Output[Final Workflow Response]
    Interrupt -- Approved --> Output
```

---

## 2. Key Features & Capabilities

- **LangGraph Multi-Agent Orchestration**: Six collaborating agents (Planner, Document Retrieval, MCP Data Analysis, Researcher, Responder, Validator) executing across a compiled, stateful LangGraph graph.
- **Durable Human-in-the-Loop (HITL) Execution**: Interruption and resumption backed by PostgreSQL (`AsyncPostgresSaver`). Workflows can pause at critical review points, survive server reboots, and resume without repeating earlier steps.
- **Enterprise RAG via Native FAISS 1.15.1**: Multi-format document ingestion (PDF, TXT, Markdown) with sliding chunking and inner-product cosine similarity search (`IndexFlatIP`).
- **Model Context Protocol (MCP) Integration**: Analytical SQL tools querying PostgreSQL for verified mathematical operations and business metric calculations.
- **Validation Guardrails with Self-Correction**: Bounded loop (up to 2 retries) checking citation provenance, calculation accuracy, Pydantic format compliance, and confidence score thresholds.
- **React 18 Monitoring Dashboard**: Real-time KPI cards, searchable workflow run table, execution timeline visualizer, and detailed step inspector.
- **Deterministic Evaluation & Benchmarking Engine (M9A/M9B)**: Evaluates 35 benchmark cases across 6 metric categories (Recall@k, MRR, NDCG, citation coverage, factual accuracy, and guardrail resistance) with dual `metric_only` and live `integration` modes.
- **Side-by-Side Benchmark Run Comparison**: Compares candidate and baseline benchmark runs with automated regression detection and downloadable standardized JSON reports.
- **Google Antigravity-Inspired Monochrome UI**: Clean, modern sans-serif typography, solid opaque surfaces, minimal borders, and fixed-layout tables with horizontal scroll resilience.
- **100% Deterministic Testing**: 202 automated tests (189 backend + 13 frontend) passing on both host and Docker Compose environments with zero external paid API dependencies.

---

## 3. Technology Stack

| Domain | Technology | Version | Purpose |
|---|---|---|---|
| **Backend Framework** | Python / FastAPI | 3.11+ / 0.110+ | Asynchronous REST API, middleware, lifecycle probes |
| **Agent Orchestration** | LangGraph / LangChain Core | 0.2+ | Stateful multi-agent graph compilation and transitions |
| **Persistence & ORM** | PostgreSQL / SQLAlchemy / asyncpg | 16 / 2.0+ | Relational run history, intermediate step logs, pooling |
| **Durable Checkpointing** | LangGraph `AsyncPostgresSaver` | 0.2+ | Cross-restart HITL thread interruption and resumption |
| **Database Migrations** | Alembic | 1.13+ | Schema management (001 through 006 head) |
| **Vector Search & RAG** | Native FAISS | 1.15.1 | `IndexFlatIP` normalized cosine similarity vector search |
| **Document Processing** | PyMuPDF (`fitz`) | 1.23+ | High-fidelity PDF, TXT, and Markdown parsing |
| **Analytical Tool Layer** | Model Context Protocol (`mcp`) | 2.0+ | Standardized, read-only analytical SQL execution |
| **Validation Layer** | Pydantic v2 | 2.6+ | Strict type validation and guardrail compliance checking |
| **Web Frontend** | React / Vite | 18.2 / 5.4 | Single-page application, monitoring dashboard, console |
| **Design System** | Pure Sans-Serif Monochrome | Custom CSS | High-contrast Antigravity aesthetic, zero-blur surfaces |
| **Testing Framework** | pytest / pytest-asyncio / node:test | 8.0+ / 0.23+ | 189 backend tests + 13 frontend tests |
| **Containerization** | Docker / Docker Compose | Compose v2 | Multi-container stack (backend, frontend, database) |

---

## 4. Repository Structure

```text
Multi-Agent AI Workflow Automation Platform/
├── backend/
│   ├── alembic/
│   │   ├── versions/                 # Migrations 001 through 006
│   │   └── env.py
│   ├── app/
│   │   ├── agents/                   # Agent implementations
│   │   │   ├── planner.py            # Planner Agent
│   │   │   ├── retrieval.py          # Document Retrieval Agent
│   │   │   ├── data_analysis.py      # Data Analysis Agent (MCP)
│   │   │   ├── researcher.py         # Research Agent
│   │   │   ├── responder.py          # Response Agent
│   │   │   └── validator.py          # Validation & Guardrails Agent
│   │   ├── api/                      # REST API routing
│   │   │   └── routes/
│   │   │       ├── health.py         # Liveness and readiness probes
│   │   │       ├── workflow.py       # Workflow execution & stats
│   │   │       ├── approval.py       # Human-in-the-Loop review & resume
│   │   │       ├── document.py       # Document ingestion & management
│   │   │       └── evaluation.py     # Evaluation & benchmarking APIs
│   │   ├── core/                     # Application settings & logging
│   │   │   ├── config.py
│   │   │   └── logging.py
│   │   ├── evaluation/               # Milestone 9A Evaluation Engine
│   │   │   ├── dataset.py            # 35-case benchmark loader
│   │   │   ├── metrics.py            # Answer & guardrail metrics
│   │   │   ├── retrieval_metrics.py  # Recall@k, MRR, NDCG math
│   │   │   ├── retrieval_adapter.py  # Live FAISS query adapter
│   │   │   ├── runner.py             # Benchmark concurrency runner
│   │   │   ├── comparison.py         # Delta comparison & regression engine
│   │   │   └── service.py            # Evaluation persistence service
│   │   ├── graph/                    # LangGraph orchestration
│   │   │   ├── state.py              # Shared WorkflowState TypedDict
│   │   │   └── workflow.py           # Compiled StateGraph pipeline
│   │   ├── mcp/                      # Model Context Protocol tools
│   │   │   └── server.py             # Read-only analytical SQL tools
│   │   ├── models/                   # SQLAlchemy ORM models & Pydantic schemas
│   │   ├── services/                 # Database, FAISS, and LLM services
│   │   ├── static/                   # Monochrome Swagger CSS overrides
│   │   └── main.py                   # FastAPI entrypoint
│   ├── tests/                        # 189 automated backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/            # Monitoring dashboard & timeline
│   │   │   ├── evaluation/           # M9B React Evaluation Console
│   │   │   ├── DocumentManager.jsx   # Document upload & chunk viewer
│   │   │   ├── PendingApprovals.jsx  # HITL approval review queue
│   │   │   ├── QueryInput.jsx        # Interactive query prompt runner
│   │   │   ├── WorkflowHistory.jsx   # Paginated run history
│   │   │   └── WorkflowResult.jsx    # Formatted response view
│   │   ├── services/                 # Frontend API client
│   │   ├── App.jsx                   # Application navigation
│   │   ├── App.css                   # Component styles & fixed tables
│   │   └── index.css                 # Base design tokens
│   ├── test/                         # 13 automated frontend tests
│   ├── nginx.conf
│   ├── vite.config.js
│   ├── Dockerfile
│   └── package.json
├── docs/                             # Engineering documentation
│   ├── PROJECT_COMPLETION_REPORT.md  # Detailed milestone-by-milestone audit
│   ├── architecture.md               # Architecture specification
│   ├── deployment.md                 # Production deployment guide
│   └── evaluation.md                 # Evaluation engine design
├── docker-compose.yml                # Multi-service stack definition
└── README.md
```

---

## 5. Quick Start with Docker (PowerShell)

Launch the complete stack (PostgreSQL, FastAPI Backend, React Frontend) in isolated containers:

```powershell
# 1. Clone or navigate to the repository
cd "D:\Projects\Multi-Agent AI Workflow Automation Platform"

# 2. Build and start all services in the background
docker compose up --build -d

# 3. Verify container status
docker compose ps

# 4. Check backend health
curl http://localhost:8000/api/v1/health

# 5. Access the applications
# Frontend Dashboard:  http://localhost:5173
# FastAPI Swagger Docs: http://localhost:8000/docs
```

To view logs or shut down the stack:

```powershell
# View live container logs
docker compose logs -f backend

# Stop all containers and preserve database volumes
docker compose down
```

---

## 6. Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 16 (or running via `docker compose up -d postgres`)

### 1. Backend Setup

```powershell
# Navigate to the backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```powershell
# In a separate terminal, navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

---

## 7. Environment Configuration & Mock/Fallback Transparency

Copy `.env.example` to `.env` to configure application settings:

```powershell
cp .env.example .env
```

| Variable | Description | Default | Production Setting |
|---|---|---|---|
| `APP_ENV` | Application environment mode | `development` | `production` |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_db` | Your PostgreSQL cluster URI |
| `LLM_PROVIDER` | LLM backend: `mock`, `openai`, `azure`, `ollama` | `mock` | `openai` or `azure` |
| `LLM_MODEL` | Model identifier | `gpt-4o-mini` | `gpt-4o` or `gpt-4o-mini` |
| `LLM_API_KEY` | Provider API key | `""` | `sk-...` |
| `CORS_ORIGINS` | Permitted browser origins | `http://localhost:5173,http://localhost:3000` | Domain URL |
| `FAISS_INDEX_PATH`| Directory for FAISS index persistence | `./data/faiss` | Mounted persistent volume |

### Transparent Mock & Production Disclosures
- **Deterministic Offline Execution**: By default, the system runs with `LLM_PROVIDER="mock"`, requiring **zero external API keys** and **zero internet access**. All 6 agents transition deterministically, calculating verified answers and testing guardrails.
- **Production LLM Compatibility**: Switching to live models (OpenAI, Azure OpenAI, Ollama) requires only updating `LLM_PROVIDER="openai"` and setting `LLM_API_KEY`. The state graph and agent prompts transition seamlessly.
- **Live Vector & Database Infrastructure**: The vector store uses **real native FAISS 1.15.1** (`IndexFlatIP`), real **PostgreSQL 16**, and real **AsyncPostgresSaver** checkpoints in both mock and production modes.

---

## 8. API Reference

All endpoints return JSON and propagate the `X-Request-ID` header.

### Workflow & Monitoring Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Overall system health probe |
| `GET` | `/api/v1/health/liveness` | Kubernetes liveness probe (`/live`) |
| `GET` | `/api/v1/health/readiness` | Kubernetes readiness probe (`/ready`) |
| `POST` | `/api/v1/workflows` | Execute a multi-agent workflow |
| `GET` | `/api/v1/workflows` | List paginated workflow runs |
| `GET` | `/api/v1/workflows/{run_id}` | Retrieve run details with individual agent steps |
| `GET` | `/api/v1/workflows/stats` | Aggregate dashboard KPI metrics |

### Human-in-the-Loop (HITL) Approvals

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/approvals/pending` | List workflows waiting for human review |
| `POST` | `/api/v1/approvals/{run_id}/action` | Submit operator action (`APPROVE`, `REJECT`, `CHANGES_REQUESTED`) |

### Document Management & RAG

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents` | Upload and chunk PDF, TXT, or Markdown documents |
| `GET` | `/api/v1/documents` | List all ingested documents and chunk counts |
| `DELETE`| `/api/v1/documents/{doc_id}` | Delete document and remove vectors from FAISS index |

### Evaluation & Benchmarking (Milestones 9A & 9B)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/evaluations/datasets` | List available evaluation benchmark datasets |
| `POST` | `/api/v1/evaluations/runs` | Launch a new evaluation benchmark run |
| `GET` | `/api/v1/evaluations/runs` | List paginated historical evaluation runs |
| `GET` | `/api/v1/evaluations/runs/{run_id}` | Get evaluation run summary and macro scores |
| `GET` | `/api/v1/evaluations/runs/{run_id}/cases` | Get per-case diagnostic results and fact diffs |
| `GET` | `/api/v1/evaluations/runs/{run_id}/report`| Download full standardized JSON benchmark report |
| `POST` | `/api/v1/evaluations/compare` | Compare candidate vs baseline run with delta report |

---

## 9. Multi-Agent Workflow Details

The system coordinates six specialized agents across a stateful pipeline:

1. **Planner Agent**:
   - Parses the inbound prompt to identify the core objective, required domain knowledge, and whether external documents or calculations are necessary.
   - Formulates a structured execution plan (`Plan` schema) with sequential sub-tasks.
2. **Document Retrieval Agent**:
   - Computes query embeddings and queries the native FAISS 1.15.1 index (`IndexFlatIP`).
   - Retrieves top-k semantically relevant chunks above similarity threshold (0.65) and maps citation IDs to page numbers and filenames.
3. **Data Analysis Agent (MCP)**:
   - Evaluates analytical and quantitative queries using Model Context Protocol (MCP) tools.
   - Executes parameterized read-only SQL queries against PostgreSQL to compute exact sums, averages, and statistical metrics.
4. **Research Agent**:
   - Synthesizes findings across retrieved document chunks, computed data tables, and general domain knowledge into structured observations.
5. **Response Agent**:
   - Drafts the final comprehensive answer, formatting key takeaways, confidence ratings, and strict inline bracket citations (e.g., `[Doc1:p2]`).
6. **Validation & Guardrails Agent**:
   - Verifies that all citations map to actual retrieved chunks (citation provenance).
   - Verifies that all numerical claims match computed MCP data analysis values.
   - Enforces format compliance and confidence thresholds.
   - Triggers bounded self-correction (up to 2 retries) if recoverable errors are detected.

---

## 10. Human-in-the-Loop (HITL) Approval System

```text
Workflow Execution
       ↓
Validator Agent passes
       ↓
High-Impact Action or Policy Trigger Detected?
       ├── No  → Finalize and return response (COMPLETED)
       └── Yes → LangGraph interrupt()
                     ↓
         PostgreSQL Thread Checkpoint Saved (AsyncPostgresSaver)
                     ↓
         Status: waiting_for_approval
                     ↓
         Operator reviews in Approvals Queue
                     ├── APPROVE → Resumes from checkpoint → COMPLETED
                     ├── REJECT  → Marks workflow FAILED
                     └── CHANGES_REQUESTED → Rewinds state to Planner with feedback
```

- **Checkpoint Durability**: Checkpoints are stored in PostgreSQL (`checkpoints` and `checkpoint_writes` tables). The backend server or Docker container can restart entirely, and the pending approval remains intact and resumable.
- **Operator Actions**:
  - `APPROVE`: Resumes execution directly from the checkpoint, returning the verified answer.
  - `REJECT`: Terminates the workflow and records operator rejection reason in persistence history.
  - `CHANGES_REQUESTED`: Injects operator feedback into the workflow state and routes execution back to the Planner for a bounded revision pass.

---

## 11. Evaluation & Benchmarking Engine

The evaluation engine (M9A backend, M9B frontend console) provides deterministic grading of system performance across 35 benchmark cases (`benchmark_v1`):

### Evaluated Metric Categories

1. **Retrieval Performance**:
   - `Recall@k` (k=1, 3, 5): Fraction of ground-truth relevant chunks retrieved.
   - `Precision@k`: Fraction of retrieved chunks that are relevant.
   - `HitRate@k`: Whether at least one relevant chunk was retrieved.
   - `MRR` (Mean Reciprocal Rank): Position of the first relevant chunk.
   - `MAP` (Mean Average Precision): Precision across all relevant positions.
2. **Citation Provenance**:
   - `Citation Precision`: Percentage of inline citations pointing to valid retrieved documents.
   - `Citation Recall`: Percentage of factual claims supported by citations.
   - `Grounded Claim Ratio`: Ratio of claims directly supported by evidence.
3. **Factual Accuracy**:
   - `Atomic Fact Coverage`: Percentage of expected benchmark facts present in the answer.
   - `Key Fact Recall`: Presence of critical domain-specific findings.
4. **Safety & Guardrails**:
   - `Guardrail Accuracy`: Correct detection and handling of adversarial or ungrounded queries.
   - `False Rejection Rate`: Rate of valid queries erroneously blocked.
5. **Execution Latency & Performance**:
   - End-to-end execution duration, individual agent step latency, and execution cost.

### CLI Benchmark Runner

Run the benchmark directly from the terminal:

```powershell
# Run benchmark in metric_only mode
python -m backend.app.evaluation.runner --dataset benchmark_v1 --mode metric_only

# Run benchmark in live integration mode (queries real FAISS index)
python -m backend.app.evaluation.runner --dataset benchmark_v1 --mode integration --concurrency 2
```

---

## 12. Automated Testing & Verification Matrix

The platform is covered by **202 automated tests** across the backend and frontend:

```powershell
# Run backend test suite (189 tests)
backend\.venv\Scripts\python.exe -m pytest backend/tests -q

# Run frontend test suite (13 tests)
cd frontend
npm test

# Run frontend production build
npm run build
```

### Verification Summary

```text
============================== Test Execution Summary ==============================
Backend Unit & Integration Tests:     189 passed (100%)
Frontend Service & Contract Tests:     13 passed (100%)
Total Automated Tests:                202 passed, 0 failed, 0 skipped
Docker Container Regression Parity:   100% verified (all 189 tests pass inside container)
Vite Production Bundle:               50 modules transformed, zero build errors
====================================================================================
```

---

## 13. Production Readiness & Security Disclosures

- **Kubernetes-Ready Health Probes**: `/api/v1/health/liveness` for process heartbeat and `/api/v1/health/readiness` for dependency checks (database connection, vector store readiness).
- **Request Tracing**: `CorrelationIdMiddleware` attaches a unique `X-Request-ID` to every HTTP request, tracing logs across all agent nodes and database operations.
- **Safe SQL Execution**: The MCP analytical SQL server enforces strict `SELECT`-only execution, rejecting any data manipulation or schema modification commands.
- **Credential Sanitization**: Passwords, API keys, and sensitive tokens are automatically masked in log outputs, error dumps, and API responses.
- **Database Connection Pooling**: Configured with `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`, and `pool_recycle=3600` to prevent stale connection leaks.

---

## 14. Limitations & Future Roadmap

### Current Limitations
- In `mock` mode, the `MockChatModel` generates deterministic template responses for automated testing. To enable fluid conversational generation, configure an OpenAI or Ollama provider.
- Document ingestion currently supports PDF, TXT, and Markdown files up to 25 MB.
- FAISS vector storage is currently file-backed (`./data/faiss`); distributed vector databases (e.g., pgvector, Milvus) can be swapped in for multi-node deployments.

### Future Roadmap
- **Distributed Vector Search**: Integration with PostgreSQL `pgvector` for unified vector and relational storage.
- **WebSocket Streaming**: Real-time token streaming from individual agent nodes to the React frontend.
- **Asynchronous Task Workers**: Celery / Redis integration for long-running batch evaluation runs.
- **Multi-Tenant Workspaces**: Role-based access control (RBAC) and tenant isolation for enterprise teams.

---

## 15. License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
