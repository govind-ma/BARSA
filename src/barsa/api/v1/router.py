"""API v1 router composition."""

from fastapi import APIRouter

from barsa.api.v1.endpoints.artifacts import router as artifacts_router
from barsa.api.v1.endpoints.bms import router as bms_router
from barsa.api.v1.endpoints.context import router as context_router
from barsa.api.v1.endpoints.coordination import router as coordination_router
from barsa.api.v1.endpoints.graph import router as graph_router
from barsa.api.v1.endpoints.info import router as info_router
from barsa.api.v1.endpoints.packages import router as packages_router
from barsa.api.v1.endpoints.records import router as records_router
from barsa.api.v1.endpoints.security import router as security_router
from barsa.api.v1.endpoints.versioning import router as versioning_router
from barsa.api.v1.endpoints.workspaces import router as workspaces_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(info_router)
api_v1_router.include_router(bms_router)
api_v1_router.include_router(workspaces_router)
api_v1_router.include_router(records_router)
api_v1_router.include_router(versioning_router)
api_v1_router.include_router(graph_router)
api_v1_router.include_router(artifacts_router)
api_v1_router.include_router(packages_router)
api_v1_router.include_router(context_router)
api_v1_router.include_router(coordination_router)
api_v1_router.include_router(security_router)
