"""Main FastAPI application entrypoint.

Initializes middleware, routing, lifecycle events, and application configuration.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes.analytics import router as analytics_router
from backend.app.api.routes.approvals import router as approvals_router
from backend.app.api.routes.documents import router as documents_router
from backend.app.api.routes.evaluation import router as evaluation_router
from backend.app.api.routes.health import router as health_router, get_readiness
from backend.app.api.routes.workflow import router as workflow_router
from backend.app.core.config import get_settings
from backend.app.core.logging import format_log_msg, get_logger, setup_logging
from backend.app.graph.checkpointer import close_checkpointer, init_checkpointer
from backend.app.services.database import check_database_connection, close_database_connection

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' environment...")

    # Preliminary database check with bounded retry for graceful boot synchronization
    db_status = {"status": "disconnected"}
    for attempt in range(1, 4):
        db_status = await check_database_connection()
        if db_status.get("status") == "connected":
            break
        if attempt < 3:
            logger.info(f"Database check attempt {attempt}/3 pending, retrying in 1s...")
            await asyncio.sleep(1.0)

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

    docs_enabled = settings.ENABLE_DOCS and settings.APP_ENV != "production" or settings.ENABLE_DOCS

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Portfolio-grade Multi-Agent AI Workflow Automation Platform powered by LangGraph and FastAPI.",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )

    # 1. Request correlation middleware & unhandled error barrier
    @app.middleware("http")
    async def request_correlation_middleware(request: Request, call_next):
        raw_id = request.headers.get("X-Request-ID")
        # Support UUID strings or generate standard uuid hex
        request_id = raw_id.strip() if raw_id and raw_id.strip() else uuid.uuid4().hex
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception as exc:
            response = await global_exception_handler(request, exc)
        response.headers["X-Request-ID"] = request_id
        return response

    # 2. Global unhandled exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
        logger.error(format_log_msg(f"Unhandled server exception: {exc}", req_id), exc_info=True)
        is_prod = settings.APP_ENV == "production"
        err_msg = "Internal Server Error" if is_prod else str(exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": err_msg,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": err_msg,
                    "request_id": req_id,
                },
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id},
        )

    # 3. Configure CORS with secure origin handling
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
    allow_credentials = "*" not in origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 4. Mount API v1 Routers
    api_v1_prefix = "/api/v1"
    app.include_router(health_router, prefix=api_v1_prefix)
    app.include_router(workflow_router, prefix=api_v1_prefix)
    app.include_router(documents_router, prefix=api_v1_prefix)
    app.include_router(analytics_router, prefix=api_v1_prefix)
    app.include_router(approvals_router, prefix=api_v1_prefix)
    app.include_router(evaluation_router, prefix=api_v1_prefix)

    # Root diagnostic and readiness endpoints
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "0.1.0",
            "status": "online",
            "docs": "/docs" if docs_enabled else "disabled in production",
        }

    @app.get("/live", tags=["Root"], include_in_schema=False)
    async def root_live():
        return {"status": "alive"}

    @app.get("/ready", tags=["Root"], include_in_schema=False)
    async def root_ready():
        return await get_readiness()

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
