"""Core Synchronization Coordinator implementing CAS object sync, push/pull protocols, and conflict detection."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from barsa.bms.serialization import deserialize_record
from barsa.core.exceptions import ConflictError, ResourceNotFoundError, StorageError
from barsa.models.versioning import AuthorType, Commit
from barsa.sync.adapters.local import LocalFilesystemStorageAdapter
from barsa.sync.adapters.s3 import S3StorageAdapter
from barsa.sync.crypto import (
    SyncEncryptor,
    canonical_json_bytes,
    compute_sha256,
)
from barsa.sync.models import (
    RemoteConfig,
    RemoteProviderType,
    SyncOperation,
    SyncResult,
    SyncStatus,
    SyncStatusReport,
)

if TYPE_CHECKING:
    from barsa.core.config import Settings
    from barsa.storage.sqlite import SQLiteStorageProvider
    from barsa.sync.adapters.base import RemoteStorageAdapter
    from barsa.versioning.engine import VersionControlEngine

logger = logging.getLogger("barsa.sync.coordinator")


class SyncCoordinator:
    """Manages project remote configurations, CAS object transfers, and DAG synchronization."""

    def __init__(
        self,
        storage: SQLiteStorageProvider,
        vc: VersionControlEngine,
        settings: Settings | None = None,
    ) -> None:
        self.storage = storage
        self.vc = vc
        self.settings = settings

    def _get_conn(self):
        return self.storage._get_connection()

    def _row_to_remote_config(self, row: dict[str, Any] | Any) -> RemoteConfig:
        d = dict(row)
        cfg_str = d.get("config_json")
        cfg = json.loads(cfg_str) if cfg_str else {}
        d.update(cfg)
        return RemoteConfig.model_validate(d)

    def get_adapter(self, remote: RemoteConfig, passphrase: str | None = None) -> RemoteStorageAdapter:
        """Instantiate the appropriate storage adapter for a remote configuration."""
        encryptor = None
        if remote.encryption_enabled:
            encryptor = SyncEncryptor(passphrase=passphrase or "barsa-default-byos-key")

        if remote.provider_type == RemoteProviderType.LOCAL:
            if not remote.local_path:
                raise ValueError("local_path is required for Local remote provider")
            return LocalFilesystemStorageAdapter(base_dir=remote.local_path, encryptor=encryptor)

        if remote.provider_type == RemoteProviderType.S3:
            if not remote.s3_bucket_name:
                raise ValueError("s3_bucket_name is required for S3 remote provider")

            access_key = None
            secret_key = None
            # Retrieve encrypted credentials if available
            conn = self._get_conn()
            row = conn.execute("SELECT config_json FROM remotes WHERE id = ?;", (remote.id,)).fetchone()
            if row and row["config_json"]:
                cfg = json.loads(row["config_json"])
                access_key = cfg.get("s3_access_key")
                secret_key = cfg.get("s3_secret_key")

            return S3StorageAdapter(
                bucket_name=remote.s3_bucket_name,
                endpoint_url=remote.s3_endpoint_url,
                region_name=remote.s3_region or "us-east-1",
                access_key_id=access_key,
                secret_access_key=secret_key,
                prefix=remote.s3_prefix,
                encryptor=encryptor,
            )

        raise StorageError(f"Unsupported remote provider type: {remote.provider_type}")

    async def initialize_remote(self, remote: RemoteConfig, passphrase: str | None = None) -> None:
        """Initialize the remote repository layout and manifest."""
        adapter = self.get_adapter(remote, passphrase=passphrase)
        manifest = await adapter.read_manifest()
        if not manifest:
            await adapter.initialize(
                repository_id=f"repo-{remote.project_id}",
                project_id=remote.project_id,
                encryption_enabled=remote.encryption_enabled,
            )
        await adapter.close()

    async def push(
        self,
        remote_id: str,
        branch_name: str = "main",
        force: bool = False,
        passphrase: str | None = None,
        actor_id: str = "system",
    ) -> SyncResult:
        """Push local commits and content-addressed records to the configured remote."""
        _ = actor_id
        start_time = time.time()
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError(f"Remote '{remote_id}' does not exist")

        remote = self._row_to_remote_config(row)
        adapter = self.get_adapter(remote, passphrase=passphrase)
        try:
            # 1. Connectivity & repository check
            if not await adapter.check_connectivity():
                raise StorageError(f"Cannot connect to remote storage '{remote.name}'")

            manifest = await adapter.read_manifest()
            if not manifest:
                manifest = await adapter.initialize(
                    repository_id=f"repo-{remote.project_id}",
                    project_id=remote.project_id,
                    encryption_enabled=remote.encryption_enabled,
                )

            # 2. Inspect local branch
            local_branch = self.vc.get_branch(remote.project_id, branch_name)
            local_head = local_branch.head_commit_id

            # 3. Inspect remote branch ref
            remote_ref = await adapter.get_branch_ref(branch_name)

            if remote_ref and remote_ref.commit_id == local_head:
                duration_ms = int((time.time() - start_time) * 1000)
                self._record_sync_history(
                    remote_id, "push", branch_name, local_head, local_head, 0, 0, duration_ms, "success"
                )
                return SyncResult(
                    operation=SyncOperation.PUSH,
                    remote_id=remote.id,
                    remote_name=remote.name,
                    project_id=remote.project_id,
                    branch_name=branch_name,
                    status=SyncStatus.UP_TO_DATE,
                    local_head_commit_id=local_head,
                    remote_head_commit_id=remote_ref.commit_id,
                    duration_ms=duration_ms,
                )

            # 4. Concurrency & divergence verification
            if remote_ref and not force:
                remote_commit = self.vc.get_commit(remote.project_id, remote_ref.commit_id)
                if remote_commit:
                    try:
                        lca = self.vc.find_lowest_common_ancestor(remote.project_id, local_head, remote_ref.commit_id)
                        if lca != remote_ref.commit_id:
                            # Local does not contain remote HEAD -> Divergence
                            duration_ms = int((time.time() - start_time) * 1000)
                            self._update_sync_state(
                                remote_id,
                                branch_name,
                                local_head,
                                remote_ref.commit_id,
                                "diverged",
                                "Remote branch has diverged",
                            )
                            self._record_sync_history(
                                remote_id,
                                "push",
                                branch_name,
                                local_head,
                                remote_ref.commit_id,
                                0,
                                0,
                                duration_ms,
                                "conflict",
                                "Remote branch has diverged",
                            )
                            raise ConflictError(
                                f"Remote branch '{branch_name}' has diverged. Pull remote changes before pushing."
                            )
                    except StorageError as err:
                        raise ConflictError(f"No common ancestor with remote branch: {err}") from err
                else:
                    # Remote commit is unknown locally; must pull first
                    raise ConflictError(
                        f"Remote commit '{remote_ref.commit_id}' is unknown locally. Pull remote changes first."
                    )

            # 5. Collect commits to push
            commits_to_push = self._collect_commits_to_push(
                remote.project_id, local_head, remote_ref.commit_id if remote_ref else None
            )

            # 6. Upload immutable CAS objects
            objects_uploaded = 0
            bytes_transferred = 0

            for commit in commits_to_push:
                # A. Commit object (deterministic canonical format matching compute_commit_id)
                parents = sorted(commit.parent_commit_ids)
                changes_dict = [c.model_dump(mode="json") for c in commit.changes]
                changes_dict.sort(key=lambda x: (x["record_id"], x["operation"]))
                iso_created = commit.created_at.astimezone(UTC).isoformat()
                canonical_obj = {
                    "bms_version": commit.bms_version,
                    "project_id": commit.project_id,
                    "parent_commit_ids": parents,
                    "author_id": commit.author_id,
                    "author_type": commit.author_type.value
                    if hasattr(commit.author_type, "value")
                    else str(commit.author_type),
                    "message": commit.message,
                    "created_at": iso_created,
                    "changes": changes_dict,
                    "resulting_state_hash": commit.resulting_state_hash,
                    "metadata": commit.metadata,
                }
                commit_bytes = json.dumps(canonical_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
                commit_hash = commit.commit_id

                if not await adapter.object_exists(commit_hash):
                    await adapter.put_object(commit_hash, commit_bytes, object_type="commit")
                    objects_uploaded += 1
                    bytes_transferred += len(commit_bytes)

                # B. Record objects referenced in commit state
                records_at_commit = conn.execute(
                    "SELECT record_id, record_type, record_data_json FROM commit_record_states WHERE commit_id = ? AND record_data_json IS NOT NULL;",
                    (commit.commit_id,),
                ).fetchall()

                for r in records_at_commit:
                    rec_json = r["record_data_json"]
                    rec_dict = json.loads(rec_json)
                    rec_bytes = canonical_json_bytes(rec_dict)
                    rec_hash = compute_sha256(rec_bytes)

                    if not await adapter.object_exists(rec_hash):
                        await adapter.put_object(rec_hash, rec_bytes, object_type=r["record_type"])
                        objects_uploaded += 1
                        bytes_transferred += len(rec_bytes)

            # 7. Conditionally update remote branch ref
            expected_etag = remote_ref.etag if remote_ref else None
            new_remote_ref = await adapter.update_branch_ref(branch_name, local_head, expected_etag=expected_etag)

            # 8. Record local sync state
            duration_ms = int((time.time() - start_time) * 1000)
            self._update_remote_ref(remote_id, branch_name, local_head, new_remote_ref.etag)
            self._update_sync_state(remote_id, branch_name, local_head, local_head, "up_to_date", None)
            self._record_sync_history(
                remote_id,
                "push",
                branch_name,
                local_head,
                local_head,
                objects_uploaded,
                bytes_transferred,
                duration_ms,
                "success",
            )

            return SyncResult(
                operation=SyncOperation.PUSH,
                remote_id=remote.id,
                remote_name=remote.name,
                project_id=remote.project_id,
                branch_name=branch_name,
                status=SyncStatus.UP_TO_DATE,
                local_head_commit_id=local_head,
                remote_head_commit_id=local_head,
                objects_uploaded=objects_uploaded,
                bytes_transferred=bytes_transferred,
                duration_ms=duration_ms,
            )
        finally:
            await adapter.close()

    async def pull(
        self,
        remote_id: str,
        branch_name: str = "main",
        passphrase: str | None = None,
        actor_id: str = "system",
    ) -> SyncResult:
        """Pull remote commits and content-addressed objects into local storage."""
        _ = actor_id
        start_time = time.time()
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError(f"Remote '{remote_id}' does not exist")

        remote = self._row_to_remote_config(row)
        adapter = self.get_adapter(remote, passphrase=passphrase)
        try:
            if not await adapter.check_connectivity():
                raise StorageError(f"Cannot connect to remote storage '{remote.name}'")

            remote_ref = await adapter.get_branch_ref(branch_name)
            if not remote_ref:
                raise ResourceNotFoundError(f"Remote branch '{branch_name}' does not exist in remote repository")

            local_branch = self.vc.get_branch(remote.project_id, branch_name)
            local_head = local_branch.head_commit_id if local_branch else None
            remote_head = remote_ref.commit_id

            if local_head == remote_head:
                duration_ms = int((time.time() - start_time) * 1000)
                self._update_sync_state(remote_id, branch_name, local_head, remote_head, "up_to_date", None)
                return SyncResult(
                    operation=SyncOperation.PULL,
                    remote_id=remote.id,
                    remote_name=remote.name,
                    project_id=remote.project_id,
                    branch_name=branch_name,
                    status=SyncStatus.UP_TO_DATE,
                    local_head_commit_id=local_head,
                    remote_head_commit_id=remote_head,
                    duration_ms=duration_ms,
                )

            # Download missing commits and CAS objects
            objects_downloaded = 0
            bytes_transferred = 0

            queue = [remote_head]
            visited = set()
            downloaded_commits: list[Commit] = []

            while queue:
                cid = queue.pop(0)
                if not cid or cid in visited:
                    continue
                visited.add(cid)

                # Check if commit already present locally
                existing_commit = self.vc.get_commit(remote.project_id, cid)
                if existing_commit:
                    continue

                # Download commit from CAS
                commit_bytes = await adapter.get_object(cid)
                objects_downloaded += 1
                bytes_transferred += len(commit_bytes)

                commit_dict = json.loads(commit_bytes.decode("utf-8"))
                commit_dict["commit_id"] = cid
                commit_obj = Commit.model_validate(commit_dict)
                downloaded_commits.append(commit_obj)

                # Download referenced records in commit changes
                for change in commit_obj.changes:
                    if change.after_state:
                        rec_bytes = canonical_json_bytes(change.after_state)
                        rec_hash = compute_sha256(rec_bytes)
                        # Fetch record object from CAS if not present locally
                        if await adapter.object_exists(rec_hash):
                            r_bytes = await adapter.get_object(rec_hash)
                            objects_downloaded += 1
                            bytes_transferred += len(r_bytes)
                            rec_dict = json.loads(r_bytes.decode("utf-8"))
                            rec_model = deserialize_record(rec_dict)
                            self.storage.create_record(rec_model)

                # Queue parent commits
                for parent_id in commit_obj.parent_commit_ids:
                    queue.append(parent_id)

            # Store downloaded commits in topological order (parents first)
            for commit_obj in reversed(downloaded_commits):
                self._insert_downloaded_commit(remote.project_id, commit_obj)

            # Check divergence vs fast-forward
            can_fast_forward = False
            if local_head is None:
                can_fast_forward = True
            else:
                try:
                    lca = self.vc.find_lowest_common_ancestor(remote.project_id, local_head, remote_head)
                    if lca == local_head:
                        can_fast_forward = True
                    elif lca == remote_head:
                        # Local is already ahead of remote
                        can_fast_forward = False
                except Exception:
                    can_fast_forward = False

            duration_ms = int((time.time() - start_time) * 1000)

            if can_fast_forward:
                # Update local branch HEAD (upsert if new branch)
                conn.execute(
                    """
                    INSERT INTO branches (project_id, name, head_commit_id, created_at, updated_at)
                    VALUES (?, ?, ?, datetime('now', 'utc'), datetime('now', 'utc'))
                    ON CONFLICT(project_id, name) DO UPDATE SET
                        head_commit_id = excluded.head_commit_id,
                        updated_at = excluded.updated_at;
                    """,
                    (remote.project_id, branch_name, remote_head),
                )
                conn.commit()

                # Rebuild graph projection if FalkorDB enabled
                if self.settings and self.settings.graph_enabled:
                    try:
                        from barsa.graph.projection import GraphProjector

                        projector = GraphProjector(self.storage, self.settings)
                        projector.project_commit(remote.project_id, remote_head)
                    except Exception as g_err:
                        logger.warning(f"Graph projection after pull failed: {g_err}")

                self._update_remote_ref(remote_id, branch_name, remote_head, remote_ref.etag)
                self._update_sync_state(remote_id, branch_name, remote_head, remote_head, "up_to_date", None)
                self._record_sync_history(
                    remote_id,
                    "pull",
                    branch_name,
                    local_head,
                    remote_head,
                    objects_downloaded,
                    bytes_transferred,
                    duration_ms,
                    "success",
                )

                return SyncResult(
                    operation=SyncOperation.PULL,
                    remote_id=remote.id,
                    remote_name=remote.name,
                    project_id=remote.project_id,
                    branch_name=branch_name,
                    status=SyncStatus.UP_TO_DATE,
                    local_head_commit_id=remote_head,
                    remote_head_commit_id=remote_head,
                    objects_downloaded=objects_downloaded,
                    bytes_transferred=bytes_transferred,
                    duration_ms=duration_ms,
                )

            # Diverged: Preserve local branch intact, track remote ref, mark diverged
            self._update_remote_ref(remote_id, branch_name, remote_head, remote_ref.etag)
            self._update_sync_state(
                remote_id, branch_name, local_head, remote_head, "diverged", "Branches have diverged; merge required"
            )
            self._record_sync_history(
                remote_id,
                "pull",
                branch_name,
                local_head,
                remote_head,
                objects_downloaded,
                bytes_transferred,
                duration_ms,
                "conflict",
                "Branches diverged",
            )

            return SyncResult(
                operation=SyncOperation.PULL,
                remote_id=remote.id,
                remote_name=remote.name,
                project_id=remote.project_id,
                branch_name=branch_name,
                status=SyncStatus.DIVERGED,
                local_head_commit_id=local_head,
                remote_head_commit_id=remote_head,
                objects_downloaded=objects_downloaded,
                bytes_transferred=bytes_transferred,
                duration_ms=duration_ms,
                diverged=True,
                error_message="Local and remote branches have diverged. A merge commit is required.",
            )
        finally:
            await adapter.close()

    async def get_sync_status(
        self, remote_id: str, branch_name: str = "main", passphrase: str | None = None
    ) -> SyncStatusReport:
        """Compare local branch state with the remote repository."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM remotes WHERE id = ?;", (remote_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError(f"Remote '{remote_id}' does not exist")

        remote = self._row_to_remote_config(row)
        local_branch = self.vc.get_branch(remote.project_id, branch_name)
        local_head = local_branch.head_commit_id

        adapter = self.get_adapter(remote, passphrase=passphrase)
        try:
            remote_ref = await adapter.get_branch_ref(branch_name)
            remote_head = remote_ref.commit_id if remote_ref else None

            if not remote_head:
                return SyncStatusReport(
                    remote_id=remote.id,
                    remote_name=remote.name,
                    project_id=remote.project_id,
                    branch_name=branch_name,
                    local_head_commit_id=local_head,
                    remote_head_commit_id=None,
                    status=SyncStatus.AHEAD,
                    ahead_count=1,
                    behind_count=0,
                )

            if local_head == remote_head:
                return SyncStatusReport(
                    remote_id=remote.id,
                    remote_name=remote.name,
                    project_id=remote.project_id,
                    branch_name=branch_name,
                    local_head_commit_id=local_head,
                    remote_head_commit_id=remote_head,
                    status=SyncStatus.UP_TO_DATE,
                )

            # Compare DAG positions
            try:
                lca = self.vc.find_lowest_common_ancestor(remote.project_id, local_head, remote_head)
                if lca == remote_head:
                    return SyncStatusReport(
                        remote_id=remote.id,
                        remote_name=remote.name,
                        project_id=remote.project_id,
                        branch_name=branch_name,
                        local_head_commit_id=local_head,
                        remote_head_commit_id=remote_head,
                        status=SyncStatus.AHEAD,
                        ahead_count=1,
                        behind_count=0,
                    )
                if lca == local_head:
                    return SyncStatusReport(
                        remote_id=remote.id,
                        remote_name=remote.name,
                        project_id=remote.project_id,
                        branch_name=branch_name,
                        local_head_commit_id=local_head,
                        remote_head_commit_id=remote_head,
                        status=SyncStatus.BEHIND,
                        ahead_count=0,
                        behind_count=1,
                    )
                # Diverged
                return SyncStatusReport(
                    remote_id=remote.id,
                    remote_name=remote.name,
                    project_id=remote.project_id,
                    branch_name=branch_name,
                    local_head_commit_id=local_head,
                    remote_head_commit_id=remote_head,
                    status=SyncStatus.DIVERGED,
                    diverged=True,
                    ahead_count=1,
                    behind_count=1,
                )
            except Exception:
                return SyncStatusReport(
                    remote_id=remote.id,
                    remote_name=remote.name,
                    project_id=remote.project_id,
                    branch_name=branch_name,
                    local_head_commit_id=local_head,
                    remote_head_commit_id=remote_head,
                    status=SyncStatus.DIVERGED,
                    diverged=True,
                )
        finally:
            await adapter.close()

    def _collect_commits_to_push(self, project_id: str, local_head: str, stop_commit_id: str | None) -> list[Commit]:
        """Walk commit DAG backwards from local_head to stop_commit_id."""
        commits: list[Commit] = []
        queue = [local_head]
        visited = set()

        while queue:
            cid = queue.pop(0)
            if not cid or cid in visited or cid == stop_commit_id:
                continue
            visited.add(cid)

            c = self.vc.get_commit(project_id, cid)
            if c:
                commits.append(c)
                for pid in c.parent_commit_ids:
                    if pid != stop_commit_id:
                        queue.append(pid)

        return commits

    def _insert_downloaded_commit(self, project_id: str, commit: Commit) -> None:
        """Persist a downloaded commit into local SQLite tables."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR IGNORE INTO commits (
                commit_id, project_id, parent_commit_ids_json, author_id, author_type,
                message, created_at, changes_json, resulting_state_hash, metadata_json, bms_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                commit.commit_id,
                project_id,
                json.dumps(commit.parent_commit_ids),
                commit.author_id,
                commit.author_type.value if isinstance(commit.author_type, AuthorType) else str(commit.author_type),
                commit.message,
                commit.created_at.isoformat() if hasattr(commit.created_at, "isoformat") else str(commit.created_at),
                json.dumps([chg.model_dump(mode="json") for chg in commit.changes]),
                commit.resulting_state_hash,
                json.dumps(commit.metadata or {}),
                commit.bms_version,
            ),
        )
        for pid in commit.parent_commit_ids:
            conn.execute(
                "INSERT OR IGNORE INTO commit_parents (project_id, commit_id, parent_id) VALUES (?, ?, ?);",
                (project_id, commit.commit_id, pid),
            )
        for chg in commit.changes:
            if chg.after_state:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO commit_record_states (
                        project_id, commit_id, record_id, record_type, record_data_json
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        project_id,
                        commit.commit_id,
                        chg.record_id,
                        chg.record_type,
                        json.dumps(chg.after_state),
                    ),
                )
        conn.commit()
        # Keep active SQLite tables synchronized with downloaded commit
        self.vc._synchronize_active_storage(project_id, commit.changes)

    def _update_remote_ref(self, remote_id: str, branch_name: str, commit_id: str, etag: str | None) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO remote_refs (remote_id, branch_name, commit_id, etag, updated_at)
            VALUES (?, ?, ?, ?, datetime('now', 'utc'))
            ON CONFLICT(remote_id, branch_name) DO UPDATE SET
                commit_id = excluded.commit_id,
                etag = excluded.etag,
                updated_at = excluded.updated_at;
            """,
            (remote_id, branch_name, commit_id, etag),
        )
        conn.commit()

    def _update_sync_state(
        self,
        remote_id: str,
        branch_name: str,
        pushed_id: str | None,
        pulled_id: str | None,
        status: str,
        error: str | None,
    ) -> None:
        conn = self._get_conn()
        state_id = f"state-{remote_id}-{branch_name}"
        conn.execute(
            """
            INSERT INTO sync_state (id, remote_id, branch_name, last_pushed_commit_id, last_pulled_commit_id, last_synced_at, status, last_error)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'utc'), ?, ?)
            ON CONFLICT(remote_id, branch_name) DO UPDATE SET
                last_pushed_commit_id = coalesce(excluded.last_pushed_commit_id, sync_state.last_pushed_commit_id),
                last_pulled_commit_id = coalesce(excluded.last_pulled_commit_id, sync_state.last_pulled_commit_id),
                last_synced_at = excluded.last_synced_at,
                status = excluded.status,
                last_error = excluded.last_error;
            """,
            (state_id, remote_id, branch_name, pushed_id, pulled_id, status, error),
        )
        conn.commit()

    def _record_sync_history(
        self,
        remote_id: str,
        operation: str,
        branch_name: str,
        start_id: str,
        end_id: str,
        objects: int,
        bytes_transferred: int,
        duration_ms: int,
        status: str,
        error: str | None = None,
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO sync_history (id, remote_id, operation, branch_name, start_commit_id, end_commit_id, objects_transferred, bytes_transferred, duration_ms, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'utc'));
            """,
            (
                f"hist-{uuid4().hex[:12]}",
                remote_id,
                operation,
                branch_name,
                start_id,
                end_id,
                objects,
                bytes_transferred,
                duration_ms,
                status,
                error,
            ),
        )
        conn.commit()
