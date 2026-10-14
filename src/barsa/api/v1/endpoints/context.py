"""FastAPI endpoints for the Barsa Smart Context Engine (Phase 8)."""

import logging

from fastapi import APIRouter, Depends, Path

from barsa.api.deps import get_context_engine
from barsa.context.engine import SmartContextEngine
from barsa.context.models import (
    BarsaContextPackage,
    ContextEstimateResponse,
    ContextRequest,
    ContextStatusResponse,
)

logger = logging.getLogger("barsa.api.v1.context")

router = APIRouter(tags=["Context Engine"])


@router.post(
    "/context/build",
    response_model=BarsaContextPackage,
    summary="Build an optimized, token-budgeted context package",
)
def build_context_package(
    request: ContextRequest,
    engine: SmartContextEngine = Depends(get_context_engine),
) -> BarsaContextPackage:
    """Build a validated, token-budgeted, graph-aware context package for AI agent task continuation."""
    return engine.build_context(request)


@router.post(
    "/context/estimate",
    response_model=ContextEstimateResponse,
    summary="Estimate context token usage and budget feasibility",
)
def estimate_context_tokens(
    request: ContextRequest,
    engine: SmartContextEngine = Depends(get_context_engine),
) -> ContextEstimateResponse:
    """Estimate token consumption without committing changes or returning complete context."""
    return engine.estimate_tokens(request)


@router.get(
    "/projects/{project_id}/context/status",
    response_model=ContextStatusResponse,
    summary="Check project context readiness and graph projection freshness",
)
def get_project_context_status(
    project_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-\.]{1,128}$"),
    engine: SmartContextEngine = Depends(get_context_engine),
) -> ContextStatusResponse:
    """Report authoritative commit, graph projection freshness, and active record counts."""
    return engine.get_context_status(project_id)
