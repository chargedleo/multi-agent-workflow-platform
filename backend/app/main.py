"""Main FastAPI application entrypoint.

Initializes middleware, routing, lifecycle events, and application configuration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.analytics import router as analytics_router
from backend.app.api.routes.approvals import router as approvals_router
from backend.app.api.routes.documents import router as documents_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.workflow import router as workflow_router
from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger, setup_logging
from backend.app.graph.checkpointer import close_checkpointer, init_checkpointer
from backend.app.services.database import check_database_connection, close_database_connection

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' environment...")

    # Preliminary database check
    db_status = await check_database_connection()
    logger.info(f"Initial database status: {db_status['status']} ({db_status.get('details', '')})")

    # Initialize durable checkpointer for human-in-the-loop workflows
    try:
        await init_checkpointer()
    except Exception as exc:
        logger.warning(f"Checkpointer initialization warning: {exc}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_checkpointer()
    await close_database_connection()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    """Application factory for FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Portfolio-grade Multi-Agent AI Workflow Automation Platform powered by LangGraph and FastAPI.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 Routers
    api_v1_prefix = "/api/v1"
    app.include_router(health_router, prefix=api_v1_prefix)
    app.include_router(workflow_router, prefix=api_v1_prefix)
    app.include_router(documents_router, prefix=api_v1_prefix)
    app.include_router(analytics_router, prefix=api_v1_prefix)
    app.include_router(approvals_router, prefix=api_v1_prefix)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "0.1.0",
            "status": "online",
            "docs": "/docs",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=(settings.APP_ENV == "development"),
    )
