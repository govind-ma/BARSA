"""Comprehensive test suite for Phase 6 Model Context Protocol (MCP) Server."""

import json
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.memory import create_client_server_memory_streams

from barsa.bms.records import (
    CheckpointStatus,
    DecisionRecord,
    DecisionStatus,
    KnowledgeRecord,
    KnowledgeType,
    Project,
    ResumeCheckpoint,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    VerificationStatus,
    Workspace,
)
from barsa.core.config import Settings
from barsa.mcp.errors import BarsaMCPError, MCPErrorCode
from barsa.mcp.security import (
    validate_branch_name,
    validate_changes_payload,
    validate_depth,
    validate_identifier,
    validate_limit,
    validate_query_string,
)
from barsa.mcp.server import create_mcp_server
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.versioning.engine import VersionControlEngine


@pytest.fixture
def mcp_test_env(tmp_path: Path):
    """Fixture initializing temporary SQLite storage and configured MCP server."""
    from barsa.storage.factory import get_storage_provider

    settings = Settings(
        app_name="BARSA-MCP-Test",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=tmp_path / "barsa_data",
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings.ensure_data_dir()

    storage = get_storage_provider(settings)
    vc = VersionControlEngine(storage)

    # Seed Workspace and Project
    ws = storage.create_workspace(Workspace(id="ws-mcp-1", name="MCP Test Workspace", owner_id="test-user"))
    proj = storage.create_project(
        Project(
            id="proj-mcp-1", name="MCP Test Project", workspace_id=ws.id, description="Project for testing MCP tools"
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


def test_mcp_tool_registration(mcp_test_env: dict) -> None:
    """1. Verify that all 12 tools are registered on the MCPServer."""
    server = mcp_test_env["server"]
    tools = server._tool_manager._tools

    expected_tools = [
        "barsa_list_projects",
        "barsa_get_project",
        "barsa_search_memory",
        "barsa_get_memory",
        "barsa_get_checkpoint",
        "barsa_resume",
        "barsa_get_history",
        "barsa_get_diff",
        "barsa_propose_changes",
        "barsa_commit",
        "barsa_list_conflicts",
        "barsa_get_graph_context",
        "barsa_build_context",
    ]

    for tool_name in expected_tools:
        assert tool_name in tools, f"Tool '{tool_name}' was not registered on MCPServer."
        tool = tools[tool_name]
        assert tool.description, f"Tool '{tool_name}' has no description."


def test_mcp_resources_and_prompts_registration(mcp_test_env: dict) -> None:
    """2. Verify that standard read-only resources and prompts are registered."""
    server = mcp_test_env["server"]
    resources = server._resource_manager._resources
    templates = server._resource_manager._templates
    prompts = server._prompt_manager._prompts

    assert "barsa://system/info" in resources
    assert "barsa://bms/schema/version" in resources
    assert "barsa://bms/schema/records" in resources
    assert "barsa://projects/{project_id}/overview" in templates
    assert "barsa://projects/{project_id}/checkpoints/latest" in templates

    assert "barsa_resume_project" in prompts
    assert "barsa_save_checkpoint" in prompts
    assert "barsa_review_changes" in prompts


def test_mcp_input_validation() -> None:
    """3. Verify input validation and security boundary checks."""
    # Identifier validation
    assert validate_identifier("proj", "proj-alpha_1.0") == "proj-alpha_1.0"
    with pytest.raises(BarsaMCPError) as exc_info:
        validate_identifier("proj", "proj/with/slashes")
    assert exc_info.value.code == MCPErrorCode.INVALID_INPUT

    with pytest.raises(BarsaMCPError):
        validate_identifier("proj", "")

    # Branch name validation
    assert validate_branch_name("feature/add-auth_v2") == "feature/add-auth_v2"
    with pytest.raises(BarsaMCPError):
        validate_branch_name("../dangerous/path")
    with pytest.raises(BarsaMCPError):
        validate_branch_name("/leading-slash")

    # Query string validation
    assert validate_query_string("search terms") == "search terms"
    with pytest.raises(BarsaMCPError):
        validate_query_string("")
    with pytest.raises(BarsaMCPError):
        validate_query_string("a" * 501)

    # Clamping limits and depth
    assert validate_limit(10) == 10
    assert validate_limit(500) == 100
    assert validate_depth(10) == 5

    # Changes payload validation
    with pytest.raises(BarsaMCPError):
        validate_changes_payload([])
    with pytest.raises(BarsaMCPError):
        validate_changes_payload([{"op": "create"}] * 51)


def test_mcp_list_projects_tool(mcp_test_env: dict) -> None:
    """4. Test barsa_list_projects tool and pagination."""
    server = mcp_test_env["server"]
    proj = mcp_test_env["project"]

    fn = server._tool_manager._tools["barsa_list_projects"].fn
    res = fn(limit=10, offset=0)

    assert "projects" in res
    assert res["total_count"] >= 1
    matching = [p for p in res["projects"] if p["project_id"] == proj.id]
    assert len(matching) == 1
    assert matching[0]["project_name"] == proj.name
    assert matching[0]["latest_main_commit"] is not None


def test_mcp_get_project_tool(mcp_test_env: dict) -> None:
    """5. Test barsa_get_project tool and not-found rejection."""
    server = mcp_test_env["server"]
    proj = mcp_test_env["project"]

    fn = server._tool_manager._tools["barsa_get_project"].fn
    res = fn(project_id=proj.id)

    assert res["project_id"] == proj.id
    assert res["project_name"] == proj.name
    assert res["current_main_commit"] is not None

    # Rejection of non-existent project
    with pytest.raises(ToolError):
        fn(project_id="non-existent-proj")


def test_mcp_search_and_get_memory_tools(mcp_test_env: dict) -> None:
    """6. Test barsa_search_memory and barsa_get_memory with historical lookups."""
    server = mcp_test_env["server"]
    vc: VersionControlEngine = mcp_test_env["vc"]
    proj = mcp_test_env["project"]

    # Commit a knowledge record
    kn = KnowledgeRecord(
        id="kn-search-1",
        project_id=proj.id,
        content="Cryptographic token expiration standard",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="agent-1",
    )
    c1 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=kn.id,
                record_type="knowledge",
                after_state=kn.model_dump(mode="json"),
            )
        ],
        message="Add cryptographic token standard",
        author_id="agent-1",
    )

    search_fn = server._tool_manager._tools["barsa_search_memory"].fn
    search_res = search_fn(project_id=proj.id, query="cryptographic")
    assert search_res["total_matches"] >= 1
    assert search_res["matches"][0]["record_id"] == "kn-search-1"
    assert "retrieval_limitations" in search_res

    # Test exact get memory
    get_fn = server._tool_manager._tools["barsa_get_memory"].fn
    get_res = get_fn(project_id=proj.id, record_id="kn-search-1")
    assert get_res["record"]["id"] == "kn-search-1"
    assert get_res["commit_id"] is None

    # Test historical get memory at commit
    get_hist = get_fn(project_id=proj.id, record_id="kn-search-1", commit_id=c1.commit_id)
    assert get_hist["record"]["id"] == "kn-search-1"
    assert get_hist["commit_id"] == c1.commit_id


def test_mcp_get_checkpoint_and_resume_package(mcp_test_env: dict) -> None:
    """7. Test barsa_get_checkpoint and barsa_resume structured package."""
    server = mcp_test_env["server"]
    vc: VersionControlEngine = mcp_test_env["vc"]
    proj = mcp_test_env["project"]

    task = TaskRecord(
        id="task-resume-1",
        project_id=proj.id,
        title="Resume target task",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        assigned_agent_id="coding-agent",
        dependencies=[],
    )
    cp = ResumeCheckpoint(
        id="cp-resume-1",
        project_id=proj.id,
        task_id="task-resume-1",
        status=CheckpointStatus.ACTIVE,
        completed_actions=["Step 1 finished"],
        pending_actions=["Step 2 next"],
        next_action="Perform step 2",
        blockers=[],
        decision_refs=[],
        artifact_refs=[],
        base_revision="root",
        created_by="coding-agent",
    )
    c1 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=task.id,
                record_type="task",
                after_state=task.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=cp.id,
                record_type="checkpoint",
                after_state=cp.model_dump(mode="json"),
            ),
        ],
        message="Add task and checkpoint",
        author_id="coding-agent",
    )

    cp_fn = server._tool_manager._tools["barsa_get_checkpoint"].fn
    cp_res = cp_fn(project_id=proj.id, task_id="task-resume-1")
    assert cp_res["checkpoint_id"] == "cp-resume-1"
    assert cp_res["next_action"] == "Perform step 2"

    # Test resume package
    resume_fn = server._tool_manager._tools["barsa_resume"].fn
    resume_res = resume_fn(project_id=proj.id, task_id="task-resume-1", max_context_tokens=1000)
    assert resume_res["project_identity"]["project_id"] == proj.id
    assert resume_res["authoritative_revision"] == c1.commit_id
    assert resume_res["current_task"]["raw_id"] == "task-resume-1"
    assert "token_budget_info" in resume_res
    assert resume_res["token_budget_info"]["budget_enforcement"] == "approximate"


def test_mcp_history_and_diff_tools(mcp_test_env: dict) -> None:
    """8. Test barsa_get_history and barsa_get_diff tools."""
    server = mcp_test_env["server"]
    vc: VersionControlEngine = mcp_test_env["vc"]
    proj = mcp_test_env["project"]

    main_b = vc.get_branch(proj.id, "main")
    root_cid = main_b.head_commit_id

    dec = DecisionRecord(
        id="dec-diff-1",
        project_id=proj.id,
        title="Diff Decision",
        decision="Adopt Diff",
        rationale="Testing diff",
        status=DecisionStatus.APPROVED,
        created_by="arch-agent",
    )
    c2 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=dec.id,
                record_type="decision",
                after_state=dec.model_dump(mode="json"),
            )
        ],
        message="Add decision",
        author_id="arch-agent",
    )

    hist_fn = server._tool_manager._tools["barsa_get_history"].fn
    hist_res = hist_fn(project_id=proj.id, branch="main")
    assert hist_res["total_returned"] >= 2
    assert hist_res["commits"][0]["commit_id"] == c2.commit_id

    diff_fn = server._tool_manager._tools["barsa_get_diff"].fn
    diff_res = diff_fn(project_id=proj.id, from_commit=root_cid, to_commit=c2.commit_id)
    assert len(diff_res["diff"]["added_records"]) == 1
    assert diff_res["diff"]["added_records"][0] == "dec-diff-1"
    assert len(diff_res["diff"]["changes"]) == 1
    assert diff_res["diff"]["changes"][0]["record_id"] == "dec-diff-1"


def test_mcp_propose_changes_and_main_protection(mcp_test_env: dict) -> None:
    """9. Test barsa_propose_changes validates BMS, creates branch, and rejects main."""
    server = mcp_test_env["server"]
    vc: VersionControlEngine = mcp_test_env["vc"]
    proj = mcp_test_env["project"]
    main_b = vc.get_branch(proj.id, "main")

    propose_fn = server._tool_manager._tools["barsa_propose_changes"].fn

    task_payload = TaskRecord(
        id="task-prop-1",
        project_id=proj.id,
        title="Proposed Task",
        status=TaskStatus.TODO,
        priority=TaskPriority.LOW,
        dependencies=[],
    ).model_dump(mode="json")

    # 1. Proposing to main must be rejected
    with pytest.raises(Exception) as exc_info:
        propose_fn(
            project_id=proj.id,
            branch="main",
            base_commit=main_b.head_commit_id,
            changes=[
                {"operation": "create", "record_id": "task-prop-1", "record_type": "task", "after_state": task_payload}
            ],
            message="Direct proposal to main",
        )
    assert "protected 'main' branch" in str(exc_info.value)

    # 2. Proposing to feature branch succeeds
    prop_res = propose_fn(
        project_id=proj.id,
        branch="feature/proposal-task",
        base_commit=main_b.head_commit_id,
        changes=[
            {"operation": "create", "record_id": "task-prop-1", "record_type": "task", "after_state": task_payload}
        ],
        message="Proposal on feature branch",
    )
    assert prop_res["status"] == "PROPOSED"
    assert prop_res["branch"] == "feature/proposal-task"


def test_mcp_commit_and_optimistic_concurrency_conflict(mcp_test_env: dict) -> None:
    """10. Test barsa_commit with optimistic concurrency check."""
    server = mcp_test_env["server"]
    vc: VersionControlEngine = mcp_test_env["vc"]
    proj = mcp_test_env["project"]
    main_b = vc.get_branch(proj.id, "main")

    commit_fn = server._tool_manager._tools["barsa_commit"].fn

    task_payload = TaskRecord(
        id="task-commit-1",
        project_id=proj.id,
        title="Committed Task",
        status=TaskStatus.TODO,
        priority=TaskPriority.LOW,
        dependencies=[],
    ).model_dump(mode="json")

    # 1. Successful commit with matching expected_head
    c_res = commit_fn(
        project_id=proj.id,
        branch="main",
        expected_head=main_b.head_commit_id,
        changes=[
            {"operation": "create", "record_id": "task-commit-1", "record_type": "task", "after_state": task_payload}
        ],
        message="Commit via MCP test",
    )
    assert c_res["status"] == "COMMITTED"
    assert len(c_res["commit_id"]) > 0

    # 2. Stale expected_head produces conflict error
    with pytest.raises(ToolError) as exc_info:
        commit_fn(
            project_id=proj.id,
            branch="main",
            expected_head=main_b.head_commit_id,  # Old head!
            changes=[
                {
                    "operation": "create",
                    "record_id": "task-commit-2",
                    "record_type": "task",
                    "after_state": task_payload,
                }
            ],
            message="Stale commit attempt",
        )
    assert "HEAD has moved" in str(exc_info.value) or "STALE_REVISION" in str(exc_info.value)


def test_mcp_graph_context_and_conflicts_tools(mcp_test_env: dict) -> None:
    """11. Test barsa_list_conflicts and barsa_get_graph_context."""
    server = mcp_test_env["server"]
    proj = mcp_test_env["project"]

    conflicts_fn = server._tool_manager._tools["barsa_list_conflicts"].fn
    conflicts_res = conflicts_fn(project_id=proj.id)
    assert "divergent_branches" in conflicts_res

    graph_fn = server._tool_manager._tools["barsa_get_graph_context"].fn
    graph_res = graph_fn(project_id=proj.id)
    assert "freshness" in graph_res


@pytest.mark.asyncio
async def test_mcp_protocol_client_session_integration(mcp_test_env: dict) -> None:
    """12. Real end-to-end integration test with MCP ClientSession."""
    server = mcp_test_env["server"]
    proj = mcp_test_env["project"]

    async with create_client_server_memory_streams() as (c_stream, s_stream), anyio.create_task_group() as tg:
        tg.start_soon(
            server._lowlevel_server.run,
            s_stream[0],
            s_stream[1],
            server._lowlevel_server.create_initialization_options(),
        )
        async with ClientSession(c_stream[0], c_stream[1]) as client:
            # 1. Initialize MCP protocol
            init_res = await client.initialize()
            assert init_res.server_info.name == "barsa-mcp-server"

            # 2. Discover Tools
            tools_res = await client.list_tools()
            tool_names = [t.name for t in tools_res.tools]
            assert "barsa_list_projects" in tool_names
            assert "barsa_resume" in tool_names
            assert "barsa_commit" in tool_names

            # 3. Discover Resources
            res_list = await client.list_resources()
            res_uris = [str(r.uri) for r in res_list.resources]
            assert "barsa://system/info" in res_uris
            assert "barsa://bms/schema/version" in res_uris

            # Read resource
            sys_res = await client.read_resource("barsa://system/info")
            sys_data = json.loads(sys_res.contents[0].text)
            assert sys_data["application"] == "BARSA-MCP-Test"

            # 4. Discover Prompts
            prompts_res = await client.list_prompts()
            prompt_names = [p.name for p in prompts_res.prompts]
            assert "barsa_resume_project" in prompt_names

            # Get prompt
            p_out = await client.get_prompt("barsa_resume_project", {"project_id": proj.id})
            assert proj.id in p_out.messages[0].content.text

            # 5. Call Tool: barsa_get_project
            call_res = await client.call_tool("barsa_get_project", {"project_id": proj.id})
            assert not call_res.is_error
            proj_out = json.loads(call_res.content[0].text)
            assert proj_out["project_id"] == proj.id

            # Cancel and finish cleanly
            tg.cancel_scope.cancel()


def test_mcp_cli_help_and_info() -> None:
    """13. Test CLI commands barsa --help and barsa info."""
    res_help = subprocess.run(
        [sys.executable, "-m", "barsa.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_help.returncode == 0
    assert "BARSA" in res_help.stdout or "BARSA" in res_help.stderr

    res_info = subprocess.run(
        [sys.executable, "-m", "barsa.cli", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_info.returncode == 0
    assert "Storage Provider:" in res_info.stdout
