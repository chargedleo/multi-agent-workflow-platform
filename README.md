# Multi-Agent AI Workflow Automation Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6F00?style=flat)](https://github.com/langchain-ai/langgraph)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-ready **Multi-Agent AI Workflow Automation Platform** that decomposes complex business and technical queries into collaborative, specialized AI agent workflows orchestrating via **LangGraph**, **FastAPI**, **PostgreSQL**, **FAISS Vector Search**, and **Model Context Protocol (MCP)** tools.

---

## Current Status: Milestone 5 — Validation Guardrails & Agent Correction Loop

**Milestone 5** introduces a robust, production-grade **Validation & Guardrails Layer** with a bounded agent correction loop. The system validates agent outputs, MCP tool outputs, citation provenance, numerical calculations, and factual assertions before the workflow is allowed to complete:

```text
User Query
    ↓
FastAPI REST API (POST /api/v1/workflows)
    ↓
Database Run Record Created (status: PENDING → RUNNING)
    ↓
LangGraph StateGraph Execution (6 Collaborative Agents)
    ├── 1. Planner Agent            → Extract goals & sequential plan
    ├── 2. Document Retrieval Agent → Query FAISS vector index & retrieve matching chunks
    ├── 3. Data Analysis Agent      → Decide requirement & invoke approved MCP analytical tools
    ├── 4. Research Agent           → Synthesize plan, documents, and verified numerical figures
    ├── 5. Response Agent           → Synthesize executive response with citations & metric tables
    └── 6. Validation Agent         → Guardrail checks across schema, citations, math, tools, & claims
            ├── PASS                → Complete workflow (status: COMPLETED, validation_status: PASS)
            ├── RECOVERABLE         → Route back to Response Agent with actionable feedback (max 2 attempts)
            └── FAIL / BLOCKED      → Terminate safely with violation audit (status: FAILED)
    ↓
Database Run Record Completed (validation_status, validation_score, duration_ms)
    ↓
Structured API Response (with Grounded Citations, Quantitative Metrics, & Validation Audit)
```

### Capabilities Introduced in Milestone 5:
- **Comprehensive Validation Agent & Node**: Governs final workflow completion via LangGraph conditional routing (`validation_router`).
- **Modular Deterministic Validators**:
  - `response_schema`: Enforces non-empty answer bodies, structured key takeaways, calibrated confidence bounds `[0.0, 1.0]`, and matching request identifiers.
  - `citation`: Provenance checks against retrieved documents, preventing fabricated filenames or hallucinated chunk IDs.
  - `analysis`: Mathematical consistency checks (`count >= 0`, `sum / count == mean`, `min <= mean <= max`, group rows reconciliation to total sum, top-N limit validation).
  - `tool_output`: Validates allowlisted MCP tool names, prevents unapproved tool calls, and detects masked execution failures.
  - `claim`: Compares numerical and currency claims in synthesized answers against verified analysis metrics and retrieved source documents to prevent hallucinated figures.
- **Bounded Dynamic Correction Loop**:
  - Automatically feeds validation feedback into the Response Agent on recoverable issues.
  - Hard limit of `MAX_VALIDATION_ATTEMPTS = 2` ensures termination with zero infinite loops.
- **Durable Database Persistence & Auditing**:
  - Alembic migration `004_workflow_validation.py` adds `validation_status` and `validation_score` columns to `workflow_runs`.
  - All validation attempts and issues stored in `metadata_json["validation"]`.
  - Validation steps tracked with timing and status in `workflow_steps`.
- **Enhanced Frontend UI**:
  - Milestone 5 badge and updated 6-node visual pipeline.
  - Dedicated Validation Guardrails inspection card displaying status badge, score percentage, passed checks count, duration, and structured issue tags.
  - Run detail modal with validation metrics and issue audit.
- **Comprehensive Test Suite**: **100 automated tests** passing across host environment and Docker backend.

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
