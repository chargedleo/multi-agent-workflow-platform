"""Production hardening tests for Milestone 8.

Tests cover:
- Liveness probes (/api/v1/health/live, /live)
- Readiness probes (/api/v1/health/ready, /ready) and HTTP 503 on database disconnection
- Degraded status in /api/v1/health when database is unreachable
- Request correlation ID (X-Request-ID generation and propagation)
- Sensitive credential and log sanitization
- LangGraph checkpointer lifecycle and idempotency
- Production exception masking and headers
- Hardened timeout configuration defaults
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.core.config import get_settings
from backend.app.core.logging import sanitize_log_msg, format_log_msg
from backend.app.graph.checkpointer import is_checkpointer_healthy, close_checkpointer


@pytest.mark.asyncio
async def test_liveness_probes(async_client: AsyncClient):
    """Verify both /api/v1/health/live and /live return HTTP 200 with 'alive' status."""
    res1 = await async_client.get("/api/v1/health/live")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "alive"

    res2 = await async_client.get("/live")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_probe_healthy(async_client: AsyncClient):
    """Verify /api/v1/health/ready and /ready return HTTP 200 when database is connected."""
    res1 = await async_client.get("/api/v1/health/ready")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "ready"
    assert data1["database"] == "connected"
    assert "checkpointer" in data1
    assert "version" in data1

    res2 = await async_client.get("/ready")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "ready"
    assert data2["database"] == "connected"


@pytest.mark.asyncio
async def test_readiness_probe_unhealthy_returns_503(async_client: AsyncClient, monkeypatch):
    """Verify readiness probes return HTTP 503 when the database connection fails."""
    async def mock_check_db():
        return {"status": "disconnected", "details": "Simulated database connection failure"}

    monkeypatch.setattr("backend.app.api.routes.health.check_database_connection", mock_check_db)

    # Readiness probe must return 503 Service Unavailable
    res_ready = await async_client.get("/api/v1/health/ready")
    assert res_ready.status_code == 503
    data_ready = res_ready.json()
    assert data_ready["status"] == "not_ready"
    assert data_ready["database"] == "disconnected"

    # Convenience alias /ready must also return 503
    res_ready_alias = await async_client.get("/ready")
    assert res_ready_alias.status_code == 503
    assert res_ready_alias.json()["status"] == "not_ready"

    # General /health should report degraded status
    res_health = await async_client.get("/api/v1/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "degraded"
    assert data_health["database"] == "disconnected"


@pytest.mark.asyncio
async def test_request_id_correlation_generated(async_client: AsyncClient):
    """Verify that requests without X-Request-ID receive an auto-generated UUID in headers."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    req_id = response.headers["x-request-id"]
    # Ensure it is a valid UUID
    parsed = uuid.UUID(req_id)
    assert parsed.hex == req_id or str(parsed) == req_id


@pytest.mark.asyncio
async def test_request_id_correlation_propagated(async_client: AsyncClient):
    """Verify that incoming X-Request-ID is preserved and returned in response headers."""
    custom_id = "trace-correlation-id-998877"
    response = await async_client.get(
        "/api/v1/health",
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


def test_log_sanitization():
    """Verify that sensitive tokens, passwords, and connection strings are masked in logs."""
    test_cases = [
        ("postgresql+asyncpg://admin:SecretPass123!@db.host.internal:5432/proddb",
         "postgresql+asyncpg://admin:***@db.host.internal:5432/proddb"),
        ("Error with password=MySuperSecretPassword and user=bob",
         "Error with password=*** and user=bob"),
        ("Authorization header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz",
         "Authorization header: Bearer ***"),
        ("OpenAI request key: sk-abcdef1234567890abcdef1234567890",
         "OpenAI request key: sk-***"),
        ("Auth token=ghp_ABC123secretToken",
         "Auth token=***"),
    ]

    for raw, expected in test_cases:
        sanitized = sanitize_log_msg(raw)
        assert sanitized == expected, f"Failed for raw input: {raw}"

    # Verify format_log_msg applies sanitization and context tags
    formatted = format_log_msg("DB conn: postgresql://u:p@h:5432/d", req_id="r1", run_id="run1")
    assert "[req:r1]" in formatted
    assert "[run:run1]" in formatted
    assert "postgresql://u:***@h:5432/d" in formatted


@pytest.mark.asyncio
async def test_checkpointer_lifecycle():
    """Verify checkpointer health check and idempotent closure."""
    healthy = await is_checkpointer_healthy()
    assert isinstance(healthy, bool)

    await close_checkpointer()
    await close_checkpointer()


@pytest.mark.asyncio
async def test_production_exception_handler_masking():
    """Verify that in production mode, unhandled 500 exceptions mask sensitive internals."""
    from backend.app.main import create_app

    prod_app = create_app()

    @prod_app.get("/test-internal-error")
    async def faulty_route():
        raise RuntimeError("DATABASE_PASSWORD=Secret123 internal failure details")

    transport = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # In test mode
        res_test = await client.get("/test-internal-error")
        assert res_test.status_code == 500
        assert "x-request-id" in res_test.headers

        # In production mode
        settings = get_settings()
        old_env = settings.APP_ENV
        try:
            settings.APP_ENV = "production"
            res_prod = await client.get("/test-internal-error")
            assert res_prod.status_code == 500
            data_prod = res_prod.json()
            assert data_prod.get("detail") == "Internal Server Error"
            assert "DATABASE_PASSWORD" not in str(data_prod)
            assert "x-request-id" in res_prod.headers
            assert data_prod.get("request_id") == res_prod.headers["x-request-id"]
        finally:
            settings.APP_ENV = old_env


def test_hardening_config_defaults():
    """Verify that Milestone 8 production configuration parameters are present and valid."""
    settings = get_settings()
    assert hasattr(settings, "LLM_TIMEOUT")
    assert settings.LLM_TIMEOUT >= 5
    assert hasattr(settings, "WORKFLOW_TIMEOUT_SECONDS")
    assert settings.WORKFLOW_TIMEOUT_SECONDS >= 10
    assert hasattr(settings, "DB_POOL_TIMEOUT")
    assert settings.DB_POOL_TIMEOUT >= 5
    assert hasattr(settings, "CHECKPOINTER_POOL_TIMEOUT")
    assert settings.CHECKPOINTER_POOL_TIMEOUT >= 5
    assert hasattr(settings, "ENABLE_DOCS")
    assert isinstance(settings.ENABLE_DOCS, bool)
