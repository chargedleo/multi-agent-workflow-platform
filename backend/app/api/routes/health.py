"""Health and readiness check API routes."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from backend.app.core.config import get_settings
from backend.app.graph.checkpointer import is_checkpointer_healthy
from backend.app.models.schemas import HealthResponse, ReadinessResponse
from backend.app.services.database import check_database_connection

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness and basic health check",
    description="Returns the application liveness status, environment, and database connectivity.",
)
async def get_health() -> HealthResponse:
    """Check service health and database connectivity status."""
    settings = get_settings()
    db_result = await check_database_connection()
    db_status = db_result.get("status", "disconnected")

    service_status = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=service_status,
        database=db_status,
        app_env=settings.APP_ENV,
        version="0.1.0",
    )


@router.get(
    "/live",
    summary="Kubernetes/Docker liveness probe",
    description="Quickly confirms that the application process is running and accepting HTTP requests.",
)
async def get_liveness():
    """Lightweight process liveness endpoint."""
    return {"status": "alive"}


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "Service is fully ready to process workflow executions"},
        503: {"description": "Critical dependencies are unavailable (e.g. database unreachable)"},
    },
    summary="Kubernetes/Docker readiness probe",
    description="Verifies that all critical dependencies (PostgreSQL and LangGraph checkpointer) are available to serve workflow requests.",
)
async def get_readiness():
    """Comprehensive readiness endpoint verifying database and checkpointer connectivity."""
    settings = get_settings()
    db_result = await check_database_connection()
    if isinstance(db_result, dict):
        is_db_connected = db_result.get("status") == "connected"
    elif isinstance(db_result, (tuple, list)):
        is_db_connected = bool(db_result[0])
    else:
        is_db_connected = bool(db_result)
    is_cp_ready = await is_checkpointer_healthy()

    if is_db_connected:
        return ReadinessResponse(
            status="ready",
            database="connected",
            checkpointer="ready" if is_cp_ready else "degraded",
            app_env=settings.APP_ENV,
            version="0.1.0",
        )

    # Return 503 Service Unavailable when critical database dependency is down
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "not_ready",
            "database": "disconnected",
            "checkpointer": "degraded",
            "app_env": settings.APP_ENV,
            "version": "0.1.0",
        },
    )
