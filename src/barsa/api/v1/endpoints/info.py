"""Platform informational endpoints (v1)."""

from fastapi import APIRouter, Depends

from barsa.api.deps import get_app_settings
from barsa.core.config import Settings
from barsa.models.api import PlatformFeatures, PlatformInfoResponse

router = APIRouter(prefix="/info", tags=["Platform Info"])


@router.get(
    "",
    response_model=PlatformInfoResponse,
    summary="Get platform information",
    description="Returns current Barsa platform configuration, environment, and feature flags.",
)
async def get_platform_info(
    settings: Settings = Depends(get_app_settings),
) -> PlatformInfoResponse:
    """Return platform metadata and supported feature matrix."""
    return PlatformInfoResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        description="Universal AI Memory and Collaboration Infrastructure",
        current_phase="Phase 1: Project Foundation",
        storage_provider=settings.storage_provider.value,
        data_dir=str(settings.data_dir),
        features=PlatformFeatures(
            bms_standard=True,
            local_storage=True,
            cloud_storage_adapters=False,
            git_versioning=False,
            falkordb_graph=False,
            smart_context_engine=False,
            agent_coordinator=False,
            mcp_server=False,
        ),
        documentation_url="/docs",
        metadata={
            "environment": settings.environment.value,
            "debug": settings.debug,
            "log_level": settings.log_level,
        },
    )
