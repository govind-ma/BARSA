"""ACID SQLite storage adapter for security, authentication, and authorization."""

from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from barsa.core.exceptions import ConflictError, ResourceNotFoundError
from barsa.security.models import (
    AgentCredentialResponse,
    AuditEventRecord,
    AuthenticatedPrincipal,
    PrincipalType,
    ProjectGrantResponse,
    WorkspaceMembershipResponse,
    WorkspaceRole,
)

if TYPE_CHECKING:
    from barsa.storage.sqlite import SQLiteStorageProvider


class SecurityStorage:
    """Storage operations for users, principals, credentials, permissions, and audit logs."""

    def __init__(self, storage: SQLiteStorageProvider) -> None:
        self.storage = storage

    def _get_conn(self) -> sqlite3.Connection:
        return self.storage._get_connection()

    def _rollback(self, conn: sqlite3.Connection) -> None:
        with contextlib.suppress(Exception):
            conn.execute("ROLLBACK;")

    # =========================================================================
    # Principals
    # =========================================================================

    def create_principal(self, principal: AuthenticatedPrincipal) -> AuthenticatedPrincipal:
        """Insert a new principal."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO principals (
                    principal_id, principal_type, display_name, is_active, is_superuser,
                    created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    principal.principal_id,
                    principal.principal_type.value,
                    principal.display_name or principal.principal_id,
                    1 if not hasattr(principal, "is_active") or getattr(principal, "is_active", True) else 0,
                    1 if principal.is_superuser else 0,
                    now,
                    now,
                    json.dumps(principal.metadata),
                ),
            )
            conn.commit()
            return principal
        except sqlite3.IntegrityError as err:
            self._rollback(conn)
            raise ConflictError(f"Principal '{principal.principal_id}' already exists") from err

    def get_principal(self, principal_id: str) -> AuthenticatedPrincipal | None:
        """Fetch principal by ID."""
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM principals WHERE principal_id = ?;", (principal_id,))
        row = cur.fetchone()
        if not row:
            return None

        return AuthenticatedPrincipal(
            principal_id=row["principal_id"],
            principal_type=PrincipalType(row["principal_type"]),
            display_name=row["display_name"],
            is_superuser=bool(row["is_superuser"]),
            metadata=json.loads(row["metadata_json"] or "{}"),
            authenticated_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_principals(
        self, principal_type: PrincipalType | None = None, is_active: bool | None = None
    ) -> list[AuthenticatedPrincipal]:
        """List principals with optional filters."""
        conn = self._get_conn()
        sql = "SELECT * FROM principals WHERE 1=1"
        params: list[Any] = []
        if principal_type:
            sql += " AND principal_type = ?"
            params.append(principal_type.value)
        if is_active is not None:
            sql += " AND is_active = ?"
            params.append(1 if is_active else 0)
        sql += " ORDER BY created_at DESC;"

        cur = conn.execute(sql, tuple(params))
        res: list[AuthenticatedPrincipal] = []
        for row in cur.fetchall():
            res.append(
                AuthenticatedPrincipal(
                    principal_id=row["principal_id"],
                    principal_type=PrincipalType(row["principal_type"]),
                    display_name=row["display_name"],
                    is_superuser=bool(row["is_superuser"]),
                    metadata=json.loads(row["metadata_json"] or "{}"),
                    authenticated_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return res

    def disable_principal(self, principal_id: str) -> bool:
        """Deactivate a principal."""
        conn = self._get_conn()
        cur = conn.execute(
            "UPDATE principals SET is_active = 0, updated_at = ? WHERE principal_id = ?;",
            (datetime.now(UTC).isoformat(), principal_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def delete_principal(self, principal_id: str) -> bool:
        """Delete a principal and cascade associated data."""
        conn = self._get_conn()
        cur = conn.execute("DELETE FROM principals WHERE principal_id = ?;", (principal_id,))
        conn.commit()
        return cur.rowcount > 0

    # =========================================================================
    # Identities & Human Password Logins
    # =========================================================================

    def create_identity(
        self,
        principal_id: str,
        identifier: str,
        password_hash: str,
        provider: str = "local",
    ) -> str:
        """Register local password identity for a principal."""
        identity_id = f"ident-{uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO identities (
                    identity_id, principal_id, provider, identifier, password_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (identity_id, principal_id, provider, identifier, password_hash, now, now),
            )
            conn.commit()
            return identity_id
        except sqlite3.IntegrityError as err:
            self._rollback(conn)
            raise ConflictError(f"Identifier '{identifier}' already registered") from err

    def get_identity_by_identifier(self, identifier: str, provider: str = "local") -> dict[str, Any] | None:
        """Retrieve identity row including password_hash for authentication."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM identities WHERE provider = ? AND identifier = ?;",
            (provider, identifier),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def update_password(self, principal_id: str, new_password_hash: str) -> bool:
        """Update password hash for a principal's local identity."""
        conn = self._get_conn()
        cur = conn.execute(
            "UPDATE identities SET password_hash = ?, updated_at = ? WHERE principal_id = ? AND provider = 'local';",
            (new_password_hash, datetime.now(UTC).isoformat(), principal_id),
        )
        conn.commit()
        return cur.rowcount > 0

    # =========================================================================
    # Credentials (Agent & Service API Keys)
    # =========================================================================

    def create_credential(
        self,
        principal_id: str,
        name: str,
        key_prefix: str,
        key_hash: str,
        salt: str,
        scopes: list[str],
        allowed_projects: list[str],
        expires_at: datetime | None,
    ) -> AgentCredentialResponse:
        """Save a new hashed API key credential."""
        credential_id = f"cred-{uuid4().hex[:12]}"
        now = datetime.now(UTC)
        conn = self._get_conn()

        conn.execute(
            """
            INSERT INTO credentials (
                credential_id, principal_id, name, key_prefix, key_hash, salt,
                scopes_json, allowed_projects_json, expires_at, revoked, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?);
            """,
            (
                credential_id,
                principal_id,
                name,
                key_prefix,
                key_hash,
                salt,
                json.dumps(scopes),
                json.dumps(allowed_projects),
                expires_at.isoformat() if expires_at else None,
                now.isoformat(),
            ),
        )
        conn.commit()
        return AgentCredentialResponse(
            credential_id=credential_id,
            principal_id=principal_id,
            name=name,
            key_prefix=key_prefix,
            scopes=scopes,
            allowed_projects=allowed_projects,
            expires_at=expires_at,
            revoked=False,
            revoked_at=None,
            last_used_at=None,
            created_at=now,
        )

    def find_active_credentials_by_prefix(self, key_prefix: str) -> list[dict[str, Any]]:
        """Fetch active credentials matching a prefix for verification."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM credentials WHERE key_prefix = ? AND revoked = 0;",
            (key_prefix,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_credential_by_id(self, credential_id: str) -> AgentCredentialResponse | None:
        """Fetch public credential metadata by ID."""
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM credentials WHERE credential_id = ?;", (credential_id,))
        row = cur.fetchone()
        if not row:
            return None
        return AgentCredentialResponse(
            credential_id=row["credential_id"],
            principal_id=row["principal_id"],
            name=row["name"],
            key_prefix=row["key_prefix"],
            scopes=json.loads(row["scopes_json"] or "[]"),
            allowed_projects=json.loads(row["allowed_projects_json"] or '["*"]'),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            revoked=bool(row["revoked"]),
            revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
            last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_credentials_for_principal(self, principal_id: str) -> list[AgentCredentialResponse]:
        """List all credentials for an agent or service principal."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM credentials WHERE principal_id = ? ORDER BY created_at DESC;",
            (principal_id,),
        )
        res: list[AgentCredentialResponse] = []
        for row in cur.fetchall():
            res.append(
                AgentCredentialResponse(
                    credential_id=row["credential_id"],
                    principal_id=row["principal_id"],
                    name=row["name"],
                    key_prefix=row["key_prefix"],
                    scopes=json.loads(row["scopes_json"] or "[]"),
                    allowed_projects=json.loads(row["allowed_projects_json"] or '["*"]'),
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                    revoked=bool(row["revoked"]),
                    revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
                    last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return res

    def revoke_credential(self, credential_id: str) -> bool:
        """Mark a credential as revoked immediately."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        cur = conn.execute(
            "UPDATE credentials SET revoked = 1, revoked_at = ? WHERE credential_id = ? AND revoked = 0;",
            (now, credential_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def rotate_credential(
        self,
        credential_id: str,
        new_prefix: str,
        new_hash: str,
        new_salt: str,
    ) -> AgentCredentialResponse:
        """Rotate existing credential with new key material while preserving scopes and metadata."""
        conn = self._get_conn()
        cur = conn.execute(
            """
            UPDATE credentials
            SET key_prefix = ?, key_hash = ?, salt = ?, revoked = 0, revoked_at = NULL
            WHERE credential_id = ?;
            """,
            (new_prefix, new_hash, new_salt, credential_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ResourceNotFoundError(f"Credential '{credential_id}' not found")
        cred = self.get_credential_by_id(credential_id)
        if not cred:
            raise ResourceNotFoundError(f"Credential '{credential_id}' not found")
        return cred

    def record_credential_used(self, credential_id: str) -> None:
        """Update last_used timestamp for credential."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE credentials SET last_used_at = ? WHERE credential_id = ?;",
            (datetime.now(UTC).isoformat(), credential_id),
        )
        conn.commit()

    # =========================================================================
    # Workspace Memberships & Project Grants
    # =========================================================================

    def add_workspace_membership(
        self,
        workspace_id: str,
        principal_id: str,
        role: WorkspaceRole,
        granted_by: str,
    ) -> WorkspaceMembershipResponse:
        """Add or update a principal's role in a workspace."""
        conn = self._get_conn()
        now = datetime.now(UTC)

        conn.execute(
            """
            INSERT INTO workspace_memberships (workspace_id, principal_id, role, granted_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (workspace_id, principal_id) DO UPDATE SET
                role = excluded.role,
                granted_by = excluded.granted_by,
                updated_at = excluded.updated_at;
            """,
            (workspace_id, principal_id, role.value, granted_by, now.isoformat(), now.isoformat()),
        )
        conn.commit()
        return WorkspaceMembershipResponse(
            workspace_id=workspace_id,
            principal_id=principal_id,
            role=role,
            granted_by=granted_by,
            created_at=now,
            updated_at=now,
        )

    def get_workspace_membership(self, workspace_id: str, principal_id: str) -> WorkspaceMembershipResponse | None:
        """Retrieve workspace membership for principal."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM workspace_memberships WHERE workspace_id = ? AND principal_id = ?;",
            (workspace_id, principal_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return WorkspaceMembershipResponse(
            workspace_id=row["workspace_id"],
            principal_id=row["principal_id"],
            role=WorkspaceRole(row["role"]),
            granted_by=row["granted_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_workspace_members(self, workspace_id: str) -> list[WorkspaceMembershipResponse]:
        """List all members of a workspace."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM workspace_memberships WHERE workspace_id = ? ORDER BY created_at ASC;",
            (workspace_id,),
        )
        return [
            WorkspaceMembershipResponse(
                workspace_id=r["workspace_id"],
                principal_id=r["principal_id"],
                role=WorkspaceRole(r["role"]),
                granted_by=r["granted_by"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in cur.fetchall()
        ]

    def remove_workspace_membership(self, workspace_id: str, principal_id: str) -> bool:
        """Remove a member from a workspace."""
        conn = self._get_conn()
        cur = conn.execute(
            "DELETE FROM workspace_memberships WHERE workspace_id = ? AND principal_id = ?;",
            (workspace_id, principal_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def add_project_grant(
        self,
        project_id: str,
        principal_id: str,
        role: WorkspaceRole,
        granted_by: str,
    ) -> ProjectGrantResponse:
        """Add or update a project-level role grant."""
        conn = self._get_conn()
        now = datetime.now(UTC)

        conn.execute(
            """
            INSERT INTO project_grants (project_id, principal_id, role, granted_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (project_id, principal_id) DO UPDATE SET
                role = excluded.role,
                granted_by = excluded.granted_by,
                updated_at = excluded.updated_at;
            """,
            (project_id, principal_id, role.value, granted_by, now.isoformat(), now.isoformat()),
        )
        conn.commit()
        return ProjectGrantResponse(
            project_id=project_id,
            principal_id=principal_id,
            role=role,
            granted_by=granted_by,
            created_at=now,
            updated_at=now,
        )

    def get_project_grant(self, project_id: str, principal_id: str) -> ProjectGrantResponse | None:
        """Retrieve project-specific grant."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM project_grants WHERE project_id = ? AND principal_id = ?;",
            (project_id, principal_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return ProjectGrantResponse(
            project_id=row["project_id"],
            principal_id=row["principal_id"],
            role=WorkspaceRole(row["role"]),
            granted_by=row["granted_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def remove_project_grant(self, project_id: str, principal_id: str) -> bool:
        """Remove a project grant."""
        conn = self._get_conn()
        cur = conn.execute(
            "DELETE FROM project_grants WHERE project_id = ? AND principal_id = ?;",
            (project_id, principal_id),
        )
        conn.commit()
        return cur.rowcount > 0

    # =========================================================================
    # Agent Scopes
    # =========================================================================

    def grant_agent_scope(self, agent_id: str, project_id: str, scope: str, granted_by: str) -> None:
        """Grant a fine-grained scope to an agent on a project."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO agent_scopes (agent_id, project_id, scope, granted_by, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (agent_id, project_id, scope, granted_by, now),
        )
        conn.commit()

    def get_agent_scopes(self, agent_id: str, project_id: str) -> list[str]:
        """Fetch scopes granted to an agent on a specific project."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT scope FROM agent_scopes WHERE agent_id = ? AND (project_id = ? OR project_id = '*');",
            (agent_id, project_id),
        )
        return [row[0] for row in cur.fetchall()]

    def revoke_agent_scope(self, agent_id: str, project_id: str, scope: str) -> bool:
        """Revoke a specific scope from an agent."""
        conn = self._get_conn()
        cur = conn.execute(
            "DELETE FROM agent_scopes WHERE agent_id = ? AND project_id = ? AND scope = ?;",
            (agent_id, project_id, scope),
        )
        conn.commit()
        return cur.rowcount > 0

    # =========================================================================
    # Audit Events
    # =========================================================================

    def log_audit_event(self, event: AuditEventRecord) -> None:
        """Append an immutable security audit event."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO audit_events (
                event_id, timestamp, principal_id, action, resource_type,
                resource_id, outcome, correlation_id, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                event.event_id,
                event.timestamp.isoformat(),
                event.principal_id,
                event.action,
                event.resource_type,
                event.resource_id,
                event.outcome,
                event.correlation_id,
                json.dumps(event.metadata),
            ),
        )
        conn.commit()

    def list_audit_events(
        self,
        principal_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditEventRecord]:
        """Query security audit log."""
        conn = self._get_conn()
        sql = "SELECT * FROM audit_events WHERE 1=1"
        params: list[Any] = []
        if principal_id:
            sql += " AND principal_id = ?"
            params.append(principal_id)
        if action:
            sql += " AND action = ?"
            params.append(action)
        sql += " ORDER BY timestamp DESC LIMIT ?;"
        params.append(limit)

        cur = conn.execute(sql, tuple(params))
        res: list[AuditEventRecord] = []
        for row in cur.fetchall():
            res.append(
                AuditEventRecord(
                    event_id=row["event_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    principal_id=row["principal_id"],
                    action=row["action"],
                    resource_type=row["resource_type"],
                    resource_id=row["resource_id"],
                    outcome=row["outcome"],
                    correlation_id=row["correlation_id"],
                    metadata=json.loads(row["metadata_json"] or "{}"),
                )
            )
        return res
