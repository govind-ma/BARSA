"""End-to-end project resume and context continuity evaluation test (Phase 12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from barsa.bms.base import BMS_VERSION
from barsa.bms.records import ArtifactType, Project, Workspace
from barsa.core.config import Settings
from barsa.integrations.adapter import MCPClientAdapter
from barsa.integrations.evaluation import ContextContinuityEvaluator
from barsa.integrations.models import AIProvider, ClientSessionConfig
from barsa.integrations.session import AgentSession
from barsa.mcp.server import create_mcp_server
from barsa.storage.factory import get_storage_provider
from barsa.versioning.engine import VersionControlEngine


@pytest.fixture
def spring_boot_auth_env(tmp_path: Path):
    """Isolated environment seeded with Spring Boot Auth project and real file artifacts."""
    data_dir = tmp_path / "barsa_spring_auth_data"
    settings = Settings(
        app_name="BARSA-Spring-Auth-Test",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=data_dir,
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings.ensure_data_dir()

    storage = get_storage_provider(settings)
    vc = VersionControlEngine(storage)

    ws = storage.create_workspace(Workspace(id="ws-spring-auth", name="Spring Microservices", owner_id="lead-dev"))
    proj = storage.create_project(
        Project(
            id="proj-spring-auth",
            name="Spring Boot JWT Authentication Service",
            workspace_id=ws.id,
            description="Production JWT auth service with token refresh and role validation",
            goals=["Provide stateless JWT authentication", "Support refresh token rotation"],
        )
    )
    vc.initialize_project_main_branch(proj.id)

    server = create_mcp_server(settings)

    yield {
        "settings": settings,
        "storage": storage,
        "vc": vc,
        "project": proj,
        "server": server,
        "tmp_path": tmp_path,
    }
    storage.close()


@pytest.mark.asyncio
async def test_spring_boot_auth_handoff_and_rubric_evaluation(spring_boot_auth_env: dict) -> None:
    """Agent A begins Spring Boot auth service, Agent B continues, scoring 100% on rubric."""
    server = spring_boot_auth_env["server"]
    proj_id = spring_boot_auth_env["project"].id

    # Reference actual files in examples/spring_boot_auth
    base_examples_dir = Path("examples/spring_boot_auth/src/main/java/com/example/auth")
    user_file = base_examples_dir / "model" / "User.java"
    jwt_file = base_examples_dir / "security" / "JwtUtil.java"
    auth_controller_file = base_examples_dir / "controller" / "AuthController.java"

    assert user_file.exists(), f"Expected artifact {user_file} to exist"
    assert jwt_file.exists(), f"Expected artifact {jwt_file} to exist"

    # =========================================================================
    # Phase A: Agent A (Claude 3.5 Sonnet) Session
    # =========================================================================
    config_a = ClientSessionConfig(
        client_id="claude-backend-agent",
        provider=AIProvider.ANTHROPIC,
        model="claude-3-5-sonnet-20241022",
    )
    adapter_a = MCPClientAdapter(config_a, server)
    session_a = AgentSession(config_a, adapter_a)

    await session_a.start(proj_id)

    # Initial records created by Agent A
    records_a = [
        {
            "id": "dec-symmetric-hs512",
            "schema_version": BMS_VERSION,
            "record_type": "decision",
            "project_id": proj_id,
            "title": "Use HMAC-SHA512 for JWT Signing",
            "decision": "Standardize on HS512 with 512-bit secure secret key",
            "rationale": "Selected HS512 over RS256 for symmetric microservice architecture",
            "status": "approved",
            "created_by": config_a.client_id,
        },
        {
            "id": "art-user-model",
            "schema_version": BMS_VERSION,
            "record_type": "artifact",
            "project_id": proj_id,
            "artifact_type": ArtifactType.SOURCE_CODE.value,
            "uri": str(user_file).replace("\\", "/"),
            "media_type": "text/x-java-source",
        },
        {
            "id": "art-jwt-util",
            "schema_version": BMS_VERSION,
            "record_type": "artifact",
            "project_id": proj_id,
            "artifact_type": ArtifactType.SOURCE_CODE.value,
            "uri": str(jwt_file).replace("\\", "/"),
            "media_type": "text/x-java-source",
        },
        {
            "id": "task-login-endpoint",
            "schema_version": BMS_VERSION,
            "record_type": "task",
            "project_id": proj_id,
            "title": "Implement POST /api/auth/login",
            "description": "Authenticate user credentials and issue signed HS512 token",
            "status": "completed",
            "priority": "high",
        },
    ]

    res_a = await session_a.complete_work_and_commit(
        task_id="task-login-endpoint",
        task_title="Implement POST /api/auth/login",
        action_performed="Implemented User model, JwtUtil with HS512, and POST /api/auth/login endpoint",
        new_records=records_a,
        next_task_for_future_agent="Implement JWT token refresh endpoint (/api/auth/refresh)",
        commit_message="feat(auth): implement login endpoint, User model, and JwtUtil",
        test_results={"passed": True, "tests_run": 4},
    )
    assert res_a.new_commit_hash
    await session_a.finish()

    # =========================================================================
    # Phase B: Agent B (GPT-4o) Resumes with Zero Prior Context
    # =========================================================================
    config_b = ClientSessionConfig(
        client_id="gpt4o-continuation-agent",
        provider=AIProvider.OPENAI,
        model="gpt-4o",
    )
    adapter_b = MCPClientAdapter(config_b, server)
    session_b = AgentSession(config_b, adapter_b)

    ctx_b = await session_b.start(proj_id)

    # 1. Inspect understanding strictly from Barsa state
    understanding_b = session_b.inspect_understanding()
    assert understanding_b["next_task"] == "Implement JWT token refresh endpoint (/api/auth/refresh)"
    assert len(understanding_b["completed_actions"]) == 1
    assert "Implemented User model" in understanding_b["completed_actions"][0]

    # 2. Agent B completes continuation work
    records_b = [
        {
            "id": "art-auth-controller",
            "schema_version": BMS_VERSION,
            "record_type": "artifact",
            "project_id": proj_id,
            "artifact_type": ArtifactType.SOURCE_CODE.value,
            "uri": str(auth_controller_file).replace("\\", "/"),
            "media_type": "text/x-java-source",
        },
        {
            "id": "task-refresh-endpoint",
            "schema_version": BMS_VERSION,
            "record_type": "task",
            "project_id": proj_id,
            "title": "Implement POST /api/auth/refresh",
            "description": "Verify refresh token signature and expiry, issue rotated access token",
            "status": "completed",
            "priority": "high",
        },
    ]

    res_b = await session_b.complete_work_and_commit(
        task_id="task-refresh-endpoint",
        task_title="Implement POST /api/auth/refresh",
        action_performed="Implemented /api/auth/refresh endpoint in AuthController with token rotation",
        new_records=records_b,
        next_task_for_future_agent="Implement role-based authorization filter",
        commit_message="feat(auth): add /api/auth/refresh endpoint with token rotation",
        test_results={"passed": True, "tests_run": 6},
    )
    await session_b.finish()

    # =========================================================================
    # Phase C: Rubric Evaluation
    # =========================================================================
    eval_result = ContextContinuityEvaluator.evaluate(
        context=ctx_b,
        continuation_result=res_b,
        expected_goal_substr="Spring Boot JWT Authentication",
        expected_next_task="Implement JWT token refresh endpoint (/api/auth/refresh)",
        expected_completed_count=1,
    )

    # Assert 100% score on all evaluation dimensions
    assert eval_result.goal_identification, f"Goal identification failed: {eval_result.notes}"
    assert eval_result.architecture_identification, f"Architecture identification failed: {eval_result.notes}"
    assert eval_result.completed_work_identification, f"Completed work failed: {eval_result.notes}"
    assert eval_result.next_task_identification, f"Next task failed: {eval_result.notes}"
    assert eval_result.artifact_verification, f"Artifact verification failed: {eval_result.notes}"
    assert eval_result.no_incorrect_assumptions, f"Bad assumptions: {eval_result.notes}"
    assert eval_result.task_continuation_success, f"Task continuation failed: {eval_result.notes}"
    assert eval_result.score_percentage == 100.0, (
        f"Score was {eval_result.score_percentage}%, notes: {eval_result.notes}"
    )


def test_rubric_detects_bad_continuation_and_incomplete_goals() -> None:
    """Verify ContextContinuityEvaluator accurately flags missing requirements and failed tests."""
    from barsa.integrations.models import ClientHandoffContext, TaskContinuationResult

    mock_ctx = ClientHandoffContext(
        project_id="proj-other",
        project_name="Random Unrelated Project",
        latest_checkpoint=None,
        next_task="Something completely different",
        completed_actions=[],
        pending_actions=[],
        blockers=[],
        recent_decisions=[],
        relevant_artifacts=[],
        token_budget=4000,
        total_tokens=150,
        rendered_context="Some plain text without extra details",
    )

    failed_result = TaskContinuationResult(
        agent_id="test-agent",
        provider="openai",
        model="gpt-4o",
        starting_checkpoint_id=None,
        task_id="t-fail",
        task_title="Failed task",
        action_performed="Attempted task but tests failed",
        test_results={"passed": False, "error": "AssertionError"},
        new_commit_hash="c0ffee",
        new_checkpoint_id="chk-fail",
        execution_time_seconds=1.2,
    )

    rubric = ContextContinuityEvaluator.evaluate(
        context=mock_ctx,
        continuation_result=failed_result,
        expected_goal_substr="Spring Boot JWT",
        expected_next_task="Implement JWT token refresh",
        expected_completed_count=1,
    )

    assert not rubric.goal_identification
    assert not rubric.architecture_identification
    assert not rubric.completed_work_identification
    assert not rubric.next_task_identification
    assert not rubric.artifact_verification
    assert not rubric.task_continuation_success
    assert rubric.score_percentage < 30.0
    assert len(rubric.notes) >= 4
