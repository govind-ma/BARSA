"""Multi-Agent Coordination Engine for BARSA (Phase 9)."""

import logging
from datetime import UTC, datetime
from typing import Any

from barsa.coordination.leases import compute_lease_expiration, generate_fencing_token
from barsa.coordination.matching import CapabilityMatcher
from barsa.coordination.models import (
    AgentProfile,
    AgentRegistration,
    AgentState,
    AssignmentDecision,
    CollaborationMessage,
    CoordinationEvent,
    CoordinationIssue,
    CoordinationTask,
    CoordinationTaskStatus,
    CoordinatorPolicy,
    HelpRequest,
    HelpRequestStatus,
    IssueStatus,
    MessageType,
    TaskClaimResponse,
)
from barsa.coordination.storage import CoordinationStorage
from barsa.core.exceptions import ConflictError, ResourceNotFoundError, ValidationError
from barsa.models.versioning import AuthorType, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine

logger = logging.getLogger("barsa.coordination.engine")


class CoordinatorEngine:
    """Core coordination engine orchestrating agents, tasks, leases, issues, reviews, and versioned memory."""

    def __init__(
        self,
        storage: SQLiteStorageProvider,
        vc: VersionControlEngine | None = None,
        policy: CoordinatorPolicy | None = None,
    ) -> None:
        self.storage = storage
        self.coord_storage = CoordinationStorage(storage)
        self.vc = vc or VersionControlEngine(storage)
        self.policy = policy or CoordinatorPolicy()

    # =========================================================================
    # Agent Registry
    # =========================================================================

    def register_agent(self, reg: AgentRegistration) -> AgentProfile:
        """Register an agent or update its registration profile."""
        profile = self.coord_storage.register_agent(reg)
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=reg.allowed_projects[0]
                if reg.allowed_projects and reg.allowed_projects[0] != "*"
                else "global",
                event_type="AGENT_REGISTERED",
                agent_id=reg.agent_id,
                payload={"display_name": reg.display_name, "provider": reg.provider, "model": reg.model},
            )
        )
        return profile

    def get_agent(self, agent_id: str) -> AgentProfile:
        """Fetch an agent by ID or raise ResourceNotFoundError."""
        agent = self.coord_storage.get_agent(agent_id)
        if not agent:
            raise ResourceNotFoundError(f"Agent '{agent_id}' is not registered")
        return agent

    def list_agents(
        self,
        project_id: str | None = None,
        status: AgentState | None = None,
    ) -> list[AgentProfile]:
        """List registered agents."""
        return self.coord_storage.list_agents(project_id=project_id, status=status)

    def heartbeat_agent(self, agent_id: str) -> AgentProfile:
        """Record an agent heartbeat."""
        return self.coord_storage.heartbeat_agent(agent_id)

    def update_agent_status(self, agent_id: str, status: AgentState) -> AgentProfile:
        """Update an agent's availability status."""
        return self.coord_storage.update_agent_status(agent_id, status)

    # =========================================================================
    # Task Lifecycle & Claiming
    # =========================================================================

    def create_task(self, task: CoordinationTask) -> CoordinationTask:
        """Create and persist a new coordination task."""
        created = self.coord_storage.create_task(task)
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=task.project_id,
                event_type="TASK_CREATED",
                task_id=task.task_id,
                payload={"title": task.title, "priority": task.priority.value},
            )
        )
        return created

    def get_task(self, task_id: str) -> CoordinationTask:
        """Retrieve task by ID."""
        task = self.coord_storage.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task '{task_id}' not found")
        return task

    def list_tasks(
        self,
        project_id: str | None = None,
        status: CoordinationTaskStatus | None = None,
    ) -> list[CoordinationTask]:
        """List tasks optionally filtered by project or status."""
        return self.coord_storage.list_tasks(project_id=project_id, status=status)

    def list_available_tasks(
        self,
        project_id: str,
        agent_id: str | None = None,
    ) -> list[CoordinationTask]:
        """List tasks that are ready or pending with satisfied dependencies."""
        # First promote pending tasks with satisfied dependencies to READY
        self._promote_ready_tasks(project_id)

        all_tasks = self.coord_storage.list_tasks(project_id=project_id)
        completed_ids = {t.task_id for t in all_tasks if t.status == CoordinationTaskStatus.COMPLETED}

        agent = self.get_agent(agent_id) if agent_id else None

        available: list[CoordinationTask] = []
        for task in all_tasks:
            if task.status not in (CoordinationTaskStatus.READY, CoordinationTaskStatus.PENDING):
                continue

            # Check dependencies
            unmet = [d for d in task.dependencies if d not in completed_ids]
            if unmet:
                continue

            # If agent specified, verify agent capability and tool suitability
            if agent:
                if "*" not in agent.allowed_projects and project_id not in agent.allowed_projects:
                    continue
                missing_tools = [t for t in task.required_tools if t not in agent.supported_tools]
                if missing_tools:
                    continue

                if task.min_verified_level.value == "verified":
                    missing_caps = [c for c in task.required_capabilities if c not in agent.verified_capabilities]
                else:
                    all_caps = set(agent.verified_capabilities).union(agent.claimed_capabilities)
                    missing_caps = [c for c in task.required_capabilities if c not in all_caps]

                if missing_caps:
                    continue

            available.append(task)

        return available

    def _promote_ready_tasks(self, project_id: str) -> None:
        """Promote PENDING tasks with satisfied dependencies to READY."""
        all_tasks = self.coord_storage.list_tasks(project_id=project_id)
        completed_ids = {t.task_id for t in all_tasks if t.status == CoordinationTaskStatus.COMPLETED}

        for t in all_tasks:
            if t.status == CoordinationTaskStatus.PENDING and (
                not t.dependencies or all(d in completed_ids for d in t.dependencies)
            ):
                self.coord_storage.update_task_status(t.task_id, CoordinationTaskStatus.READY)

    def claim_task(
        self,
        task_id: str,
        agent_id: str,
        lease_duration_seconds: int | None = None,
    ) -> TaskClaimResponse:
        """Atomically claim a task with a unique fencing token and lease."""
        task = self.get_task(task_id)
        agent = self.get_agent(agent_id)

        # Check authorization
        if "*" not in agent.allowed_projects and task.project_id not in agent.allowed_projects:
            raise ValidationError(f"Agent '{agent_id}' is not authorized for project '{task.project_id}'")

        # Verify capabilities
        if task.min_verified_level.value == "verified":
            missing_caps = [c for c in task.required_capabilities if c not in agent.verified_capabilities]
            if missing_caps:
                raise ValidationError(f"Agent '{agent_id}' lacks verified capabilities: {', '.join(missing_caps)}")
        else:
            all_caps = set(agent.verified_capabilities).union(agent.claimed_capabilities)
            missing_caps = [c for c in task.required_capabilities if c not in all_caps]
            if missing_caps:
                raise ValidationError(f"Agent '{agent_id}' lacks required capabilities: {', '.join(missing_caps)}")

        # Verify tools
        missing_tools = [t for t in task.required_tools if t not in agent.supported_tools]
        if missing_tools:
            raise ValidationError(f"Agent '{agent_id}' lacks required tools: {', '.join(missing_tools)}")

        duration = (
            lease_duration_seconds or task.heartbeat_timeout_seconds or self.policy.default_lease_duration_seconds
        )
        expires_at = compute_lease_expiration(duration)
        token = generate_fencing_token(prefix=f"lease-{task_id[:6]}")

        claimed = self.coord_storage.claim_task(
            task_id=task_id,
            agent_id=agent_id,
            lease_token=token,
            lease_expires_at=expires_at,
        )

        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=task.project_id,
                event_type="TASK_CLAIMED",
                agent_id=agent_id,
                task_id=task_id,
                payload={"lease_token": token, "expires_at": expires_at.isoformat()},
            )
        )

        return TaskClaimResponse(
            task_id=task_id,
            assigned_agent_id=agent_id,
            lease_token=token,
            lease_expires_at=expires_at,
            status=claimed.status,
            explanation=f"Successfully claimed lease for task '{task.title}' by agent '{agent.display_name}'",
        )

    def start_task(self, task_id: str, agent_id: str, lease_token: str) -> CoordinationTask:
        """Start executing a claimed task."""
        running = self.coord_storage.start_task(task_id, agent_id, lease_token)
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=running.project_id,
                event_type="TASK_STARTED",
                agent_id=agent_id,
                task_id=task_id,
                payload={"lease_token": lease_token},
            )
        )
        return running

    def heartbeat_task(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        lease_duration_seconds: int | None = None,
    ) -> CoordinationTask:
        """Renew task lease and record agent heartbeat."""
        duration = lease_duration_seconds or self.policy.default_lease_duration_seconds
        new_expires_at = compute_lease_expiration(duration)
        return self.coord_storage.heartbeat_task(
            task_id=task_id,
            agent_id=agent_id,
            lease_token=lease_token,
            new_lease_expires_at=new_expires_at,
        )

    def update_task_progress(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        message: str,
        progress_percent: float | None = None,
        resource_usage: dict[str, Any] | None = None,
    ) -> CoordinationTask:
        """Update progress on a running task."""
        return self.coord_storage.update_task_progress(
            task_id=task_id,
            agent_id=agent_id,
            lease_token=lease_token,
            message=message,
            progress_percent=progress_percent,
            resource_usage=resource_usage,
        )

    def release_task(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        reason: str | None = None,
    ) -> CoordinationTask:
        """Voluntarily release a claimed/running task back to ready."""
        released = self.coord_storage.release_task(
            task_id=task_id,
            agent_id=agent_id,
            lease_token=lease_token,
            reason=reason,
        )
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=released.project_id,
                event_type="TASK_RELEASED",
                agent_id=agent_id,
                task_id=task_id,
                payload={"reason": reason},
            )
        )
        return released

    def submit_task_result(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        result: dict[str, Any],
        commit_id: str | None = None,
        requires_review: bool | None = None,
        resource_usage: dict[str, Any] | None = None,
    ) -> CoordinationTask:
        """Submit completed task results, routing to review or completion."""
        # Determine whether review is required
        needs_review = requires_review if requires_review is not None else self.policy.require_review_for_completion
        target_status = CoordinationTaskStatus.UNDER_REVIEW if needs_review else CoordinationTaskStatus.COMPLETED

        submitted = self.coord_storage.submit_task(
            task_id=task_id,
            agent_id=agent_id,
            lease_token=lease_token,
            result=result,
            new_status=target_status,
            resource_usage=resource_usage,
        )

        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=submitted.project_id,
                event_type="TASK_SUBMITTED",
                agent_id=agent_id,
                task_id=task_id,
                payload={
                    "status": submitted.status.value,
                    "commit_id": commit_id,
                    "requires_review": needs_review,
                },
            )
        )

        # If completed, check if any dependent tasks can now be unblocked
        if submitted.status == CoordinationTaskStatus.COMPLETED:
            self._promote_ready_tasks(submitted.project_id)

        return submitted

    # =========================================================================
    # Scheduling & Capability Matching
    # =========================================================================

    def schedule_tasks(self, project_id: str) -> list[AssignmentDecision]:
        """Evaluate ready tasks and match to available agents deterministically."""
        self._promote_ready_tasks(project_id)

        tasks = self.coord_storage.list_tasks(project_id=project_id)
        ready_tasks = [t for t in tasks if t.status == CoordinationTaskStatus.READY]
        agents = self.coord_storage.list_agents(project_id=project_id, status=AgentState.AVAILABLE)
        completed_ids = {t.task_id for t in tasks if t.status == CoordinationTaskStatus.COMPLETED}

        decisions: list[AssignmentDecision] = []

        for task in ready_tasks:
            decision = CapabilityMatcher.match_task_to_agents(
                task=task,
                candidates=agents,
                completed_task_ids=completed_ids,
            )
            decisions.append(decision)

            # If auto-assignment enabled and an agent matched, claim atomically
            if self.policy.auto_assignment_enabled and decision.assigned_agent_id:
                try:
                    self.claim_task(task.task_id, decision.assigned_agent_id)
                    # Refresh agent list to reflect updated workload
                    agents = self.coord_storage.list_agents(project_id=project_id, status=AgentState.AVAILABLE)
                except Exception as err:
                    logger.warning(
                        "Auto-assignment for task %s to %s failed: %s", task.task_id, decision.assigned_agent_id, err
                    )

        return decisions

    # =========================================================================
    # Collaboration & Communication
    # =========================================================================

    def add_comment(
        self,
        project_id: str,
        task_id: str | None,
        author_agent_id: str,
        content: str,
        message_type: MessageType = MessageType.COMMENT,
        related_record_refs: list[str] | None = None,
    ) -> CollaborationMessage:
        """Post a collaboration message or comment."""
        msg = CollaborationMessage(
            project_id=project_id,
            task_id=task_id,
            author_agent_id=author_agent_id,
            message_type=message_type,
            content=content,
            related_record_refs=related_record_refs or [],
        )
        return self.coord_storage.add_collaboration_message(msg)

    add_collaboration_message = add_comment

    def list_comments(
        self,
        project_id: str,
        task_id: str | None = None,
    ) -> list[CollaborationMessage]:
        """List collaboration comments."""
        return self.coord_storage.list_collaboration_messages(project_id=project_id, task_id=task_id)

    # =========================================================================
    # Issues & Help Requests
    # =========================================================================

    def report_issue(
        self,
        project_id: str,
        task_id: str,
        author_agent_id: str,
        title: str,
        description: str,
        evidence: dict[str, Any] | None = None,
        required_capabilities: list[str] | None = None,
    ) -> CoordinationIssue:
        """Report an issue encountered during execution."""
        issue = CoordinationIssue(
            project_id=project_id,
            task_id=task_id,
            author_agent_id=author_agent_id,
            title=title,
            description=description,
            evidence=evidence or {},
            required_capabilities=required_capabilities or [],
        )
        created = self.coord_storage.create_issue(issue)
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=project_id,
                event_type="ISSUE_REPORTED",
                agent_id=author_agent_id,
                task_id=task_id,
                payload={"issue_id": created.issue_id, "title": title},
            )
        )
        return created

    def list_issues(
        self,
        project_id: str,
        task_id: str | None = None,
        status: IssueStatus | None = None,
    ) -> list[CoordinationIssue]:
        """List issues."""
        return self.coord_storage.list_issues(project_id=project_id, task_id=task_id, status=status)

    def request_help(
        self,
        project_id: str,
        task_id: str,
        requester_agent_id: str,
        required_capabilities: list[str],
        issue_id: str | None = None,
        target_agent_id: str | None = None,
    ) -> HelpRequest:
        """Raise a help request targeted or broadcast to capable agents."""
        req = HelpRequest(
            project_id=project_id,
            task_id=task_id,
            issue_id=issue_id,
            requester_agent_id=requester_agent_id,
            target_agent_id=target_agent_id,
            required_capabilities=required_capabilities,
        )
        created = self.coord_storage.create_help_request(req)
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=project_id,
                event_type="HELP_REQUESTED",
                agent_id=requester_agent_id,
                task_id=task_id,
                payload={
                    "request_id": created.request_id,
                    "issue_id": issue_id,
                    "required_capabilities": required_capabilities,
                },
            )
        )
        return created

    def list_help_requests(
        self,
        project_id: str,
        task_id: str | None = None,
        status: HelpRequestStatus | None = None,
    ) -> list[HelpRequest]:
        """List help requests."""
        return self.coord_storage.list_help_requests(project_id=project_id, task_id=task_id, status=status)

    def match_helper_for_request(self, request_id: str) -> AssignmentDecision:
        """Find the best eligible helper agent for a help request."""
        req = self.coord_storage.get_help_request(request_id)
        if not req:
            raise ResourceNotFoundError(f"Help request '{request_id}' not found")

        agents = self.coord_storage.list_agents(project_id=req.project_id, status=AgentState.AVAILABLE)
        # Exclude requester
        candidates = [a for a in agents if a.agent_id != req.requester_agent_id]

        synthetic_task = CoordinationTask(
            task_id=f"help-task-{req.request_id}",
            project_id=req.project_id,
            title="Helper Task",
            required_capabilities=req.required_capabilities,
        )
        decision = CapabilityMatcher.match_task_to_agents(
            task=synthetic_task,
            candidates=candidates,
        )
        return decision

    def claim_help_request(self, request_id: str, helper_agent_id: str) -> HelpRequest:
        """Assign helper to help request."""
        self.get_agent(helper_agent_id)
        req = self.coord_storage.get_help_request(request_id)
        if not req:
            raise ResourceNotFoundError(f"Help request '{request_id}' not found")

        if req.requester_agent_id == helper_agent_id:
            raise ConflictError("Requester cannot claim their own help request")

        claimed = self.coord_storage.claim_help_request(request_id, helper_agent_id)
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=req.project_id,
                event_type="HELP_CLAIMED",
                agent_id=helper_agent_id,
                task_id=req.task_id,
                payload={"request_id": request_id},
            )
        )
        return claimed

    def resolve_issue(
        self,
        issue_id: str,
        resolver_agent_id: str,
        proposal: dict[str, Any],
    ) -> CoordinationIssue:
        """Mark issue resolved with resolution details."""
        resolved = self.coord_storage.resolve_issue(issue_id, resolver_agent_id, proposal)
        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=resolved.project_id,
                event_type="ISSUE_RESOLVED",
                agent_id=resolver_agent_id,
                task_id=resolved.task_id,
                payload={"issue_id": issue_id, "proposal": proposal},
            )
        )
        return resolved

    # =========================================================================
    # Shared Knowledge & Version Control Engine Integration
    # =========================================================================

    def commit_agent_contribution(
        self,
        project_id: str,
        author_agent_id: str,
        message: str,
        changes: list[MemoryChange],
        branch_name: str = "main",
        expected_head_commit_id: str | None = None,
    ) -> Any:
        """Commit an agent contribution through the VersionControlEngine."""
        # Ensure main branch is initialized
        self.vc.initialize_project_main_branch(project_id, author_id=author_agent_id)

        # Fetch current head if expected_head not passed
        if not expected_head_commit_id:
            branch = self.vc.get_branch(project_id, branch_name)
            if branch:
                expected_head_commit_id = branch.head_commit_id

        commit = self.vc.create_commit(
            project_id=project_id,
            branch_name=branch_name,
            author_id=author_agent_id,
            author_type=AuthorType.AGENT,
            message=message,
            changes=changes,
            expected_head_commit_id=expected_head_commit_id,
        )

        self.coord_storage.log_event(
            CoordinationEvent(
                project_id=project_id,
                event_type="KNOWLEDGE_COMMITTED",
                agent_id=author_agent_id,
                payload={"commit_id": commit.commit_id, "branch": branch_name, "message": message},
            )
        )
        return commit

    def submit_review_decision(
        self,
        proposal_id: str,
        project_id: str,
        reviewer_agent_id: str,
        status: str,  # 'approved', 'changes_requested', 'rejected'
        summary: str | None = None,
        associated_task_id: str | None = None,
    ) -> Any:
        """Submit a formal review on a merge proposal with self-approval checks."""
        from barsa.models.versioning import ReviewStatus

        # 1. Fetch proposal to prevent self-review
        proposal = self.vc.get_merge_proposal(project_id, proposal_id)
        if not proposal:
            raise ResourceNotFoundError(f"Proposal '{proposal_id}' not found")

        if proposal.author_id == reviewer_agent_id:
            raise ValidationError(
                f"Self-approval prohibited: reviewer '{reviewer_agent_id}' cannot review their own proposal '{proposal_id}'"
            )

        review = self.vc.submit_review(
            project_id=project_id,
            proposal_id=proposal_id,
            reviewer_id=reviewer_agent_id,
            reviewer_type=AuthorType.AGENT,
            status=ReviewStatus(status),
            summary=summary,
        )

        # If approved and task is under review, complete task
        if status == "approved" and associated_task_id:
            task = self.get_task(associated_task_id)
            if task.status == CoordinationTaskStatus.UNDER_REVIEW:
                self.coord_storage.update_task_status(associated_task_id, CoordinationTaskStatus.COMPLETED)
                self._promote_ready_tasks(project_id)

        return review

    # =========================================================================
    # Lease Management, Heartbeats & Expiration Sweeper
    # =========================================================================

    def reclaim_expired_leases(self, now: datetime | None = None) -> list[tuple[CoordinationTask, str]]:
        """Sweep expired task leases and reassign or fail them."""
        reaped = self.coord_storage.reap_expired_leases(now)
        for task, action in reaped:
            self.coord_storage.log_event(
                CoordinationEvent(
                    project_id=task.project_id,
                    event_type="LEASE_EXPIRED",
                    agent_id=task.assigned_agent_id,
                    task_id=task.task_id,
                    payload={"action": action, "attempt_count": task.attempt_count},
                )
            )
        return reaped

    def get_status(self, project_id: str | None = None) -> dict[str, Any]:
        """Return diagnostic status of coordinator engine."""
        agents = self.coord_storage.list_agents(project_id=project_id)
        tasks = self.coord_storage.list_tasks(project_id=project_id)

        task_counts: dict[str, int] = {}
        for t in tasks:
            task_counts[t.status.value] = task_counts.get(t.status.value, 0) + 1

        agent_counts: dict[str, int] = {}
        for a in agents:
            agent_counts[a.availability_status.value] = agent_counts.get(a.availability_status.value, 0) + 1

        return {
            "status": "healthy",
            "project_id": project_id,
            "total_agents": len(agents),
            "agents_by_status": agent_counts,
            "total_tasks": len(tasks),
            "tasks_by_status": task_counts,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def list_events(
        self,
        project_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[CoordinationEvent]:
        """Retrieve audit log events."""
        return self.coord_storage.list_events(project_id=project_id, event_type=event_type, limit=limit)
