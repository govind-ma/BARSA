"""Models and schemas for the Barsa Multi-Agent Coordination Engine (Phase 9)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentState(StrEnum):
    """Lifecycle and availability states for an agent."""

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    DISABLED = "disabled"


class CoordinationTaskStatus(StrEnum):
    """Persistent lifecycle states for a coordinated task."""

    PENDING = "pending"
    READY = "ready"
    CLAIMED = "claimed"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(StrEnum):
    """Types of structured collaboration messages."""

    COMMENT = "comment"
    OBSERVATION = "observation"
    ISSUE = "issue"
    HELP_REQUEST = "help_request"
    SUGGESTION = "suggestion"
    PROGRESS_UPDATE = "progress_update"
    REVIEW_REQUEST = "review_request"
    RESOLUTION = "resolution"


class Priority(StrEnum):
    """Priority level for coordination tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationLevel(StrEnum):
    """Capability verification requirement."""

    CLAIMED = "claimed"
    VERIFIED = "verified"


class IssueStatus(StrEnum):
    """Status of coordination issues."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class HelpRequestStatus(StrEnum):
    """Status of agent help requests."""

    OPEN = "open"
    CLAIMED = "claimed"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


# =========================================================================
# Agent Models
# =========================================================================


class AgentRegistration(BaseModel):
    """Payload to register or update an agent in the coordinator registry."""

    agent_id: str = Field(..., min_length=1, description="Unique agent identifier")
    display_name: str = Field(..., min_length=1, description="Human-readable agent display name")
    provider: str = Field(..., min_length=1, description="Provider/platform name (e.g. openai, anthropic, local)")
    model: str | None = Field(default=None, description="Underlying model if applicable")
    claimed_capabilities: list[str] = Field(
        default_factory=list, description="Self-reported capabilities announced by the agent"
    )
    verified_capabilities: list[str] = Field(
        default_factory=list, description="Capabilities verified by administrator or verification tests"
    )
    supported_tools: list[str] = Field(
        default_factory=list, description="List of tools the agent runtime has access to"
    )
    allowed_projects: list[str] = Field(
        default_factory=lambda: ["*"], description="Projects the agent is authorized to access (or ['*'])"
    )
    maximum_concurrent_tasks: int = Field(
        default=2, ge=1, description="Maximum concurrent tasks this agent can execute"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary provider or runtime metadata")


class AgentProfile(BaseModel):
    """Full persistent profile of a registered agent."""

    agent_id: str
    display_name: str
    provider: str
    model: str | None = None
    claimed_capabilities: list[str] = Field(default_factory=list)
    verified_capabilities: list[str] = Field(default_factory=list)
    supported_tools: list[str] = Field(default_factory=list)
    allowed_projects: list[str] = Field(default_factory=lambda: ["*"])
    availability_status: AgentState = AgentState.AVAILABLE
    last_heartbeat: datetime
    current_workload: int = 0
    maximum_concurrent_tasks: int = 2
    registered_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


# =========================================================================
# Task Models
# =========================================================================


class CoordinationTask(BaseModel):
    """Persistent task managed by the coordination engine."""

    task_id: str = Field(..., description="Unique task identifier")
    project_id: str = Field(..., description="Project this task belongs to")
    title: str = Field(..., description="Short summary title of the task")
    description: str | None = Field(default=None, description="Detailed description and specifications")
    required_capabilities: list[str] = Field(default_factory=list, description="Required capabilities to execute")
    required_tools: list[str] = Field(default_factory=list, description="Required tools (e.g. pytest, git)")
    min_verified_level: VerificationLevel = Field(
        default=VerificationLevel.CLAIMED,
        description="Whether capabilities must be verified or can be claimed",
    )
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    dependencies: list[str] = Field(
        default_factory=list, description="List of predecessor task_ids that must be completed first"
    )
    status: CoordinationTaskStatus = Field(default=CoordinationTaskStatus.PENDING)
    assigned_agent_id: str | None = None
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    heartbeat_timeout_seconds: int = 60
    max_attempts: int = 3
    attempt_count: int = 0
    failure_reason: str | None = None
    result: dict[str, Any] | None = None
    resource_usage: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskClaimRequest(BaseModel):
    """Request payload for an agent claiming a task."""

    agent_id: str = Field(..., min_length=1)
    lease_duration_seconds: int | None = Field(default=None, ge=5, le=3600)


class TaskClaimResponse(BaseModel):
    """Response returned upon successfully claiming a task lease."""

    task_id: str
    assigned_agent_id: str
    lease_token: str
    lease_expires_at: datetime
    status: CoordinationTaskStatus
    explanation: str


class TaskStartRequest(BaseModel):
    """Transition a claimed task to running state."""

    agent_id: str
    lease_token: str


class TaskHeartbeatRequest(BaseModel):
    """Heartbeat and lease renewal request."""

    agent_id: str
    lease_token: str
    lease_duration_seconds: int | None = Field(default=None, ge=5, le=3600)


class TaskProgressUpdate(BaseModel):
    """Periodic progress report from an active agent."""

    agent_id: str
    lease_token: str
    message: str
    progress_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    resource_usage: dict[str, Any] | None = None


class TaskSubmitRequest(BaseModel):
    """Submission of task results by an active agent."""

    agent_id: str
    lease_token: str
    result: dict[str, Any]
    commit_id: str | None = None
    requires_review: bool | None = None
    resource_usage: dict[str, Any] | None = None


class TaskReleaseRequest(BaseModel):
    """Voluntary release of a task back to the ready pool."""

    agent_id: str
    lease_token: str
    reason: str | None = None


# =========================================================================
# Collaboration & Communication Models
# =========================================================================


class CollaborationMessage(BaseModel):
    """Structured message in the collaboration stream."""

    message_id: str = Field(default_factory=lambda: f"msg-{uuid4().hex[:12]}")
    project_id: str
    task_id: str | None = None
    author_agent_id: str
    message_type: MessageType = MessageType.COMMENT
    content: str
    related_record_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoordinationIssue(BaseModel):
    """An issue or impediment raised during execution."""

    issue_id: str = Field(default_factory=lambda: f"issue-{uuid4().hex[:12]}")
    project_id: str
    task_id: str
    author_agent_id: str
    title: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    status: IssueStatus = IssueStatus.OPEN
    resolver_agent_id: str | None = None
    resolution_proposal: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None


class HelpRequest(BaseModel):
    """A formal request for assistance targeted at capable agents."""

    request_id: str = Field(default_factory=lambda: f"help-{uuid4().hex[:12]}")
    project_id: str
    task_id: str
    issue_id: str | None = None
    requester_agent_id: str
    target_agent_id: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    status: HelpRequestStatus = HelpRequestStatus.OPEN
    assigned_helper_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# =========================================================================
# Policy & Scheduling Models
# =========================================================================


class CoordinatorPolicy(BaseModel):
    """Configurable coordinator scheduling and reliability policies."""

    max_concurrent_tasks_per_agent: int = 2
    default_lease_duration_seconds: int = 60
    heartbeat_interval_seconds: int = 15
    max_attempts_per_task: int = 3
    enforce_verified_capabilities: bool = False
    require_review_for_completion: bool = False
    auto_assignment_enabled: bool = True


class AssignmentDecision(BaseModel):
    """Explainable result of matching a task to candidate agents."""

    task_id: str
    assigned_agent_id: str | None = None
    eligible_agents: list[str] = Field(default_factory=list)
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class CoordinationEvent(BaseModel):
    """Audit and telemetry event recorded by the coordinator."""

    event_id: str = Field(default_factory=lambda: f"evt-{uuid4().hex[:12]}")
    project_id: str
    event_type: str
    agent_id: str | None = None
    task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
