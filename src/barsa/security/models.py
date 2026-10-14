"""Models and schemas for the Barsa Security, Authentication & Authorization Engine (Phase 10)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PrincipalType(StrEnum):
    """Types of authenticated actors."""

    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"


class AuthMethod(StrEnum):
    """Authentication mechanism utilized."""

    LOCAL = "local"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    PASSWORD = "password"


class WorkspaceRole(StrEnum):
    """Hierarchical workspace and project membership roles."""

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class SensitivityLevel(StrEnum):
    """Record and knowledge sensitivity classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Scope(StrEnum):
    """Fine-grained permission scopes."""

    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    MEMORY_READ = "memory:read"
    MEMORY_PROPOSE = "memory:propose"
    MEMORY_COMMIT = "memory:commit"
    CHECKPOINT_WRITE = "checkpoint:write"
    GRAPH_READ = "graph:read"
    ARTIFACT_READ = "artifact:read"
    ARTIFACT_WRITE = "artifact:write"
    COORDINATION_CLAIM = "coordination:claim"
    COORDINATION_SUBMIT = "coordination:submit"
    REVIEW_APPROVE = "review:approve"
    ADMIN_ALL = "admin:*"
    WORKSPACE_ALL = "workspace:*"


# Standard role permissions mapping
ROLE_PERMISSIONS: dict[WorkspaceRole, set[str]] = {
    WorkspaceRole.OWNER: {
        Scope.PROJECT_READ,
        Scope.PROJECT_WRITE,
        Scope.PROJECT_DELETE,
        Scope.MEMORY_READ,
        Scope.MEMORY_PROPOSE,
        Scope.MEMORY_COMMIT,
        Scope.CHECKPOINT_WRITE,
        Scope.GRAPH_READ,
        Scope.ARTIFACT_READ,
        Scope.ARTIFACT_WRITE,
        Scope.COORDINATION_CLAIM,
        Scope.COORDINATION_SUBMIT,
        Scope.REVIEW_APPROVE,
        Scope.ADMIN_ALL,
        Scope.WORKSPACE_ALL,
    },
    WorkspaceRole.ADMIN: {
        Scope.PROJECT_READ,
        Scope.PROJECT_WRITE,
        Scope.MEMORY_READ,
        Scope.MEMORY_PROPOSE,
        Scope.MEMORY_COMMIT,
        Scope.CHECKPOINT_WRITE,
        Scope.GRAPH_READ,
        Scope.ARTIFACT_READ,
        Scope.ARTIFACT_WRITE,
        Scope.COORDINATION_CLAIM,
        Scope.COORDINATION_SUBMIT,
        Scope.REVIEW_APPROVE,
        Scope.ADMIN_ALL,
    },
    WorkspaceRole.EDITOR: {
        Scope.PROJECT_READ,
        Scope.MEMORY_READ,
        Scope.MEMORY_PROPOSE,
        Scope.MEMORY_COMMIT,
        Scope.CHECKPOINT_WRITE,
        Scope.GRAPH_READ,
        Scope.ARTIFACT_READ,
        Scope.ARTIFACT_WRITE,
        Scope.COORDINATION_CLAIM,
        Scope.COORDINATION_SUBMIT,
    },
    WorkspaceRole.REVIEWER: {
        Scope.PROJECT_READ,
        Scope.MEMORY_READ,
        Scope.GRAPH_READ,
        Scope.ARTIFACT_READ,
        Scope.REVIEW_APPROVE,
        Scope.COORDINATION_CLAIM,
    },
    WorkspaceRole.VIEWER: {
        Scope.PROJECT_READ,
        Scope.MEMORY_READ,
        Scope.GRAPH_READ,
        Scope.ARTIFACT_READ,
    },
}


class AuthenticatedPrincipal(BaseModel):
    """Unified authenticated actor context."""

    principal_id: str = Field(..., description="Unique persistent identifier of human, agent, or service")
    principal_type: PrincipalType = Field(default=PrincipalType.HUMAN)
    authentication_method: AuthMethod = Field(default=AuthMethod.LOCAL)
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    credential_id: str | None = Field(default=None, description="API key or credential ID used to authenticate")
    granted_scopes: list[str] = Field(default_factory=list, description="Scopes explicitly granted to this principal")
    allowed_projects: list[str] = Field(default_factory=lambda: ["*"], description="Projects authorized for access")
    display_name: str | None = Field(default=None)
    is_superuser: bool = Field(default=False, description="System administrator bypass override")
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserCreate(BaseModel):
    """Payload to register a new human user."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public human user profile."""

    principal_id: str
    username: str
    display_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class UserLogin(BaseModel):
    """Login credentials for password authentication."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    principal_id: str


class AgentCredentialCreate(BaseModel):
    """Request payload to generate a new agent API credential."""

    agent_id: str = Field(..., description="ID of the agent principal to associate with")
    name: str = Field(..., description="Human-readable credential descriptor")
    scopes: list[str] = Field(default_factory=list, description="Explicit scopes granted to this credential")
    allowed_projects: list[str] = Field(default_factory=lambda: ["*"], description="Authorized project identifiers")
    expires_in_days: int | None = Field(default=90, ge=1, le=365, description="Expiration in days (None for permanent)")


class AgentCredentialRawResponse(BaseModel):
    """Response returned upon credential creation containing the plaintext key (displayed only once)."""

    credential_id: str
    principal_id: str
    name: str
    raw_key: str
    key_prefix: str
    scopes: list[str]
    allowed_projects: list[str]
    expires_at: datetime | None
    created_at: datetime


class AgentCredentialResponse(BaseModel):
    """Public credential metadata (never contains plaintext key or hash)."""

    credential_id: str
    principal_id: str
    name: str
    key_prefix: str
    scopes: list[str]
    allowed_projects: list[str]
    expires_at: datetime | None
    revoked: bool
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class WorkspaceMembershipCreate(BaseModel):
    """Add or update a member in a workspace."""

    principal_id: str
    role: WorkspaceRole


class WorkspaceMembershipResponse(BaseModel):
    """Workspace membership detail."""

    workspace_id: str
    principal_id: str
    role: WorkspaceRole
    granted_by: str
    created_at: datetime
    updated_at: datetime


class ProjectGrantCreate(BaseModel):
    """Assign a role to a principal for a specific project."""

    principal_id: str
    role: WorkspaceRole


class ProjectGrantResponse(BaseModel):
    """Project-level access grant."""

    project_id: str
    principal_id: str
    role: WorkspaceRole
    granted_by: str
    created_at: datetime
    updated_at: datetime


class AuditEventRecord(BaseModel):
    """Persistent security audit event."""

    event_id: str = Field(default_factory=lambda: f"sec-evt-{uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    principal_id: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str = Field(..., description="'allow' or 'deny'")
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
