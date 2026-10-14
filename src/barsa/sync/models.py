"""Pydantic models and schemas for Phase 13 BYOS and Cloud Synchronization."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RemoteProviderType(StrEnum):
    """Supported BYOS storage adapter types."""

    LOCAL = "local"
    S3 = "s3"
    GIT = "git"


class SyncStatus(StrEnum):
    """Synchronization branch comparison status."""

    IDLE = "idle"
    SYNCING = "syncing"
    UP_TO_DATE = "up_to_date"
    AHEAD = "ahead"
    BEHIND = "behind"
    DIVERGED = "diverged"
    CONFLICT = "conflict"
    ERROR = "error"


class SyncOperation(StrEnum):
    """Types of synchronization operations."""

    PUSH = "push"
    PULL = "pull"
    INIT = "init"


class TransferStatus(StrEnum):
    """Result of a sync transfer."""

    SUCCESS = "success"
    CONFLICT = "conflict"
    FAILED = "failed"


class RemoteConfig(BaseModel):
    """Stored configuration for a remote project repository."""

    id: str
    project_id: str
    name: str
    provider_type: RemoteProviderType
    local_path: str | None = None
    s3_endpoint_url: str | None = None
    s3_bucket_name: str | None = None
    s3_region: str | None = None
    s3_prefix: str = ""
    credential_id: str | None = None
    encryption_enabled: bool = False
    encryption_key_id: str | None = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class RemoteCreate(BaseModel):
    """Request payload to configure a new BYOS remote."""

    name: str
    provider_type: RemoteProviderType
    local_path: str | None = None
    s3_endpoint_url: str | None = None
    s3_bucket_name: str | None = None
    s3_region: str | None = None
    s3_prefix: str = ""
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    encryption_enabled: bool = False
    encryption_passphrase: str | None = None


class RemoteResponse(BaseModel):
    """Sanitized public metadata for a configured remote (no raw secrets)."""

    id: str
    project_id: str
    name: str
    provider_type: RemoteProviderType
    local_path: str | None = None
    s3_endpoint_url: str | None = None
    s3_bucket_name: str | None = None
    s3_region: str | None = None
    s3_prefix: str = ""
    encryption_enabled: bool = False
    is_active: bool = True
    created_at: str
    updated_at: str


class RepositoryManifest(BaseModel):
    """Root metadata manifest describing a remote Barsa repository layout."""

    format_version: str = "1.0"
    repository_id: str
    project_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    encryption_enabled: bool = False
    encryption_algorithm: str | None = None
    branches: dict[str, str] = Field(default_factory=dict)  # branch_name -> commit_id
    objects_count: int = 0
    total_bytes: int = 0


class RemoteBranchRef(BaseModel):
    """Branch pointer stored remotely."""

    branch_name: str
    commit_id: str
    etag: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ContentAddressedObject(BaseModel):
    """An immutable, content-addressed CAS entity."""

    content_hash: str
    object_type: str  # "commit", "bms_record", "artifact", "manifest"
    data_bytes: bytes
    size_bytes: int


class SyncResult(BaseModel):
    """Detailed summary of a completed push or pull execution."""

    operation: SyncOperation
    remote_id: str
    remote_name: str
    project_id: str
    branch_name: str
    status: SyncStatus
    local_head_commit_id: str
    remote_head_commit_id: str | None = None
    objects_uploaded: int = 0
    objects_downloaded: int = 0
    bytes_transferred: int = 0
    duration_ms: int = 0
    diverged: bool = False
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == SyncStatus.UP_TO_DATE and self.error_message is None


class SyncStatusReport(BaseModel):
    """Status comparison between local branch and remote repository."""

    remote_id: str
    remote_name: str
    project_id: str
    branch_name: str
    local_head_commit_id: str
    remote_head_commit_id: str | None = None
    status: SyncStatus
    ahead_count: int = 0
    behind_count: int = 0
    diverged: bool = False
    last_synced_at: str | None = None
    last_error: str | None = None
