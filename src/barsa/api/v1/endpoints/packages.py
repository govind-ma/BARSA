"""Packages export and import API endpoints (v1)."""

from typing import Any

from fastapi import APIRouter, Depends, Request, status

from barsa.api.deps import get_storage
from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.serialization import validate_package
from barsa.core.exceptions import ResourceNotFoundError, ValidationError
from barsa.storage.protocol import StorageProvider

router = APIRouter(prefix="/projects", tags=["Portable Packages"])


@router.post(
    "/import",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Import a Barsa Memory Package into local storage",
)
async def import_project_package(
    request: Request,
    storage: StorageProvider = Depends(get_storage),
) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception as err:
        raise ValidationError(f"Invalid JSON payload: {err}") from err

    is_valid, pkg, errors = validate_package(body)
    if not is_valid or not pkg:
        raise ValidationError(f"Package validation failed: {'; '.join(errors)}", details={"errors": errors})

    storage.save_package(pkg)

    return {
        "status": "imported",
        "workspace_id": pkg.workspace.id,
        "project_id": pkg.project.id,
        "record_counts": {
            "knowledge": len(pkg.records.knowledge),
            "decisions": len(pkg.records.decisions),
            "tasks": len(pkg.records.tasks),
            "agents": len(pkg.records.agents),
            "artifacts": len(pkg.records.artifacts),
            "checkpoints": len(pkg.records.checkpoints),
            "relationships": len(pkg.relationships),
        },
    }


@router.get(
    "/{project_id}/export",
    response_model=BarsaMemoryPackage,
    summary="Export a complete project as a Barsa Memory Package",
)
def export_project_package(
    project_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> BarsaMemoryPackage:
    pkg = storage.load_package(project_id)
    if not pkg:
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)
    return pkg
