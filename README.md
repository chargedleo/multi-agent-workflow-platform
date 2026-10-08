# Multi-Agent AI Workflow Automation Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6F00?style=flat)](https://github.com/langchain-ai/langgraph)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-ready **Multi-Agent AI Workflow Automation Platform** that decomposes complex business and technical queries into collaborative, specialized AI agent workflows orchestrating via **LangGraph**, **FastAPI**, **PostgreSQL**, **FAISS Vector Search**, and **Model Context Protocol (MCP)** tools.

---

## Current Status: Milestone 7 — React Monitoring Dashboard & Live Workflow Observability

**Milestone 7** delivers an enterprise-grade **React Monitoring Dashboard** that provides deep observability into the autonomous multi-agent pipeline, durable PostgreSQL execution records, and human-in-the-loop workflows:

```text
User / Reviewer
    ↓
React Monitoring Dashboard (Port 5173)
    ├── 1. Executive Metrics Bar     → Real-time PostgreSQL stats (Total, Active, Awaiting Approval, Completed, Failed, Rejected, Avg Duration)
    ├── 2. Pipeline Stage Visualizer → 8-stage interactive LangGraph timeline with per-node latency (Planner → Retrieval → Analytics → Research → Response → Validation → HITL → Finalized)
    ├── 3. Filterable Workflow Table → Search by query/ID, filter by status, auto-refresh with visibility pause, pagination
    ├── 4. Run Detail Modal          → Deep inspection: inputs/outputs, guardrail audits, MCP data analysis, document citations, decision history
    ├── 5. Approvals Queue           → Dedicated HITL review workspace for Approve / Reject / Changes Requested
    └── 6. Knowledge Base Manager    → Document ingestion & FAISS vector index management
    ↓
FastAPI Backend (Port 8000) & PostgreSQL 16 Persistence
```

### Capabilities Introduced in Milestone 7:
- **Executive Metrics Aggregation (`GET /api/v1/workflows/stats`)**:
  - High-performance, single-query SQL aggregation across all persisted runs: total runs, active/running, awaiting approval, completed, failed, rejected/cancelled, and average execution duration for completed workflows.
- **Searchable, Filterable, Paginated Run History (`GET /api/v1/workflows`)**:
  - Query parameters for status filtering (`ALL`, `ACTIVE`, `WAITING_FOR_APPROVAL`, `COMPLETED`, `FAILED`, `REJECTED`) and full-text keyword search matching queries and run UUIDs.
  - Dynamic page-size and page-index controls with total count attribution.
- **Multi-Agent Pipeline Stage Timeline (`WorkflowTimeline`)**:
  - Visualizes all 8 execution stages with agent roles, per-step execution durations (ms), and active/completed/waiting/failed states.
- **Comprehensive Run Detail Inspection (`RunDetailModal`)**:
  - Compartmentalized tabs for Overview, Execution Timeline, Synthesized Output, Guardrails Evaluation, MCP PostgreSQL Analytics, HITL Decision Audit Trail, and FAISS Citations.
- **Auto-Refresh with Page Visibility Detection**:
  - Configurable polling intervals (Off, 5s, 10s, 30s) that automatically pause when the tab/window is inactive (`document.hidden`) and immediately re-synchronize when reactivated.
- **115 Passing Tests**:
  - Full automated verification across unit, integration, persistence, MCP, guardrails, HITL, and dashboard API endpoints.
  - `POST /api/v1/workflows/{run_id}/approval` — Submits human decision (`APPROVE`, `REJECT`, `CHANGES_REQUESTED`).
- **Interactive React Monitoring UI**:
  - `ApprovalCard`: Review draft answer, validation score, reviewer name, feedback textarea, and Approve / Request Changes / Reject buttons.
  - `PendingApprovals`: Live queue of runs waiting for human action with 1-click inspection.
  - `RunDetailModal`: Complete human approval history timeline and embedded review capability.
- **Comprehensive Test Suite**: **110 automated tests** passing across host environment and Docker backend.

---

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Orchestration**: LangGraph, LangChain Core
- **MCP Tool Layer**: Model Context Protocol (`mcp` 2.x `MCPServer`)
- **Vector Search & RAG**: FAISS (native 1.15.1), NumPy IndexFlatIP fallback, PyMuPDF (fitz)
- **Database & ORM**: PostgreSQL 16, SQLAlchemy 2.x (async), Alembic, asyncpg
- **Configuration & Validation**: Pydantic v2, Pydantic Settings
- **Frontend**: React 18, Vite
- **Testing**: pytest, pytest-asyncio, HTTPX (78 automated tests)
- **DevOps**: Docker, Docker Compose (volumes for PostgreSQL, documents, FAISS, and sample data)

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

The test suite covers configuration, schema constraints, health check endpoints, the LLM factory, LangGraph workflow execution, SQLAlchemy persistence models, persistence lifecycle services, and API history endpoints. All 30 tests run deterministically without requiring external paid API keys.

```bash
# Run full test suite with pytest
pytest -v
```

**Test Coverage Summary (30 Passing Tests):**
- `test_config.py`: Settings defaults, environment overrides, and CORS string parsing.
- `test_schemas.py`: Pydantic validation of `Plan`, `ResearchResult`, `WorkflowResponse`, and boundary assertions.
- `test_health.py`: HTTP 200 responses on `/api/v1/health` and `/`.
- `test_llm.py`: Central LLM abstraction factory and structured mock outputs.
- `test_workflow.py`: End-to-end LangGraph execution, state transitions (Planner → Researcher → Responder), intermediate step accumulation, and error capturing.
- `test_api.py`: FastAPI endpoint execution and validation error rejection.
- `test_persistence_models.py`: SQLAlchemy `WorkflowRun` and `WorkflowStep` creation and one-to-many relationship mapping.
- `test_workflow_persistence.py`: Service-level workflow run lifecycle (`PENDING` → `RUNNING` → `COMPLETED` / `FAILED`), step recording, and pagination.
- `test_workflow_execution_persistence.py`: Verifies LangGraph execution writes durable records to PostgreSQL, records agent timing, and tracks agent failure persistence.
- `test_api_persistence.py`: Integration testing for `POST /workflows` (returns `run_id`), `GET /workflows` (paginated history), and `GET /workflows/{run_id}` (detail inspection & 404 handling).

---

## Current Scope & Limitations (Milestone 2)

Milestone 2 establishes full database persistence and run history tracking for multi-agent workflows.

- **Web Search**: The Research Agent currently uses structured LLM reasoning rather than live internet search. (Planned for Milestone 3+).
- **Vector Search / FAISS**: Semantic document retrieval is deferred to Milestone 3.
- **Tool Sandbox**: Function calling, MCP protocol servers, and code execution sandboxing will be integrated in Milestone 4.
- **Human-in-the-Loop**: Approval checkpoints and pauses will build on top of the Milestone 2 persistence models in Milestone 5.

---

## Planned Future Milestones

- **Milestone 2**: PostgreSQL State Checkpointing, Run History API, and Persistent Workflow Replay.
- **Milestone 3**: Document Retrieval Agent with FAISS Vector Store and RAG integration.
- **Milestone 4**: Data Analysis Agent with sandboxed function calling and tool execution.
- **Milestone 5**: Validation Agent and Human-in-the-Loop (HITL) pause/resume approval gates.
- **Milestone 6**: React monitoring dashboard with real-time streaming, run inspection, and workflow management.
