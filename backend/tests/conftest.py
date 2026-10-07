"""Test configuration and shared fixtures."""

import os
import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import (
    close_database_connection,
    get_async_engine,
    get_db,
    get_session_factory,
)
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def reset_settings():
    """Ensure settings cache is refreshed for tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Ensure database schema is created once for the test session."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await close_database_connection()


@pytest.fixture
async def db_session():
    """Fixture providing an active AsyncSession connected to test database."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@pytest.fixture
def app():
    """Fixture for FastAPI app instance."""
    return create_app()


@pytest.fixture
async def async_client(app):
    """Fixture for async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
