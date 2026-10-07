"""Database service foundation for PostgreSQL.

Provides connection pooling and non-blocking connectivity health verification,
laying the groundwork for persistence in Milestone 2.
"""

from typing import Any, Dict, Optional
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

_engine: Optional[AsyncEngine] = None


def get_async_engine() -> AsyncEngine:
    """Create or return singleton SQLAlchemy async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        logger.info("Initializing async database engine")
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=(settings.LOG_LEVEL.upper() == "DEBUG"),
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )
    return _engine


async def check_database_connection() -> Dict[str, Any]:
    """Verify database connectivity.

    Returns:
        Dict with status ('connected' | 'disconnected') and optional details.
    """
    settings = get_settings()
    if not settings.DATABASE_URL:
        return {"status": "unconfigured", "details": "DATABASE_URL not set"}

    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "connected", "details": "Successfully connected to PostgreSQL"}
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        return {"status": "disconnected", "details": str(exc)}


async def close_database_connection() -> None:
    """Dispose of the database engine on application shutdown."""
    global _engine
    if _engine is not None:
        logger.info("Disposing database engine")
        await _engine.dispose()
        _engine = None
