# Multi-Agent AI Workflow Automation Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6F00?style=flat)](https://github.com/langchain-ai/langgraph)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-ready **Multi-Agent AI Workflow Automation Platform** that decomposes complex business and technical queries into collaborative, specialized AI agent workflows orchestrating via **LangGraph**, **FastAPI**, **PostgreSQL**, **FAISS Vector Search**, and **Model Context Protocol (MCP)** tools.

---

## Current Status: Milestone 9B — React Evaluation Console & Final Release

**Milestone 9B** is the final mandatory milestone of the platform, delivering the **React Evaluation Console**, full end-to-end multi-agent verification, durable HITL approval controls, complete test parity across Host and Docker, and portfolio-ready documentation.

```text
User / Reviewer / Evaluation Client
    ↓
React 18 Production Frontend (Port 5173, Nginx Reverse Proxy)
    ├── 📊 Monitoring Dashboard (Macro stats, live run history, execution timeline)
    ├── ⚡ Query Runner (Interactive business query execution & source citations)
    ├── ⏳ Approvals Queue (Durable HITL approval/rejection/revision flow)
    ├── 📁 Knowledge Base (PDF, TXT, MD document ingestion & FAISS indexing)
    └── 🧪 Evaluation Console (Milestone 9B)
        ├── Launch Benchmark (metric_only & integration modes, concurrency, timeouts)
        ├── Evaluation History (Paginated run tracking, status, duration, macro metrics)
        ├── Run Details & Diagnostics (Retrieval, citation, fact coverage, guardrail matrix)
        ├── Per-Case Diagnostics (Expandable 35-case audit table with atomic fact diffs)
        ├── Side-by-Side Run Comparison (Metric deltas, regression detection, verdict)
        └── Standalone Report Export (Standardized machine-readable JSON reports)
    ↓
FastAPI Backend (Port 8000)
    ├── Correlation Middleware (X-Request-ID propagation) & Health/Readiness Probes
    ├── Workflow REST APIs (/api/v1/workflows)
    ├── HITL Approvals REST APIs (/api/v1/approvals)
    ├── Document Ingestion REST APIs (/api/v1/documents)
    └── Evaluation Engine REST APIs (/api/v1/evaluations)
    ↓
LangGraph Multi-Agent Orchestration Pipeline
    Planner → Document Retrieval → Data Analysis (MCP) → Researcher → Responder → Validation
    ↓
PostgreSQL 16 Persistence (Alembic 006) & Native FAISS 1.15.1 Store (IndexFlatIP)
```

### Capabilities Delivered Across All Milestones:
- **LangGraph Multi-Agent Flow**: Structured collaboration across Planner, Document Retrieval, MCP Data Analysis, Researcher, Responder, and Validation agents.
- **Native FAISS 1.15.1 Vector Search**: Normalized inner-product (`IndexFlatIP`) cosine similarity with atomic persistence in `./data/faiss`.
- **Model Context Protocol (MCP)**: Analytical SQL tools querying PostgreSQL for structured mathematical and business data analysis.
- **Validation & Guardrails Layer**: Bounded correction loop verifying citations, numerical calculations, format schemas, and response confidence.
- **Durable HITL Approval Engine**: LangGraph PostgreSQL checkpointer (`AsyncPostgresSaver`) providing interrupt/resume control across server restarts with `APPROVE`, `REJECT`, and `CHANGES_REQUESTED` flows.
- **React Monitoring Dashboard**: Live workflow metrics, run filtering, pagination, and multi-agent execution timeline visualization.
- **React Evaluation Console (Milestone 9B)**: Benchmark execution, run history, macro metrics, per-case diagnostics, run comparison with regression alerts, and JSON export.
- **202 Automated Tests (100% Passing)**: 189 backend tests passing on both host and Docker, plus 13 frontend service tests.

---

## Technology Stack

- **Backend**: Python 3.11.17, FastAPI, Uvicorn
- **Orchestration**: LangGraph 0.2+, LangChain Core
- **MCP Tool Layer**: Model Context Protocol (`mcp` 2.x `MCPServer`)
- **Vector Search & RAG**: FAISS (native 1.15.1), IndexFlatIP cosine similarity, PyMuPDF (fitz)
- **Database & Persistence**: PostgreSQL 16 Alpine, SQLAlchemy 2.x (async), Alembic, asyncpg
- **Checkpointer**: LangGraph `AsyncPostgresSaver` for durable interrupt/resume
- **Frontend**: React 18, Vite, dark-mode CSS design system
- **Testing**: pytest, pytest-asyncio, HTTPX, node:test (202 automated tests passing)
- **DevOps**: Docker, Docker Compose (PostgreSQL, FastAPI Backend, React Frontend)

---

## Repository Structure

```text
multi-agent-workflow-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── health.py         # GET /api/v1/health
│   │   │   │   └── workflow.py       # POST /api/v1/workflows
│   │   │   └── __init__.py
│   │   │
│   │   ├── agents/
│   │   │   ├── planner.py            # Planner Agent (Plan schema)
│   │   │   ├── researcher.py         # Research Agent (ResearchResult schema)
│   │   │   └── responder.py          # Response Agent (WorkflowResponse schema)
│   │   │
│   │   ├── graph/
│   │   │   ├── state.py              # Shared WorkflowState TypedDict
│   │   │   └── workflow.py           # Compiled LangGraph StateGraph pipeline
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic schemas for agents and API
│   │   │
│   │   ├── services/
│   │   │   ├── llm.py                # LLM factory (OpenAI, Azure, Ollama, Mock)
│   │   │   └── database.py           # Async PostgreSQL engine and health check
│   │   │
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings & environment parsing
│   │   │   └── logging.py            # Standardized request-aware logging
│   │   │
│   │   └── main.py                   # FastAPI factory, CORS, and lifecycle
│   │
│   ├── tests/
│   │   ├── conftest.py               # Shared pytest fixtures & test config
│   │   ├── test_api.py               # API endpoint integration tests
│   │   ├── test_config.py            # Configuration & CORS parsing tests
│   │   ├── test_health.py            # Health check & root endpoint tests
│   │   ├── test_llm.py               # LLM abstraction & MockChatModel tests
│   │   ├── test_schemas.py           # Pydantic schema validation tests
│   │   └── test_workflow.py          # LangGraph state transitions & error handling
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── QueryInput.jsx        # Query input, quick prompts, hotkeys
│   │   │   └── WorkflowResult.jsx    # Formatted response, badges, key points
│   │   ├── services/
│   │   │   └── api.js                # API service layer (fetch client)
│   │   ├── App.jsx                   # Main application container
│   │   ├── App.css                   # Custom responsive styling
│   │   ├── index.css                 # Design tokens and resets
│   │   └── main.jsx                  # React DOM mount point
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── Dockerfile
│
├── docker-compose.yml                # Multi-service stack (backend, frontend, postgres)
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore rules
├── pytest.ini                        # Pytest configuration
├── README.md                         # Project documentation
└── docs/
    └── architecture.md               # Detailed architecture & Mermaid diagrams
```

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` to configure your environment:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Name of the platform | `Multi-Agent AI Workflow Platform` |
| `APP_ENV` | Environment (`development`, `test`, `production`) | `development` |
| `API_HOST` | Host for the FastAPI server | `0.0.0.0` |
| `API_PORT` | Port for the FastAPI server | `8000` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated or JSON list) | `http://localhost:5173,http://localhost:3000` |
| `LLM_PROVIDER` | LLM provider: `openai`, `azure`, `ollama`, or `mock` | `mock` (works offline with zero keys) |
| `LLM_MODEL` | Model identifier | `gpt-4o-mini` |
| `LLM_API_KEY` | Provider API key | `""` |
| `LLM_BASE_URL` | Optional custom base URL for OpenAI-compatible APIs | `""` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_db` |
| `POSTGRES_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_PASSWORD`| PostgreSQL password | `postgres` |
| `POSTGRES_DB` | PostgreSQL database name | `workflow_db` |

> **Note**: If `LLM_PROVIDER="mock"` is selected, the platform runs completely offline using a deterministic mock chat model. To use OpenAI or local Ollama, set `LLM_PROVIDER="openai"` and provide your `LLM_API_KEY` or `LLM_BASE_URL`.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker and Docker Compose (optional for containerized run)

---

### Local Development Setup

#### 1. Backend Setup

```bash
# Navigate to the project root
cd "multi-agent-workflow-platform"

# Create and activate virtual environment
python -m venv backend/.venv
# Windows:
.\backend\.venv\Scripts\activate
# Linux/macOS:
source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run the FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at:
- **API URL**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### 2. Frontend Setup

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173).

---

### Running with Docker Compose

You can launch the entire stack (PostgreSQL, FastAPI Backend, and React Frontend) with a single command:

```bash
docker compose up --build
```

Services started:
- **Frontend**: [http://localhost:5173](http://localhost:5173) (served via Nginx)
- **Backend**: [http://localhost:8000](http://localhost:8000)
- **PostgreSQL**: `localhost:5432` (with persistent volume `workflow_postgres_data`)

To stop the services:

```bash
docker compose down
```

---

## Database Architecture & Migrations

Milestone 2 introduces durable PostgreSQL persistence using **SQLAlchemy 2.x async ORM** and **Alembic** migrations.

### Tables
1. **`workflow_runs`**:
   - `id` (UUID, primary key)
   - `request_id` (UUID, indexed)
   - `user_query` (Text)
   - `status` (VARCHAR, indexed: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`)
   - `started_at`, `completed_at`, `created_at`, `updated_at` (TIMESTAMPTZ)
   - `duration_ms` (BIGINT)
   - `final_answer` (TEXT)
   - `key_points` (JSONB)
   - `confidence` (FLOAT)
   - `plan`, `research_results` (JSONB)
   - `errors` (JSONB)
   - `metadata` (JSONB)

2. **`workflow_steps`**:
   - `id` (UUID, primary key)
   - `run_id` (UUID, foreign key referencing `workflow_runs.id` on delete cascade)
   - `agent_name` (VARCHAR: `planner`, `researcher`, `responder`)
   - `step_order` (INTEGER, indexed with `run_id`)
   - `status` (VARCHAR: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`)
   - `started_at`, `completed_at`, `created_at` (TIMESTAMPTZ)
   - `duration_ms` (BIGINT)
   - `input_data`, `output_data` (JSONB)
   - `error` (TEXT)

### Running Migrations

```bash
# Run latest migrations
alembic upgrade head

# Roll back the most recent migration
alembic downgrade -1

# Generate a new migration revision
alembic revision --autogenerate -m "description_of_change"
```

---

## API Reference

### Health Check

```http
GET /api/v1/health
```

**Response (`200 OK`):**
```json
{
  "status": "healthy",
  "database": "connected",
  "app_env": "development",
  "version": "0.1.0"
}
```

---

### Execute Multi-Agent Workflow

```http
POST /api/v1/workflows
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "Compare PostgreSQL and MongoDB for a startup SaaS application."
}
```

**Response (`200 OK`):**
```json
{
  "request_id": "766ad1ae-0c48-4cb9-b1d5-bc7551066060",
  "run_id": "045b10c2-d427-4719-bf7e-81a8b669de33",
  "status": "completed",
  "answer": "Based on the analysis of your query: PostgreSQL is strongly recommended as the default database for most SaaS startups...",
  "key_points": [
    "PostgreSQL offers superior data integrity, relational constraints, and flexible JSONB querying.",
    "MongoDB provides rapid prototyping for polymorphic documents and out-of-the-box horizontal scaling.",
    "For a SaaS startup, starting with PostgreSQL reduces early schema technical debt."
  ],
  "confidence": 0.95,
  "errors": []
}
```

---

### List Recent Workflow Runs

```http
GET /api/v1/workflows?page=1&page_size=10
```

**Response (`200 OK`):**
```json
{
  "items": [
    {
      "run_id": "045b10c2-d427-4719-bf7e-81a8b669de33",
      "request_id": "766ad1ae-0c48-4cb9-b1d5-bc7551066060",
      "query": "Compare PostgreSQL and MongoDB for a startup SaaS application.",
      "status": "COMPLETED",
      "started_at": "2026-10-07T12:20:38.668894Z",
      "completed_at": "2026-10-07T12:20:38.783876Z",
      "duration_ms": 114
    }
  ],
  "page": 1,
  "page_size": 10,
  "total": 1
}
```

---

### Get Workflow Run Details with Steps

```http
GET /api/v1/workflows/{run_id}
```

**Response (`200 OK`):**
```json
{
  "run_id": "045b10c2-d427-4719-bf7e-81a8b669de33",
  "request_id": "766ad1ae-0c48-4cb9-b1d5-bc7551066060",
  "query": "Compare PostgreSQL and MongoDB for a startup SaaS application.",
  "status": "COMPLETED",
  "started_at": "2026-10-07T12:20:38.668894Z",
  "completed_at": "2026-10-07T12:20:38.783876Z",
  "duration_ms": 114,
  "final_answer": "Based on the analysis of your query...",
  "key_points": ["PostgreSQL offers superior data integrity..."],
  "confidence": 0.95,
  "errors": [],
  "steps": [
    {
      "id": "e96c449c-aef6-4354-a957-234b655517e5",
      "agent_name": "planner",
      "step_order": 1,
      "status": "COMPLETED",
      "duration_ms": 22,
      "output_data": { "goal": "Compare databases", "steps": ["..."] },
      "error": null
    },
    {
      "id": "c67a1881-af8a-4b20-96fc-8cb6772f6759",
      "agent_name": "researcher",
      "step_order": 2,
      "status": "COMPLETED",
      "duration_ms": 12,
      "output_data": { "findings": ["..."] },
      "error": null
    },
    {
      "id": "8588b3e7-223d-4a20-a4ef-fb9b70c7f1c9",
      "agent_name": "responder",
      "step_order": 3,
      "status": "COMPLETED",
      "duration_ms": 12,
      "output_data": { "answer": "...", "confidence": 0.95 },
      "error": null
    }
  ]
}
```

#### Example cURL Commands

```bash
# Execute a workflow
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{"query": "Assess Kafka vs RabbitMQ for streaming architecture."}'

# List recent runs
curl -X GET "http://localhost:8000/api/v1/workflows?page=1&page_size=10"

# Inspect specific run detail
curl -X GET "http://localhost:8000/api/v1/workflows/045b10c2-d427-4719-bf7e-81a8b669de33"
```

---

## Running Automated Tests

The test suite covers configuration, schema constraints, health check endpoints, the LLM factory, LangGraph workflow execution, SQLAlchemy persistence models, persistence lifecycle services, document ingestion, native FAISS retrieval, MCP analytics tooling, guardrails validation, Human-in-the-Loop approval loops, React dashboard APIs, production hardening probes, and the Milestone 9A/9B Evaluation Engine. All tests run deterministically without requiring external paid API keys.

```bash
# Run full backend test suite on host (189 tests)
backend\.venv\Scripts\python.exe -m pytest backend/tests -q

# Run full backend test suite inside Docker container (189 tests)
docker exec workflow_backend pytest /app/backend/tests -q

# Run frontend test suite (13 tests)
cd frontend && npm test

# Run frontend production build
cd frontend && npm run build
```

**Test Coverage Summary (202 Passing Tests):**
- **Milestones 1–4 (42 tests):** LangGraph workflow transitions, LLM abstraction, document ingestion, native FAISS vector search, and MCP tools.
- **Milestone 5 (28 tests):** Validation and guardrails engine, numerical verification, citation provenance, and bounded correction loop.
- **Milestone 6 (30 tests):** Durable HITL review gates, `AsyncPostgresSaver` checkpointing, resume from interrupt, and revision bounds.
- **Milestone 7 (25 tests):** Executive metrics aggregation (`/stats`), paginated search, and execution timeline visualization.
- **Milestone 8 (20 tests):** Liveness/readiness probes, pool sizing, request correlation `X-Request-ID`, and credential sanitization.
- **Milestones 9A & 9B Backend (44 tests):** Dataset loading, deterministic metrics (Recall@k, Precision@k, HitRate@k, MRR, MAP, Latency), citation metrics, answer metrics, guardrail matrix, evaluation runner, comparison engine, REST endpoints, and automated benchmark ground-truth audit.
- **Milestone 9B Frontend (13 tests):** Service layer contracts, parameter serialization, error response handling, and comparison execution.

---

## Real Versus Mock Provider Transparency Disclosure

To ensure complete engineering integrity and portfolio credibility:
- **Default Offline Configuration**: The platform ships configured with `LLM_PROVIDER="mock"` and `EMBEDDING_PROVIDER="mock"` to guarantee zero-cost, instant, and reproducible execution out of the box.
- **Live Model Support**: External LLMs (OpenAI, Azure OpenAI, Ollama) can be configured simply by setting `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY` in `.env`.
- **Real Production Infrastructure**: The system operates with **real native FAISS 1.15.1** (`IndexFlatIP`), real **PostgreSQL 16**, real **LangGraph checkpointer**, and real **FastAPI** web application.
- **Integration Evaluation**: In `integration` evaluation mode, the evaluator queries the real, live native FAISS index and PostgreSQL metadata.

---

## Operations & Portfolio Presentation Guide

### Quickstart Demo Walkthrough
1. **Launch Containers**: `docker compose up --build -d`
2. **Access Frontend**: Open `http://localhost:5173` in your browser.
3. **Run Query**: Go to **⚡ Query Runner**, submit an architectural query. Notice the workflow pause in `waiting_for_approval` at the HITL gate.
4. **Approve Workflow**: Navigate to **⏳ Approvals Queue**, review the candidate response and citation snippets, then click **Approve**. Watch the workflow resume to completion.
5. **Inspect Timeline**: Go to **📊 Monitoring Dashboard**, select the completed run, and view the multi-agent step execution sequence.
6. **Benchmark System**: Go to **🧪 Evaluation Console**, select `benchmark_v1`, click **Execute Benchmark Run**, inspect the 35-case diagnostics table, and compare against previous runs.

See [docs/final_release_report.md](file:///d:/Projects/Multi-Agent%20AI%20Workflow%20Automation%20Platform/docs/final_release_report.md) for the complete release gate report and [docs/deployment.md](file:///d:/Projects/Multi-Agent%20AI%20Workflow%20Automation%20Platform/docs/deployment.md) for production operational guidance.
