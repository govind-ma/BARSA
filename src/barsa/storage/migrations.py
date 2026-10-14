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
    (
        2,
        "version_control_schema",
        """
        -- Commits table
        CREATE TABLE IF NOT EXISTS commits (
            commit_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            parent_commit_ids_json TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            changes_json TEXT NOT NULL,
            resulting_state_hash TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            bms_version TEXT NOT NULL,
            PRIMARY KEY (project_id, commit_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_commits_project ON commits(project_id, created_at);

        -- Commit parent DAG edges table
        CREATE TABLE IF NOT EXISTS commit_parents (
            project_id TEXT NOT NULL,
            commit_id TEXT NOT NULL,
            parent_id TEXT NOT NULL,
            PRIMARY KEY (project_id, commit_id, parent_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_commit_parents ON commit_parents(project_id, parent_id);

        -- Historical record state index per commit (allows O(1) state reconstruction without full replay)
        CREATE TABLE IF NOT EXISTS commit_record_states (
            project_id TEXT NOT NULL,
            commit_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            record_data_json TEXT,  -- NULL if deleted
            PRIMARY KEY (project_id, commit_id, record_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_commit_record ON commit_record_states(project_id, record_id, commit_id);

        -- Branches table
        CREATE TABLE IF NOT EXISTS branches (
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            head_commit_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (project_id, name),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        -- Merge proposals table
        CREATE TABLE IF NOT EXISTS merge_proposals (
            proposal_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            source_branch TEXT NOT NULL,
            target_branch TEXT NOT NULL,
            source_head TEXT NOT NULL,
            target_head TEXT NOT NULL,
            author_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (project_id, proposal_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_proposals_status ON merge_proposals(project_id, status);

        -- Review comments table
        CREATE TABLE IF NOT EXISTS review_comments (
            comment_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            proposal_id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_type TEXT NOT NULL,
            content TEXT NOT NULL,
            record_id TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (project_id, comment_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_review_comments_proposal ON review_comments(project_id, proposal_id);

        -- Reviews table
        CREATE TABLE IF NOT EXISTS reviews (
            review_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            proposal_id TEXT NOT NULL,
            reviewer_id TEXT NOT NULL,
            reviewer_type TEXT NOT NULL,
            status TEXT NOT NULL,  -- approved, changes_requested, rejected
            summary TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (project_id, review_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_reviews_proposal ON reviews(project_id, proposal_id);

        -- Conflicts table
        CREATE TABLE IF NOT EXISTS conflicts (
            conflict_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            proposal_id TEXT,
            source_branch TEXT NOT NULL,
            target_branch TEXT NOT NULL,
            affected_record_id TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            base_value_json TEXT,
            source_value_json TEXT,
            target_value_json TEXT,
            resolution_status TEXT NOT NULL DEFAULT 'unresolved',
            resolved_by TEXT,
            resolution_timestamp TEXT,
            resolved_value_json TEXT,
            PRIMARY KEY (project_id, conflict_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_conflicts_proposal ON conflicts(project_id, proposal_id);
        CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(project_id, resolution_status);
        """,
    ),
    (
        3,
        "knowledge_graph_outbox_schema",
        """
        -- Transactional outbox table for event-driven graph projections
        CREATE TABLE IF NOT EXISTS graph_outbox (
            event_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            commit_id TEXT NOT NULL,
            event_type TEXT NOT NULL,  -- 'COMMIT_APPROVED', 'REBUILD_REQUESTED', etc.
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',  -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL,
            processed_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_graph_outbox_status ON graph_outbox(project_id, status, created_at);
        CREATE INDEX IF NOT EXISTS idx_graph_outbox_commit ON graph_outbox(project_id, commit_id);

        -- Graph projection metadata tracking per project
        CREATE TABLE IF NOT EXISTS graph_projections (
            project_id TEXT PRIMARY KEY,
            applied_commit_id TEXT NOT NULL,
            applied_revision INTEGER NOT NULL DEFAULT 0,
            applied_state_hash TEXT NOT NULL,
            node_count INTEGER NOT NULL DEFAULT 0,
            relationship_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'UP_TO_DATE',  -- 'UP_TO_DATE', 'LAGGING', 'REBUILDING', 'ERROR'
            last_projected_at TEXT NOT NULL,
            last_error TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """,
    ),
    (
        4,
        "coordination_engine_schema",
        """
        -- Multi-Agent Coordination Schema (Phase 9)
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            claimed_capabilities_json TEXT NOT NULL DEFAULT '[]',
            verified_capabilities_json TEXT NOT NULL DEFAULT '[]',
            supported_tools_json TEXT NOT NULL DEFAULT '[]',
            allowed_projects_json TEXT NOT NULL DEFAULT '["*"]',
            availability_status TEXT NOT NULL DEFAULT 'available',
            last_heartbeat TEXT NOT NULL,
            current_workload INTEGER NOT NULL DEFAULT 0,
            maximum_concurrent_tasks INTEGER NOT NULL DEFAULT 2,
            registered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(availability_status, last_heartbeat);

        CREATE TABLE IF NOT EXISTS coordination_tasks (
            task_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            required_capabilities_json TEXT NOT NULL DEFAULT '[]',
            required_tools_json TEXT NOT NULL DEFAULT '[]',
            min_verified_level TEXT NOT NULL DEFAULT 'claimed',
            priority TEXT NOT NULL DEFAULT 'medium',
            dependencies_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_agent_id TEXT,
            lease_token TEXT,
            lease_expires_at TEXT,
            heartbeat_timeout_seconds INTEGER NOT NULL DEFAULT 60,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            failure_reason TEXT,
            result_json TEXT,
            resource_usage_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_coord_tasks_status ON coordination_tasks(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_coord_tasks_assigned ON coordination_tasks(assigned_agent_id, status);
        CREATE INDEX IF NOT EXISTS idx_coord_tasks_lease ON coordination_tasks(lease_expires_at);

        CREATE TABLE IF NOT EXISTS collaboration_messages (
            message_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_id TEXT,
            author_agent_id TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            related_record_refs_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_collab_messages ON collaboration_messages(project_id, task_id, created_at);

        CREATE TABLE IF NOT EXISTS coordination_issues (
            issue_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            author_agent_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            required_capabilities_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'open',
            resolver_agent_id TEXT,
            resolution_proposal_json TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_coord_issues ON coordination_issues(project_id, task_id, status);

        CREATE TABLE IF NOT EXISTS help_requests (
            request_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            issue_id TEXT,
            requester_agent_id TEXT NOT NULL,
            target_agent_id TEXT,
            required_capabilities_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'open',
            assigned_helper_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_help_requests ON help_requests(project_id, status);

        CREATE TABLE IF NOT EXISTS coordination_events (
            event_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            agent_id TEXT,
            task_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_coord_events ON coordination_events(project_id, event_type, timestamp);
        """,
    ),
    (
        5,
        "security_engine_schema",
        """
        -- Principals table: Human users, AI agents, and service accounts
        CREATE TABLE IF NOT EXISTS principals (
            principal_id TEXT PRIMARY KEY,
            principal_type TEXT NOT NULL, -- 'human', 'agent', 'service'
            display_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_superuser INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_principals_type ON principals(principal_type, is_active);

        -- Identities table: Authentication credentials (passwords, external IDP links)
        CREATE TABLE IF NOT EXISTS identities (
            identity_id TEXT PRIMARY KEY,
            principal_id TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'local', -- 'local', 'oidc', etc.
            identifier TEXT NOT NULL, -- username or email
            password_hash TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE CASCADE,
            UNIQUE (provider, identifier)
        );
        CREATE INDEX IF NOT EXISTS idx_identities_lookup ON identities(provider, identifier);

        -- Credentials table: Cryptographic API keys and tokens for agents and service principals
        CREATE TABLE IF NOT EXISTS credentials (
            credential_id TEXT PRIMARY KEY,
            principal_id TEXT NOT NULL,
            name TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            scopes_json TEXT NOT NULL DEFAULT '[]',
            allowed_projects_json TEXT NOT NULL DEFAULT '["*"]',
            expires_at TEXT,
            revoked INTEGER NOT NULL DEFAULT 0,
            revoked_at TEXT,
            last_used_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_credentials_lookup ON credentials(key_prefix, revoked);

        -- Sessions table: Active human or service sessions
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            principal_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash, revoked);

        -- Workspace memberships table: Role-based access control per workspace
        CREATE TABLE IF NOT EXISTS workspace_memberships (
            workspace_id TEXT NOT NULL,
            principal_id TEXT NOT NULL,
            role TEXT NOT NULL, -- 'owner', 'admin', 'editor', 'reviewer', 'viewer'
            granted_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, principal_id),
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
            FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_workspace_members ON workspace_memberships(workspace_id, role);

        -- Project grants table: Project-level role overrides or scoped access
        CREATE TABLE IF NOT EXISTS project_grants (
            project_id TEXT NOT NULL,
            principal_id TEXT NOT NULL,
            role TEXT NOT NULL, -- 'owner', 'admin', 'editor', 'reviewer', 'viewer'
            granted_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (project_id, principal_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_project_grants ON project_grants(project_id, principal_id);

        -- Agent scopes table: Fine-grained permissions per agent per project
        CREATE TABLE IF NOT EXISTS agent_scopes (
            agent_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            scope TEXT NOT NULL,
            granted_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (agent_id, project_id, scope)
        );
        CREATE INDEX IF NOT EXISTS idx_agent_scopes ON agent_scopes(agent_id, project_id);

        -- Audit events table: Append-only security audit log
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            principal_id TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            outcome TEXT NOT NULL, -- 'allow', 'deny'
            correlation_id TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_audit_events_lookup ON audit_events(principal_id, action, timestamp);

        -- Security policies table: Configurable workspace policies
        CREATE TABLE IF NOT EXISTS security_policies (
            policy_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        );

        -- Migration safeguard: Ensure existing workspace owners are registered as principals and owners
        INSERT OR IGNORE INTO principals (principal_id, principal_type, display_name, is_active, is_superuser, created_at, updated_at)
        SELECT DISTINCT owner_id, 'human', owner_id, 1, 1, datetime('now', 'utc'), datetime('now', 'utc')
        FROM workspaces
        WHERE owner_id IS NOT NULL AND owner_id != '';

        INSERT OR IGNORE INTO workspace_memberships (workspace_id, principal_id, role, granted_by, created_at, updated_at)
        SELECT DISTINCT id, owner_id, 'owner', owner_id, datetime('now', 'utc'), datetime('now', 'utc')
        FROM workspaces
        WHERE owner_id IS NOT NULL AND owner_id != '';
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
