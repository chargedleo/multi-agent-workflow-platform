"""Configuration module for Multi-Agent AI Workflow Automation Platform.

Uses Pydantic Settings to load and validate application configuration
from environment variables and .env files.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    # Application settings
    APP_NAME: str = Field(default="Multi-Agent AI Workflow Platform", description="Application name")
    APP_ENV: str = Field(default="development", description="Environment: development, test, production")
    API_HOST: str = Field(default="0.0.0.0", description="API server host")
    API_PORT: int = Field(default=8000, description="API server port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")

    # CORS Origins
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
        description="Allowed CORS origins",
    )

    # LLM Settings
    LLM_PROVIDER: str = Field(
        default="mock",
        description="LLM Provider: openai, azure, ollama, mock",
    )
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="Model identifier")
    LLM_API_KEY: Optional[str] = Field(default=None, description="API key for the LLM provider")
    LLM_BASE_URL: Optional[str] = Field(default=None, description="Custom base URL for OpenAI-compatible APIs")
    LLM_TEMPERATURE: float = Field(default=0.2, description="LLM sampling temperature")

    # Database Settings (PostgreSQL foundation)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_db",
        description="PostgreSQL async connection string",
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database max connection overflow")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated string into a list of origins if necessary."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache()
def get_settings() -> Settings:
    """Return cached instance of application settings."""
    return Settings()
