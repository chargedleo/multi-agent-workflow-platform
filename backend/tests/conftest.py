"""Test configuration and shared fixtures."""

import os
import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set environment before any app imports
os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"

from backend.app.core.config import get_settings
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def reset_settings():
    """Ensure settings cache is refreshed for tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
