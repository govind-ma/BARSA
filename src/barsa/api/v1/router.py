"""API v1 router composition."""

from fastapi import APIRouter

from barsa.api.v1.endpoints.bms import router as bms_router
from barsa.api.v1.endpoints.info import router as info_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(info_router)
api_v1_router.include_router(bms_router)
