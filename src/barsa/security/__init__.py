"""Security, authentication, and authorization package for BARSA (Phase 10)."""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from barsa.security.authorizer import CentralAuthorizer
from barsa.security.crypto import (
    SecretScanner,
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)
from barsa.security.models import (
    AgentCredentialCreate,
    AgentCredentialRawResponse,
    AgentCredentialResponse,
    AuditEventRecord,
    AuthenticatedPrincipal,
    AuthMethod,
    PrincipalType,
    ProjectGrantCreate,
    ProjectGrantResponse,
    Scope,
    SensitivityLevel,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    WorkspaceMembershipCreate,
    WorkspaceMembershipResponse,
    WorkspaceRole,
)
from barsa.security.service import SecurityService
from barsa.security.storage import SecurityStorage


@runtime_checkable
class SecurityProvider(Protocol):
    """Protocol for project isolation, role-based authorization, and approvals."""

    @abstractmethod
    async def verify_project_access(self, user_or_agent_id: str, project_id: str) -> bool:
        """Check whether user or agent is permitted to read/write project memories."""
        ...


__all__ = [
    "AgentCredentialCreate",
    "AgentCredentialRawResponse",
    "AgentCredentialResponse",
    "AuditEventRecord",
    "AuthMethod",
    "AuthenticatedPrincipal",
    "CentralAuthorizer",
    "PrincipalType",
    "ProjectGrantCreate",
    "ProjectGrantResponse",
    "Scope",
    "SecurityProvider",
    "SecurityService",
    "SecurityStorage",
    "SensitivityLevel",
    "SecretScanner",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "WorkspaceMembershipCreate",
    "WorkspaceMembershipResponse",
    "WorkspaceRole",
    "create_access_token",
    "decode_access_token",
    "generate_api_key",
    "hash_password",
    "verify_api_key",
    "verify_password",
]
