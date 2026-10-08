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

    # Document & Vector Retrieval Settings (Milestone 3)
    DOCUMENT_STORAGE_PATH: str = Field(default="./data/documents", description="Filesystem directory for uploaded documents")
    FAISS_INDEX_PATH: str = Field(default="./data/faiss", description="Filesystem directory for persisted FAISS index")
    EMBEDDING_PROVIDER: str = Field(default="mock", description="Embedding provider: mock, local, openai")
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model identifier")
    EMBEDDING_DIMENSION: int = Field(default=384, description="Embedding vector dimension")
    CHUNK_SIZE: int = Field(default=1000, description="Target chunk size in characters")
    CHUNK_OVERLAP: int = Field(default=150, description="Chunk overlap in characters")
    TOP_K_RETRIEVAL: int = Field(default=5, description="Number of top relevant chunks to retrieve")
    MAX_DOCUMENT_SIZE_MB: int = Field(default=25, description="Maximum allowed document upload size in megabytes")

    # Validation & Guardrails Settings (Milestone 5)
    VALIDATION_ENABLED: bool = Field(default=True, description="Enable workflow validation and guardrails layer")
    MAX_VALIDATION_ATTEMPTS: int = Field(default=2, ge=1, le=5, description="Maximum validation/correction attempts before terminating")
    VALIDATION_SCORE_THRESHOLD: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum validation score threshold to pass")

    # Human-in-the-Loop & Approval Settings (Milestone 6)
    APPROVAL_ENABLED: bool = Field(default=True, description="Enable human-in-the-loop approval gate")
    MAX_APPROVAL_REVISIONS: int = Field(default=3, ge=1, le=10, description="Maximum approval revision cycles before final rejection")

    # Production Hardening Settings (Milestone 8)
    ENABLE_DOCS: bool = Field(default=True, description="Enable FastAPI OpenAPI/Swagger documentation endpoints")
    LLM_TIMEOUT: float = Field(default=60.0, ge=5.0, le=300.0, description="HTTP request timeout for external LLM providers in seconds")
    WORKFLOW_TIMEOUT_SECONDS: float = Field(default=120.0, ge=10.0, le=600.0, description="Total workflow execution timeout in seconds")
    DB_POOL_TIMEOUT: float = Field(default=30.0, ge=1.0, le=120.0, description="Database connection pool checkout timeout in seconds")
    CHECKPOINTER_POOL_TIMEOUT: float = Field(default=10.0, ge=1.0, le=60.0, description="Checkpointer pool checkout timeout in seconds")

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
