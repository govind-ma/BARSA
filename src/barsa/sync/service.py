"""High-level SyncService managing Remotes CRUD, authorization, and SyncCoordinator execution."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from barsa.core.exceptions import ConflictError, ResourceNotFoundError
from barsa.security.models import AuthenticatedPrincipal, PrincipalType
from barsa.sync.coordinator import SyncCoordinator
from barsa.sync.models import (
    RemoteCreate,
    RemoteProviderType,
    RemoteResponse,
    SyncResult,
    SyncStatusReport,
)
from barsa.versioning.engine import VersionControlEngine

if TYPE_CHECKING:
    from barsa.core.config import Settings
    from barsa.security.authorizer import CentralAuthorizer
    from barsa.storage.sqlite import SQLiteStorageProvider

logger = logging.getLogger("barsa.sync.service")


class SyncService:
    """Service layer for BYOS Remotes management and synchronization."""

    def __init__(
        self,
        storage: SQLiteStorageProvider,
        settings: Settings | None = None,
        authorizer: CentralAuthorizer | None = None,
    ) -> None:
        self.storage = storage
        self.settings = settings
        self.vc = VersionControlEngine(storage)
        self.coordinator = SyncCoordinator(storage, self.vc, settings=settings)
        self.authorizer = authorizer

    def _get_conn(self):
        return self.storage._get_connection()

    def _authorize(self, project_id: str, action: str, principal_id: str) -> None:
        if not self.authorizer:
            return
        is_sys = principal_id in ("system", "sysadmin")
        if is_sys:
            principal = AuthenticatedPrincipal(
                principal_id=principal_id,
                principal_type=PrincipalType.SERVICE,
                is_superuser=True,
                granted_scopes=["memory:read", "memory:write", "project:read", "project:write"],
            )
        else:
            p_record = self.authorizer.sec_storage.get_principal(principal_id)
            if p_record:
                principal = p_record
            else:
                principal = AuthenticatedPrincipal(principal_id=principal_id, principal_type=PrincipalType.AGENT)
        self.authorizer.authorize(principal, action=action, resource={"project_id": project_id})

    def create_remote(self, project_id: str, req: RemoteCreate, principal_id: str = "system") -> RemoteResponse:
        """Register a new BYOS remote destination."""
        self._authorize(project_id, "memory:write", principal_id)
        conn = self._get_conn()

        # Verify project exists
        proj = conn.execute("SELECT workspace_id FROM projects WHERE id = ?;", (project_id,)).fetchone()
        if not proj:
            raise ResourceNotFoundError(f"Project '{project_id}' does not exist")

        # Check unique remote name per project
        existing = conn.execute(
            "SELECT id FROM remotes WHERE project_id = ? AND name = ?;", (project_id, req.name)
        ).fetchone()
        if existing:
            raise ConflictError(f"Remote with name '{req.name}' already exists for project '{project_id}'")

        remote_id = f"rem-{uuid4().hex[:12]}"
        config_payload: dict[str, Any] = {
            "local_path": req.local_path,
            "s3_endpoint_url": req.s3_endpoint_url,
            "s3_bucket_name": req.s3_bucket_name,
            "s3_region": req.s3_region,
            "s3_prefix": req.s3_prefix,
            "encryption_enabled": req.encryption_enabled,
        }
        if req.s3_access_key and req.s3_secret_key:
            config_payload["s3_access_key"] = req.s3_access_key
            config_payload["s3_secret_key"] = req.s3_secret_key

        conn.execute(
            """
            INSERT INTO remotes (id, project_id, name, provider_type, config_json, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, datetime('now', 'utc'), datetime('now', 'utc'));
            """,
            (remote_id, project_id, req.name, req.provider_type.value, json.dumps(config_payload)),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
        return self._to_response(dict(row))

    def list_remotes(self, project_id: str, principal_id: str = "system") -> list[RemoteResponse]:
        """List configured remotes for a project."""
        self._authorize(project_id, "memory:read", principal_id)
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM remotes WHERE project_id = ? ORDER BY created_at ASC;", (project_id,)
        ).fetchall()
        return [self._to_response(dict(r)) for r in rows]

    def get_remote(self, remote_id: str, principal_id: str = "system") -> RemoteResponse:
        """Fetch remote details."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError(f"Remote '{remote_id}' does not exist")
        res = self._to_response(dict(row))
        self._authorize(res.project_id, "memory:read", principal_id)
        return res

    def delete_remote(self, remote_id: str, principal_id: str = "system") -> None:
        """Remove a configured remote."""
        conn = self._get_conn()
        row = conn.execute("SELECT project_id FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError(f"Remote '{remote_id}' does not exist")
        self._authorize(row["project_id"], "memory:write", principal_id)

        conn.execute("DELETE FROM remotes WHERE id = ?;", (remote_id,))
        conn.commit()

    async def push(
        self,
        remote_id: str,
        branch_name: str = "main",
        force: bool = False,
        passphrase: str | None = None,
        principal_id: str = "system",
    ) -> SyncResult:
        """Execute a push sync operation."""
        rem = self.get_remote(remote_id, principal_id=principal_id)
        self._authorize(rem.project_id, "memory:write", principal_id)
        return await self.coordinator.push(
            remote_id=remote_id,
            branch_name=branch_name,
            force=force,
            passphrase=passphrase,
            actor_id=principal_id,
        )

    async def pull(
        self,
        remote_id: str,
        branch_name: str = "main",
        passphrase: str | None = None,
        principal_id: str = "system",
    ) -> SyncResult:
        """Execute a pull sync operation."""
        rem = self.get_remote(remote_id, principal_id=principal_id)
        self._authorize(rem.project_id, "memory:write", principal_id)
        return await self.coordinator.pull(
            remote_id=remote_id,
            branch_name=branch_name,
            passphrase=passphrase,
            actor_id=principal_id,
        )

    async def get_status(
        self,
        remote_id: str,
        branch_name: str = "main",
        passphrase: str | None = None,
        principal_id: str = "system",
    ) -> SyncStatusReport:
        """Fetch remote comparison status."""
        rem = self.get_remote(remote_id, principal_id=principal_id)
        self._authorize(rem.project_id, "memory:read", principal_id)
        return await self.coordinator.get_sync_status(
            remote_id=remote_id,
            branch_name=branch_name,
            passphrase=passphrase,
        )

    def get_history(self, remote_id: str, limit: int = 20, principal_id: str = "system") -> list[dict[str, Any]]:
        """List synchronization operation history for a remote."""
        rem = self.get_remote(remote_id, principal_id=principal_id)
        self._authorize(rem.project_id, "memory:read", principal_id)
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT id, operation, branch_name, start_commit_id, end_commit_id, objects_transferred,
                   bytes_transferred, duration_ms, status, error_message, created_at
            FROM sync_history
            WHERE remote_id = ?
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (remote_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def _to_response(self, row: dict[str, Any]) -> RemoteResponse:
        cfg = json.loads(row.get("config_json", "{}"))
        return RemoteResponse(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            provider_type=RemoteProviderType(row["provider_type"]),
            local_path=cfg.get("local_path"),
            s3_endpoint_url=cfg.get("s3_endpoint_url"),
            s3_bucket_name=cfg.get("s3_bucket_name"),
            s3_region=cfg.get("s3_region"),
            s3_prefix=cfg.get("s3_prefix", ""),
            encryption_enabled=bool(cfg.get("encryption_enabled", False)),
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
