"""BARSA Phase 9 Multi-Agent Coordination Demonstration Scenario.

Demonstrates:
1. Agent A (Research Agent):
   - Claims research task with atomic lease.
   - Researches auth architecture and commits Spring Security 6.2 + JWT decision via VersionControlEngine.
   - Completes task with structured result.
2. Agent B (Coding Agent):
   - Claims implementation task and reads Agent A's committed decision.
   - Encounters RSA key mismatch issue during token validation.
   - Reports issue and raises targeted help request for security testing.
3. Agent C (Testing / Security Agent):
   - Matched by Coordinator based on verified capabilities.
   - Investigates, proposes resolution (JWK Set URI endpoint fix), and resolves issue.
   - Agent B verifies resolution, completes task, and submits for lead review.
4. Fault Tolerance & Lease Expiry:
   - Worker crashes without heartbeating.
   - Sweeper reclaims task safely using monotonic fencing tokens.
   - Replacement worker completes task; late submission by zombie worker is rejected.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from barsa.bms.records import (
    DecisionRecord,
    DecisionStatus,
    Project,
    Workspace,
)
from barsa.coordination.engine import CoordinatorEngine
from barsa.coordination.models import (
    AgentRegistration,
    CoordinationTask,
    Priority,
)
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


def run_coordination_demo() -> None:
    print("=" * 80)
    print("BARSA Phase 9: Multi-Agent Capability-Based Coordination Demonstration")
    print("=" * 80)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "barsa_coord_demo.db"
        artifacts_dir = tmp_path / "artifacts"

        # 0. Initialize System Components
        storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
        storage.initialize()
        vc = VersionControlEngine(storage)
        coordinator = CoordinatorEngine(storage=storage, vc=vc)

        # Create Workspace and Project
        ws = Workspace(id="ws-demo", name="Enterprise Backend Workspace", owner_id="sysadmin")
        storage.create_workspace(ws)
        proj = Project(
            id="proj-auth-service",
            name="OAuth2 Auth Service",
            workspace_id="ws-demo",
            description="Core authentication and authorization microservice",
        )
        storage.create_project(proj)
        vc.initialize_project_main_branch(proj.id, author_id="sysadmin")
        print(f"\n[INIT] Initialized Project: {proj.name} ({proj.id})")

        # 1. Register Agents with Capabilities
        print("\n--- 1. Agent Registration & Discovery ---")
        agent_a = coordinator.register_agent(
            AgentRegistration(
                agent_id="agent-researcher-a",
                display_name="Research Agent A",
                provider="anthropic",
                model_family="claude-3-7-sonnet",
                claimed_capabilities=["research", "technical-analysis", "architecture"],
                verified_capabilities=["research", "technical-analysis"],
                assigned_projects=[proj.id],
                max_concurrent_tasks=2,
            )
        )
        print(f"Registered Agent A: {agent_a.display_name} (Verified: {agent_a.verified_capabilities})")

        agent_b = coordinator.register_agent(
            AgentRegistration(
                agent_id="agent-coder-b",
                display_name="Backend Coder B",
                provider="openai",
                model_family="gpt-4o",
                claimed_capabilities=["java", "spring-boot", "api-development"],
                verified_capabilities=["java", "spring-boot", "api-development"],
                assigned_projects=[proj.id],
                max_concurrent_tasks=2,
            )
        )
        print(f"Registered Agent B: {agent_b.display_name} (Verified: {agent_b.verified_capabilities})")

        agent_c = coordinator.register_agent(
            AgentRegistration(
                agent_id="agent-tester-c",
                display_name="Security Tester C",
                provider="google",
                model_family="gemini-2.5-pro",
                claimed_capabilities=["api-testing", "security-testing", "jwt-analysis"],
                verified_capabilities=["api-testing", "security-testing"],
                assigned_projects=[proj.id],
                max_concurrent_tasks=2,
            )
        )
        print(f"Registered Agent C: {agent_c.display_name} (Verified: {agent_c.verified_capabilities})")

        lead_reviewer = coordinator.register_agent(
            AgentRegistration(
                agent_id="agent-lead-reviewer",
                display_name="Lead Architecture Reviewer",
                provider="local",
                model_family="human-in-the-loop",
                claimed_capabilities=["architecture-review", "security-signoff"],
                verified_capabilities=["architecture-review", "security-signoff"],
                assigned_projects=[proj.id],
            )
        )
        print(f"Registered Reviewer: {lead_reviewer.display_name}")

        # 2. Create Tasks with Dependencies & Capabilities
        print("\n--- 2. Task Creation & Scheduling ---")
        task_research = coordinator.create_task(
            CoordinationTask(
                task_id="task-001-research-auth",
                project_id=proj.id,
                title="Investigate Authentication Architecture",
                description="Evaluate token formats and security filters for Spring Boot 3",
                required_capabilities=["research", "technical-analysis"],
                priority=Priority.HIGH,
                heartbeat_timeout_seconds=60,
            )
        )
        print(f"Created Task 1: '{task_research.title}' (Status: {task_research.status.value})")

        task_impl = coordinator.create_task(
            CoordinationTask(
                task_id="task-002-implement-auth",
                project_id=proj.id,
                title="Implement Spring Security & JWT Filters",
                description="Implement security filter chain and token validation endpoints",
                required_capabilities=["java", "spring-boot"],
                dependencies=[task_research.task_id],
                priority=Priority.MEDIUM,
                heartbeat_timeout_seconds=60,
            )
        )
        print(f"Created Task 2: '{task_impl.title}' (Status: {task_impl.status.value}, Depends on Task 1)")

        # Verify dependency prevents claiming task 2
        avail_for_b = coordinator.list_available_tasks(project_id=proj.id, agent_id=agent_b.agent_id)
        print(f"Available tasks for Agent B before Task 1 completes: {[t.task_id for t in avail_for_b]}")

        # 3. Agent A Claims Task 1 and Commits Decision
        print("\n--- 3. Agent A Execution & Version-Controlled Shared Memory ---")
        claim_a = coordinator.claim_task(task_research.task_id, agent_a.agent_id)
        print(
            f"Agent A claimed Task 1: lease_token={claim_a.lease_token}, expires_at={claim_a.lease_expires_at.isoformat()}"
        )

        coordinator.start_task(task_research.task_id, agent_a.agent_id, claim_a.lease_token)
        coordinator.update_task_progress(
            task_id=task_research.task_id,
            agent_id=agent_a.agent_id,
            lease_token=claim_a.lease_token,
            message="Analyzing Spring Security 6.2 vs Nimbus JOSE",
            progress_percent=50,
        )

        # Agent A records architectural decision and commits it to shared VC memory
        dec = DecisionRecord(
            id="dec-auth-standard",
            project_id=proj.id,
            created_by=agent_a.agent_id,
            title="Adopt Spring Security 6.2 and JJWT for Token Validation",
            decision="Use Spring Security 6.2 Resource Server with JJWT and asymmetric RS256 signatures",
            rationale="Standard enterprise compliance, robust cryptographic validation, and built-in OIDC support",
            status=DecisionStatus.APPROVED,
        )
        commit = coordinator.commit_agent_contribution(
            project_id=proj.id,
            author_agent_id=agent_a.agent_id,
            message="feat: decide on Spring Security 6.2 and JJWT RS256 architecture",
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
        print(f"Agent A committed decision to shared memory: Commit ID {commit.commit_id[:8]} on main")

        # Agent A submits task result
        res_a = coordinator.submit_task_result(
            task_id=task_research.task_id,
            agent_id=agent_a.agent_id,
            lease_token=claim_a.lease_token,
            result={
                "summary": "Completed auth architecture evaluation",
                "recommended_stack": "Spring Security 6.2 + JJWT (RS256)",
                "decision_id": dec.id,
            },
        )
        print(f"Task 1 status after submission: {res_a.status.value}")

        # Check that Task 2 has now automatically unlocked
        task_impl_updated = coordinator.get_task(task_impl.task_id)
        print(f"Task 2 status after Task 1 completion: {task_impl_updated.status.value}")

        # 4. Agent B Claims Task 2, Reads Decision, and Hits Issue
        print("\n--- 4. Agent B Execution, Issue Reporting & Help Request ---")
        claim_b = coordinator.claim_task(task_impl.task_id, agent_b.agent_id)
        coordinator.start_task(task_impl.task_id, agent_b.agent_id, claim_b.lease_token)
        print(f"Agent B claimed Task 2: lease_token={claim_b.lease_token}")

        # Agent B reads the committed decision from VC
        rec_tuple = storage.get_record(proj.id, dec.id)
        assert rec_tuple is not None
        read_dec = rec_tuple[0]
        print(f"Agent B read decision from shared memory: '{read_dec.title}'")

        # Agent B encounters an issue during integration testing
        issue = coordinator.report_issue(
            project_id=proj.id,
            task_id=task_impl.task_id,
            author_agent_id=agent_b.agent_id,
            title="RSA Signature Verification Failed on JwtDecoder",
            description="NimbusJwtDecoder rejects tokens with InvalidKeySpecException: key format not recognised",
            evidence={
                "error_code": "JWT_SIGNATURE_MISMATCH",
                "attempted_key_format": "PKCS#1",
                "expected_key_format": "PKCS#8 / X.509 JWK Set",
            },
            required_capabilities=["api-testing", "security-testing"],
        )
        print(f"Agent B reported Issue '{issue.title}' (Issue ID: {issue.issue_id})")

        help_req = coordinator.request_help(
            project_id=proj.id,
            task_id=task_impl.task_id,
            requester_agent_id=agent_b.agent_id,
            issue_id=issue.issue_id,
            required_capabilities=["security-testing", "api-testing"],
        )
        print(
            f"Agent B requested help: Help Request ID {help_req.request_id} (Requires: {help_req.required_capabilities})"
        )

        # 5. Coordinator Matches Agent C and Resolves Issue
        print("\n--- 5. Capability-Based Helper Matching & Collaboration ---")
        match_decision = coordinator.match_helper_for_request(help_req.request_id)
        print(f"Coordinator matched helper: Agent '{match_decision.assigned_agent_id}' (Score: {match_decision.score})")
        print(f"Match Reasons: {', '.join(match_decision.reasons)}")

        # Agent C claims the help request
        claimed_help = coordinator.claim_help_request(help_req.request_id, agent_c.agent_id)
        print(f"Agent C claimed help request: Status={claimed_help.status.value}")

        # Agent C leaves collaboration comment
        coordinator.add_collaboration_message(
            project_id=proj.id,
            task_id=task_impl.task_id,
            author_agent_id=agent_c.agent_id,
            content="Discovered root cause: auth server exposes JWK Set at /.well-known/jwks.json using standard X.509 JWK format.",
        )

        # Agent C resolves issue
        resolution_patch = {
            "solution": "Configure spring.security.oauth2.resourceserver.jwt.jwk-set-uri",
            "endpoint": "https://auth.internal.corp/.well-known/jwks.json",
            "fixed_format": "JWK Set",
        }
        resolved_issue = coordinator.resolve_issue(
            issue_id=issue.issue_id,
            resolver_agent_id=agent_c.agent_id,
            proposal=resolution_patch,
        )
        print(f"Agent C resolved issue: Status={resolved_issue.status.value}")

        # 6. Agent B Resumes and Submits for Review
        print("\n--- 6. Resuming Task & Protected Review Workflow ---")
        # Agent B heartbeats to keep lease fresh
        renewed_b = coordinator.heartbeat_task(task_impl.task_id, agent_b.agent_id, claim_b.lease_token)
        print(f"Agent B renewed lease: New expires_at={renewed_b.lease_expires_at.isoformat()}")

        # Agent B submits result with requires_review=True
        submitted_b = coordinator.submit_task_result(
            task_id=task_impl.task_id,
            agent_id=agent_b.agent_id,
            lease_token=claim_b.lease_token,
            result={
                "status": "All JWT tests passing",
                "jwk_set_uri_configured": True,
                "coverage": "94.2%",
            },
            requires_review=True,
        )
        print(f"Task 2 status after Agent B submission: {submitted_b.status.value} (Awaiting Peer Review)")

        # Propose changes on feature branch
        vc.create_branch(proj.id, "feat-security-filter")
        vc.create_commit(
            project_id=proj.id,
            branch_name="feat-security-filter",
            author_id=agent_b.agent_id,
            message="feat: complete Spring Security filter and JWK Set integration",
            changes=[],
        )
        proposal = vc.create_merge_proposal(
            project_id=proj.id,
            title="Merge Spring Security 6.2 JWT Filter Implementation",
            source_branch="feat-security-filter",
            target_branch="main",
            author_id=agent_b.agent_id,
        )

        # Verify Agent B cannot approve their own proposal
        print("Checking self-approval prohibition...")
        try:
            coordinator.submit_review_decision(
                proposal_id=proposal.proposal_id,
                project_id=proj.id,
                reviewer_agent_id=agent_b.agent_id,
                status="approved",
            )
            print("ERROR: Self-approval was unexpectedly permitted!")
        except Exception as e:
            print(f"Self-approval correctly blocked: {e}")

        # Lead Reviewer reviews and approves proposal, completing the task
        rev = coordinator.submit_review_decision(
            proposal_id=proposal.proposal_id,
            project_id=proj.id,
            reviewer_agent_id=lead_reviewer.agent_id,
            status="approved",
            summary="Thorough security configuration, verified against enterprise OAuth2 server.",
            associated_task_id=task_impl.task_id,
        )
        assert rev["status"] == "approved"
        task_impl_done = coordinator.get_task(task_impl.task_id)
        print(f"Review approved by {lead_reviewer.agent_id}. Final Task 2 Status: {task_impl_done.status.value}")

        # 7. Fault Tolerance & Stale Worker Rejection
        print("\n--- 7. Worker Crash, Lease Sweeper & Fencing Token Rejection ---")
        task_flakey = coordinator.create_task(
            CoordinationTask(
                task_id="task-003-batch-export",
                project_id=proj.id,
                title="Audit Log Batch Export",
                heartbeat_timeout_seconds=1,  # Short lease for simulation
            )
        )
        zombie_worker = coordinator.register_agent(
            AgentRegistration(agent_id="agent-zombie", display_name="Flakey Worker", provider="local")
        )
        claim_zombie = coordinator.claim_task(task_flakey.task_id, zombie_worker.agent_id, lease_duration_seconds=1)
        coordinator.start_task(task_flakey.task_id, zombie_worker.agent_id, claim_zombie.lease_token)
        print(f"Zombie worker claimed task with lease_token={claim_zombie.lease_token}")

        # Simulate worker hanging / network partition until lease expires
        import datetime

        simulated_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=5)
        reaped = coordinator.reclaim_expired_leases(now=simulated_time)
        print(f"Sweeper detected expired leases: {[t.task_id for t, action in reaped]}")

        # Replacement worker claims task
        replacement_claim = coordinator.claim_task(task_flakey.task_id, agent_b.agent_id)
        print(f"Replacement worker {agent_b.agent_id} claimed task: new lease_token={replacement_claim.lease_token}")

        # Zombie worker wakes up and attempts late submission with old token
        print("Zombie worker attempts late submission with stale lease token...")
        try:
            coordinator.submit_task_result(
                task_id=task_flakey.task_id,
                agent_id=zombie_worker.agent_id,
                lease_token=claim_zombie.lease_token,
                result={"corrupted": "stale data"},
            )
            print("ERROR: Stale submission was accepted!")
        except Exception as e:
            print(f"Stale submission correctly rejected by fencing token: {e}")

        # Replacement worker starts and submits result successfully
        coordinator.start_task(task_flakey.task_id, agent_b.agent_id, replacement_claim.lease_token)
        comp = coordinator.submit_task_result(
            task_id=task_flakey.task_id,
            agent_id=agent_b.agent_id,
            lease_token=replacement_claim.lease_token,
            result={"batch_export": "completed 1,500 records"},
        )
        print(f"Replacement worker successfully finished task: Status={comp.status.value}")

        print("\n" + "=" * 80)
        print("ALL MULTI-AGENT COORDINATION WORKFLOWS COMPLETED SUCCESSFULLY!")
        print("=" * 80)


if __name__ == "__main__":
    run_coordination_demo()
