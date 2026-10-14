"""Central Authorization Service for BARSA (Phase 10).

Enforces Role-Based Access Control (RBAC), agent-scoped permissions,
project boundary isolation, and record sensitivity classifications.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from barsa.core.exceptions import AuthorizationError
from barsa.security.models import (
    ROLE_PERMISSIONS,
    AuditEventRecord,
    AuthenticatedPrincipal,
    PrincipalType,
    Scope,
    SensitivityLevel,
    WorkspaceRole,
)

if TYPE_CHECKING:
    from barsa.security.storage import SecurityStorage
    from barsa.storage.sqlite import SQLiteStorageProvider

logger = logging.getLogger("barsa.security.authorizer")


class CentralAuthorizer:
    """Central authority evaluating and auditing access decisions across all Barsa subsystems."""

    def __init__(self, security_storage: SecurityStorage, storage: SQLiteStorageProvider) -> None:
        self.sec_storage = security_storage
        self.storage = storage

    def is_authorized(
        self,
        principal: AuthenticatedPrincipal,
        action: str,
        resource: dict[str, Any] | None = None,
    ) -> bool:
        """Check if principal is authorized for action without raising an exception."""
        try:
            self.authorize(principal=principal, action=action, resource=resource)
            return True
        except AuthorizationError:
            return False

    def authorize(
        self,
        principal: AuthenticatedPrincipal,
        action: str,
        resource: dict[str, Any] | None = None,
    ) -> None:
        """Evaluate permission for principal on resource; raises AuthorizationError on denial."""
        res = resource or {}
        project_id = res.get("project_id")
        workspace_id = res.get("workspace_id")
        sensitivity = res.get("sensitivity")

        # 1. Superuser override
        if principal.is_superuser:
            return

        # 2. Resolve workspace from project if missing
        if project_id and not workspace_id:
            proj = self.storage.get_project(project_id)
            if proj:
                workspace_id = proj.workspace_id

        # 3. Project Isolation & Whitelist check
        if project_id and "*" not in principal.allowed_projects and project_id not in principal.allowed_projects:
            self._deny(
                principal,
                action,
                project_id,
                f"Principal '{principal.principal_id}' is not authorized for project '{project_id}'",
            )

        # 4. Agent & Service Scope Check
        # For agents/services, credentials MUST explicitly grant the action scope
        if (
            principal.principal_type in (PrincipalType.AGENT, PrincipalType.SERVICE)
            and Scope.ADMIN_ALL.value not in principal.granted_scopes
        ):
            # Check if specific action scope or category wildcard is granted
            action_category = action.split(":")[0] + ":*" if ":" in action else action
            has_scope = action in principal.granted_scopes or action_category in principal.granted_scopes
            if not has_scope and project_id:
                # Also check project-level agent_scopes table
                db_scopes = self.sec_storage.get_agent_scopes(principal.principal_id, project_id)
                has_scope = action in db_scopes or action_category in db_scopes

            if not has_scope:
                self._deny(
                    principal,
                    action,
                    project_id or workspace_id or "global",
                    f"Agent '{principal.principal_id}' lacks required scope '{action}'",
                )

        # 5. Role-Based Access Control (RBAC) Check
        role = self.get_effective_role(principal, project_id=project_id, workspace_id=workspace_id)

        # If a workspace/project is targeted, a valid role or agent grant is required
        if workspace_id or project_id:
            if not role:
                # For agents that already passed scope verification and project whitelist, allow scoped access
                if principal.principal_type in (PrincipalType.AGENT, PrincipalType.SERVICE):
                    pass
                else:
                    self._deny(
                        principal,
                        action,
                        project_id or workspace_id or "global",
                        f"Principal '{principal.principal_id}' has no membership in workspace '{workspace_id}'",
                    )
            else:
                allowed_actions = ROLE_PERMISSIONS.get(role, set())
                # Check exact action or admin wildcard
                if (
                    action not in allowed_actions
                    and Scope.ADMIN_ALL.value not in allowed_actions
                    and Scope.WORKSPACE_ALL.value not in allowed_actions
                ):
                    self._deny(
                        principal,
                        action,
                        project_id or workspace_id or "global",
                        f"Role '{role.value}' does not permit action '{action}'",
                    )

        # 6. Sensitivity Classification Check
        if sensitivity:
            sens_enum = SensitivityLevel(sensitivity) if isinstance(sensitivity, str) else sensitivity
            if not self.check_sensitivity(principal, sens_enum, role):
                self._deny(
                    principal,
                    action,
                    project_id or workspace_id or "global",
                    f"Insufficient clearance for sensitivity level '{sens_enum.value}'",
                )

    def get_effective_role(
        self,
        principal: AuthenticatedPrincipal,
        project_id: str | None = None,
        workspace_id: str | None = None,
    ) -> WorkspaceRole | None:
        """Resolve highest effective role from project grants or workspace membership."""
        # 1. Project-level grant overrides workspace role
        if project_id:
            grant = self.sec_storage.get_project_grant(project_id, principal.principal_id)
            if grant:
                return grant.role

        # 2. Workspace membership role
        if workspace_id:
            membership = self.sec_storage.get_workspace_membership(workspace_id, principal.principal_id)
            if membership:
                return membership.role

            # Check if principal is recorded workspace owner
            ws = self.storage.get_workspace(workspace_id)
            if ws and ws.owner_id == principal.principal_id:
                return WorkspaceRole.OWNER

        return None

    def check_sensitivity(
        self,
        principal: AuthenticatedPrincipal,
        sensitivity: SensitivityLevel,
        role: WorkspaceRole | None = None,
    ) -> bool:
        """Check whether principal has clearance to view/manipulate given sensitivity level."""
        if principal.is_superuser:
            return True
        if sensitivity == SensitivityLevel.PUBLIC:
            return True
        if sensitivity == SensitivityLevel.INTERNAL:
            return role in (
                WorkspaceRole.VIEWER,
                WorkspaceRole.EDITOR,
                WorkspaceRole.REVIEWER,
                WorkspaceRole.ADMIN,
                WorkspaceRole.OWNER,
            )
        if sensitivity == SensitivityLevel.CONFIDENTIAL:
            return role in (WorkspaceRole.EDITOR, WorkspaceRole.ADMIN, WorkspaceRole.OWNER)
        if sensitivity == SensitivityLevel.RESTRICTED:
            return role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER)
        return False

    def _deny(
        self,
        principal: AuthenticatedPrincipal,
        action: str,
        resource_id: str,
        reason: str,
    ) -> None:
        """Log audit failure and raise AuthorizationError."""
        self.sec_storage.log_audit_event(
            AuditEventRecord(
                principal_id=principal.principal_id,
                action=action,
                resource_type="resource",
                resource_id=resource_id,
                outcome="deny",
                metadata={"reason": reason, "principal_type": principal.principal_type.value},
            )
        )
        logger.warning("Access denied: %s (Principal: %s, Action: %s)", reason, principal.principal_id, action)
        raise AuthorizationError(reason)
