"""FastAPI REST router for Phase 13 BYOS and Cloud Synchronization."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from barsa.api.deps import get_sync_service
from barsa.sync.models import (
    RemoteCreate,
    RemoteResponse,
    RepositoryManifest,
    SyncResult,
    SyncStatusReport,
)
from barsa.sync.service import SyncService

logger = logging.getLogger("barsa.api.sync")

router = APIRouter(prefix="/sync", tags=["Cloud Synchronization (BYOS)"])


@router.post("/remotes", response_model=RemoteResponse, status_code=status.HTTP_201_CREATED)
def create_remote(
    project_id: str = Query(..., description="Project ID to bind the remote repository"),
    req: RemoteCreate = ...,
    sync_service: SyncService = Depends(get_sync_service),
) -> RemoteResponse:
    """Register a new BYOS remote (Local filesystem, S3 bucket, etc.)."""
    return sync_service.create_remote(project_id=project_id, req=req)


@router.get("/remotes", response_model=list[RemoteResponse])
def list_remotes(
    project_id: str = Query(..., description="Project ID whose remotes to list"),
    sync_service: SyncService = Depends(get_sync_service),
) -> list[RemoteResponse]:
    """List all registered BYOS remotes for a project."""
    return sync_service.list_remotes(project_id=project_id)


@router.get("/remotes/{remote_id}", response_model=RemoteResponse)
def get_remote(
    remote_id: str,
    sync_service: SyncService = Depends(get_sync_service),
) -> RemoteResponse:
    """Fetch configuration for a specific remote."""
    return sync_service.get_remote(remote_id=remote_id)


@router.delete("/remotes/{remote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_remote(
    remote_id: str,
    sync_service: SyncService = Depends(get_sync_service),
) -> None:
    """Remove a configured remote."""
    sync_service.delete_remote(remote_id=remote_id)


@router.post("/remotes/{remote_id}/push", response_model=SyncResult)
async def push_remote(
    remote_id: str,
    branch: str = Query("main", description="Branch name to push"),
    force: bool = Query(False, description="Force push overwriting divergence check"),
    passphrase: str | None = Query(None, description="Optional client-side decryption/encryption passphrase"),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncResult:
    """Push local commits and content-addressed objects to the remote storage target."""
    return await sync_service.push(remote_id=remote_id, branch_name=branch, force=force, passphrase=passphrase)


@router.post("/remotes/{remote_id}/pull", response_model=SyncResult)
async def pull_remote(
    remote_id: str,
    branch: str = Query("main", description="Branch name to pull"),
    passphrase: str | None = Query(None, description="Optional client-side decryption/encryption passphrase"),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncResult:
    """Pull remote commits and content-addressed objects from the remote storage target."""
    return await sync_service.pull(remote_id=remote_id, branch_name=branch, passphrase=passphrase)


@router.get("/remotes/{remote_id}/status", response_model=SyncStatusReport)
async def get_remote_status(
    remote_id: str,
    branch: str = Query("main", description="Branch name to evaluate"),
    passphrase: str | None = Query(None, description="Optional decryption passphrase"),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncStatusReport:
    """Inspect synchronization state (ahead, behind, diverged, up_to_date)."""
    return await sync_service.get_status(remote_id=remote_id, branch_name=branch, passphrase=passphrase)


@router.get("/remotes/{remote_id}/history", response_model=list[dict[str, Any]])
def get_remote_history(
    remote_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max history records to return"),
    sync_service: SyncService = Depends(get_sync_service),
) -> list[dict[str, Any]]:
    """Retrieve synchronization transfer audit history."""
    return sync_service.get_history(remote_id=remote_id, limit=limit)


@router.post("/repositories/init", response_model=RepositoryManifest)
async def init_repository(
    remote_id: str = Query(..., description="Configured remote ID to initialize"),
    passphrase: str | None = Query(None, description="Optional encryption passphrase"),
    sync_service: SyncService = Depends(get_sync_service),
) -> RepositoryManifest:
    """Initialize remote repository layout and write root repository.json manifest."""
    rem = sync_service.get_remote(remote_id)
    adapter = (
        sync_service.coordinator.get_adapter(
            sync_service.coordinator._get_remote_config(rem.id)
            if hasattr(sync_service.coordinator, "_get_remote_config")
            else sync_service.coordinator.storage.get_remote_config(rem.id)
            if hasattr(sync_service.coordinator.storage, "get_remote_config")
            else None,
            passphrase=passphrase,
        )
        if False
        else None
    )  # Handled below
    # Clean invocation via coordinator
    conn = sync_service._get_conn()
    row = conn.execute("SELECT * FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
    from barsa.sync.models import RemoteConfig

    config = RemoteConfig.model_validate(dict(row))
    adapter = sync_service.coordinator.get_adapter(config, passphrase=passphrase)
    try:
        manifest = await adapter.read_manifest()
        if not manifest:
            manifest = await adapter.initialize(
                repository_id=f"repo-{config.project_id}",
                project_id=config.project_id,
                encryption_enabled=config.encryption_enabled,
            )
        return manifest
    finally:
        await adapter.close()


@router.get("/repositories/{remote_id}/manifest", response_model=RepositoryManifest | None)
async def get_repository_manifest(
    remote_id: str,
    passphrase: str | None = Query(None, description="Optional decryption passphrase"),
    sync_service: SyncService = Depends(get_sync_service),
) -> RepositoryManifest | None:
    """Read remote repository.json manifest."""
    conn = sync_service._get_conn()
    row = conn.execute("SELECT * FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
    if not row:
        from barsa.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Remote '{remote_id}' does not exist")
    from barsa.sync.models import RemoteConfig

    config = RemoteConfig.model_validate(dict(row))
    adapter = sync_service.coordinator.get_adapter(config, passphrase=passphrase)
    try:
        return await adapter.read_manifest()
    finally:
        await adapter.close()


@router.get("/remotes/{remote_id}/conflicts", response_model=list[dict[str, Any]])
def get_remote_conflicts(
    remote_id: str,
    sync_service: SyncService = Depends(get_sync_service),
) -> list[dict[str, Any]]:
    """Retrieve active conflicts or diverged branches for this remote."""
    rem = sync_service.get_remote(remote_id)
    conn = sync_service._get_conn()
    rows = conn.execute(
        "SELECT * FROM sync_state WHERE remote_id = ? AND status IN ('diverged', 'conflict', 'error');",
        (remote_id,),
    ).fetchall()
    return [dict(r) for r in rows]
