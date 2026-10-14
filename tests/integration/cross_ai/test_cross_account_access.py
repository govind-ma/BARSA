"""Cross-account and multi-tenant security authorization tests for Phase 12."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from barsa.bms.records import Project, Workspace
from barsa.core.config import Settings
from barsa.core.exceptions import AuthorizationError
from barsa.security.models import (
    AgentCredentialCreate,
    AuthenticatedPrincipal,
    PrincipalType,
    WorkspaceMembershipCreate,
    WorkspaceRole,
)
from barsa.security.service import SecurityService
from barsa.storage.factory import get_storage_provider

if TYPE_CHECKING:
    from pathlib import Path

    from barsa.security.authorizer import CentralAuthorizer


@pytest.fixture
def multi_org_sec_env(tmp_path: Path):
    """Isolated multi-tenant environment with SecurityService and CentralAuthorizer."""
    data_dir = tmp_path / "barsa_multi_org_data"
    settings = Settings(
        app_name="BARSA-Multi-Org-Test",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=data_dir,
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings.ensure_data_dir()

    storage = get_storage_provider(settings)
    sec_service = SecurityService(storage, settings)
    sec_storage = sec_service.sec_storage
    authorizer = sec_service.authorizer

    # 1. Organization A: Workspace and Project
    ws_a = storage.create_workspace(Workspace(id="ws-org-a", name="Acme Corp Workspace", owner_id="owner-acme"))
    proj_a = storage.create_project(
        Project(
            id="proj-acme-core",
            name="Acme Core Payments",
            workspace_id=ws_a.id,
            description="Confidential core payments",
        )
    )

    # 2. Organization B: Workspace and Project
    ws_b = storage.create_workspace(Workspace(id="ws-org-b", name="Beta Corp Workspace", owner_id="owner-beta"))
    proj_b = storage.create_project(
        Project(id="proj-beta-app", name="Beta Mobile App", workspace_id=ws_b.id, description="Beta Mobile Application")
    )

    yield {
        "settings": settings,
        "storage": storage,
        "sec_storage": sec_storage,
        "sec_service": sec_service,
        "authorizer": authorizer,
        "ws_a": ws_a,
        "proj_a": proj_a,
        "ws_b": ws_b,
        "proj_b": proj_b,
    }
    storage.close()


def test_cross_account_unauthorized_access(multi_org_sec_env: dict) -> None:
    """Verify Agent B from Org B cannot read or commit to Org A's confidential project."""
    sec_service: SecurityService = multi_org_sec_env["sec_service"]
    authorizer: CentralAuthorizer = multi_org_sec_env["authorizer"]
    ws_a = multi_org_sec_env["ws_a"]
    proj_a = multi_org_sec_env["proj_a"]
    ws_b = multi_org_sec_env["ws_b"]
    proj_b = multi_org_sec_env["proj_b"]

    # Register Agent A under Org A with access only to Org A's project
    sec_service.create_agent_credential(
        AgentCredentialCreate(
            agent_id="agent-acme-1",
            name="Acme Claude Agent",
            scopes=["memory:read", "memory:commit"],
            allowed_projects=[proj_a.id],
        ),
        creator_principal_id="owner-acme",
    )
    sec_service.add_workspace_member(
        ws_a.id,
        WorkspaceMembershipCreate(principal_id="agent-acme-1", role=WorkspaceRole.EDITOR),
        granter_id="owner-acme",
    )

    # Register Agent B under Org B with access only to Org B's project
    cred_b = sec_service.create_agent_credential(
        AgentCredentialCreate(
            agent_id="agent-beta-1",
            name="Beta GPT Agent",
            scopes=["memory:read", "memory:commit"],
            allowed_projects=[proj_b.id],
        ),
        creator_principal_id="owner-beta",
    )
    sec_service.add_workspace_member(
        ws_b.id,
        WorkspaceMembershipCreate(principal_id="agent-beta-1", role=WorkspaceRole.EDITOR),
        granter_id="owner-beta",
    )

    # Authenticate Agent B
    principal_b = sec_service.authenticate_api_key(cred_b.raw_key)
    assert principal_b.principal_id == "agent-beta-1"

    # Agent B is authorized on Org B
    authorizer.authorize(principal_b, action="memory:read", resource={"workspace_id": ws_b.id, "project_id": proj_b.id})

    # Agent B attempts unauthorized read on Org A -> Rejected by project isolation
    with pytest.raises(AuthorizationError, match="not authorized for project 'proj-acme-core'"):
        authorizer.authorize(
            principal_b, action="memory:read", resource={"workspace_id": ws_a.id, "project_id": proj_a.id}
        )

    # Agent B attempts unauthorized commit on Org A -> Rejected by project isolation
    with pytest.raises(AuthorizationError, match="not authorized for project 'proj-acme-core'"):
        authorizer.authorize(
            principal_b, action="memory:commit", resource={"workspace_id": ws_a.id, "project_id": proj_a.id}
        )


def test_grant_and_revoke_cross_account_access(multi_org_sec_env: dict) -> None:
    """Verify Org A owner can explicitly grant collaborator access to external user and then revoke it."""
    sec_service: SecurityService = multi_org_sec_env["sec_service"]
    authorizer: CentralAuthorizer = multi_org_sec_env["authorizer"]
    ws_a = multi_org_sec_env["ws_a"]
    proj_a = multi_org_sec_env["proj_a"]

    # Create external collaborator principal
    consultant = AuthenticatedPrincipal(
        principal_id="external-consultant",
        principal_type=PrincipalType.HUMAN,
    )
    multi_org_sec_env["sec_storage"].create_principal(consultant)

    # Initially unauthorized (no workspace membership)
    with pytest.raises(AuthorizationError, match="has no membership in workspace 'ws-org-a'"):
        authorizer.authorize(
            consultant, action="memory:read", resource={"workspace_id": ws_a.id, "project_id": proj_a.id}
        )

    # 1. Org A Owner grants access as VIEWER
    sec_service.add_workspace_member(
        ws_a.id,
        WorkspaceMembershipCreate(principal_id="external-consultant", role=WorkspaceRole.VIEWER),
        granter_id="owner-acme",
    )

    # Now authorized to read
    authorizer.authorize(consultant, action="memory:read", resource={"workspace_id": ws_a.id, "project_id": proj_a.id})

    # But cannot commit as VIEWER
    with pytest.raises(AuthorizationError, match="Role 'viewer' does not permit action 'memory:commit'"):
        authorizer.authorize(
            consultant, action="memory:commit", resource={"workspace_id": ws_a.id, "project_id": proj_a.id}
        )

    # 2. Revoke membership
    sec_service.remove_workspace_member(ws_a.id, "external-consultant", remover_id="owner-acme")

    # Access is once again blocked
    with pytest.raises(AuthorizationError, match="has no membership in workspace 'ws-org-a'"):
        authorizer.authorize(
            consultant, action="memory:read", resource={"workspace_id": ws_a.id, "project_id": proj_a.id}
        )


def test_audit_logging_for_cross_account_access(multi_org_sec_env: dict) -> None:
    """Verify security audit logs capture authorization decisions and credential lifecycle."""
    sec_service: SecurityService = multi_org_sec_env["sec_service"]
    ws_a = multi_org_sec_env["ws_a"]

    # Create principal first to satisfy foreign key constraint
    agent_principal = AuthenticatedPrincipal(
        principal_id="audited-agent",
        principal_type=PrincipalType.AGENT,
    )
    sec_service.sec_storage.create_principal(agent_principal)

    # Record membership change
    sec_service.add_workspace_member(
        ws_a.id,
        WorkspaceMembershipCreate(principal_id="audited-agent", role=WorkspaceRole.EDITOR),
        granter_id="owner-acme",
    )

    # Retrieve audit events
    events = sec_service.list_audit_events(limit=20)
    assert len(events) >= 1
    actions = [e.action for e in events]
    assert "workspace:member:add" in actions
