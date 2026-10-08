"""Durable LangGraph Checkpointer Manager for Human-in-the-Loop Approval.

Provides PostgreSQL checkpoint persistence using AsyncPostgresSaver and AsyncConnectionPool,
with transparent fallback to MemorySaver for unit testing and local environments.
"""

import asyncio
import sys
from typing import Any, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from backend.app.core.config import get_settings
from backend.app.core.logging import format_log_msg, get_logger

logger = get_logger(__name__)

# Ensure Windows Proactor event loop compatibility for psycopg async
if sys.platform == "win32":
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

_global_checkpointer: Optional[BaseCheckpointSaver] = None
_global_pool: Any = None


def _format_postgres_conn_string(db_url: str) -> str:
    """Normalize SQLAlchemy async connection strings to standard psycopg connection strings."""
    if "postgresql+asyncpg://" in db_url:
        return db_url.replace("postgresql+asyncpg://", "postgresql://")
    if "postgresql+psycopg://" in db_url:
        return db_url.replace("postgresql+psycopg://", "postgresql://")
    return db_url


async def init_checkpointer() -> BaseCheckpointSaver:
    """Initialize and setup the durable checkpointer (PostgreSQL or fallback)."""
    global _global_checkpointer, _global_pool

    if _global_checkpointer is not None and _global_pool is not None:
        return _global_checkpointer

    settings = get_settings()
    db_url = settings.DATABASE_URL

    if "postgresql" in db_url:
        try:
            from psycopg_pool import AsyncConnectionPool
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            conn_str = _format_postgres_conn_string(db_url)
            logger.info("Initializing AsyncPostgresSaver checkpointer connection pool...")
            _global_pool = AsyncConnectionPool(
                conn_str,
                max_size=settings.DB_POOL_SIZE or 5,
                open=False,
                kwargs={"autocommit": True},
            )
            await _global_pool.open()
            saver = AsyncPostgresSaver(_global_pool)
            await saver.setup()
            _global_checkpointer = saver
            logger.info("AsyncPostgresSaver initialized and migration tables verified.")
            return _global_checkpointer
        except Exception as exc:
            logger.warning(
                format_log_msg(
                    f"Could not initialize AsyncPostgresSaver, falling back to MemorySaver: {exc}",
                    "checkpointer",
                )
            )

    logger.info("Using MemorySaver checkpointer.")
    _global_checkpointer = MemorySaver()
    return _global_checkpointer


def get_checkpointer() -> BaseCheckpointSaver:
    """Return the active checkpointer instance, defaulting to MemorySaver if uninitialized."""
    global _global_checkpointer
    if _global_checkpointer is None:
        _global_checkpointer = MemorySaver()
    return _global_checkpointer


def set_checkpointer(checkpointer: Optional[BaseCheckpointSaver]) -> None:
    """Explicitly set or reset the active checkpointer (useful for testing)."""
    global _global_checkpointer
    _global_checkpointer = checkpointer


async def close_checkpointer() -> None:
    """Gracefully close active connection pool upon application shutdown."""
    global _global_checkpointer, _global_pool
    if _global_pool is not None:
        try:
            await _global_pool.close()
            logger.info("Checkpointer connection pool closed.")
        except Exception as exc:
            logger.warning(f"Error closing checkpointer connection pool: {exc}")
        finally:
            _global_pool = None
    _global_checkpointer = None
