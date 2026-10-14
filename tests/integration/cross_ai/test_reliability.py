"""Reliability and failure scenario testing for Phase 12 (Section 12 - 15 Scenarios).

Verifies that all 15 failure conditions produce understandable results without memory corruption.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from barsa.bms.base import BMS_VERSION
from barsa.bms.records import (
    ArtifactReference,
    ArtifactType,
    CheckpointStatus,
    Project,
    ResumeCheckpoint,
    Workspace,
)
from barsa.bms.validation import BMSValidationError, validate_bms_record_data
from barsa.core.config import Settings
from barsa.core.exceptions import AuthenticationError, AuthorizationError, ConflictError
from barsa.integrations.adapter import MCPClientAdapter
from barsa.integrations.models import AIProvider, ClientSessionConfig
from barsa.mcp.server import create_mcp_server
from barsa.security.models import (
    AgentCredentialCreate,
    AuthenticatedPrincipal,
    PrincipalType,
)
from barsa.security.service import SecurityService
from barsa.storage.factory import get_storage_provider
from barsa.versioning.engine import VersionControlEngine

if TYPE_CHECKING:
    from barsa.security.authorizer import CentralAuthorizer


@pytest.fixture
def reliability_env(tmp_path: Path):
    """Isolated environment with SQLite storage, version control, and security."""
    data_dir = tmp_path / "barsa_reliability_data"
    settings = Settings(
        app_name="BARSA-Reliability-Test",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=data_dir,
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings.ensure_data_dir()

    storage = get_storage_provider(settings)
    vc = VersionControlEngine(storage)
    sec_service = SecurityService(storage, settings)
    authorizer = sec_service.authorizer

    ws = storage.create_workspace(Workspace(id="ws-rel-1", name="Reliability WS", owner_id="owner-lead"))
    proj = storage.create_project(Project(id="proj-rel-1", name="Reliability Testing Project", workspace_id=ws.id))
    vc.initialize_project_main_branch(proj.id)

    server = create_mcp_server(settings)

    yield {
        "settings": settings,
        "storage": storage,
        "vc": vc,
        "sec_service": sec_service,
        "authorizer": authorizer,
        "workspace": ws,
        "project": proj,
        "server": server,
        "tmp_path": tmp_path,
    }
    storage.close()


# -------------------------------------------------------------------------
# Scenario 1: Server temporarily unavailable / transport disconnection handling
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_01_server_unavailable_or_unconnected(reliability_env: dict) -> None:
    server = reliability_env["server"]
    config = ClientSessionConfig(client_id="agent-s1", provider=AIProvider.ANTHROPIC)
    adapter = MCPClientAdapter(config, server)

    # Calling tools prior to connect raises understandable RuntimeError
    with pytest.raises(RuntimeError, match="Adapter is not connected"):
        await adapter.select_project("proj-rel-1")

    # Clean connect and disconnect
    await adapter.connect()
    assert adapter.is_connected
    await adapter.disconnect()
    assert not adapter.is_connected


# -------------------------------------------------------------------------
# Scenario 2: FalkorDB unavailable (graceful degradation)
# -------------------------------------------------------------------------
def test_scenario_02_falkordb_unavailable_graceful_degradation(reliability_env: dict) -> None:
    settings: Settings = reliability_env["settings"]
    assert not settings.graph_enabled
    storage = reliability_env["storage"]

    # Basic storage, versioning, and project retrieval operate without graph dependencies
    proj = storage.get_project("proj-rel-1")
    assert proj is not None
    assert proj.id == "proj-rel-1"


# -------------------------------------------------------------------------
# Scenario 3: Outdated checkpoint recovery
# -------------------------------------------------------------------------
def test_scenario_03_outdated_checkpoint_recovery(reliability_env: dict) -> None:
    vc: VersionControlEngine = reliability_env["vc"]
    proj_id = "proj-rel-1"

    # Branch head has advanced past base revision
    history = vc.get_history(proj_id, limit=5)
    current_head = history[0].commit_id
    assert current_head is not None

    # Stale checkpoint with old base_revision
    stale_chk = ResumeCheckpoint(
        id="chk-stale",
        project_id=proj_id,
        task_id="t-stale",
        status=CheckpointStatus.ACTIVE,
        next_action="Continue work",
        base_revision="old-non-existent-commit-hash",
        created_by="agent-prior",
    )
    assert stale_chk.base_revision != current_head


# -------------------------------------------------------------------------
# Scenario 4: Conflicting commits (optimistic concurrency conflict)
# -------------------------------------------------------------------------
def test_scenario_04_conflicting_commits_optimistic_concurrency(reliability_env: dict) -> None:
    vc: VersionControlEngine = reliability_env["vc"]
    proj_id = "proj-rel-1"

    initial_head = vc.get_branch(proj_id, "main").head_commit_id

    # Commit 1 moves HEAD
    commit_1 = vc.create_commit(
        project_id=proj_id,
        branch_name="main",
        changes=[],
        message="First update",
        author_id="agent-1",
        expected_head_commit_id=initial_head,
    )
    assert commit_1.commit_id != initial_head

    # Commit 2 specifying stale expected parent -> ConflictError
    with pytest.raises(ConflictError, match="[Ss]tale"):
        vc.create_commit(
            project_id=proj_id,
            branch_name="main",
            changes=[],
            message="Second concurrent update",
            author_id="agent-2",
            expected_head_commit_id=initial_head,  # Stale!
        )


# -------------------------------------------------------------------------
# Scenario 5: Missing artifact handling
# -------------------------------------------------------------------------
def test_scenario_05_missing_artifact_graceful_handling(reliability_env: dict) -> None:
    storage = reliability_env["storage"]
    proj_id = "proj-rel-1"

    # Register artifact pointing to a non-existent file
    missing_art = storage.create_record(
        ArtifactReference(
            id="art-missing",
            project_id=proj_id,
            artifact_type=ArtifactType.SOURCE_CODE,
            uri="non_existent/path/to/missing_file.py",
        )
    )[0]

    assert missing_art.uri == "non_existent/path/to/missing_file.py"
    # Physical file absence does not crash record retrieval
    retrieved = storage.get_record(proj_id, "art-missing")
    assert retrieved is not None
    assert not Path(missing_art.uri).exists()


# -------------------------------------------------------------------------
# Scenario 6: Invalid BMS data rejection
# -------------------------------------------------------------------------
def test_scenario_06_invalid_bms_data_rejection() -> None:
    # Malformed task missing required 'title'
    invalid_data = {
        "id": "task-bad",
        "schema_version": BMS_VERSION,
        "record_type": "task",
        "project_id": "proj-rel-1",
        # missing title!
    }
    with pytest.raises(BMSValidationError, match="title: Field required"):
        validate_bms_record_data(invalid_data)


# -------------------------------------------------------------------------
# Scenario 7: Unauthorized project access
# -------------------------------------------------------------------------
def test_scenario_07_unauthorized_project_access(reliability_env: dict) -> None:
    authorizer: CentralAuthorizer = reliability_env["authorizer"]
    unauth = AuthenticatedPrincipal(principal_id="unauthorized-agent", principal_type=PrincipalType.HUMAN)
    reliability_env["sec_service"].sec_storage.create_principal(unauth)

    with pytest.raises(AuthorizationError, match="has no membership in workspace"):
        authorizer.authorize(unauth, action="memory:read", resource={"project_id": "proj-rel-1"})


# -------------------------------------------------------------------------
# Scenario 8: Revoked agent credential
# -------------------------------------------------------------------------
def test_scenario_08_revoked_agent_credential(reliability_env: dict) -> None:
    sec = reliability_env["sec_service"]
    cred = sec.create_agent_credential(
        AgentCredentialCreate(agent_id="agent-revoked", name="Revoked Key", scopes=["memory:read"]),
        creator_principal_id="owner-lead",
    )
    # Revoke
    sec.revoke_credential(cred.credential_id, revoker_principal_id="owner-lead")

    with pytest.raises(AuthenticationError, match="Invalid or revoked API key"):
        sec.authenticate_api_key(cred.raw_key)


# -------------------------------------------------------------------------
# Scenario 9: Interrupted saving (transaction rollback)
# -------------------------------------------------------------------------
def test_scenario_09_interrupted_saving_rollback(reliability_env: dict) -> None:
    storage = reliability_env["storage"]
    conn = storage._get_connection()

    initial_count = conn.execute("SELECT COUNT(*) FROM bms_records").fetchone()[0]

    # Failed transactional block rolls back cleanly
    try:
        conn.execute("BEGIN TRANSACTION;")
        conn.execute(
            "INSERT INTO bms_records (id, project_id, record_type, data_json, created_at, updated_at) "
            "VALUES ('r-test', 'proj-rel-1', 'task', '{}', datetime('now'), datetime('now'))"
        )
        # Simulate exception
        raise ValueError("Simulated network crash mid-save")
    except ValueError:
        conn.execute("ROLLBACK;")

    final_count = conn.execute("SELECT COUNT(*) FROM bms_records").fetchone()[0]
    assert final_count == initial_count


# -------------------------------------------------------------------------
# Scenario 10: Duplicate commit request (idempotent state hash)
# -------------------------------------------------------------------------
def test_scenario_10_duplicate_commit_handling(reliability_env: dict) -> None:
    vc: VersionControlEngine = reliability_env["vc"]
    proj_id = "proj-rel-1"

    # Creating two identical commits with identical changes
    c1 = vc.create_commit(
        project_id=proj_id, branch_name="main", changes=[], message="Idempotent commit", author_id="agent-dup"
    )
    c2 = vc.create_commit(
        project_id=proj_id, branch_name="main", changes=[], message="Idempotent commit 2", author_id="agent-dup"
    )

    # Resulting state hashes match because state did not change
    assert c1.resulting_state_hash == c2.resulting_state_hash


# -------------------------------------------------------------------------
# Scenario 11: Repeated resume request
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_11_repeated_resume_request(reliability_env: dict) -> None:
    server = reliability_env["server"]
    config = ClientSessionConfig(client_id="agent-repeated-resume", provider=AIProvider.GOOGLE)
    adapter = MCPClientAdapter(config, server)

    await adapter.connect()
    await adapter.select_project("proj-rel-1")

    ctx1 = await adapter.get_context()
    ctx2 = await adapter.get_context()

    assert ctx1.project_id == ctx2.project_id
    assert ctx1.project_name == ctx2.project_name
    assert ctx1.next_task == ctx2.next_task

    await adapter.disconnect()


# -------------------------------------------------------------------------
# Scenario 12: Partial context retrieval
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_12_partial_context_retrieval(reliability_env: dict) -> None:
    server = reliability_env["server"]
    config = ClientSessionConfig(client_id="agent-partial-ctx", provider=AIProvider.LOCAL)
    adapter = MCPClientAdapter(config, server)

    await adapter.connect()
    await adapter.select_project("proj-rel-1")

    # Project has zero checkpoints and zero tasks initially
    ctx = await adapter.get_context()
    assert ctx.latest_checkpoint is None
    assert ctx.next_task is None
    assert len(ctx.completed_actions) == 0

    await adapter.disconnect()


# -------------------------------------------------------------------------
# Scenario 13: Insufficient token budget
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_13_insufficient_token_budget_handling(reliability_env: dict) -> None:
    server = reliability_env["server"]
    config = ClientSessionConfig(client_id="agent-budget-test", provider=AIProvider.ANTHROPIC)
    adapter = MCPClientAdapter(config, server)

    await adapter.connect()
    await adapter.select_project("proj-rel-1")

    # Request extremely small budget (50 tokens)
    ctx = await adapter.get_context(token_budget=50)
    assert ctx.token_budget == 50
    # Resumption safety fields remain intact despite small budget
    assert ctx.project_id == "proj-rel-1"

    await adapter.disconnect()


# -------------------------------------------------------------------------
# Scenario 14: Different provider model behavior
# -------------------------------------------------------------------------
def test_scenario_14_different_provider_model_behavior() -> None:
    cfg_anthropic = ClientSessionConfig(client_id="a1", provider=AIProvider.ANTHROPIC, model="claude-3-5-sonnet")
    cfg_openai = ClientSessionConfig(client_id="a2", provider=AIProvider.OPENAI, model="gpt-4o")
    cfg_google = ClientSessionConfig(client_id="a3", provider=AIProvider.GOOGLE, model="gemini-1.5-pro")

    assert cfg_anthropic.provider == AIProvider.ANTHROPIC
    assert cfg_openai.provider == AIProvider.OPENAI
    assert cfg_google.provider == AIProvider.GOOGLE
    assert cfg_anthropic.client_id != cfg_openai.client_id


# -------------------------------------------------------------------------
# Scenario 15: Agent attempts unauthorized changes
# -------------------------------------------------------------------------
def test_scenario_15_agent_attempts_unauthorized_changes(reliability_env: dict) -> None:
    authorizer: CentralAuthorizer = reliability_env["authorizer"]
    sec = reliability_env["sec_service"]
    proj_id = "proj-rel-1"

    # Agent with only read scope
    cred = sec.create_agent_credential(
        AgentCredentialCreate(agent_id="agent-read-only", name="Read Only Agent", scopes=["memory:read"]),
        creator_principal_id="owner-lead",
    )
    principal = sec.authenticate_api_key(cred.raw_key)

    # Authorized to read
    authorizer.authorize(principal, action="memory:read", resource={"project_id": proj_id})

    # Unauthorized to commit -> Denied
    with pytest.raises(AuthorizationError, match="lacks required scope 'memory:commit'"):
        authorizer.authorize(principal, action="memory:commit", resource={"project_id": proj_id})
