# Deployment and Operations Guide — Multi-Agent AI Workflow Automation Platform

This document describes deployment, configuration, operational procedures, health monitoring, and troubleshooting for the **Multi-Agent AI Workflow Automation Platform** (Milestone 8 — Production Hardening).

---

## 1. Prerequisites

### Containerized Environment (Recommended)
- **Docker**: Engine version 24.0+ (or compatible Docker Desktop)
- **Docker Compose**: v2.20+
- **Host Resources**: Minimum 2 CPU cores, 4 GB RAM, 10 GB disk space

### Local Developer Environment
- **Python**: 3.11+ (tested with 3.11.17 AMD64)
- **Node.js**: v20+ with `npm`
- **PostgreSQL**: 16+ running locally or in Docker
- **C++ Runtime / OpenMP**: `libgomp1` (Linux) or MSVC redistributable (Windows) for native FAISS

---

## 2. Configuration & Environment Variables

All configuration is loaded through Pydantic Settings in `backend/app/core/config.py`.
Defaults are configured for safe local development (`APP_ENV=development`, `LLM_PROVIDER=mock`).

### Environment Variables Reference

| Variable | Default | Purpose | Production Recommendation |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | `Multi-Agent AI Workflow Platform` | Application title | Custom organization name |
| `APP_ENV` | `development` | Operating environment (`development`, `production`, `test`) | Set to `production` |
| `API_HOST` | `0.0.0.0` | Backend bind host | `0.0.0.0` inside container |
| `API_PORT` | `8000` | Backend bind port | `8000` |
| `ENABLE_DOCS` | `false` in prod, `true` in dev | Exposes `/docs` and `/redoc` Swagger UI | `false` in production |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_db` | Async PostgreSQL connection string | Use secret manager / vault |
| `DB_POOL_SIZE` | `10` | SQLAlchemy async connection pool size | `20` - `50` depending on traffic |
| `DB_MAX_OVERFLOW` | `20` | Maximum surge connections in pool | `10` - `30` |
| `DB_POOL_TIMEOUT` | `30` | Connection pool acquisition timeout (seconds) | `30` |
| `CHECKPOINTER_POOL_TIMEOUT`| `30` | LangGraph checkpointer connection timeout (seconds)| `30` |
| `LLM_PROVIDER` | `mock` | LLM driver: `mock`, `openai`, `gemini`, `anthropic` | `openai` or enterprise provider |
| `LLM_MODEL` | `gpt-4o-mini` | Model identifier | `gpt-4o-mini` or `gpt-4o` |
| `LLM_API_KEY` | *(empty)* | API key for LLM provider | Set via secret manager |
| `LLM_TIMEOUT` | `60` | HTTP timeout for external LLM requests (seconds) | `60` |
| `WORKFLOW_TIMEOUT_SECONDS` | `180` | LangGraph complete workflow execution timeout | `180` |
| `APPROVAL_ENABLED`| `true` | Enforces Human-in-the-Loop review gates | `true` |
| `MAX_APPROVAL_REVISIONS` | `3` | Bounded iteration limit for human revision loops | `3` |
| `VALIDATION_ENABLED` | `true` | Enables deterministic guardrails and schema validation | `true` |
| `EMBEDDING_PROVIDER` | `mock` | Vector embedding driver (`mock`, `openai`) | `mock` or `openai` |
| `DOCUMENT_STORAGE_PATH` | `./data/documents` | Directory for uploaded documents | Mounted durable volume |
| `FAISS_INDEX_PATH` | `./data/faiss` | Directory for persistent vector indices | Mounted durable volume |
| `LOG_LEVEL` | `INFO` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins (comma-separated or list) | Explicit trusted production domains |

---

## 3. Secrets Hygiene & Sanitization

1. **Zero Secret Persistence**: Never commit `.env` files or API credentials into source control. Always copy `.env.example` to `.env`.
2. **Log Masking**: The platform includes automated log sanitization (`backend/app/core/logging.py`) that redacts:
   - Database passwords: `postgresql://user:***@host:5432/db`
   - Bearer authentication tokens: `Bearer ***`
   - API keys and tokens: `token=***`, `api_key=***`
   - OpenAI API keys: `sk-***`
3. **Production Exception Masking**: In `APP_ENV=production`, internal exceptions return sanitized JSON (`"Internal Server Error"`) with an attached correlation `X-Request-ID`. Stack traces and internal database schemas are never exposed in production HTTP responses.

---

## 4. Health, Liveness & Readiness Probes

The service implements distinct liveness and readiness probes designed for Kubernetes, Docker Compose, and load balancers:

```mermaid
flowchart LR
    LB["Load Balancer / Ingress"]
    Orch["Docker / Kubernetes Orchestrator"]
    
    subgraph App ["FastAPI Application"]
        Live["GET /api/v1/health/live\n(Liveness Probe)"]
        Ready["GET /api/v1/health/ready\n(Readiness Probe)"]
    end
    
    subgraph Deps ["Dependencies"]
        PG[("PostgreSQL 16")]
        CP[("AsyncPostgresSaver Checkpointer")]
    end
    
    Orch -->|Process Alive?| Live
    Live -->|HTTP 200| Orch
    
    LB -->|Ready for Traffic?| Ready
    Ready -->|Ping| PG
    Ready -->|Check| CP
    PG -->|Connected| Ready
    CP -->|Ready| Ready
    Ready -->|HTTP 200 (Ready)\nHTTP 503 (Unavailable)| LB
```

### Endpoints Summary

| Endpoint | Type | Purpose | Success (200) | Failure (503) |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/health/live` (or `/live`) | Liveness | Verifies ASGI event loop is responsive | `{"status": "alive"}` | N/A (Process hung) |
| `GET /api/v1/health/ready` (or `/ready`) | Readiness | Verifies DB and LangGraph checkpointer | `{"status": "ready", "database": "connected"}` | `{"status": "not_ready", "database": "disconnected"}` |
| `GET /api/v1/health` | Diagnostic | Service health report | `{"status": "healthy"}` | `{"status": "degraded"}` |

### HTTP Correlation (`X-Request-ID`)
Every incoming request receives or generates a unique correlation ID:
- If provided by the client: `X-Request-ID: <client-uuid>` is preserved and forwarded.
- If omitted: an auto-generated UUID is assigned.
- The `X-Request-ID` is included in all log entries (`[req:<id>]`) and returned in the HTTP response headers.

---

## 5. Startup & Shutdown Lifecycle

### Startup Sequence (`lifespan` in `backend/app/main.py`)
1. Configure structured logging with sensitive pattern masking.
2. Initialize database connection pool with pre-ping validation (`pool_pre_ping=True`).
3. Execute bounded retry check (up to 3 attempts with exponential backoff) to synchronize with PostgreSQL boot.
4. Execute Alembic schema migrations (`alembic upgrade head`).
5. Initialize the `AsyncPostgresSaver` connection pool and create LangGraph checkpoint tables.

### Shutdown Sequence
1. Gracefully close LangGraph checkpointer pool (`close_checkpointer()`).
2. Dispose SQLAlchemy async engine connection pool (`close_database_connection()`).
3. Flush application log streams.

---

## 6. Docker Deployment

### Launching the Complete Platform
To build and start all containers in detached mode:
```bash
docker compose up --build -d
```

### Inspecting Running Services
```bash
docker compose ps
```
Expected output:
```text
NAME                IMAGE                                 STATUS                    PORTS
workflow_backend    ...-backend                          Up (healthy)              0.0.0.0:8000->8000/tcp
workflow_frontend   ...-frontend                         Up                        0.0.0.0:5173->80/tcp
workflow_postgres   postgres:16-alpine                   Up (healthy)              0.0.0.0:5432->5432/tcp
```

### Verifying Service Readiness
```bash
curl -i http://localhost:8000/api/v1/health/ready
```
Returns:
```http
HTTP/1.1 200 OK
content-type: application/json
x-request-id: <uuid>

{"status":"ready","database":"connected","checkpointer":"ready","app_env":"development","version":"0.1.0"}
```

---

## 7. Container Restart & State Persistence Verification

The platform is designed for zero data loss across container restarts.

### Restart Test
```bash
# Restart backend container
docker restart workflow_backend

# Wait 5-10 seconds for migration check and pool initialization
curl -i http://localhost:8000/api/v1/health/ready
```

### Verifying Persistent State
After restart, query existing workflow runs or document indexes:
```bash
curl http://localhost:8000/api/v1/workflows/<run_id>
```
Workflow runs, intermediate steps, approval decisions, and checkpoints will be fully intact from PostgreSQL volumes (`workflow_postgres_data`).

---

## 8. Database Migrations

Database migrations are managed via **Alembic**.

### Running Migrations Automatically
In Docker, migrations run automatically on container startup before Uvicorn binds to port 8000:
```dockerfile
CMD ["sh", "-c", "alembic -c /app/backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
```

### Running Migrations Manually
```bash
# Inside Docker backend container
docker exec -it workflow_backend alembic -c /app/backend/alembic.ini upgrade head

# On host machine
cd backend
alembic upgrade head
```

---

## 9. Troubleshooting Runbook

### Issue: Backend returns HTTP 503 on `/api/v1/health/ready`
- **Root Cause**: PostgreSQL is unreachable or still initializing.
- **Diagnosis**:
  ```bash
  docker logs workflow_postgres --tail 50
  docker logs workflow_backend --tail 50
  ```
- **Remediation**: Check that `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` match between `.env` and `DATABASE_URL`. Ensure PostgreSQL healthcheck passes (`pg_isready`).

### Issue: Workflow execution times out
- **Root Cause**: Heavy analytical query or slow external LLM response exceeded `WORKFLOW_TIMEOUT_SECONDS` (default: 180s) or `LLM_TIMEOUT` (default: 60s).
- **Diagnosis**: Look for log entry `Workflow execution timed out after 180s [req:<req_id>]`.
- **Remediation**: Increase `WORKFLOW_TIMEOUT_SECONDS` or `LLM_TIMEOUT` in `.env` for large documents/workloads.

### Issue: CORS error in browser
- **Root Cause**: Frontend origin is not allowed in `CORS_ORIGINS`.
- **Diagnosis**: Inspect browser network console for missing `Access-Control-Allow-Origin` header.
- **Remediation**: Add the client domain/port to `CORS_ORIGINS` in `.env` (e.g. `http://localhost:5173,http://yourdomain.com`).
