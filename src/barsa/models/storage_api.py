"""API request/response schemas for storage operations."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from barsa.bms.records import ProjectStatus


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    owner_id: str = Field(..., min_length=1, max_length=128)
    id: str | None = Field(default=None, max_length=128)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    metadata: dict[str, Any] | None = None
    expected_revision: int | None = None


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    id: str | None = Field(default=None, max_length=128)
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)
    description: str | None = None
    goals: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    status: ProjectStatus | None = None
    description: str | None = None
    goals: list[str] | None = None
    metadata: dict[str, Any] | None = None
    expected_revision: int | None = None


class RecordEnvelope(BaseModel):
    record: dict[str, Any]
    revision: int
    project_id: str
    record_id: str
    record_type: str


class RecordUpdateRequest(BaseModel):
    record: dict[str, Any]
    expected_revision: int


class StorageStatsResponse(BaseModel):
    provider: str
    data_dir: str
    stats: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
