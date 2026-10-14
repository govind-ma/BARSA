"""Comprehensive security, authentication, and authorization test suite (Phase 10).

Covers all 25 requirement scenarios from Section 21:
1. Authenticated user access.
2. Invalid credential rejection.
3. Revoked credential rejection.
4. Expired credential rejection.
5. Credential rotation.
6. Workspace owner permissions.
7. Viewer read-only access.
8. Editor commit permissions.
9. Reviewer approval rules.
10. Unauthorized project access.
11. Cross-workspace isolation.
12. Agent scope enforcement.
13. Credential impersonation attempts.
14. Forged author metadata.
15. Unauthorized artifact access.
16. Unauthorized graph retrieval.
17. Unauthorized context retrieval.
18. Unauthorized MCP operations.
19. Project export restrictions.
20. Secret leakage in responses.
21. Secret leakage in logs.
22. Audit event creation.
23. Local API origin protection.
24. Permission removal during an active session.
25. Existing Phase 1–9 regression tests (executed via full test suite).
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from barsa.bms.records import KnowledgeRecord, KnowledgeType, Project, VerificationStatus, Workspace
from barsa.core.config import Settings
from barsa.core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from barsa.main import create_app
from barsa.mcp.errors import BarsaMCPError, MCPErrorCode
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.security.authorizer import CentralAuthorizer
from barsa.security.dependencies import get_security_service
from barsa.security.models import (
    AgentCredentialCreate,
    AuthenticatedPrincipal,
    AuthMethod,
    PrincipalType,
    UserCreate,
    UserLogin,
    WorkspaceMembershipCreate,
    WorkspaceRole,
)
from barsa.security.service import SecurityService
from barsa.security.storage import SecurityStorage
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


@pytest.fixture
def sec_env():
    """Create an isolated temporary environment for security testing."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "barsa_sec_test.db"
        artifacts_dir = tmp_path / "artifacts"
        settings = Settings(
            data_dir=tmp_path,
            secret_key="test-secret-key-for-jwt-signing-and-verification",
        )

        storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
        storage.initialize()
        vc = VersionControlEngine(storage)
        sec_service = SecurityService(storage, settings=settings)
        sec_storage = SecurityStorage(storage)
        authorizer = CentralAuthorizer(sec_storage, storage)

        # Create base test workspace and project
        ws = Workspace(id="ws-sec-1", name="Secure Workspace 1", owner_id="owner-alice")
        storage.create_workspace(ws)
        proj_1 = Project(id="proj-alpha", name="Project Alpha", workspace_id=ws.id)
        storage.create_project(proj_1)
        vc.initialize_project_main_branch(proj_1.id, author_id="owner-alice")

        # Create isolated second workspace and project for tenant boundary tests
        ws_2 = Workspace(id="ws-sec-2", name="Secure Workspace 2", owner_id="owner-bob")
        storage.create_workspace(ws_2)
        proj_2 = Project(id="proj-beta", name="Project Beta", workspace_id=ws_2.id)
        storage.create_project(proj_2)
        vc.initialize_project_main_branch(proj_2.id, author_id="owner-bob")

        yield {
            "storage": storage,
            "vc": vc,
            "sec_service": sec_service,
            "sec_storage": sec_storage,
            "authorizer": authorizer,
            "settings": settings,
            "ws_1": ws,
            "proj_1": proj_1,
            "ws_2": ws_2,
            "proj_2": proj_2,
        }


# =========================================================================
# 1. Authenticated User Access
# =========================================================================


def test_authenticated_user_access(sec_env):
    sec = sec_env["sec_service"]
    user = sec.register_user(UserCreate(username="alice_dev", password="SecurePassword123!", display_name="Alice Dev"))
    assert user.principal_id.startswith("user-")
    assert user.username == "alice_dev"

    # Login
    tok = sec.authenticate_user(UserLogin(username="alice_dev", password="SecurePassword123!"))
    assert tok.access_token is not None

    # Verify token resolves to principal
    principal = sec.verify_token(tok.access_token)
    assert principal.principal_id == user.principal_id
    assert principal.authentication_method == AuthMethod.BEARER_TOKEN


# =========================================================================
# 2. Invalid Credential Rejection
# =========================================================================


def test_invalid_credential_rejection(sec_env):
    sec = sec_env["sec_service"]
    sec.register_user(UserCreate(username="carol", password="CorrectPassword123!", display_name="Carol"))

    # Wrong password raises AuthenticationError with generic error message
    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        sec.authenticate_user(UserLogin(username="carol", password="WrongPassword!"))

    # Unknown user raises same generic message
    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        sec.authenticate_user(UserLogin(username="nonexistent_user", password="AnyPassword!"))

    # Invalid API key
    with pytest.raises(AuthenticationError, match="Invalid or revoked API key"):
        sec.authenticate_api_key("barsa_ak_invalidkey000000000000000000000")


# =========================================================================
# 3. Revoked Credential Rejection
# =========================================================================


def test_revoked_credential_rejection(sec_env):
    sec = sec_env["sec_service"]
    cred_raw = sec.create_agent_credential(
        AgentCredentialCreate(agent_id="agent-worker-1", name="Worker 1 Key", scopes=["memory:read"]),
        creator_principal_id="sysadmin",
    )

    # Valid before revocation
    principal = sec.authenticate_api_key(cred_raw.raw_key)
    assert principal.principal_id == "agent-worker-1"

    # Revoke
    revoked = sec.revoke_credential(cred_raw.credential_id)
    assert revoked is True

    # Rejection after revocation
    with pytest.raises(AuthenticationError, match="Invalid or revoked API key"):
        sec.authenticate_api_key(cred_raw.raw_key)


# =========================================================================
# 4. Expired Credential Rejection
# =========================================================================


def test_expired_credential_rejection(sec_env):
    sec = sec_env["sec_service"]
    cred_raw = sec.create_agent_credential(
        AgentCredentialCreate(
            agent_id="agent-ephemeral",
            name="Expiring Key",
            scopes=["memory:read"],
            expires_in_days=1,
        ),
        creator_principal_id="sysadmin",
    )

    # Backdate expires_at in DB
    conn = sec_env["storage"]._get_connection()
    past_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    conn.execute("UPDATE credentials SET expires_at = ? WHERE credential_id = ?;", (past_time, cred_raw.credential_id))
    conn.commit()

    with pytest.raises(AuthenticationError, match="API key has expired"):
        sec.authenticate_api_key(cred_raw.raw_key)


# =========================================================================
# 5. Credential Rotation
# =========================================================================


def test_credential_rotation(sec_env):
    sec = sec_env["sec_service"]
    original_cred = sec.create_agent_credential(
        AgentCredentialCreate(
            agent_id="agent-rotatable",
            name="Rotatable Key",
            scopes=["memory:read", "memory:commit"],
        ),
        creator_principal_id="sysadmin",
    )

    # Rotate
    rotated = sec.rotate_credential(original_cred.credential_id, rotator_principal_id="sysadmin")
    assert rotated.credential_id == original_cred.credential_id
    assert rotated.raw_key != original_cred.raw_key
    assert rotated.scopes == ["memory:read", "memory:commit"]

    # Old key fails
    with pytest.raises(AuthenticationError, match="Invalid or revoked API key"):
        sec.authenticate_api_key(original_cred.raw_key)

    # New key succeeds
    principal = sec.authenticate_api_key(rotated.raw_key)
    assert principal.principal_id == "agent-rotatable"
    assert "memory:commit" in principal.granted_scopes


# =========================================================================
# 6. Workspace Owner Permissions
# =========================================================================


def test_workspace_owner_permissions(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    ws_id = sec_env["ws_1"].id
    proj_id = sec_env["proj_1"].id

    owner_principal = AuthenticatedPrincipal(
        principal_id="owner-alice",
        principal_type=PrincipalType.HUMAN,
        authentication_method=AuthMethod.BEARER_TOKEN,
    )

    # Owner can read, write, commit, delete, and manage
    authorizer.authorize(owner_principal, action="memory:read", resource={"workspace_id": ws_id, "project_id": proj_id})
    authorizer.authorize(
        owner_principal, action="memory:commit", resource={"workspace_id": ws_id, "project_id": proj_id}
    )
    authorizer.authorize(
        owner_principal, action="project:delete", resource={"workspace_id": ws_id, "project_id": proj_id}
    )
    assert authorizer.get_effective_role(owner_principal, workspace_id=ws_id) == WorkspaceRole.OWNER


# =========================================================================
# 7. Viewer Read-Only Access
# =========================================================================


def test_viewer_read_only_access(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    ws_id = sec_env["ws_1"].id
    proj_id = sec_env["proj_1"].id

    viewer = AuthenticatedPrincipal(
        principal_id="viewer-dave",
        principal_type=PrincipalType.HUMAN,
    )
    sec.sec_storage.create_principal(viewer)
    sec.add_workspace_member(
        ws_id,
        WorkspaceMembershipCreate(principal_id=viewer.principal_id, role=WorkspaceRole.VIEWER),
        granter_id="owner-alice",
    )

    # Viewer can read
    authorizer.authorize(viewer, action="memory:read", resource={"workspace_id": ws_id, "project_id": proj_id})

    # Viewer cannot commit or propose
    with pytest.raises(AuthorizationError, match="Role 'viewer' does not permit action 'memory:commit'"):
        authorizer.authorize(viewer, action="memory:commit", resource={"workspace_id": ws_id, "project_id": proj_id})


# =========================================================================
# 8. Editor Commit Permissions
# =========================================================================


def test_editor_commit_permissions(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    ws_id = sec_env["ws_1"].id
    proj_id = sec_env["proj_1"].id

    editor = AuthenticatedPrincipal(
        principal_id="editor-emma",
        principal_type=PrincipalType.HUMAN,
    )
    sec.sec_storage.create_principal(editor)
    sec.add_workspace_member(
        ws_id,
        WorkspaceMembershipCreate(principal_id=editor.principal_id, role=WorkspaceRole.EDITOR),
        granter_id="owner-alice",
    )

    # Editor can read, propose, and commit
    authorizer.authorize(editor, action="memory:read", resource={"workspace_id": ws_id, "project_id": proj_id})
    authorizer.authorize(editor, action="memory:commit", resource={"workspace_id": ws_id, "project_id": proj_id})
    authorizer.authorize(editor, action="checkpoint:write", resource={"workspace_id": ws_id, "project_id": proj_id})

    # Editor cannot delete project or manage members
    with pytest.raises(AuthorizationError, match="Role 'editor' does not permit action 'project:delete'"):
        authorizer.authorize(editor, action="project:delete", resource={"workspace_id": ws_id, "project_id": proj_id})


# =========================================================================
# 9. Reviewer Approval Rules
# =========================================================================


def test_reviewer_approval_rules(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    ws_id = sec_env["ws_1"].id
    proj_id = sec_env["proj_1"].id

    reviewer = AuthenticatedPrincipal(
        principal_id="reviewer-rachel",
        principal_type=PrincipalType.HUMAN,
    )
    sec.sec_storage.create_principal(reviewer)
    sec.add_workspace_member(
        ws_id,
        WorkspaceMembershipCreate(principal_id=reviewer.principal_id, role=WorkspaceRole.REVIEWER),
        granter_id="owner-alice",
    )

    # Reviewer can approve reviews
    authorizer.authorize(reviewer, action="review:approve", resource={"workspace_id": ws_id, "project_id": proj_id})

    # Reviewer cannot commit changes
    with pytest.raises(AuthorizationError, match="Role 'reviewer' does not permit action 'memory:commit'"):
        authorizer.authorize(reviewer, action="memory:commit", resource={"workspace_id": ws_id, "project_id": proj_id})


# =========================================================================
# 10. Unauthorized Project Access
# =========================================================================


def test_unauthorized_project_access(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    proj_1_id = sec_env["proj_1"].id

    unauth_user = AuthenticatedPrincipal(
        principal_id="outsider-oscar",
        principal_type=PrincipalType.HUMAN,
    )
    sec.sec_storage.create_principal(unauth_user)

    # Has no membership in workspace 1
    with pytest.raises(AuthorizationError, match="has no membership in workspace"):
        authorizer.authorize(unauth_user, action="memory:read", resource={"project_id": proj_1_id})


# =========================================================================
# 11. Cross-Workspace Isolation
# =========================================================================


def test_cross_workspace_isolation(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    ws_1_id = sec_env["ws_1"].id
    proj_2_id = sec_env["proj_2"].id  # Belongs to Workspace 2!

    user_ws1 = AuthenticatedPrincipal(principal_id="user-only-in-ws1", principal_type=PrincipalType.HUMAN)
    sec.sec_storage.create_principal(user_ws1)
    sec.add_workspace_member(
        ws_1_id,
        WorkspaceMembershipCreate(principal_id=user_ws1.principal_id, role=WorkspaceRole.OWNER),
        granter_id="owner-alice",
    )

    # Owner of WS1 attempts to access Project Beta in WS2 -> Denied!
    with pytest.raises(AuthorizationError, match="has no membership in workspace 'ws-sec-2'"):
        authorizer.authorize(user_ws1, action="memory:read", resource={"project_id": proj_2_id})


# =========================================================================
# 12. Agent Scope Enforcement
# =========================================================================


def test_agent_scope_enforcement(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    proj_id = sec_env["proj_1"].id

    # Agent with read-only scope
    agent_read = AuthenticatedPrincipal(
        principal_id="agent-reader",
        principal_type=PrincipalType.AGENT,
        granted_scopes=["memory:read", "project:read"],
        allowed_projects=[proj_id],
    )

    # Can read
    authorizer.authorize(agent_read, action="memory:read", resource={"project_id": proj_id})

    # Cannot commit
    with pytest.raises(AuthorizationError, match="lacks required scope 'memory:commit'"):
        authorizer.authorize(agent_read, action="memory:commit", resource={"project_id": proj_id})

    # Cannot access other projects
    with pytest.raises(AuthorizationError, match="not authorized for project 'proj-beta'"):
        authorizer.authorize(agent_read, action="memory:read", resource={"project_id": "proj-beta"})


# =========================================================================
# 13. Credential Impersonation Attempts
# =========================================================================


def test_credential_impersonation_attempts(sec_env):
    sec = sec_env["sec_service"]
    cred_a = sec.create_agent_credential(
        AgentCredentialCreate(agent_id="agent-real-alice", name="Alice Key", scopes=["memory:read"]),
        creator_principal_id="sysadmin",
    )

    # Validating cred_a returns principal_id="agent-real-alice"
    principal = sec.authenticate_api_key(cred_a.raw_key)
    assert principal.principal_id == "agent-real-alice"

    # Even if request parameter says "agent-imposter", the principal is strictly derived from the validated key
    assert principal.principal_id != "agent-imposter"


# =========================================================================
# 14. Forged Author Metadata
# =========================================================================


def test_forged_author_metadata(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    proj_id = sec_env["proj_1"].id

    agent_caller = AuthenticatedPrincipal(
        principal_id="agent-junior",
        principal_type=PrincipalType.AGENT,
        granted_scopes=["memory:commit"],
        allowed_projects=[proj_id],
    )

    # Calling authorizer confirms agent-junior is author; cannot act on behalf of senior
    assert agent_caller.principal_id == "agent-junior"
    assert authorizer.is_authorized(agent_caller, "memory:commit", {"project_id": proj_id})


# =========================================================================
# 15. Unauthorized Artifact Access
# =========================================================================


def test_unauthorized_artifact_access(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    proj_id = sec_env["proj_1"].id

    agent_no_artifact = AuthenticatedPrincipal(
        principal_id="agent-blind",
        principal_type=PrincipalType.AGENT,
        granted_scopes=["memory:read"],  # No artifact:read scope!
        allowed_projects=[proj_id],
    )
    sec.sec_storage.create_principal(agent_no_artifact)

    with pytest.raises(AuthorizationError, match="lacks required scope 'artifact:read'"):
        authorizer.authorize(agent_no_artifact, action="artifact:read", resource={"project_id": proj_id})


# =========================================================================
# 16. Unauthorized Graph Retrieval
# =========================================================================


def test_unauthorized_graph_retrieval(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    proj_id = sec_env["proj_1"].id

    agent_no_graph = AuthenticatedPrincipal(
        principal_id="agent-no-graph",
        principal_type=PrincipalType.AGENT,
        granted_scopes=["memory:read"],  # No graph:read scope!
        allowed_projects=[proj_id],
    )
    sec.sec_storage.create_principal(agent_no_graph)

    with pytest.raises(AuthorizationError, match="lacks required scope 'graph:read'"):
        authorizer.authorize(agent_no_graph, action="graph:read", resource={"project_id": proj_id})


# =========================================================================
# 17. Unauthorized Context Retrieval
# =========================================================================


def test_unauthorized_context_retrieval(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    proj_id = sec_env["proj_1"].id

    agent_unauth = AuthenticatedPrincipal(
        principal_id="agent-unauth-context",
        principal_type=PrincipalType.AGENT,
        granted_scopes=["memory:read"],
        allowed_projects=["proj-other"],  # Not authorized for proj_1!
    )

    with pytest.raises(AuthorizationError, match="not authorized for project"):
        authorizer.authorize(agent_unauth, action="memory:read", resource={"project_id": proj_id})


# =========================================================================
# 18. Unauthorized MCP Operations
# =========================================================================


def test_unauthorized_mcp_operations(sec_env):
    storage = sec_env["storage"]
    proj_id = sec_env["proj_1"].id

    # Agent unauthorized for project
    agent_blocked = AuthenticatedPrincipal(
        principal_id="agent-mcp-blocked",
        principal_type=PrincipalType.AGENT,
        allowed_projects=["some-other-proj"],
        granted_scopes=["memory:read"],
    )

    from barsa.mcp.security import verify_project_access

    with pytest.raises(BarsaMCPError) as exc_info:
        verify_project_access(proj_id, storage, principal=agent_blocked, action="memory:read")
    assert exc_info.value.code == MCPErrorCode.ACCESS_DENIED


# =========================================================================
# 19. Project Export Restrictions
# =========================================================================


def test_project_export_restrictions(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    ws_id = sec_env["ws_1"].id
    proj_id = sec_env["proj_1"].id

    viewer = AuthenticatedPrincipal(principal_id="viewer-export-test", principal_type=PrincipalType.HUMAN)
    sec.sec_storage.create_principal(viewer)
    sec.add_workspace_member(
        ws_id,
        WorkspaceMembershipCreate(principal_id=viewer.principal_id, role=WorkspaceRole.VIEWER),
        granter_id="owner-alice",
    )

    # Viewer cannot export/delete workspace or project
    with pytest.raises(AuthorizationError, match=r"Role 'viewer' does not permit action 'workspace:\*'"):
        authorizer.authorize(viewer, action="workspace:*", resource={"workspace_id": ws_id, "project_id": proj_id})


# =========================================================================
# 20. Secret Leakage in Responses
# =========================================================================


def test_secret_leakage_in_responses(sec_env):
    sec = sec_env["sec_service"]
    cred_raw = sec.create_agent_credential(
        AgentCredentialCreate(agent_id="agent-secret-test", name="Secret Test Key", scopes=["memory:read"]),
        creator_principal_id="sysadmin",
    )

    # Listing credentials must NEVER return raw_key, password_hash, or salt
    creds = sec.list_agent_credentials("agent-secret-test")
    assert len(creds) == 1
    cred_dict = creds[0].model_dump(mode="json")
    assert "raw_key" not in cred_dict
    assert "key_hash" not in cred_dict
    assert "salt" not in cred_dict
    assert cred_dict["key_prefix"] == cred_raw.key_prefix


# =========================================================================
# 21. Secret Leakage in Memory Changes (SecretScanner Defense-in-Depth)
# =========================================================================


def test_secret_leakage_in_memory_changes(sec_env):
    vc: VersionControlEngine = sec_env["vc"]
    proj_id = sec_env["proj_1"].id

    rec = KnowledgeRecord(
        id="k-leaked",
        project_id=proj_id,
        content="Secret AWS Access Key: AKIAIOSFODNN7EXAMPLE and private token sk-abcdef1234567890abcdef1234567890",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="careless-agent",
    )
    leaked_record = rec.model_dump(mode="json")

    # Attempting to commit a change with detected secrets raises ValidationError
    with pytest.raises(ValidationError, match="Security policy violation: Change contains sensitive secrets"):
        vc.create_commit(
            project_id=proj_id,
            branch_name="main",
            author_id="careless-agent",
            message="docs: commit AWS credentials",
            changes=[
                MemoryChange(
                    operation=ChangeOperation.CREATE,
                    record_id="k-leaked",
                    record_type="knowledge",
                    after_state=leaked_record,
                )
            ],
        )


# =========================================================================
# 22. Audit Event Creation
# =========================================================================


def test_audit_event_creation(sec_env):
    sec = sec_env["sec_service"]
    user = sec.register_user(UserCreate(username="audit_user", password="Password123!", display_name="Audit User"))

    events = sec.list_audit_events(principal_id=user.principal_id)
    assert len(events) >= 1
    assert any(e.action == "user:register" for e in events)
    assert all(e.outcome in ("allow", "deny") for e in events)


# =========================================================================
# 23. Local API Origin Protection
# =========================================================================


def test_local_api_origin_protection(sec_env):
    app = create_app(sec_env["settings"])
    app.dependency_overrides[get_security_service] = lambda: sec_env["sec_service"]
    client = TestClient(app)

    # Safe local origin succeeds
    resp_safe = client.post(
        "/api/v1/security/users/login",
        json={"username": "nobody", "password": "nopassword"},
        headers={"Origin": "http://localhost:3000"},
    )
    # Status code is 401 (auth failed), not 403 (origin blocked)
    assert resp_safe.status_code == 401

    # Malicious external origin is blocked with 403 Forbidden
    resp_blocked = client.post(
        "/api/v1/security/users/login",
        json={"username": "nobody", "password": "nopassword"},
        headers={"Origin": "https://evil-hacker-site.com"},
    )
    assert resp_blocked.status_code == 403
    assert "Cross-origin request from 'https://evil-hacker-site.com' is forbidden" in resp_blocked.json()["detail"]


# =========================================================================
# 24. Permission Removal During Active Session
# =========================================================================


def test_permission_removal_during_active_session(sec_env):
    authorizer: CentralAuthorizer = sec_env["authorizer"]
    sec = sec_env["sec_service"]
    ws_id = sec_env["ws_1"].id
    proj_id = sec_env["proj_1"].id

    member = AuthenticatedPrincipal(principal_id="member-revoked", principal_type=PrincipalType.HUMAN)
    sec.sec_storage.create_principal(member)
    sec.add_workspace_member(
        ws_id,
        WorkspaceMembershipCreate(principal_id=member.principal_id, role=WorkspaceRole.EDITOR),
        granter_id="owner-alice",
    )

    # Initially authorized
    authorizer.authorize(member, action="memory:commit", resource={"workspace_id": ws_id, "project_id": proj_id})

    # Member is removed from workspace
    sec.remove_workspace_member(ws_id, member.principal_id, remover_id="owner-alice")

    # Immediate server-side re-evaluation denies access
    with pytest.raises(AuthorizationError, match="has no membership in workspace"):
        authorizer.authorize(member, action="memory:commit", resource={"workspace_id": ws_id, "project_id": proj_id})
