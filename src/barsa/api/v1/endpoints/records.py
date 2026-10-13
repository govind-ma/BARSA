"""BMS Record management API endpoints with optimistic concurrency (v1)."""

from fastapi import APIRouter, Depends, Query, Request, status

from barsa.api.deps import get_storage
from barsa.bms.serialization import deserialize_record
from barsa.core.exceptions import ResourceNotFoundError, ValidationError
from barsa.models.storage_api import RecordEnvelope, RecordUpdateRequest
from barsa.storage.protocol import StorageProvider

router = APIRouter(prefix="/projects/{project_id}/records", tags=["Memory Records"])


@router.post(
    "",
    response_model=RecordEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new BMS record in a project",
)
async def create_record(
    project_id: str,
    request: Request,
    storage: StorageProvider = Depends(get_storage),
) -> RecordEnvelope:
    try:
        body = await request.json()
    except Exception as err:
        raise ValidationError(f"Invalid JSON payload: {err}") from err

    if not isinstance(body, dict):
        raise ValidationError("Record payload must be a JSON object")

    # Enforce project_id match
    body["project_id"] = project_id
    record = deserialize_record(body)
    saved_record, revision = storage.create_record(record)

    return RecordEnvelope(
        record=saved_record.model_dump(mode="json"),
        revision=revision,
        project_id=project_id,
        record_id=saved_record.id,
        record_type=saved_record.record_type,
    )


@router.get(
    "",
    response_model=list[RecordEnvelope],
    summary="List records in a project with optional type filter",
)
def list_records(
    project_id: str,
    record_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    storage: StorageProvider = Depends(get_storage),
) -> list[RecordEnvelope]:
    if not storage.get_project(project_id):
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)

    records = storage.list_records(project_id, record_type=record_type, limit=limit, offset=offset)
    return [
        RecordEnvelope(
            record=rec.model_dump(mode="json"),
            revision=rev,
            project_id=project_id,
            record_id=rec.id,
            record_type=rec.record_type,
        )
        for rec, rev in records
    ]


@router.get(
    "/{record_id}",
    response_model=RecordEnvelope,
    summary="Get a specific BMS record by ID",
)
def get_record(
    project_id: str,
    record_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> RecordEnvelope:
    result = storage.get_record(project_id, record_id)
    if not result:
        raise ResourceNotFoundError(f"Record '{record_id}' not found in project '{project_id}'.", "Record", record_id)
    rec, rev = result
    return RecordEnvelope(
        record=rec.model_dump(mode="json"),
        revision=rev,
        project_id=project_id,
        record_id=rec.id,
        record_type=rec.record_type,
    )


@router.put(
    "/{record_id}",
    response_model=RecordEnvelope,
    summary="Update a BMS record with optimistic concurrency revision check",
)
def update_record(
    project_id: str,
    record_id: str,
    req: RecordUpdateRequest,
    storage: StorageProvider = Depends(get_storage),
) -> RecordEnvelope:
    raw_data = req.record
    raw_data["id"] = record_id
    raw_data["project_id"] = project_id

    record = deserialize_record(raw_data)
    updated_rec, new_rev = storage.update_record(record, expected_revision=req.expected_revision)

    return RecordEnvelope(
        record=updated_rec.model_dump(mode="json"),
        revision=new_rev,
        project_id=project_id,
        record_id=updated_rec.id,
        record_type=updated_rec.record_type,
    )


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a BMS record with optional expected revision check",
)
def delete_record(
    project_id: str,
    record_id: str,
    expected_revision: int | None = Query(default=None),
    storage: StorageProvider = Depends(get_storage),
) -> None:
    deleted = storage.delete_record(project_id, record_id, expected_revision=expected_revision)
    if not deleted:
        raise ResourceNotFoundError(f"Record '{record_id}' not found in project '{project_id}'.", "Record", record_id)
