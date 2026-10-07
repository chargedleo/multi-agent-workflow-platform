"""Tests for configuration layer and environment settings."""

import pytest
from backend.app.core.config import Settings


def test_default_configuration():
    """Verify default configuration attributes load with valid values."""
    settings = Settings(
        APP_NAME="Test Platform",
        APP_ENV="test",
        LLM_PROVIDER="mock",
    )
    assert settings.APP_NAME == "Test Platform"
    assert settings.APP_ENV == "test"
    assert settings.LLM_PROVIDER == "mock"
    assert settings.API_PORT == 8000
    assert "postgresql+asyncpg" in settings.DATABASE_URL


def test_cors_origins_parsing():
    """Verify comma-separated string for CORS is parsed into a list."""
    settings = Settings(
        CORS_ORIGINS="http://localhost:3000, http://example.com ,https://app.domain.com",
    )
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) == 3
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://example.com" in settings.CORS_ORIGINS
    assert "https://app.domain.com" in settings.CORS_ORIGINS


def test_cors_origins_as_list():
    """Verify CORS origins passed as a list remain intact."""
    origins = ["http://localhost:5173", "http://localhost:8080"]
    settings = Settings(CORS_ORIGINS=origins)
    assert settings.CORS_ORIGINS == origins
