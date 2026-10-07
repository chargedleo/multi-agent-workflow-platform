"""Database service proxy preserving Milestone 1 backwards compatibility.

Delegates engine and connectivity management to the unified backend.app.db.session module.
"""

from backend.app.db.session import (
    check_database_connection,
    close_database_connection,
    get_async_engine,
    get_db,
    get_db_context,
    get_session_factory,
)

__all__ = [
    "get_async_engine",
    "get_session_factory",
    "get_db",
    "get_db_context",
    "check_database_connection",
    "close_database_connection",
]
