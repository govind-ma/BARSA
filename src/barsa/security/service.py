"""High-level security and identity management service for BARSA (Phase 10)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from barsa.core.config import Settings
from barsa.core.exceptions import AuthenticationError, ConflictError, ResourceNotFoundError
from barsa.security.authorizer import CentralAuthorizer
from barsa.security.crypto import (
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
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    WorkspaceMembershipCreate,
    WorkspaceMembershipResponse,
)
from barsa.security.storage import SecurityStorage

if TYPE_CHECKING:
    from barsa.storage.sqlite import SQLiteStorageProvider

logger = logging.getLogger("barsa.security.service")


class SecurityService:
    """Manages identity, authentication, credentials, permissions, and audit logging."""

    def __init__(self, storage: SQLiteStorageProvider, settings: Settings | None = None) -> None:
        self.storage = storage
        self.settings = settings or Settings()
        self.sec_storage = SecurityStorage(storage)
        self.authorizer = CentralAuthorizer(self.sec_storage, storage)
        self._jwt_secret = (
            self.settings.secret_key.get_secret_value()
            if self.settings.secret_key
            else "barsa-local-dev-jwt-secret-do-not-use-in-production"
        )
        self._failed_attempts: dict[str, list[datetime]] = {}

    # =========================================================================
    # Human User Authentication & Management
    # =========================================================================

    def register_user(self, req: UserCreate, is_superuser: bool = False) -> UserResponse:
        """Register a new human user with Argon2id hashed password."""
        # Check if identifier already exists
        existing = self.sec_storage.get_identity_by_identifier(req.username, provider="local")
        if existing:
            raise ConflictError(f"Username '{req.username}' is already registered")

        principal_id = f"user-{uuid4().hex[:12]}"
        now = datetime.now(UTC)

        principal = AuthenticatedPrincipal(
            principal_id=principal_id,
            principal_type=PrincipalType.HUMAN,
            authentication_method=AuthMethod.PASSWORD,
            display_name=req.display_name,
            is_superuser=is_superuser,
            authenticated_at=now,
        )
        self.sec_storage.create_principal(principal)

        pwd_hash = hash_password(req.password)
        self.sec_storage.create_identity(
            principal_id=principal_id,
            identifier=req.username,
            password_hash=pwd_hash,
            provider="local",
        )

        self.sec_storage.log_audit_event(
            AuditEventRecord(
                principal_id=principal_id,
                action="user:register",
                resource_type="user",
                resource_id=principal_id,
                outcome="allow",
                metadata={"username": req.username},
            )
        )
        return UserResponse(
            principal_id=principal_id,
            username=req.username,
            display_name=req.display_name,
            is_active=True,
            is_superuser=is_superuser,
            created_at=now,
        )

    def authenticate_user(self, req: UserLogin) -> TokenResponse:
        """Authenticate user with login rate limiting and generic error messages."""
        self._check_rate_limit(req.username)

        identity = self.sec_storage.get_identity_by_identifier(req.username, provider="local")
        if not identity or not identity.get("password_hash"):
            self._record_failed_attempt(req.username)
            raise AuthenticationError("Invalid username or password")

        if not verify_password(req.password, identity["password_hash"]):
            self._record_failed_attempt(req.username)
            raise AuthenticationError("Invalid username or password")

        principal_id = identity["principal_id"]
        principal = self.sec_storage.get_principal(principal_id)
        if not principal:
            raise AuthenticationError("Principal not found or deactivated")

        expires_in = 86400  # 24 hours
        token = create_access_token(
            principal_id=principal_id,
            secret_key=self._jwt_secret,
            expires_in_seconds=expires_in,
            extra_claims={"username": req.username, "principal_type": PrincipalType.HUMAN.value},
        )

        self.sec_storage.log_audit_event(
            AuditEventRecord(
                principal_id=principal_id,
                action="user:login",
                resource_type="session",
                resource_id=principal_id,
                outcome="allow",
                metadata={"username": req.username},
            )
        )
        return TokenResponse(
            access_token=token,
            expires_in_seconds=expires_in,
            principal_id=principal_id,
        )

    def verify_token(self, token: str) -> AuthenticatedPrincipal:
        """Verify and decode a JWT bearer token."""
        try:
            payload = decode_access_token(token, self._jwt_secret)
            principal_id = payload.get("sub")
            if not principal_id:
                raise AuthenticationError("Token missing subject claim")

            principal = self.sec_storage.get_principal(principal_id)
            if not principal:
                raise AuthenticationError(f"Principal '{principal_id}' not found")

            principal.authentication_method = AuthMethod.BEARER_TOKEN
            return principal
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Invalid or expired token: {e}") from e

    # =========================================================================
    # Agent Credential (API Key) Management
    # =========================================================================

    def create_agent_credential(
        self,
        req: AgentCredentialCreate,
        creator_principal_id: str,
    ) -> AgentCredentialRawResponse:
        """Create a new hashed API key credential for an agent."""
        # Ensure agent principal exists
        agent = self.sec_storage.get_principal(req.agent_id)
        if not agent:
            # Register agent principal automatically
            agent = AuthenticatedPrincipal(
                principal_id=req.agent_id,
                principal_type=PrincipalType.AGENT,
                display_name=req.name,
                allowed_projects=req.allowed_projects,
                granted_scopes=req.scopes,
            )
            self.sec_storage.create_principal(agent)

        raw_key, prefix, key_hash, salt = generate_api_key(prefix="barsa_ak")
        expires_at = datetime.now(UTC) + timedelta(days=req.expires_in_days) if req.expires_in_days else None

        cred = self.sec_storage.create_credential(
            principal_id=req.agent_id,
            name=req.name,
            key_prefix=prefix,
            key_hash=key_hash,
            salt=salt,
            scopes=req.scopes,
            allowed_projects=req.allowed_projects,
            expires_at=expires_at,
        )

        self.sec_storage.log_audit_event(
            AuditEventRecord(
                principal_id=creator_principal_id,
                action="credential:create",
                resource_type="credential",
                resource_id=cred.credential_id,
                outcome="allow",
                metadata={"agent_id": req.agent_id, "name": req.name, "scopes": req.scopes},
            )
        )
        return AgentCredentialRawResponse(
            credential_id=cred.credential_id,
            principal_id=req.agent_id,
            name=req.name,
            raw_key=raw_key,
            key_prefix=prefix,
            scopes=req.scopes,
            allowed_projects=req.allowed_projects,
            expires_at=expires_at,
            created_at=cred.created_at,
        )

    def authenticate_api_key(self, api_key: str) -> AuthenticatedPrincipal:
        """Validate API key credential against salted hash and return authenticated principal."""
        if not api_key or len(api_key) < 16:
            raise AuthenticationError("Invalid API key format")

        prefix = api_key[:12]
        candidates = self.sec_storage.find_active_credentials_by_prefix(prefix)
        if not candidates:
            raise AuthenticationError("Invalid or revoked API key")

        matched = None
        for cand in candidates:
            if verify_api_key(api_key, cand["key_hash"], cand["salt"]):
                matched = cand
                break

        if not matched:
            raise AuthenticationError("Invalid or revoked API key")

        # Check expiration
        if matched.get("expires_at"):
            exp = datetime.fromisoformat(matched["expires_at"])
            if datetime.now(UTC) > exp:
                raise AuthenticationError("API key has expired")

        principal = self.sec_storage.get_principal(matched["principal_id"])
        if not principal:
            raise AuthenticationError("Associated agent principal not found")

        # Record usage
        self.sec_storage.record_credential_used(matched["credential_id"])

        import json

        scopes = json.loads(matched["scopes_json"] or "[]")
        allowed_projs = json.loads(matched["allowed_projects_json"] or '["*"]')

        principal.credential_id = matched["credential_id"]
        principal.authentication_method = AuthMethod.API_KEY
        principal.granted_scopes = scopes
        principal.allowed_projects = allowed_projs
        return principal

    def revoke_credential(self, credential_id: str, revoker_principal_id: str = "system") -> bool:
        """Revoke a credential immediately."""
        revoked = self.sec_storage.revoke_credential(credential_id)
        if revoked:
            self.sec_storage.log_audit_event(
                AuditEventRecord(
                    principal_id=revoker_principal_id,
                    action="credential:revoke",
                    resource_type="credential",
                    resource_id=credential_id,
                    outcome="allow",
                )
            )
        return revoked

    def rotate_credential(
        self,
        credential_id: str,
        rotator_principal_id: str = "system",
    ) -> AgentCredentialRawResponse:
        """Rotate an existing credential generating a new key while preserving scopes."""
        cred = self.sec_storage.get_credential_by_id(credential_id)
        if not cred:
            raise ResourceNotFoundError(f"Credential '{credential_id}' not found")

        raw_key, prefix, key_hash, salt = generate_api_key(prefix="barsa_ak")
        updated = self.sec_storage.rotate_credential(
            credential_id=credential_id,
            new_prefix=prefix,
            new_hash=key_hash,
            new_salt=salt,
        )

        self.sec_storage.log_audit_event(
            AuditEventRecord(
                principal_id=rotator_principal_id,
                action="credential:rotate",
                resource_type="credential",
                resource_id=credential_id,
                outcome="allow",
            )
        )
        return AgentCredentialRawResponse(
            credential_id=updated.credential_id,
            principal_id=updated.principal_id,
            name=updated.name,
            raw_key=raw_key,
            key_prefix=prefix,
            scopes=updated.scopes,
            allowed_projects=updated.allowed_projects,
            expires_at=updated.expires_at,
            created_at=updated.created_at,
        )

    def list_agent_credentials(self, agent_id: str) -> list[AgentCredentialResponse]:
        """List credentials for an agent."""
        return self.sec_storage.list_credentials_for_principal(agent_id)

    # =========================================================================
    # Workspace & Project Permissions
    # =========================================================================

    def add_workspace_member(
        self,
        workspace_id: str,
        req: WorkspaceMembershipCreate,
        granter_id: str,
    ) -> WorkspaceMembershipResponse:
        """Add or update member in workspace."""
        res = self.sec_storage.add_workspace_membership(
            workspace_id=workspace_id,
            principal_id=req.principal_id,
            role=req.role,
            granted_by=granter_id,
        )
        self.sec_storage.log_audit_event(
            AuditEventRecord(
                principal_id=granter_id,
                action="workspace:member:add",
                resource_type="workspace",
                resource_id=workspace_id,
                outcome="allow",
                metadata={"member_id": req.principal_id, "role": req.role.value},
            )
        )
        return res

    def list_workspace_members(self, workspace_id: str) -> list[WorkspaceMembershipResponse]:
        """List members of a workspace."""
        return self.sec_storage.list_workspace_members(workspace_id)

    def remove_workspace_member(self, workspace_id: str, principal_id: str, remover_id: str) -> bool:
        """Remove member from workspace."""
        removed = self.sec_storage.remove_workspace_membership(workspace_id, principal_id)
        if removed:
            self.sec_storage.log_audit_event(
                AuditEventRecord(
                    principal_id=remover_id,
                    action="workspace:member:remove",
                    resource_type="workspace",
                    resource_id=workspace_id,
                    outcome="allow",
                    metadata={"removed_principal_id": principal_id},
                )
            )
        return removed

    def add_project_grant(
        self,
        project_id: str,
        req: ProjectGrantCreate,
        granter_id: str,
    ) -> ProjectGrantResponse:
        """Add project-specific role grant."""
        res = self.sec_storage.add_project_grant(
            project_id=project_id,
            principal_id=req.principal_id,
            role=req.role,
            granted_by=granter_id,
        )
        self.sec_storage.log_audit_event(
            AuditEventRecord(
                principal_id=granter_id,
                action="project:grant:add",
                resource_type="project",
                resource_id=project_id,
                outcome="allow",
                metadata={"principal_id": req.principal_id, "role": req.role.value},
            )
        )
        return res

    def list_project_grants(self, project_id: str) -> list[ProjectGrantResponse]:
        """List grants for a project."""
        return self.sec_storage.list_project_grants(project_id)

    def remove_project_grant(self, project_id: str, principal_id: str, remover_id: str) -> bool:
        """Remove project grant."""
        removed = self.sec_storage.remove_project_grant(project_id, principal_id)
        if removed:
            self.sec_storage.log_audit_event(
                AuditEventRecord(
                    principal_id=remover_id,
                    action="project:grant:remove",
                    resource_type="project",
                    resource_id=project_id,
                    outcome="allow",
                    metadata={"removed_principal_id": principal_id},
                )
            )
        return removed

    # =========================================================================
    # Audit Logging Queries
    # =========================================================================

    def list_audit_events(
        self,
        principal_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditEventRecord]:
        """Retrieve audit events."""
        return self.sec_storage.list_audit_events(principal_id=principal_id, action=action, limit=limit)

    # =========================================================================
    # Internal Helpers & Login Rate Limiting
    # =========================================================================

    def _check_rate_limit(self, identifier: str) -> None:
        """Check failed login attempt rate limit."""
        attempts = self._failed_attempts.get(identifier, [])
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=5)
        recent = [t for t in attempts if t > cutoff]
        self._failed_attempts[identifier] = recent

        if len(recent) >= 5:
            raise AuthenticationError("Too many failed login attempts. Please wait 5 minutes.")

    def _record_failed_attempt(self, identifier: str) -> None:
        """Record a failed login timestamp."""
        now = datetime.now(UTC)
        if identifier not in self._failed_attempts:
            self._failed_attempts[identifier] = []
        self._failed_attempts[identifier].append(now)
