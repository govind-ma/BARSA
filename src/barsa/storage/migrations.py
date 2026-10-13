"""SQLite schema migrations and integrity check manager."""

import logging
import sqlite3
from typing import Any

from barsa.core.exceptions import StorageError

logger = logging.getLogger("barsa.storage.migrations")

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "initial_bms_schema",
        """
        -- Workspaces table
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            description TEXT,
            data_json TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Projects table
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            description TEXT,
            data_json TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_projects_workspace ON projects(workspace_id);

        -- Generic BMS records table with JSON document and indexed attributes
        CREATE TABLE IF NOT EXISTS bms_records (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (project_id, id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_bms_records_type ON bms_records(project_id, record_type);
        CREATE INDEX IF NOT EXISTS idx_bms_records_created ON bms_records(project_id, created_at);

        -- Relationships table
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (project_id, id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(project_id, source_id);
        CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(project_id, target_id);
        CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(project_id, relationship_type);

        -- Checkpoints table
        CREATE TABLE IF NOT EXISTS checkpoints (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            status TEXT NOT NULL,
            data_json TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            PRIMARY KEY (project_id, id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_checkpoints_task ON checkpoints(project_id, task_id);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON checkpoints(project_id, status);

        -- Artifact metadata table
        CREATE TABLE IF NOT EXISTS artifact_metadata (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            uri TEXT NOT NULL,
            content_hash TEXT,
            size_bytes INTEGER,
            media_type TEXT,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (project_id, id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_artifact_hash ON artifact_metadata(content_hash);
        """,
    ),
]


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply any unapplied database migrations within a transaction."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
        );
        """
    )
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
    applied_versions = {row[0] for row in cursor.fetchall()}

    for version, name, sql in MIGRATIONS:
        if version not in applied_versions:
            logger.info("Applying migration %d: %s", version, name)
            try:
                cursor.executescript(sql)
                cursor.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?);",
                    (version, name),
                )
                conn.commit()
                logger.info("Successfully applied migration %d: %s", version, name)
            except Exception as err:
                conn.rollback()
                msg = f"Failed to apply migration {version} ({name}): {err}"
                raise StorageError(msg) from err


def verify_database_integrity(conn: sqlite3.Connection) -> dict[str, Any]:
    """Execute SQLite PRAGMA integrity_check and foreign_key_check."""
    cursor = conn.cursor()

    cursor.execute("PRAGMA integrity_check;")
    integrity_rows = cursor.fetchall()
    integrity_ok = len(integrity_rows) == 1 and integrity_rows[0][0].lower() == "ok"

    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()

    return {
        "integrity_ok": integrity_ok,
        "integrity_messages": [row[0] for row in integrity_rows],
        "foreign_key_violations": len(fk_violations),
        "fk_details": [str(v) for v in fk_violations],
    }
