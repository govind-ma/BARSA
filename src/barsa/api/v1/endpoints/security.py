"""REST API endpoints for Security, Authentication, and Permissions (Phase 10)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from barsa.core.exceptions import AuthorizationError, ResourceNotFoundError
from barsa.security.dependencies import get_current_principal, get_security_service
from barsa.security.models import (
    AgentCredentialCreate,
    AgentCredentialRawResponse,
    AgentCredentialResponse,
    AuditEventRecord,
    AuthenticatedPrincipal,
    ProjectGrantCreate,
    ProjectGrantResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    WorkspaceMembershipCreate,
    WorkspaceMembershipResponse,
    WorkspaceRole,
)

if TYPE_CHECKING:
    from barsa.security.service import SecurityService

router = APIRouter(prefix="/security", tags=["Security & Identity"])


# =========================================================================
# Identity & User Management
# =========================================================================


@router.post("/users/register", response_model=UserResponse)
@router.post("/auth/register", response_model=UserResponse, include_in_schema=False)
def register_user(
    req: UserCreate,
    sec_service: SecurityService = Depends(get_security_service),
) -> UserResponse:
    """Register a new human user."""
    return sec_service.register_user(req)


@router.post("/users/login", response_model=TokenResponse)
@router.post("/auth/login", response_model=TokenResponse, include_in_schema=False)
def login_user(
    req: UserLogin,
    sec_service: SecurityService = Depends(get_security_service),
) -> TokenResponse:
    """Log in and acquire a signed JWT bearer token."""
    return sec_service.authenticate_user(req)


@router.get("/me", response_model=AuthenticatedPrincipal)
@router.get("/auth/me", response_model=AuthenticatedPrincipal, include_in_schema=False)
def get_current_user_profile(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> AuthenticatedPrincipal:
    """Retrieve identity and scopes of current authenticated principal."""
    return principal


# =========================================================================
# Workspace Memberships
# =========================================================================


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMembershipResponse])
def list_workspace_members(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> list[WorkspaceMembershipResponse]:
    """List members of a workspace."""
    sec_service.authorizer.authorize(
        principal=principal,
        action="workspace:read",
        resource={"workspace_id": workspace_id},
    )
    return sec_service.list_workspace_members(workspace_id)


@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceMembershipResponse)
def add_workspace_member(
    workspace_id: str,
    req: WorkspaceMembershipCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> WorkspaceMembershipResponse:
    """Add or update member in a workspace (requires admin or owner)."""
    role = sec_service.authorizer.get_effective_role(principal, workspace_id=workspace_id)
    if not principal.is_superuser and role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise AuthorizationError("Only workspace owner or admin can manage memberships")

    return sec_service.add_workspace_member(workspace_id, req, granter_id=principal.principal_id)


@router.delete("/workspaces/{workspace_id}/members/{principal_id}")
def remove_workspace_member(
    workspace_id: str,
    principal_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> dict[str, Any]:
    """Remove member from workspace."""
    role = sec_service.authorizer.get_effective_role(principal, workspace_id=workspace_id)
    if not principal.is_superuser and role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise AuthorizationError("Only workspace owner or admin can remove members")

    removed = sec_service.remove_workspace_member(workspace_id, principal_id, remover_id=principal.principal_id)
    if not removed:
        raise ResourceNotFoundError(f"Member '{principal_id}' not found in workspace '{workspace_id}'")
    return {"status": "removed", "principal_id": principal_id}


# =========================================================================
# Project Grants
# =========================================================================


@router.get("/projects/{project_id}/grants", response_model=list[ProjectGrantResponse])
def list_project_grants(
    project_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> list[ProjectGrantResponse]:
    """List role grants for a specific project."""
    sec_service.authorizer.authorize(
        principal=principal,
        action="project:read",
        resource={"project_id": project_id},
    )
    return sec_service.list_project_grants(project_id)


@router.post("/projects/{project_id}/grants", response_model=ProjectGrantResponse)
def add_project_grant(
    project_id: str,
    req: ProjectGrantCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> ProjectGrantResponse:
    """Add a project-specific grant."""
    role = sec_service.authorizer.get_effective_role(principal, project_id=project_id)
    if not principal.is_superuser and role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise AuthorizationError("Only project/workspace admin or owner can assign project grants")

    return sec_service.add_project_grant(project_id, req, granter_id=principal.principal_id)


# =========================================================================
# Agent Credentials (API Keys)
# =========================================================================


@router.post("/agents/{agent_id}/credentials", response_model=AgentCredentialRawResponse)
def create_agent_credential(
    agent_id: str,
    req: AgentCredentialCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> AgentCredentialRawResponse:
    """Generate a new secure API key credential for an agent."""
    req.agent_id = agent_id
    return sec_service.create_agent_credential(req, creator_principal_id=principal.principal_id)


@router.post("/agents/credentials", response_model=AgentCredentialRawResponse, include_in_schema=False)
def create_agent_credential_direct(
    req: AgentCredentialCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> AgentCredentialRawResponse:
    """Generate a new secure API key credential for an agent (body agent_id)."""
    return sec_service.create_agent_credential(req, creator_principal_id=principal.principal_id)


@router.get("/agents/{agent_id}/credentials", response_model=list[AgentCredentialResponse])
def list_agent_credentials(
    agent_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> list[AgentCredentialResponse]:
    """List credentials for an agent (never returns secret keys or hashes)."""
    _ = principal
    return sec_service.list_agent_credentials(agent_id)


@router.post("/credentials/{credential_id}/revoke")
def revoke_credential(
    credential_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> dict[str, Any]:
    """Immediately revoke a credential."""
    revoked = sec_service.revoke_credential(credential_id, revoker_principal_id=principal.principal_id)
    if not revoked:
        raise ResourceNotFoundError(f"Credential '{credential_id}' not found or already revoked")
    return {"status": "revoked", "credential_id": credential_id}


@router.post("/credentials/{credential_id}/rotate", response_model=AgentCredentialRawResponse)
def rotate_credential(
    credential_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> AgentCredentialRawResponse:
    """Rotate an existing credential generating a new key while preserving scopes."""
    return sec_service.rotate_credential(credential_id, rotator_principal_id=principal.principal_id)


# =========================================================================
# Permissions & Audit Events
# =========================================================================


@router.get("/workspaces/{workspace_id}/permissions")
def get_workspace_permissions(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> dict[str, Any]:
    """Get effective permissions and role of the caller for a workspace."""
    role = sec_service.authorizer.get_effective_role(principal, workspace_id=workspace_id)
    from barsa.security.models import ROLE_PERMISSIONS

    perms = list(ROLE_PERMISSIONS.get(role, set())) if role else []
    return {
        "workspace_id": workspace_id,
        "principal_id": principal.principal_id,
        "effective_role": role.value if role else None,
        "permissions": perms,
    }


@router.get("/projects/{project_id}/permissions")
def get_project_permissions(
    project_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> dict[str, Any]:
    """Get effective permissions of caller for a project."""
    role = sec_service.authorizer.get_effective_role(principal, project_id=project_id)
    from barsa.security.models import ROLE_PERMISSIONS

    perms = list(ROLE_PERMISSIONS.get(role, set())) if role else []
    return {
        "project_id": project_id,
        "principal_id": principal.principal_id,
        "effective_role": role.value if role else None,
        "permissions": perms,
        "granted_agent_scopes": principal.granted_scopes,
    }


@router.get("/audit-events", response_model=list[AuditEventRecord])
@router.get("/audit", response_model=list[AuditEventRecord], include_in_schema=False)
def get_audit_events(
    principal_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    sec_service: SecurityService = Depends(get_security_service),
) -> list[AuditEventRecord]:
    """Query security audit log."""
    # Only superusers or users querying their own events can access
    if not principal.is_superuser and principal_id != principal.principal_id:
        principal_id = principal.principal_id

    return sec_service.list_audit_events(principal_id=principal_id, action=action, limit=limit)
