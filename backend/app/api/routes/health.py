"""Health check API routes."""

from fastapi import APIRouter
from backend.app.core.config import get_settings
from backend.app.models.schemas import HealthResponse
from backend.app.services.database import check_database_connection

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Check service health and database connectivity status."""
    settings = get_settings()
    db_result = await check_database_connection()

    return HealthResponse(
        status="healthy",
        database=db_result.get("status", "disconnected"),
        app_env=settings.APP_ENV,
        version="0.1.0",
    )
