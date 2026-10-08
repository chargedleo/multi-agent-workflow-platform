"""Database session management with SQLAlchemy 2.x async engine."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine() -> AsyncEngine:
    """Create or return application-scoped singleton SQLAlchemy async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        logger.info(f"Initializing async database engine for: {settings.DATABASE_URL.split('@')[-1]}")
        engine_kwargs: Dict[str, Any] = {
            "echo": (settings.LOG_LEVEL.upper() == "DEBUG"),
        }
        if settings.APP_ENV == "test":
            from sqlalchemy.pool import NullPool
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
            engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
            engine_kwargs["pool_pre_ping"] = True
            engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT

        _engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_kwargs,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create or return sessionmaker factory."""
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_async_engine()
        _sessionmaker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an AsyncSession."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for short-lived database transactions outside request handlers."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


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
        details = "Database connection unavailable" if settings.APP_ENV == "production" else str(exc)
        return {"status": "disconnected", "details": details}


async def close_database_connection() -> None:
    """Dispose of the database engine on application shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        logger.info("Disposing database engine")
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
