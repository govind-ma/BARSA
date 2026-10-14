"""Comprehensive test suite for Phase 9 Multi-Agent Coordination Engine.

Covers all 27 requirements specified in Section 20:
1. Agent registration.
2. Duplicate registration.
3. Capability validation.
4. Verified versus claimed capabilities.
5. Agent availability.
6. Task dependency checking.
7. Capability-based matching.
8. Workload limits.
9. Atomic task claiming.
10. Concurrent task claims.
11. Lease expiration.
12. Heartbeat renewal.
13. Expired-worker result rejection.
14. Safe task reassignment.
15. Task cancellation.
16. Retry limits.
17. Coordinator restart recovery.
18. Agent comments.
19. Issue creation.
20. Help requests.
21. Cross-project authorization.
22. Task result submission.
23. Review requirements.
24. Rejected contribution handling.
25. Version-control integration.
26. MCP tool behavior.
27. Existing Phase 1–8 regression tests.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from barsa.api.deps import get_coordinator_engine
from barsa.bms.records import (
    DecisionRecord,
    DecisionStatus,
    Project,
    ProjectStatus,
    Workspace,
)
from barsa.coordination.engine import CoordinatorEngine
from barsa.coordination.matching import CapabilityMatcher
from barsa.coordination.models import (
    AgentRegistration,
    AgentState,
    CoordinationTask,
    CoordinationTaskStatus,
    HelpRequestStatus,
    IssueStatus,
    MessageType,
    VerificationLevel,
)
from barsa.core.exceptions import ConflictError, ValidationError
from barsa.main import create_app
from barsa.mcp.tools import (
    claim_task_tool,
    get_assignment_tool,
    get_available_tasks_tool,
    get_collaboration_messages_tool,
    register_agent_tool,
    report_issue_tool,
    request_help_tool,
    submit_task_result_tool,
    update_task_progress_tool,
)
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


@pytest.fixture
def coord_test_env(tmp_path: Path):
    """Fixture initializing temporary storage, version control, and CoordinatorEngine."""
    db_path = tmp_path / "test_coordination.db"
    artifacts_dir = tmp_path / "artifacts"
    storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
    storage.initialize()

    vc = VersionControlEngine(storage)
    engine = CoordinatorEngine(storage=storage, vc=vc)

    ws = Workspace(id="ws-coord", name="Coordination Workspace", owner_id="test-runner")
    storage.create_workspace(ws)

    proj = Project(
        id="proj-coord",
        workspace_id=ws.id,
        name="Coordination Project",
        description="Test project for multi-agent coordination",
        status=ProjectStatus.ACTIVE,
    )
    storage.create_project(proj)
    vc.initialize_project_main_branch(proj.id)

    return {
        "storage": storage,
        "vc": vc,
        "engine": engine,
        "project": proj,
    }


# =========================================================================
# 1. Agent Registration
# =========================================================================


def test_agent_registration(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    reg = AgentRegistration(
        agent_id="agent-research",
        display_name="Research Specialist",
        provider="anthropic",
        model="claude-3-5-sonnet",
        claimed_capabilities=["research", "technical-analysis"],
        verified_capabilities=["research"],
        supported_tools=["web-search", "bms-docs"],
        allowed_projects=["proj-coord"],
        maximum_concurrent_tasks=2,
    )
    profile = engine.register_agent(reg)
    assert profile.agent_id == "agent-research"
    assert profile.display_name == "Research Specialist"
    assert profile.availability_status == AgentState.AVAILABLE
    assert profile.current_workload == 0
    assert "research" in profile.verified_capabilities


# =========================================================================
# 2. Duplicate Registration
# =========================================================================


def test_duplicate_registration(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    reg1 = AgentRegistration(
        agent_id="agent-duplicate",
        display_name="Initial Name",
        provider="local",
        claimed_capabilities=["coding"],
    )
    engine.register_agent(reg1)

    reg2 = AgentRegistration(
        agent_id="agent-duplicate",
        display_name="Updated Display Name",
        provider="local",
        claimed_capabilities=["coding", "debugging"],
    )
    updated = engine.register_agent(reg2)
    assert updated.display_name == "Updated Display Name"
    assert "debugging" in updated.claimed_capabilities
    assert updated.current_workload == 0


# =========================================================================
# 3. Capability Validation
# =========================================================================


def test_capability_validation(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(
        CoordinationTask(
            task_id="task-cap-val",
            project_id=proj_id,
            title="Specialized Task",
            required_capabilities=["quantum-computing"],
        )
    )
    engine.register_agent(
        AgentRegistration(
            agent_id="agent-general",
            display_name="General Agent",
            provider="local",
            claimed_capabilities=["python"],
        )
    )

    with pytest.raises(ValidationError, match="lacks required capabilities"):
        engine.claim_task(task.task_id, "agent-general")


# =========================================================================
# 4. Verified vs Claimed Capabilities
# =========================================================================


def test_verified_vs_claimed_capabilities(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    # Task requires VERIFIED capability level
    task = engine.create_task(
        CoordinationTask(
            task_id="task-strict-verify",
            project_id=proj_id,
            title="Kernel Driver Audit",
            required_capabilities=["security-audit"],
            min_verified_level=VerificationLevel.VERIFIED,
        )
    )

    # Agent only CLAIMS security-audit but is NOT verified
    engine.register_agent(
        AgentRegistration(
            agent_id="agent-unverified",
            display_name="Unverified Security Bot",
            provider="local",
            claimed_capabilities=["security-audit"],
            verified_capabilities=[],
        )
    )

    with pytest.raises(ValidationError, match="lacks verified capabilities"):
        engine.claim_task(task.task_id, "agent-unverified")

    # Agent with VERIFIED capability succeeds
    engine.register_agent(
        AgentRegistration(
            agent_id="agent-certified",
            display_name="Certified Auditor",
            provider="local",
            claimed_capabilities=["security-audit"],
            verified_capabilities=["security-audit"],
        )
    )
    resp = engine.claim_task(task.task_id, "agent-certified")
    assert resp.assigned_agent_id == "agent-certified"


# =========================================================================
# 5. Agent Availability
# =========================================================================


def test_agent_availability(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    engine.register_agent(
        AgentRegistration(
            agent_id="agent-offline",
            display_name="Offline Agent",
            provider="local",
            claimed_capabilities=["python"],
        )
    )
    engine.update_agent_status("agent-offline", AgentState.OFFLINE)

    task = engine.create_task(
        CoordinationTask(
            task_id="task-avail",
            project_id=proj_id,
            title="Availability Task",
            required_capabilities=["python"],
        )
    )

    with pytest.raises(ValidationError, match="is offline"):
        engine.claim_task(task.task_id, "agent-offline")


# =========================================================================
# 6. Task Dependency Checking
# =========================================================================


def test_task_dependency_checking(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    t1 = engine.create_task(
        CoordinationTask(
            task_id="task-dep-1",
            project_id=proj_id,
            title="Step 1 Architecture",
            status=CoordinationTaskStatus.PENDING,
        )
    )
    t2 = engine.create_task(
        CoordinationTask(
            task_id="task-dep-2",
            project_id=proj_id,
            title="Step 2 Implementation",
            dependencies=["task-dep-1"],
            status=CoordinationTaskStatus.PENDING,
        )
    )

    engine.register_agent(
        AgentRegistration(
            agent_id="agent-worker",
            display_name="Worker",
            provider="local",
        )
    )

    # Claiming t2 while t1 is pending must fail
    with pytest.raises(ConflictError, match="blocked on dependency"):
        engine.claim_task(t2.task_id, "agent-worker")

    # Complete t1
    engine.coord_storage.update_task_status(t1.task_id, CoordinationTaskStatus.COMPLETED)

    # Now claiming t2 succeeds
    resp = engine.claim_task(t2.task_id, "agent-worker")
    assert resp.assigned_agent_id == "agent-worker"


# =========================================================================
# 7. Capability-Based Matching
# =========================================================================


def test_capability_based_matching(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    engine.register_agent(
        AgentRegistration(
            agent_id="agent-coder-general",
            display_name="General Coder",
            provider="local",
            claimed_capabilities=["python"],
            supported_tools=["pytest"],
        )
    )
    engine.register_agent(
        AgentRegistration(
            agent_id="agent-coder-expert",
            display_name="Expert Verified Coder",
            provider="local",
            claimed_capabilities=["python"],
            verified_capabilities=["python"],
            supported_tools=["pytest"],
        )
    )

    task = engine.create_task(
        CoordinationTask(
            task_id="task-match",
            project_id=proj_id,
            title="FastAPI Implementation",
            required_capabilities=["python"],
            required_tools=["pytest"],
            status=CoordinationTaskStatus.READY,
        )
    )

    agents = engine.list_agents(project_id=proj_id, status=AgentState.AVAILABLE)
    decision = CapabilityMatcher.match_task_to_agents(task, agents)

    # Expert verified coder should rank higher due to verified capability weight
    assert decision.assigned_agent_id == "agent-coder-expert"
    assert any("verified formally" in r or "verified" in r.lower() for r in decision.reasons)


# =========================================================================
# 8. Workload Limits
# =========================================================================


def test_workload_limits(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    engine.register_agent(
        AgentRegistration(
            agent_id="agent-single-slot",
            display_name="Single Task Worker",
            provider="local",
            maximum_concurrent_tasks=1,
            claimed_capabilities=["python"],
        )
    )

    t1 = engine.create_task(CoordinationTask(task_id="t-slot-1", project_id=proj_id, title="Task 1"))
    t2 = engine.create_task(CoordinationTask(task_id="t-slot-2", project_id=proj_id, title="Task 2"))

    # Claim first slot
    engine.claim_task(t1.task_id, "agent-single-slot")

    # Claiming second slot exceeds maximum workload
    with pytest.raises(ConflictError, match="reached maximum concurrent workload"):
        engine.claim_task(t2.task_id, "agent-single-slot")


# =========================================================================
# 9. Atomic Task Claiming
# =========================================================================


def test_atomic_task_claiming(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-claim", project_id=proj_id, title="Atomic Claim Task"))
    engine.register_agent(AgentRegistration(agent_id="a-claim", display_name="Claimer", provider="local"))

    resp = engine.claim_task(task.task_id, "a-claim", lease_duration_seconds=30)
    assert resp.status == CoordinationTaskStatus.CLAIMED
    assert resp.lease_token.startswith("lease-")
    assert resp.lease_expires_at > datetime.now(UTC)


# =========================================================================
# 10. Concurrent Task Claims
# =========================================================================


def test_concurrent_task_claims(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-race", project_id=proj_id, title="Race Task"))
    engine.register_agent(AgentRegistration(agent_id="agent-1", display_name="A1", provider="local"))
    engine.register_agent(AgentRegistration(agent_id="agent-2", display_name="A2", provider="local"))

    # First agent claims
    resp1 = engine.claim_task(task.task_id, "agent-1")
    assert resp1.assigned_agent_id == "agent-1"

    # Second agent attempts to claim the same task
    with pytest.raises(ConflictError, match="cannot be claimed; current status is 'claimed'"):
        engine.claim_task(task.task_id, "agent-2")


# =========================================================================
# 11. Lease Expiration
# =========================================================================


def test_lease_expiration(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(
        CoordinationTask(
            task_id="t-expire",
            project_id=proj_id,
            title="Expire Task",
            max_attempts=3,
        )
    )
    engine.register_agent(AgentRegistration(agent_id="a-expire", display_name="Lease Worker", provider="local"))

    # Claim with short lease
    resp = engine.claim_task(task.task_id, "a-expire", lease_duration_seconds=10)
    assert resp.lease_token is not None

    # Sweep in the future
    future_time = datetime.now(UTC) + timedelta(seconds=20)
    reaped = engine.reclaim_expired_leases(now=future_time)

    assert len(reaped) == 1
    reaped_task, action = reaped[0]
    assert reaped_task.task_id == task.task_id
    assert action == "reassigned"
    assert reaped_task.status == CoordinationTaskStatus.READY
    assert reaped_task.assigned_agent_id is None
    assert reaped_task.lease_token is None


# =========================================================================
# 12. Heartbeat Renewal
# =========================================================================


def test_heartbeat_renewal(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-hb", project_id=proj_id, title="Heartbeat Task"))
    engine.register_agent(AgentRegistration(agent_id="a-hb", display_name="HB Worker", provider="local"))

    claim = engine.claim_task(task.task_id, "a-hb", lease_duration_seconds=10)
    old_expiry = claim.lease_expires_at

    # Renew lease via heartbeat
    renewed = engine.heartbeat_task(task.task_id, "a-hb", claim.lease_token, lease_duration_seconds=60)
    assert renewed.lease_expires_at is not None
    assert renewed.lease_expires_at > old_expiry


# =========================================================================
# 13. Expired Worker Result Rejection
# =========================================================================


def test_expired_worker_result_rejection(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-late", project_id=proj_id, title="Late Worker Task"))
    engine.register_agent(AgentRegistration(agent_id="a-late", display_name="Late Worker", provider="local"))

    claim = engine.claim_task(task.task_id, "a-late", lease_duration_seconds=5)
    engine.start_task(task.task_id, "a-late", claim.lease_token)

    # Reclaim expired lease
    future_time = datetime.now(UTC) + timedelta(seconds=15)
    engine.reclaim_expired_leases(now=future_time)

    # Worker A returns late and tries to submit using old lease token
    with pytest.raises(ConflictError, match="submission rejected"):
        engine.submit_task_result(
            task_id=task.task_id,
            agent_id="a-late",
            lease_token=claim.lease_token,
            result={"status": "late_work"},
        )


# =========================================================================
# 14. Safe Task Reassignment
# =========================================================================


def test_safe_task_reassignment(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-reassign", project_id=proj_id, title="Reassign Task"))
    engine.register_agent(AgentRegistration(agent_id="a-first", display_name="Worker 1", provider="local"))
    engine.register_agent(AgentRegistration(agent_id="a-second", display_name="Worker 2", provider="local"))

    # Worker 1 claims but expires
    engine.claim_task(task.task_id, "a-first", lease_duration_seconds=5)
    engine.reclaim_expired_leases(now=datetime.now(UTC) + timedelta(seconds=10))

    # Worker 2 successfully claims reassigned task
    resp2 = engine.claim_task(task.task_id, "a-second", lease_duration_seconds=60)
    assert resp2.assigned_agent_id == "a-second"
    assert resp2.status == CoordinationTaskStatus.CLAIMED


# =========================================================================
# 15. Task Cancellation
# =========================================================================


def test_task_cancellation(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-cancel", project_id=proj_id, title="Cancel Task"))
    engine.coord_storage.update_task_status(task.task_id, CoordinationTaskStatus.CANCELLED)

    engine.register_agent(AgentRegistration(agent_id="a-cancel", display_name="Worker", provider="local"))
    with pytest.raises(ConflictError, match="cannot be claimed; current status is 'cancelled'"):
        engine.claim_task(task.task_id, "a-cancel")


# =========================================================================
# 16. Retry Limits
# =========================================================================


def test_retry_limits(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(
        CoordinationTask(
            task_id="t-retry-limit",
            project_id=proj_id,
            title="Max Retries Task",
            max_attempts=2,
        )
    )
    engine.register_agent(AgentRegistration(agent_id="a-flaky", display_name="Flaky Worker", provider="local"))

    # Attempt 1: claim & expire
    engine.claim_task(task.task_id, "a-flaky", lease_duration_seconds=5)
    engine.reclaim_expired_leases(now=datetime.now(UTC) + timedelta(seconds=10))

    # Attempt 2: claim & expire
    engine.claim_task(task.task_id, "a-flaky", lease_duration_seconds=5)
    reaped = engine.reclaim_expired_leases(now=datetime.now(UTC) + timedelta(seconds=20))

    assert len(reaped) == 1
    final_task, action = reaped[0]
    assert action == "failed"
    assert final_task.status == CoordinationTaskStatus.FAILED
    assert "maximum attempts (2) exceeded" in final_task.failure_reason


# =========================================================================
# 17. Coordinator Restart Recovery
# =========================================================================


def test_coordinator_restart_recovery(coord_test_env):
    storage = coord_test_env["storage"]
    engine1: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    engine1.register_agent(
        AgentRegistration(
            agent_id="a-survivor",
            display_name="Survivor Agent",
            provider="local",
            claimed_capabilities=["resilience"],
        )
    )
    t = engine1.create_task(CoordinationTask(task_id="t-survivor", project_id=proj_id, title="Surviving Task"))
    claim = engine1.claim_task(t.task_id, "a-survivor", lease_duration_seconds=300)

    # Simulate coordinator crash & restart with clean memory
    engine2 = CoordinatorEngine(storage=storage)

    recovered_agent = engine2.get_agent("a-survivor")
    assert recovered_agent.agent_id == "a-survivor"
    assert recovered_agent.current_workload == 1

    recovered_task = engine2.get_task(t.task_id)
    assert recovered_task.assigned_agent_id == "a-survivor"
    assert recovered_task.lease_token == claim.lease_token
    assert recovered_task.status == CoordinationTaskStatus.CLAIMED


# =========================================================================
# 18. Agent Comments
# =========================================================================


def test_agent_comments(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    t = engine.create_task(CoordinationTask(task_id="t-comment", project_id=proj_id, title="Commented Task"))
    engine.register_agent(AgentRegistration(agent_id="a-commenter", display_name="Commenter", provider="local"))

    msg = engine.add_comment(
        project_id=proj_id,
        task_id=t.task_id,
        author_agent_id="a-commenter",
        content="Investigated the endpoint latency: looks like slow DNS resolution.",
        message_type=MessageType.OBSERVATION,
    )
    assert msg.message_id.startswith("msg-")
    assert msg.content == "Investigated the endpoint latency: looks like slow DNS resolution."

    comments = engine.list_comments(proj_id, t.task_id)
    assert len(comments) == 1
    assert comments[0].author_agent_id == "a-commenter"


# =========================================================================
# 19. Issue Creation
# =========================================================================


def test_issue_creation(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    t = engine.create_task(CoordinationTask(task_id="t-issue", project_id=proj_id, title="Task with Issue"))
    engine.register_agent(AgentRegistration(agent_id="a-tester", display_name="Tester", provider="local"))

    issue = engine.report_issue(
        project_id=proj_id,
        task_id=t.task_id,
        author_agent_id="a-tester",
        title="JWT Token Signature Invalid",
        description="Signature algorithm HS256 expected RS256 public key",
        evidence={"expected": "RS256", "actual": "HS256"},
        required_capabilities=["api-security"],
    )
    assert issue.issue_id.startswith("issue-")
    assert issue.status == IssueStatus.OPEN
    assert "api-security" in issue.required_capabilities

    issues = engine.list_issues(proj_id, t.task_id)
    assert len(issues) == 1
    assert issues[0].title == "JWT Token Signature Invalid"


# =========================================================================
# 20. Help Requests
# =========================================================================


def test_help_requests(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    engine.register_agent(
        AgentRegistration(
            agent_id="a-requester",
            display_name="Coding Worker",
            provider="local",
            claimed_capabilities=["java"],
        )
    )
    engine.register_agent(
        AgentRegistration(
            agent_id="a-helper",
            display_name="Security Specialist",
            provider="local",
            claimed_capabilities=["api-security"],
            verified_capabilities=["api-security"],
        )
    )

    t = engine.create_task(CoordinationTask(task_id="t-help", project_id=proj_id, title="Needs Help Task"))
    req = engine.request_help(
        project_id=proj_id,
        task_id=t.task_id,
        requester_agent_id="a-requester",
        required_capabilities=["api-security"],
    )
    assert req.status == HelpRequestStatus.OPEN

    # Match helper
    decision = engine.match_helper_for_request(req.request_id)
    assert decision.assigned_agent_id == "a-helper"

    # Helper claims
    claimed = engine.claim_help_request(req.request_id, "a-helper")
    assert claimed.status == HelpRequestStatus.CLAIMED
    assert claimed.assigned_helper_id == "a-helper"

    # Resolving issue
    issue = engine.report_issue(proj_id, t.task_id, "a-requester", "Need security config", "Need RS256")
    resolved = engine.resolve_issue(
        issue_id=issue.issue_id,
        resolver_agent_id="a-helper",
        proposal={"solution": "Configured SecurityFilterChain with NimbusJwtDecoder"},
    )
    assert resolved.status == IssueStatus.RESOLVED
    assert resolved.resolver_agent_id == "a-helper"


# =========================================================================
# 21. Cross-Project Authorization
# =========================================================================


def test_cross_project_authorization(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    storage = coord_test_env["storage"]
    ws_id = coord_test_env["project"].workspace_id

    # Create private second project
    proj_b = Project(
        id="proj-private-b",
        workspace_id=ws_id,
        name="Private Project B",
        status=ProjectStatus.ACTIVE,
    )
    storage.create_project(proj_b)

    task_b = engine.create_task(
        CoordinationTask(
            task_id="t-private",
            project_id=proj_b.id,
            title="Private Task",
        )
    )

    # Agent only authorized for proj-coord
    engine.register_agent(
        AgentRegistration(
            agent_id="agent-restricted",
            display_name="Restricted Agent",
            provider="local",
            allowed_projects=["proj-coord"],
        )
    )

    with pytest.raises(ValidationError, match="not authorized for project"):
        engine.claim_task(task_b.task_id, "agent-restricted")


# =========================================================================
# 22. Task Result Submission
# =========================================================================


def test_task_result_submission(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-submit", project_id=proj_id, title="Submittable Task"))
    engine.register_agent(AgentRegistration(agent_id="a-submit", display_name="Submitter", provider="local"))

    claim = engine.claim_task(task.task_id, "a-submit")
    engine.start_task(task.task_id, "a-submit", claim.lease_token)

    submitted = engine.submit_task_result(
        task_id=task.task_id,
        agent_id="a-submit",
        lease_token=claim.lease_token,
        result={"output": "Authentication endpoints implemented and verified"},
        requires_review=False,
    )
    assert submitted.status == CoordinationTaskStatus.COMPLETED
    assert submitted.result["output"] == "Authentication endpoints implemented and verified"


# =========================================================================
# 23. Review Requirements & Self-Approval Prevention
# =========================================================================


def test_review_requirements_and_self_approval_prevention(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    vc: VersionControlEngine = coord_test_env["vc"]
    proj_id = coord_test_env["project"].id

    task = engine.create_task(CoordinationTask(task_id="t-review", project_id=proj_id, title="Protected Task"))
    engine.register_agent(AgentRegistration(agent_id="a-coder", display_name="Coder", provider="local"))
    engine.register_agent(AgentRegistration(agent_id="a-lead", display_name="Lead Reviewer", provider="local"))

    claim = engine.claim_task(task.task_id, "a-coder")
    engine.start_task(task.task_id, "a-coder", claim.lease_token)

    # Submitting with review requirement transitions to UNDER_REVIEW
    submitted = engine.submit_task_result(
        task_id=task.task_id,
        agent_id="a-coder",
        lease_token=claim.lease_token,
        result={"summary": "JWT configuration"},
        requires_review=True,
    )
    assert submitted.status == CoordinationTaskStatus.UNDER_REVIEW

    # Propose changes on feature branch
    vc.create_branch(proj_id, "feat-jwt")
    dec = DecisionRecord(
        id="dec-test-jwt",
        project_id=proj_id,
        created_by="a-coder",
        title="JWT Decision",
        decision="Use JJWT",
        rationale="Standard",
        status=DecisionStatus.APPROVED,
    )
    vc.create_commit(
        project_id=proj_id,
        branch_name="feat-jwt",
        author_id="a-coder",
        message="feat: JWT config",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=dec.id,
                record_type="decision",
                after_state=dec.model_dump(mode="json"),
            )
        ],
    )
    proposal = vc.create_merge_proposal(
        project_id=proj_id,
        title="Merge JWT",
        source_branch="feat-jwt",
        target_branch="main",
        author_id="a-coder",
    )

    # Self-approval MUST be prohibited!
    with pytest.raises(ValidationError, match="Self-approval prohibited"):
        engine.submit_review_decision(
            proposal_id=proposal.proposal_id,
            project_id=proj_id,
            reviewer_agent_id="a-coder",
            status="approved",
        )

    # Lead reviewer approves -> completes review and completes task
    rev = engine.submit_review_decision(
        proposal_id=proposal.proposal_id,
        project_id=proj_id,
        reviewer_agent_id="a-lead",
        status="approved",
        summary="Architecture looks solid.",
        associated_task_id=task.task_id,
    )
    assert rev["status"] == "approved"
    completed_task = engine.get_task(task.task_id)
    assert completed_task.status == CoordinationTaskStatus.COMPLETED


# =========================================================================
# 24. Rejected Contribution Handling
# =========================================================================


def test_rejected_contribution_handling(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    vc: VersionControlEngine = coord_test_env["vc"]
    proj_id = coord_test_env["project"].id

    vc.create_branch(proj_id, "feat-reject")
    proposal = vc.create_merge_proposal(
        project_id=proj_id,
        title="Flawed Architecture",
        source_branch="feat-reject",
        target_branch="main",
        author_id="a-junior",
    )

    review = engine.submit_review_decision(
        proposal_id=proposal.proposal_id,
        project_id=proj_id,
        reviewer_agent_id="a-senior",
        status="changes_requested",
        summary="Missing automated tests and security headers.",
    )
    assert review["status"] == "changes_requested"
    assert review["summary"] == "Missing automated tests and security headers."


# =========================================================================
# 25. Version Control Integration
# =========================================================================


def test_version_control_integration(coord_test_env):
    engine: CoordinatorEngine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    dec = DecisionRecord(
        id="dec-arch-1",
        project_id=proj_id,
        created_by="agent-architect",
        title="PostgreSQL Adoption",
        decision="Use PostgreSQL 16",
        rationale="Relational consistency and ACID transactions",
        status=DecisionStatus.APPROVED,
    )

    commit = engine.commit_agent_contribution(
        project_id=proj_id,
        author_agent_id="agent-architect",
        message="docs: approve PostgreSQL 16 decision",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=dec.id,
                record_type="decision",
                after_state=dec.model_dump(mode="json"),
            )
        ],
        branch_name="main",
    )
    assert commit.commit_id is not None
    assert commit.author_id == "agent-architect"

    # Verify state in VC engine
    branch = engine.vc.get_branch(proj_id, "main")
    assert branch.head_commit_id == commit.commit_id


# =========================================================================
# 26. MCP Tool Behavior
# =========================================================================


def test_mcp_coordination_tools(coord_test_env):
    storage = coord_test_env["storage"]
    vc = coord_test_env["vc"]
    engine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    # 1. Register agent tool
    reg_res = register_agent_tool(
        storage=storage,
        vc=vc,
        agent_id="mcp-agent-1",
        display_name="MCP Agent",
        provider="anthropic",
        claimed_capabilities=["python", "testing"],
        supported_tools=["pytest"],
    )
    assert reg_res["agent_id"] == "mcp-agent-1"

    # Create task
    engine.create_task(
        CoordinationTask(
            task_id="mcp-task-1",
            project_id=proj_id,
            title="MCP Task",
            required_capabilities=["python"],
        )
    )

    # 2. Get available tasks tool
    avail = get_available_tasks_tool(storage, vc, project_id=proj_id, agent_id="mcp-agent-1")
    assert any(t["task_id"] == "mcp-task-1" for t in avail)

    # 3. Claim task tool
    claim_res = claim_task_tool(storage, vc, task_id="mcp-task-1", agent_id="mcp-agent-1", lease_duration_seconds=60)
    assert claim_res["assigned_agent_id"] == "mcp-agent-1"
    token = claim_res["lease_token"]

    # 4. Start & Update progress tool
    engine.start_task("mcp-task-1", "mcp-agent-1", token)
    prog_res = update_task_progress_tool(
        storage,
        vc,
        task_id="mcp-task-1",
        agent_id="mcp-agent-1",
        lease_token=token,
        message="Running pytest test suite",
        progress_percent=50.0,
    )
    assert prog_res["task_id"] == "mcp-task-1"

    # 5. Report issue tool
    issue_res = report_issue_tool(
        storage,
        vc,
        project_id=proj_id,
        task_id="mcp-task-1",
        author_agent_id="mcp-agent-1",
        title="Pytest missing plugin",
        description="Need pytest-asyncio",
        required_capabilities=["devops"],
    )
    assert issue_res["title"] == "Pytest missing plugin"

    # 6. Request help tool
    help_res = request_help_tool(
        storage,
        vc,
        project_id=proj_id,
        task_id="mcp-task-1",
        requester_agent_id="mcp-agent-1",
        required_capabilities=["devops"],
    )
    assert help_res["request_id"].startswith("help-")

    # 7. Get collaboration messages tool
    msgs = get_collaboration_messages_tool(storage, vc, project_id=proj_id, task_id="mcp-task-1")
    assert len(msgs) >= 1

    # 8. Get assignment tool
    assign = get_assignment_tool(storage, vc, task_id="mcp-task-1")
    assert assign["assigned_agent_id"] == "mcp-agent-1"
    assert assign["lease_token"] == token

    # 9. Submit task result tool
    sub_res = submit_task_result_tool(
        storage,
        vc,
        task_id="mcp-task-1",
        agent_id="mcp-agent-1",
        lease_token=token,
        result={"summary": "All 10 tests passed"},
        requires_review=False,
    )
    assert sub_res["status"] == "completed"


# =========================================================================
# REST API Endpoints Integration Test
# =========================================================================


def test_coordination_rest_api_endpoints(coord_test_env):
    engine = coord_test_env["engine"]
    proj_id = coord_test_env["project"].id

    app = create_app()
    app.dependency_overrides[get_coordinator_engine] = lambda: engine
    client = TestClient(app)

    # 1. Register agent
    resp = client.post(
        "/api/v1/coordination/agents/register",
        json={
            "agent_id": "api-agent-1",
            "display_name": "API Worker",
            "provider": "openai",
            "model": "gpt-4o",
            "claimed_capabilities": ["api-dev"],
            "supported_tools": ["curl"],
        },
    )
    assert resp.status_code == 201
    assert resp.json()["agent_id"] == "api-agent-1"

    # 2. List agents
    resp = client.get("/api/v1/coordination/agents")
    assert resp.status_code == 200
    assert any(a["agent_id"] == "api-agent-1" for a in resp.json())

    # 3. Heartbeat agent
    resp = client.post("/api/v1/coordination/agents/api-agent-1/heartbeat")
    assert resp.status_code == 200

    # 4. Create task
    resp = client.post(
        "/api/v1/coordination/tasks",
        json={
            "task_id": "api-task-1",
            "project_id": proj_id,
            "title": "API Coordinated Task",
            "required_capabilities": ["api-dev"],
            "status": "ready",
        },
    )
    assert resp.status_code == 201

    # 5. List available tasks
    resp = client.get(f"/api/v1/coordination/tasks/available?project_id={proj_id}")
    assert resp.status_code == 200
    assert any(t["task_id"] == "api-task-1" for t in resp.json())

    # 6. Claim task
    resp = client.post(
        "/api/v1/coordination/tasks/api-task-1/claim",
        json={"agent_id": "api-agent-1", "lease_duration_seconds": 60},
    )
    assert resp.status_code == 200
    token = resp.json()["lease_token"]

    # 7. Start task
    resp = client.post(
        "/api/v1/coordination/tasks/api-task-1/start",
        json={"agent_id": "api-agent-1", "lease_token": token},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # 8. Post comment
    resp = client.post(
        "/api/v1/coordination/tasks/api-task-1/comments",
        json={
            "project_id": proj_id,
            "author_agent_id": "api-agent-1",
            "content": "Work in progress",
        },
    )
    assert resp.status_code == 201

    # 9. Get comments
    resp = client.get(f"/api/v1/coordination/tasks/api-task-1/comments?project_id={proj_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 10. Submit task
    resp = client.post(
        "/api/v1/coordination/tasks/api-task-1/submit",
        json={
            "agent_id": "api-agent-1",
            "lease_token": token,
            "result": {"status": "ok"},
            "requires_review": False,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # 11. Coordinator diagnostics
    resp = client.get("/api/v1/coordination/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
