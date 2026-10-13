"""Main FastAPI application entrypoint for BARSA."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from barsa.api.deps import get_app_settings
from barsa.api.errors import register_error_handlers
from barsa.api.health import router as health_router
from barsa.api.v1.router import api_v1_router
from barsa.core.config import Settings, get_settings
from barsa.core.logging import get_logger, setup_logging

logger = get_logger("main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: sets up runtime resources and cleans up on shutdown."""
    settings = get_settings()
    setup_logging(settings)

    # Ensure local data directory is created for local-first operations
    data_dir = settings.ensure_data_dir()
    logger.info(
        "Starting %s v%s in %s mode (data_dir=%s, storage_provider=%s)",
        settings.app_name,
        settings.app_version,
        settings.environment.value,
        data_dir,
        settings.storage_provider.value,
    )

    yield

    logger.info("Shutting down %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI application factory."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        description="Universal AI Memory and Collaboration Infrastructure",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Secure local defaults: Disallow permissive wildcard CORS
    # Only allow explicit local origins (desktop clients, localhost development)
    allowed_origins = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Centralized error handlers
    register_error_handlers(app)

    # Allow custom settings injection
    if settings is not None:
        app.dependency_overrides[get_app_settings] = lambda: settings

    # Routes
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


# Application singleton for ASGI servers (e.g. uvicorn barsa.main:app)
app = create_app()
