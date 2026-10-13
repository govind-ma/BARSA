"""Health check router."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from barsa.api.deps import get_app_settings
from barsa.core.config import Settings
from barsa.models.api import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the health status, application name, and version.",
)
async def health_check(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Return runtime service health."""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment.value,
        timestamp=datetime.now(UTC),
    )
