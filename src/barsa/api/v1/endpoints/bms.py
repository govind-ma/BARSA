"""BMS API endpoints (v1)."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from barsa.bms.base import BMS_FORMAT_IDENTIFIER, BMS_VERSION
from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.records import RECORD_TYPE_MAP
from barsa.bms.serialization import validate_package, validate_record
from barsa.models.bms_api import BMSValidationResponse, BMSVersionResponse

router = APIRouter(prefix="/bms", tags=["Barsa Memory Standard (BMS)"])


@router.get(
    "/version",
    response_model=BMSVersionResponse,
    summary="Get BMS specification version",
    description="Returns current supported BMS schema versions and registered record types.",
)
async def get_bms_version() -> BMSVersionResponse:
    """Return BMS version metadata."""
    return BMSVersionResponse(
        bms_version=BMS_VERSION,
        supported_versions=[BMS_VERSION],
        format_identifier=BMS_FORMAT_IDENTIFIER,
        supported_record_types=sorted(RECORD_TYPE_MAP.keys()),
    )


@router.get(
    "/schema/{record_type}",
    summary="Get JSON Schema for a BMS record type or package",
    description="Returns the formal JSON Schema for the requested record type or 'package'.",
)
async def get_bms_schema(record_type: str) -> dict[str, Any]:
    """Return JSON Schema for the specified record type or package."""
    req_type = record_type.lower()
    if req_type == "package":
        schema = BarsaMemoryPackage.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["title"] = f"BMS v{BMS_VERSION} BarsaMemoryPackage"
        return schema

    model_cls = RECORD_TYPE_MAP.get(req_type)
    if not model_cls:
        valid_types = sorted([*RECORD_TYPE_MAP.keys(), "package"])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown record type '{record_type}'. Supported types: {valid_types}",
        )

    schema = model_cls.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = f"BMS v{BMS_VERSION} {model_cls.__name__}"
    return schema


@router.post(
    "/validate/record",
    response_model=BMSValidationResponse,
    summary="Statelessly validate a BMS record",
    description="Validates a raw JSON BMS record against BMS v0.1 rules without persistence.",
)
async def validate_bms_record_endpoint(request: Request) -> JSONResponse:
    """Validate a single record payload."""
    try:
        body = await request.json()
    except Exception as err:  # noqa: BLE001
        res = BMSValidationResponse(
            valid=False,
            errors=[f"Invalid JSON body: {err}"],
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=res.model_dump())

    if not isinstance(body, dict):
        res = BMSValidationResponse(
            valid=False,
            errors=["Payload must be a JSON object"],
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=res.model_dump())

    is_valid, record, errors = validate_record(body)
    if not is_valid:
        res = BMSValidationResponse(
            valid=False,
            record_type=body.get("record_type"),
            record_id=body.get("id"),
            errors=errors,
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=res.model_dump())

    res = BMSValidationResponse(
        valid=True,
        record_type=getattr(record, "record_type", None),
        record_id=getattr(record, "id", None),
        errors=[],
        details={"schema_version": getattr(record, "schema_version", BMS_VERSION)},
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=res.model_dump())


@router.post(
    "/validate/package",
    response_model=BMSValidationResponse,
    summary="Statelessly validate a Barsa Memory Package",
    description="Validates a full BarsaMemoryPackage with referential checks without persistence.",
)
async def validate_bms_package_endpoint(request: Request) -> JSONResponse:
    """Validate a full package payload."""
    try:
        body = await request.json()
    except Exception as err:  # noqa: BLE001
        res = BMSValidationResponse(
            valid=False,
            errors=[f"Invalid JSON body: {err}"],
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=res.model_dump())

    if not isinstance(body, dict):
        res = BMSValidationResponse(
            valid=False,
            errors=["Package payload must be a JSON object"],
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=res.model_dump())

    is_valid, pkg, errors = validate_package(body)
    if not is_valid:
        res = BMSValidationResponse(
            valid=False,
            record_type="package",
            record_id=body.get("project", {}).get("id") if isinstance(body.get("project"), dict) else None,
            errors=errors,
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=res.model_dump())

    res = BMSValidationResponse(
        valid=True,
        record_type="package",
        record_id=pkg.project.id if pkg else None,
        errors=[],
        details={
            "workspace_id": pkg.workspace.id if pkg else None,
            "project_id": pkg.project.id if pkg else None,
            "record_counts": {
                "knowledge": len(pkg.records.knowledge),
                "decisions": len(pkg.records.decisions),
                "tasks": len(pkg.records.tasks),
                "agents": len(pkg.records.agents),
                "artifacts": len(pkg.records.artifacts),
                "checkpoints": len(pkg.records.checkpoints),
                "relationships": len(pkg.relationships),
                "commits": len(pkg.commits),
            }
            if pkg
            else {},
        },
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=res.model_dump())
