"""SQLite local-first storage provider implementation for BARSA."""

import contextlib
import logging
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from barsa.bms.package import BarsaMemoryPackage, PackageRecords
from barsa.bms.records import (
    AnyBMSRecord,
    ArtifactReference,
    DecisionRecord,
    KnowledgeRecord,
    MemoryCommit,
    Project,
    RelationshipRecord,
    ResumeCheckpoint,
    TaskRecord,
    Workspace,
)
from barsa.bms.serialization import deserialize_record
from barsa.bms.validation import validate_bms_package
from barsa.core.exceptions import ConflictError, ResourceNotFoundError, StorageError
from barsa.storage.artifacts import ArtifactStore
from barsa.storage.migrations import apply_migrations, verify_database_integrity

logger = logging.getLogger("barsa.storage.sqlite")


class SQLiteStorageProvider:
    """Production local-first SQLite storage engine.

    Features:
    - WAL (Write-Ahead Logging) mode with busy timeout handling
    - Foreign key constraints enabled
    - Project-scoped record isolation
    - Optimistic concurrency control via atomic compare-and-swap revisions
    - Transaction-protected package import and export
    - Content-addressed artifact storage
    """

    def __init__(self, db_path: Path, artifacts_dir: Path, max_artifact_size: int = 50 * 1024 * 1024) -> None:
        self.db_path = db_path.resolve()
        self.artifacts_dir = artifacts_dir.resolve()
        self.max_artifact_size = max_artifact_size
        self._artifact_store = ArtifactStore(self.artifacts_dir, self.max_artifact_size)
        self._local = threading.local()
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "sqlite"

    @property
    def is_available(self) -> bool:
        return self._initialized and self.db_path.exists()

    @property
    def artifacts(self) -> ArtifactStore:
        return self._artifact_store

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode; explicit BEGIN/COMMIT used for transactions
            )
            # Enable WAL mode, foreign keys, and 10-second busy timeout
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA busy_timeout = 10000;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def initialize(self) -> None:
        """Initialize database schema, apply migrations, and verify integrity."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        apply_migrations(conn)
        self._initialized = True
        logger.info("SQLiteStorageProvider initialized at %s", self.db_path)

    def close(self) -> None:
        """Close connection for current thread."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            with contextlib.suppress(Exception):
                self._local.conn.close()
            self._local.conn = None

    def check_integrity(self) -> dict[str, Any]:
        """Verify database integrity."""
        conn = self._get_connection()
        return verify_database_integrity(conn)

    # =========================================================================
    # Workspace Operations
    # =========================================================================

    def create_workspace(self, workspace: Workspace) -> Workspace:
        conn = self._get_connection()
        now_str = datetime.now(UTC).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO workspaces (id, name, owner_id, description, data_json, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?);
                """,
                (
                    workspace.id,
                    workspace.name,
                    workspace.owner_id,
                    workspace.description,
                    workspace.model_dump_json(),
                    now_str,
                    now_str,
                ),
            )
            return workspace
        except sqlite3.IntegrityError as err:
            msg = f"Workspace with ID '{workspace.id}' already exists."
            raise ConflictError(msg) from err

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        conn = self._get_connection()
        cur = conn.execute("SELECT data_json FROM workspaces WHERE id = ?;", (workspace_id,))
        row = cur.fetchone()
        if not row:
            return None
        return Workspace.model_validate_json(row["data_json"])

    def list_workspaces(self, limit: int = 100, offset: int = 0) -> list[Workspace]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT data_json FROM workspaces ORDER BY created_at DESC LIMIT ? OFFSET ?;",
            (limit, offset),
        )
        return [Workspace.model_validate_json(row["data_json"]) for row in cur.fetchall()]

    def update_workspace(self, workspace: Workspace, expected_revision: int | None = None) -> Workspace:
        conn = self._get_connection()
        now_str = datetime.now(UTC).isoformat()

        if expected_revision is not None:
            cur = conn.execute(
                """
                UPDATE workspaces
                SET name = ?, description = ?, data_json = ?, revision = revision + 1, updated_at = ?
                WHERE id = ? AND revision = ?;
                """,
                (
                    workspace.name,
                    workspace.description,
                    workspace.model_dump_json(),
                    now_str,
                    workspace.id,
                    expected_revision,
                ),
            )
            if cur.rowcount == 0:
                # Check if it exists to distinguish 404 from 409
                existing = self.get_workspace(workspace.id)
                if not existing:
                    raise ResourceNotFoundError(f"Workspace '{workspace.id}' not found.", "Workspace", workspace.id)
                msg = f"Optimistic lock conflict on Workspace '{workspace.id}'. Expected revision {expected_revision}."
                raise ConflictError(msg)
        else:
            cur = conn.execute(
                """
                UPDATE workspaces
                SET name = ?, description = ?, data_json = ?, revision = revision + 1, updated_at = ?
                WHERE id = ?;
                """,
                (
                    workspace.name,
                    workspace.description,
                    workspace.model_dump_json(),
                    now_str,
                    workspace.id,
                ),
            )
            if cur.rowcount == 0:
                raise ResourceNotFoundError(f"Workspace '{workspace.id}' not found.", "Workspace", workspace.id)
        return workspace

    def delete_workspace(self, workspace_id: str, cascade: bool = False) -> bool:
        conn = self._get_connection()
        # Check projects count if not cascade
        if not cascade:
            cur = conn.execute("SELECT COUNT(*) as count FROM projects WHERE workspace_id = ?;", (workspace_id,))
            count = cur.fetchone()["count"]
            if count > 0:
                msg = (
                    f"Cannot delete workspace '{workspace_id}' containing {count} projects. "
                    "Use cascade=True to delete workspace and all projects."
                )
                raise ConflictError(msg)

        cur = conn.execute("DELETE FROM workspaces WHERE id = ?;", (workspace_id,))
        return cur.rowcount > 0

    # =========================================================================
    # Project Operations
    # =========================================================================

    def create_project(self, project: Project) -> Project:
        conn = self._get_connection()
        # Verify workspace exists
        if not self.get_workspace(project.workspace_id):
            raise ResourceNotFoundError(
                f"Workspace '{project.workspace_id}' not found.", "Workspace", project.workspace_id
            )

        now_str = datetime.now(UTC).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO projects (id, workspace_id, name, status, description, data_json, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?);
                """,
                (
                    project.id,
                    project.workspace_id,
                    project.name,
                    project.status.value,
                    project.description,
                    project.model_dump_json(),
                    now_str,
                    now_str,
                ),
            )
            return project
        except sqlite3.IntegrityError as err:
            msg = f"Project with ID '{project.id}' already exists or foreign key violated."
            raise ConflictError(msg) from err

    def get_project(self, project_id: str) -> Project | None:
        conn = self._get_connection()
        cur = conn.execute("SELECT data_json FROM projects WHERE id = ?;", (project_id,))
        row = cur.fetchone()
        if not row:
            return None
        return Project.model_validate_json(row["data_json"])

    def list_projects(self, workspace_id: str, limit: int = 100, offset: int = 0) -> list[Project]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT data_json FROM projects WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
            (workspace_id, limit, offset),
        )
        return [Project.model_validate_json(row["data_json"]) for row in cur.fetchall()]

    def update_project(self, project: Project, expected_revision: int | None = None) -> Project:
        conn = self._get_connection()
        now_str = datetime.now(UTC).isoformat()

        if expected_revision is not None:
            cur = conn.execute(
                """
                UPDATE projects
                SET name = ?, status = ?, description = ?, data_json = ?, revision = revision + 1, updated_at = ?
                WHERE id = ? AND revision = ?;
                """,
                (
                    project.name,
                    project.status.value,
                    project.description,
                    project.model_dump_json(),
                    now_str,
                    project.id,
                    expected_revision,
                ),
            )
            if cur.rowcount == 0:
                existing = self.get_project(project.id)
                if not existing:
                    raise ResourceNotFoundError(f"Project '{project.id}' not found.", "Project", project.id)
                msg = f"Optimistic lock conflict on Project '{project.id}'. Expected revision {expected_revision}."
                raise ConflictError(msg)
        else:
            cur = conn.execute(
                """
                UPDATE projects
                SET name = ?, status = ?, description = ?, data_json = ?, revision = revision + 1, updated_at = ?
                WHERE id = ?;
                """,
                (
                    project.name,
                    project.status.value,
                    project.description,
                    project.model_dump_json(),
                    now_str,
                    project.id,
                ),
            )
            if cur.rowcount == 0:
                raise ResourceNotFoundError(f"Project '{project.id}' not found.", "Project", project.id)
        return project

    def delete_project(self, project_id: str) -> bool:
        conn = self._get_connection()
        cur = conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
        return cur.rowcount > 0

    # =========================================================================
    # BMS Record Operations (with Optimistic Concurrency)
    # =========================================================================

    def create_record(self, record: AnyBMSRecord) -> tuple[AnyBMSRecord, int]:
        project_id = getattr(record, "project_id", None)
        if not project_id:
            msg = f"Record type '{record.record_type}' does not have a project_id."
            raise StorageError(msg)

        if not self.get_project(project_id):
            raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)

        conn = self._get_connection()
        now_str = datetime.now(UTC).isoformat()
        record_json = record.model_dump_json()

        try:
            if record.record_type == "relationship":
                rel: RelationshipRecord = record  # type: ignore[assignment]
                conn.execute(
                    """
                    INSERT INTO relationships (id, project_id, source_id, target_id, relationship_type, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        rel.id,
                        rel.project_id,
                        rel.source_id,
                        rel.target_id,
                        rel.relationship_type.value,
                        record_json,
                        now_str,
                    ),
                )
                return record, 1
            if record.record_type == "checkpoint":
                chk: ResumeCheckpoint = record  # type: ignore[assignment]
                conn.execute(
                    """
                    INSERT INTO checkpoints (id, project_id, task_id, status, data_json, revision, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?);
                    """,
                    (chk.id, chk.project_id, chk.task_id, chk.status.value, record_json, now_str),
                )
                return record, 1
            if record.record_type == "artifact":
                art: ArtifactReference = record  # type: ignore[assignment]
                conn.execute(
                    """
                    INSERT INTO artifact_metadata (id, project_id, artifact_type, uri, content_hash, size_bytes, media_type, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        art.id,
                        art.project_id,
                        art.artifact_type.value,
                        art.uri,
                        art.content_hash,
                        art.size_bytes,
                        art.media_type,
                        record_json,
                        now_str,
                    ),
                )
                return record, 1

            # All other records (knowledge, decision, task, agent, commit) go into bms_records
            conn.execute(
                """
                INSERT INTO bms_records (id, project_id, record_type, data_json, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?);
                """,
                (record.id, project_id, record.record_type, record_json, now_str, now_str),
            )
            return record, 1
        except sqlite3.IntegrityError as err:
            msg = f"Record with ID '{record.id}' already exists in project '{project_id}'."
            raise ConflictError(msg) from err

    def get_record(self, project_id: str, record_id: str) -> tuple[AnyBMSRecord, int] | None:
        conn = self._get_connection()

        # Check bms_records
        cur = conn.execute(
            "SELECT data_json, revision FROM bms_records WHERE project_id = ? AND id = ?;",
            (project_id, record_id),
        )
        row = cur.fetchone()
        if row:
            rec = deserialize_record(row["data_json"])
            return rec, row["revision"]

        # Check checkpoints
        cur = conn.execute(
            "SELECT data_json, revision FROM checkpoints WHERE project_id = ? AND id = ?;",
            (project_id, record_id),
        )
        row = cur.fetchone()
        if row:
            rec = deserialize_record(row["data_json"])
            return rec, row["revision"]

        # Check relationships
        cur = conn.execute(
            "SELECT data_json FROM relationships WHERE project_id = ? AND id = ?;",
            (project_id, record_id),
        )
        row = cur.fetchone()
        if row:
            rec = deserialize_record(row["data_json"])
            return rec, 1

        # Check artifact_metadata
        cur = conn.execute(
            "SELECT data_json FROM artifact_metadata WHERE project_id = ? AND id = ?;",
            (project_id, record_id),
        )
        row = cur.fetchone()
        if row:
            rec = deserialize_record(row["data_json"])
            return rec, 1

        return None

    def list_records(
        self,
        project_id: str,
        record_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[AnyBMSRecord, int]]:
        conn = self._get_connection()
        results: list[tuple[AnyBMSRecord, int]] = []

        if record_type == "checkpoint":
            cur = conn.execute(
                "SELECT data_json, revision FROM checkpoints WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
                (project_id, limit, offset),
            )
            return [(deserialize_record(r["data_json"]), r["revision"]) for r in cur.fetchall()]

        if record_type == "relationship":
            cur = conn.execute(
                "SELECT data_json FROM relationships WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
                (project_id, limit, offset),
            )
            return [(deserialize_record(r["data_json"]), 1) for r in cur.fetchall()]

        if record_type == "artifact":
            cur = conn.execute(
                "SELECT data_json FROM artifact_metadata WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
                (project_id, limit, offset),
            )
            return [(deserialize_record(r["data_json"]), 1) for r in cur.fetchall()]

        if record_type:
            cur = conn.execute(
                "SELECT data_json, revision FROM bms_records WHERE project_id = ? AND record_type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
                (project_id, record_type, limit, offset),
            )
            return [(deserialize_record(r["data_json"]), r["revision"]) for r in cur.fetchall()]

        # All records
        cur = conn.execute(
            "SELECT data_json, revision FROM bms_records WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
            (project_id, limit, offset),
        )
        results.extend([(deserialize_record(r["data_json"]), r["revision"]) for r in cur.fetchall()])

        cur = conn.execute(
            "SELECT data_json, revision FROM checkpoints WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
            (project_id, limit, offset),
        )
        results.extend([(deserialize_record(r["data_json"]), r["revision"]) for r in cur.fetchall()])

        cur = conn.execute(
            "SELECT data_json FROM relationships WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
            (project_id, limit, offset),
        )
        results.extend([(deserialize_record(r["data_json"]), 1) for r in cur.fetchall()])

        cur = conn.execute(
            "SELECT data_json FROM artifact_metadata WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?;",
            (project_id, limit, offset),
        )
        results.extend([(deserialize_record(r["data_json"]), 1) for r in cur.fetchall()])

        return results

    def update_record(
        self,
        record: AnyBMSRecord,
        expected_revision: int,
    ) -> tuple[AnyBMSRecord, int]:
        project_id = getattr(record, "project_id", None)
        if not project_id:
            msg = f"Record '{record.id}' missing project_id"
            raise StorageError(msg)

        conn = self._get_connection()
        now_str = datetime.now(UTC).isoformat()
        record_json = record.model_dump_json()

        table = "checkpoints" if record.record_type == "checkpoint" else "bms_records"

        cur = conn.execute(
            f"""
            UPDATE {table}
            SET data_json = ?, revision = revision + 1, updated_at = ?
            WHERE project_id = ? AND id = ? AND revision = ?;
            """,
            (record_json, now_str, project_id, record.id, expected_revision),
        )

        if cur.rowcount == 0:
            existing = self.get_record(project_id, record.id)
            if not existing:
                raise ResourceNotFoundError(
                    f"Record '{record.id}' not found in project '{project_id}'.",
                    "Record",
                    record.id,
                )
            current_rev = existing[1]
            msg = f"Conflict updating record '{record.id}'. Current revision is {current_rev}, expected {expected_revision}."
            raise ConflictError(
                msg,
                details={"current_revision": current_rev, "expected_revision": expected_revision},
            )

        return record, expected_revision + 1

    def delete_record(
        self,
        project_id: str,
        record_id: str,
        expected_revision: int | None = None,
    ) -> bool:
        conn = self._get_connection()

        for table in ("bms_records", "checkpoints", "relationships", "artifact_metadata"):
            if expected_revision is not None and table in ("bms_records", "checkpoints"):
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE project_id = ? AND id = ? AND revision = ?;",
                    (project_id, record_id, expected_revision),
                )
            else:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE project_id = ? AND id = ?;",
                    (project_id, record_id),
                )
            if cur.rowcount > 0:
                return True

        return False

    # =========================================================================
    # Package Import and Export
    # =========================================================================

    def save_package(self, package: BarsaMemoryPackage) -> None:
        """Atomically persist an entire package in a single database transaction."""
        errors = validate_bms_package(package)
        if errors:
            msg = f"Cannot import invalid package: {'; '.join(errors)}"
            raise StorageError(msg, details={"validation_errors": errors})

        conn = self._get_connection()

        # Check existing project collision
        if self.get_project(package.project.id):
            msg = f"Cannot import package: Project '{package.project.id}' already exists in database."
            raise ConflictError(msg)

        conn.execute("BEGIN IMMEDIATE;")
        try:
            # 1. Upsert Workspace
            now_str = datetime.now(UTC).isoformat()
            conn.execute(
                """
                INSERT INTO workspaces (id, name, owner_id, description, data_json, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET data_json=excluded.data_json, updated_at=excluded.updated_at;
                """,
                (
                    package.workspace.id,
                    package.workspace.name,
                    package.workspace.owner_id,
                    package.workspace.description,
                    package.workspace.model_dump_json(),
                    now_str,
                    now_str,
                ),
            )

            # 2. Insert Project
            conn.execute(
                """
                INSERT INTO projects (id, workspace_id, name, status, description, data_json, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?);
                """,
                (
                    package.project.id,
                    package.project.workspace_id,
                    package.project.name,
                    package.project.status.value,
                    package.project.description,
                    package.project.model_dump_json(),
                    now_str,
                    now_str,
                ),
            )

            # 3. Insert Records
            record_groups = [
                ("knowledge", package.records.knowledge),
                ("decision", package.records.decisions),
                ("task", package.records.tasks),
                ("agent", package.records.agents),
            ]

            for _, items in record_groups:
                for item in items:
                    conn.execute(
                        """
                        INSERT INTO bms_records (id, project_id, record_type, data_json, revision, created_at, updated_at)
                        VALUES (?, ?, ?, ?, 1, ?, ?);
                        """,
                        (
                            item.id,
                            package.project.id,
                            item.record_type,
                            item.model_dump_json(),
                            now_str,
                            now_str,
                        ),
                    )

            # 4. Insert Artifacts
            for art in package.records.artifacts:
                conn.execute(
                    """
                    INSERT INTO artifact_metadata (id, project_id, artifact_type, uri, content_hash, size_bytes, media_type, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        art.id,
                        package.project.id,
                        art.artifact_type.value,
                        art.uri,
                        art.content_hash,
                        art.size_bytes,
                        art.media_type,
                        art.model_dump_json(),
                        now_str,
                    ),
                )

            # 5. Insert Checkpoints
            for chk in package.records.checkpoints:
                conn.execute(
                    """
                    INSERT INTO checkpoints (id, project_id, task_id, status, data_json, revision, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?);
                    """,
                    (
                        chk.id,
                        package.project.id,
                        chk.task_id,
                        chk.status.value,
                        chk.model_dump_json(),
                        now_str,
                    ),
                )

            # 6. Insert Relationships
            for rel in package.relationships:
                conn.execute(
                    """
                    INSERT INTO relationships (id, project_id, source_id, target_id, relationship_type, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        rel.id,
                        package.project.id,
                        rel.source_id,
                        rel.target_id,
                        rel.relationship_type.value,
                        rel.model_dump_json(),
                        now_str,
                    ),
                )

            # 7. Insert Commits (if present)
            for cmt in package.commits:
                conn.execute(
                    """
                    INSERT INTO bms_records (id, project_id, record_type, data_json, revision, created_at, updated_at)
                    VALUES (?, ?, 'commit', ?, 1, ?, ?);
                    """,
                    (cmt.id, package.project.id, cmt.model_dump_json(), now_str, now_str),
                )

            conn.execute("COMMIT;")
            logger.info("Successfully saved package for project '%s'", package.project.id)
        except Exception as err:
            conn.execute("ROLLBACK;")
            msg = f"Failed to save package for project '{package.project.id}': {err}"
            raise StorageError(msg) from err

    def load_package(self, project_id: str) -> BarsaMemoryPackage | None:
        """Construct a validated BarsaMemoryPackage snapshot for a project."""
        project = self.get_project(project_id)
        if not project:
            return None

        workspace = self.get_workspace(project.workspace_id)
        if not workspace:
            raise StorageError(
                f"Corrupted relationship: Workspace '{project.workspace_id}' missing for project '{project_id}'."
            )

        conn = self._get_connection()

        # Query records
        knowledge_list: list[KnowledgeRecord] = []
        decision_list: list[DecisionRecord] = []
        task_list: list[TaskRecord] = []
        agent_list: list[Any] = []
        commit_list: list[MemoryCommit] = []

        cur = conn.execute("SELECT data_json, record_type FROM bms_records WHERE project_id = ?;", (project_id,))
        for row in cur.fetchall():
            rec = deserialize_record(row["data_json"])
            t = row["record_type"]
            if t == "knowledge":
                knowledge_list.append(rec)  # type: ignore[arg-type]
            elif t == "decision":
                decision_list.append(rec)  # type: ignore[arg-type]
            elif t == "task":
                task_list.append(rec)  # type: ignore[arg-type]
            elif t == "agent":
                agent_list.append(rec)
            elif t == "commit":
                commit_list.append(rec)  # type: ignore[arg-type]

        # Artifacts
        artifact_list: list[ArtifactReference] = []
        cur = conn.execute("SELECT data_json FROM artifact_metadata WHERE project_id = ?;", (project_id,))
        for row in cur.fetchall():
            artifact_list.append(ArtifactReference.model_validate_json(row["data_json"]))

        # Checkpoints
        checkpoint_list: list[ResumeCheckpoint] = []
        cur = conn.execute(
            "SELECT data_json FROM checkpoints WHERE project_id = ? ORDER BY created_at DESC;",
            (project_id,),
        )
        for row in cur.fetchall():
            checkpoint_list.append(ResumeCheckpoint.model_validate_json(row["data_json"]))

        # Relationships
        rel_list: list[RelationshipRecord] = []
        cur = conn.execute("SELECT data_json FROM relationships WHERE project_id = ?;", (project_id,))
        for row in cur.fetchall():
            rel_list.append(RelationshipRecord.model_validate_json(row["data_json"]))

        latest_chk_id = checkpoint_list[0].id if checkpoint_list else None

        pkg = BarsaMemoryPackage(
            workspace=workspace,
            project=project,
            records=PackageRecords(
                knowledge=knowledge_list,
                decisions=decision_list,
                tasks=task_list,
                agents=agent_list,
                artifacts=artifact_list,
                checkpoints=checkpoint_list,
            ),
            relationships=rel_list,
            latest_checkpoint_id=latest_chk_id,
            commits=commit_list,
        )

        return pkg

    def get_storage_stats(self) -> dict[str, Any]:
        """Return database statistics, table counts, and disk usage."""
        conn = self._get_connection()
        counts: dict[str, int] = {}
        for table in (
            "workspaces",
            "projects",
            "bms_records",
            "relationships",
            "checkpoints",
            "artifact_metadata",
        ):
            cur = conn.execute(f"SELECT COUNT(*) as c FROM {table};")
            counts[table] = cur.fetchone()["c"]

        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "db_path": str(self.db_path),
            "db_size_bytes": db_size,
            "counts": counts,
            "artifacts_dir": str(self.artifacts_dir),
        }
