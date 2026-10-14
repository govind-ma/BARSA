"""FastAPI authentication and authorization dependencies for BARSA."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import Depends, Header, Request

from barsa.api.deps import get_app_settings, get_storage
from barsa.core.exceptions import AuthenticationError, AuthorizationError
from barsa.security.models import (
    AuthenticatedPrincipal,
    AuthMethod,
    PrincipalType,
    WorkspaceRole,
)
from barsa.security.service import SecurityService
from barsa.storage.sqlite import SQLiteStorageProvider

if TYPE_CHECKING:
    from collections.abc import Callable

    from barsa.core.config import Settings


def get_security_service(
    storage: Any = Depends(get_storage),
    settings: Settings = Depends(get_app_settings),
) -> SecurityService:
    """Dependency that provides the SecurityService."""
    if not isinstance(storage, SQLiteStorageProvider):
        raise RuntimeError("SecurityService requires SQLiteStorageProvider")
    return SecurityService(storage=storage, settings=settings)


async def get_current_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    sec_service: SecurityService = Depends(get_security_service),
) -> AuthenticatedPrincipal:
    """Extract and validate the authenticated principal from Bearer token, API key, or local desktop context."""
    # 1. Bearer Token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        return sec_service.verify_token(token)

    # 2. API Key Header
    if x_api_key:
        return sec_service.authenticate_api_key(x_api_key.strip())

    # 3. Local-First Desktop Execution Fallback
    # If on localhost without remote headers, provide secure local desktop principal
    client_host = request.client.host if request.client else "127.0.0.1"
    if client_host in ("127.0.0.1", "::1", "localhost", "testclient"):
        # Ensure default local owner is in DB
        local_id = "local-owner"
        principal = sec_service.sec_storage.get_principal(local_id)
        if not principal:
            principal = AuthenticatedPrincipal(
                principal_id=local_id,
                principal_type=PrincipalType.HUMAN,
                authentication_method=AuthMethod.LOCAL,
                display_name="Local Desktop Owner",
                is_superuser=True,
            )
            sec_service.sec_storage.create_principal(principal)
        return principal

    raise AuthenticationError("Authentication required: provide Bearer token or X-API-Key header")


def require_role(min_role: WorkspaceRole, get_workspace_id: Callable[[Request], str]) -> Any:
    """Dependency factory checking that the principal has at least min_role on the workspace."""

    async def _checker(
        request: Request,
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
        sec_service: SecurityService = Depends(get_security_service),
    ) -> AuthenticatedPrincipal:
        ws_id = get_workspace_id(request)
        action_map = {
            WorkspaceRole.VIEWER: "workspace:read",
            WorkspaceRole.REVIEWER: "review:create",
            WorkspaceRole.EDITOR: "memory:write",
            WorkspaceRole.ADMIN: "project:create",
            WorkspaceRole.OWNER: "workspace:*",
        }
        action = action_map.get(min_role, "workspace:read")
        sec_service.authorizer.authorize(
            principal=principal,
            action=action,
            resource={"workspace_id": ws_id},
        )
        return principal

    return _checker


def require_scope(required_scope: str) -> Any:
    """Dependency factory checking that an agent has the required scope."""

    async def _scope_checker(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if principal.is_superuser:
            return principal
        if (
            principal.principal_type in (PrincipalType.AGENT, PrincipalType.SERVICE)
            and required_scope not in principal.granted_scopes
            and "admin:*" not in principal.granted_scopes
        ):
            raise AuthorizationError(f"Agent lacks required scope '{required_scope}'")
        return principal

    return _scope_checker
