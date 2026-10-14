"""Integration tests for multi-session MCP client handoffs and session isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from barsa.bms.records import Project, Workspace
from barsa.core.config import Settings
from barsa.integrations.adapter import MCPClientAdapter
from barsa.integrations.models import AIProvider, ClientSessionConfig
from barsa.integrations.session import AgentSession
from barsa.mcp.server import create_mcp_server
from barsa.storage.factory import get_storage_provider
from barsa.versioning.engine import VersionControlEngine

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def cross_ai_env(tmp_path: Path):
    """Isolated test environment with storage, version control, and MCP server."""
    data_dir = tmp_path / "barsa_cross_ai_data"
    settings = Settings(
        app_name="BARSA-Cross-AI-Test",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=data_dir,
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings.ensure_data_dir()

    storage = get_storage_provider(settings)
    vc = VersionControlEngine(storage)

    # Seed initial workspace and project
    ws = storage.create_workspace(Workspace(id="ws-auth-1", name="Auth Workspace", owner_id="lead-architect"))
    proj = storage.create_project(
        Project(
            id="proj-auth-1",
            name="Spring Boot JWT Authentication Service",
            workspace_id=ws.id,
            description="Production JWT auth service with token refresh and role validation",
        )
    )
    vc.initialize_project_main_branch(proj.id)

    server = create_mcp_server(settings)

    yield {
        "settings": settings,
        "storage": storage,
        "vc": vc,
        "workspace": ws,
        "project": proj,
        "server": server,
        "tmp_path": tmp_path,
    }
    storage.close()


@pytest.mark.asyncio
async def test_isolated_mcp_sessions_handoff(cross_ai_env: dict) -> None:
    """Demonstrate clean handoff between Agent A (Claude) and Agent B (GPT-4) via MCP."""
    server = cross_ai_env["server"]
    proj_id = cross_ai_env["project"].id

    # ---------------------------------------------------------
    # 1. Agent A (Claude 3.5 Sonnet) Session
    # ---------------------------------------------------------
    config_a = ClientSessionConfig(
        client_id="claude-session-1",
        provider=AIProvider.ANTHROPIC,
        model="claude-3-5-sonnet-20241022",
    )
    adapter_a = MCPClientAdapter(config_a, server)
    session_a = AgentSession(config_a, adapter_a)

    ctx_a = await session_a.start(proj_id)
    assert ctx_a.project_id == proj_id

    # Agent A implements Login endpoint and records a Decision
    records_a = [
        {
            "id": "dec-jwt-hs512",
            "schema_version": "0.1",
            "record_type": "decision",
            "project_id": proj_id,
            "title": "Use HMAC-SHA512 for JWT Signing",
            "decision": "Standardize on HS512 with 512-bit secure secret key",
            "rationale": "Selected HS512 over RS256 for symmetric microservice architecture",
            "status": "approved",
            "created_by": config_a.client_id,
        },
        {
            "id": "task-login-endpoint",
            "schema_version": "0.1",
            "record_type": "task",
            "project_id": proj_id,
            "title": "Implement POST /api/auth/login",
            "description": "Verify credentials and issue signed JWT access token",
            "status": "completed",
            "priority": "high",
        },
    ]

    res_a = await session_a.complete_work_and_commit(
        task_id="task-login-endpoint",
        task_title="Implement POST /api/auth/login",
        action_performed="Completed user authentication and JWT issue endpoint",
        new_records=records_a,
        next_task_for_future_agent="Implement JWT token refresh endpoint (/api/auth/refresh)",
        commit_message="feat(auth): add login endpoint and HS512 signing decision",
        test_results={"passed": True, "tests_run": 3},
    )
    assert res_a.new_commit_hash != "commit_hash_unknown"
    await session_a.finish()

    # Verify session A's local log has 4 entries and adapter is disconnected
    assert len(session_a.session_conversation_log) == 4
    assert not adapter_a.is_connected

    # ---------------------------------------------------------
    # 2. Agent B (GPT-4o) Fresh Session (Zero in-memory conversation)
    # ---------------------------------------------------------
    config_b = ClientSessionConfig(
        client_id="gpt4o-session-2",
        provider=AIProvider.OPENAI,
        model="gpt-4o",
    )
    adapter_b = MCPClientAdapter(config_b, server)
    session_b = AgentSession(config_b, adapter_b)

    # Start session B
    ctx_b = await session_b.start(proj_id)

    # Verify Agent B has an empty history except its own initialization
    assert len(session_b.session_conversation_log) == 3
    assert session_b.session_conversation_log[0]["role"] == "system"
    assert "gpt4o-session-2" in session_b.session_conversation_log[0]["content"]

    # Verify context retrieved from Barsa contains the exact state left by Agent A
    understanding = session_b.inspect_understanding()
    assert understanding["next_task"] == "Implement JWT token refresh endpoint (/api/auth/refresh)"
    assert "Completed user authentication and JWT issue endpoint" in understanding["completed_actions"]
    assert ctx_b.latest_checkpoint is not None

    # Agent B performs the continuation task
    records_b = [
        {
            "id": "task-refresh-endpoint",
            "schema_version": "0.1",
            "record_type": "task",
            "project_id": proj_id,
            "title": "Implement POST /api/auth/refresh",
            "description": "Validate refresh token and issue rotated access token",
            "status": "completed",
            "priority": "high",
        }
    ]

    res_b = await session_b.complete_work_and_commit(
        task_id="task-refresh-endpoint",
        task_title="Implement POST /api/auth/refresh",
        action_performed="Implemented refresh token validation and token rotation endpoint",
        new_records=records_b,
        next_task_for_future_agent="Implement role-based authorization filter",
        commit_message="feat(auth): implement refresh token endpoint with rotation",
        test_results={"passed": True, "tests_run": 5},
    )
    assert res_b.new_commit_hash != res_a.new_commit_hash
    await session_b.finish()

    # ---------------------------------------------------------
    # 3. Verify Version History DAG
    # ---------------------------------------------------------
    vc = cross_ai_env["vc"]
    commits = vc.get_history(proj_id, limit=10)
    assert len(commits) == 3  # Initial + Agent A + Agent B
    assert commits[0].message == "feat(auth): implement refresh token endpoint with rotation"
    assert commits[1].message == "feat(auth): add login endpoint and HS512 signing decision"
    assert commits[2].message == "Initial project memory root commit"

    # Verify agent attribution in checkpoint records committed into DAG
    chk_b = next(c.after_state for c in commits[0].changes if c.record_type == "checkpoint")
    chk_a = next(c.after_state for c in commits[1].changes if c.record_type == "checkpoint")
    assert chk_b["created_by"] == "gpt4o-session-2"
    assert chk_a["created_by"] == "claude-session-1"


@pytest.mark.asyncio
async def test_unconnected_session_error(cross_ai_env: dict) -> None:
    """Verify that attempting operations before connect() or start() fails cleanly."""
    server = cross_ai_env["server"]
    config = ClientSessionConfig(client_id="unconnected-agent", provider=AIProvider.GOOGLE)
    adapter = MCPClientAdapter(config, server)
    session = AgentSession(config, adapter)

    with pytest.raises(RuntimeError, match="Session has not been started"):
        session.inspect_understanding()

    with pytest.raises(RuntimeError, match="Must call connect"):
        await adapter.authenticate()

    with pytest.raises(RuntimeError, match="Adapter is not connected"):
        await adapter.select_project("proj-auth-1")


@pytest.mark.asyncio
async def test_concurrent_sessions_read_only(cross_ai_env: dict) -> None:
    """Verify that multiple client sessions can connect concurrently and read project state."""
    server = cross_ai_env["server"]
    proj_id = cross_ai_env["project"].id

    config1 = ClientSessionConfig(client_id="client-concurrent-1", provider=AIProvider.ANTHROPIC)
    config2 = ClientSessionConfig(client_id="client-concurrent-2", provider=AIProvider.OPENAI)

    adapter1 = MCPClientAdapter(config1, server)
    adapter2 = MCPClientAdapter(config2, server)

    await adapter1.connect()
    await adapter2.connect()

    p1 = await adapter1.select_project(proj_id)
    p2 = await adapter2.select_project(proj_id)

    assert p1["project_id"] == proj_id
    assert p2["project_id"] == proj_id

    ctx1 = await adapter1.get_context()
    ctx2 = await adapter2.get_context()

    assert ctx1.project_id == proj_id
    assert ctx2.project_id == proj_id

    await adapter2.disconnect()
    await adapter1.disconnect()
