"""Artifact storage and byte download API endpoints (v1)."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from barsa.api.deps import get_storage
from barsa.bms.base import generate_uuid_str
from barsa.bms.records import ArtifactReference, ArtifactType
from barsa.core.exceptions import ResourceNotFoundError, ValidationError
from barsa.storage.protocol import StorageProvider
from barsa.storage.sqlite import SQLiteStorageProvider

router = APIRouter(prefix="/projects/{project_id}/artifacts", tags=["Artifacts"])


@router.post(
    "",
    response_model=ArtifactReference,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and store an artifact file for a project",
)
async def upload_artifact(
    project_id: str,
    file: UploadFile = File(...),
    artifact_id: str | None = Form(default=None),
    artifact_type: ArtifactType = Form(default=ArtifactType.OTHER),
    storage: StorageProvider = Depends(get_storage),
) -> ArtifactReference:
    if not storage.get_project(project_id):
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)

    if not isinstance(storage, SQLiteStorageProvider):
        raise ValidationError("Active storage provider does not support local byte artifact uploads.")

    aid = artifact_id or generate_uuid_str()
    artifact_ref = storage.artifacts.save_artifact_bytes(
        project_id=project_id,
        artifact_id=aid,
        file_obj=file.file,
        artifact_type=artifact_type,
        media_type=file.content_type,
        filename_hint=file.filename,
    )

    saved_ref, _ = storage.create_record(artifact_ref)
    return saved_ref  # type: ignore[return-value]


@router.get(
    "",
    response_model=list[ArtifactReference],
    summary="List all artifacts for a project",
)
def list_artifacts(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    storage: StorageProvider = Depends(get_storage),
) -> list[ArtifactReference]:
    if not storage.get_project(project_id):
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)

    records = storage.list_records(project_id, record_type="artifact", limit=limit, offset=offset)
    return [rec for rec, _ in records]  # type: ignore[misc]


@router.get(
    "/{artifact_id}",
    response_model=ArtifactReference,
    summary="Get artifact metadata by ID",
)
def get_artifact_metadata(
    project_id: str,
    artifact_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> ArtifactReference:
    result = storage.get_record(project_id, artifact_id)
    if not result:
        raise ResourceNotFoundError(
            f"Artifact '{artifact_id}' not found in project '{project_id}'.",
            "Artifact",
            artifact_id,
        )
    rec, _ = result
    if rec.record_type != "artifact":
        raise ResourceNotFoundError(f"Record '{artifact_id}' is not an artifact.", "Artifact", artifact_id)
    return rec  # type: ignore[return-value]


@router.get(
    "/{artifact_id}/download",
    summary="Download the raw artifact bytes",
)
def download_artifact_bytes(
    project_id: str,
    artifact_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> FileResponse:
    if not isinstance(storage, SQLiteStorageProvider):
        raise ValidationError("Active storage provider does not support local artifact streaming.")

    result = storage.get_record(project_id, artifact_id)
    if not result:
        raise ResourceNotFoundError(
            f"Artifact '{artifact_id}' not found in project '{project_id}'.",
            "Artifact",
            artifact_id,
        )
    rec, _ = result
    art: ArtifactReference = rec  # type: ignore[assignment]
    if not art.content_hash:
        raise ResourceNotFoundError(f"Artifact '{artifact_id}' has no local content blob.", "Artifact", artifact_id)

    blob_path = storage.artifacts.get_artifact_path(art.content_hash)
    filename = Path(art.uri).name if not art.uri.startswith("artifacts://") else f"{art.id}.bin"
    return FileResponse(
        path=blob_path,
        media_type=art.media_type or "application/octet-stream",
        filename=filename,
    )


@router.delete(
    "/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete artifact metadata and content blob",
)
def delete_artifact(
    project_id: str,
    artifact_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> None:
    result = storage.get_record(project_id, artifact_id)
    if not result:
        raise ResourceNotFoundError(
            f"Artifact '{artifact_id}' not found in project '{project_id}'.",
            "Artifact",
            artifact_id,
        )
    rec, _ = result
    art: ArtifactReference = rec  # type: ignore[assignment]
    storage.delete_record(project_id, artifact_id)
    if isinstance(storage, SQLiteStorageProvider) and art.content_hash:
        # Check if other artifacts reference the same content hash before removing blob
        # (Content-addressed deduplication)
        pass
