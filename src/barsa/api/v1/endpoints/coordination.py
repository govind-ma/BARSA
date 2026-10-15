"""FastAPI REST endpoints for the Barsa Multi-Agent Coordination Engine (Phase 9)."""

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from barsa.api.deps import get_coordinator_engine
from barsa.coordination.engine import CoordinatorEngine
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
    HelpRequest,
    MessageType,
    TaskClaimRequest,
    TaskClaimResponse,
    TaskHeartbeatRequest,
    TaskReleaseRequest,
    TaskStartRequest,
    TaskSubmitRequest,
)

router = APIRouter(prefix="/coordination", tags=["coordination"])


# =========================================================================
# Request Helpers
# =========================================================================


class AgentStatusUpdate(BaseModel):
    status: AgentState


class PostCommentRequest(BaseModel):
    project_id: str
    author_agent_id: str
    content: str
    message_type: MessageType = MessageType.COMMENT
    related_record_refs: list[str] = Field(default_factory=list)


class PostIssueRequest(BaseModel):
    project_id: str
    author_agent_id: str
    title: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)


class PostHelpRequestPayload(BaseModel):
    project_id: str
    requester_agent_id: str
    required_capabilities: list[str]
    issue_id: str | None = None
    target_agent_id: str | None = None


class ScheduleRequest(BaseModel):
    project_id: str


# =========================================================================
# Agents Endpoints
# =========================================================================


@router.post(
    "/agents/register",
    response_model=AgentProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Register or update agent capabilities",
)
def register_agent(
    payload: AgentRegistration,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> AgentProfile:
    return engine.register_agent(payload)


@router.get(
    "/agents",
    response_model=list[AgentProfile],
    summary="List registered agents",
)
def list_agents(
    project_id: str | None = Query(default=None),
    status: AgentState | None = Query(default=None),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[AgentProfile]:
    return engine.list_agents(project_id=project_id, status=status)


@router.get(
    "/agents/{agent_id}",
    response_model=AgentProfile,
    summary="Get agent profile",
)
def get_agent(
    agent_id: str,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> AgentProfile:
    return engine.get_agent(agent_id)


@router.post(
    "/agents/{agent_id}/heartbeat",
    response_model=AgentProfile,
    summary="Agent heartbeat update",
)
def heartbeat_agent(
    agent_id: str,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> AgentProfile:
    return engine.heartbeat_agent(agent_id)


@router.patch(
    "/agents/{agent_id}/status",
    response_model=AgentProfile,
    summary="Update agent availability status",
)
def update_agent_status(
    agent_id: str,
    payload: AgentStatusUpdate,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> AgentProfile:
    return engine.update_agent_status(agent_id, payload.status)


# =========================================================================
# Tasks Endpoints
# =========================================================================


@router.post(
    "/tasks",
    response_model=CoordinationTask,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new coordination task",
)
def create_task(
    task: CoordinationTask,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CoordinationTask:
    return engine.create_task(task)


@router.get(
    "/tasks",
    response_model=list[CoordinationTask],
    summary="List coordination tasks for a project",
)
def list_tasks(
    project_id: str | None = Query(default=None, description="Project ID"),
    status: CoordinationTaskStatus | None = Query(default=None, description="Task status filter"),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[CoordinationTask]:
    return engine.list_tasks(project_id=project_id, status=status)


@router.get(
    "/tasks/available",
    response_model=list[CoordinationTask],
    summary="Discover available tasks ready to be claimed",
)
def list_available_tasks(
    project_id: str = Query(..., description="Project ID"),
    agent_id: str | None = Query(default=None, description="Filter for specific agent capabilities"),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[CoordinationTask]:
    return engine.list_available_tasks(project_id=project_id, agent_id=agent_id)


@router.get(
    "/tasks/{task_id}",
    response_model=CoordinationTask,
    summary="Get task details",
)
def get_task(
    task_id: str,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CoordinationTask:
    return engine.get_task(task_id)


@router.post(
    "/tasks/{task_id}/claim",
    response_model=TaskClaimResponse,
    summary="Atomically claim a task lease",
)
def claim_task(
    task_id: str,
    payload: TaskClaimRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> TaskClaimResponse:
    return engine.claim_task(
        task_id=task_id,
        agent_id=payload.agent_id,
        lease_duration_seconds=payload.lease_duration_seconds,
    )


@router.post(
    "/tasks/{task_id}/start",
    response_model=CoordinationTask,
    summary="Transition a claimed task to running state",
)
def start_task(
    task_id: str,
    payload: TaskStartRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CoordinationTask:
    return engine.start_task(
        task_id=task_id,
        agent_id=payload.agent_id,
        lease_token=payload.lease_token,
    )


@router.post(
    "/tasks/{task_id}/heartbeat",
    response_model=CoordinationTask,
    summary="Renew task lease and heartbeat",
)
def heartbeat_task(
    task_id: str,
    payload: TaskHeartbeatRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CoordinationTask:
    return engine.heartbeat_task(
        task_id=task_id,
        agent_id=payload.agent_id,
        lease_token=payload.lease_token,
        lease_duration_seconds=payload.lease_duration_seconds,
    )


@router.post(
    "/tasks/{task_id}/submit",
    response_model=CoordinationTask,
    summary="Submit completed task results",
)
def submit_task(
    task_id: str,
    payload: TaskSubmitRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CoordinationTask:
    return engine.submit_task_result(
        task_id=task_id,
        agent_id=payload.agent_id,
        lease_token=payload.lease_token,
        result=payload.result,
        commit_id=payload.commit_id,
        requires_review=payload.requires_review,
        resource_usage=payload.resource_usage,
    )


@router.post(
    "/tasks/{task_id}/release",
    response_model=CoordinationTask,
    summary="Voluntarily release a task lease",
)
def release_task(
    task_id: str,
    payload: TaskReleaseRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CoordinationTask:
    return engine.release_task(
        task_id=task_id,
        agent_id=payload.agent_id,
        lease_token=payload.lease_token,
        reason=payload.reason,
    )


@router.get(
    "/tasks/{task_id}/assignment",
    response_model=dict[str, Any],
    summary="Get current task assignment and lease info",
)
def get_task_assignment(
    task_id: str,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> dict[str, Any]:
    task = engine.get_task(task_id)
    return {
        "task_id": task.task_id,
        "project_id": task.project_id,
        "status": task.status.value,
        "assigned_agent_id": task.assigned_agent_id,
        "lease_token": task.lease_token,
        "lease_expires_at": task.lease_expires_at.isoformat() if task.lease_expires_at else None,
        "attempt_count": task.attempt_count,
        "max_attempts": task.max_attempts,
    }


# =========================================================================
# Collaboration Endpoints
# =========================================================================


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CollaborationMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Add a collaboration comment or observation",
)
def add_task_comment(
    task_id: str,
    payload: PostCommentRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CollaborationMessage:
    return engine.add_comment(
        project_id=payload.project_id,
        task_id=task_id,
        author_agent_id=payload.author_agent_id,
        content=payload.content,
        message_type=payload.message_type,
        related_record_refs=payload.related_record_refs,
    )


@router.get(
    "/tasks/{task_id}/comments",
    response_model=list[CollaborationMessage],
    summary="List comments for a task",
)
def list_task_comments(
    task_id: str,
    project_id: str = Query(..., description="Project ID"),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[CollaborationMessage]:
    return engine.list_comments(project_id=project_id, task_id=task_id)


@router.post(
    "/tasks/{task_id}/issues",
    response_model=CoordinationIssue,
    status_code=status.HTTP_201_CREATED,
    summary="Report an issue on a task",
)
def report_task_issue(
    task_id: str,
    payload: PostIssueRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> CoordinationIssue:
    return engine.report_issue(
        project_id=payload.project_id,
        task_id=task_id,
        author_agent_id=payload.author_agent_id,
        title=payload.title,
        description=payload.description,
        evidence=payload.evidence,
        required_capabilities=payload.required_capabilities,
    )


@router.get(
    "/tasks/{task_id}/issues",
    response_model=list[CoordinationIssue],
    summary="List issues reported on a task",
)
def list_task_issues(
    task_id: str,
    project_id: str = Query(..., description="Project ID"),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[CoordinationIssue]:
    return engine.list_issues(project_id=project_id, task_id=task_id)


@router.post(
    "/tasks/{task_id}/help-requests",
    response_model=HelpRequest,
    status_code=status.HTTP_201_CREATED,
    summary="Request help from other capable agents",
)
def create_help_request(
    task_id: str,
    payload: PostHelpRequestPayload,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> HelpRequest:
    return engine.request_help(
        project_id=payload.project_id,
        task_id=task_id,
        requester_agent_id=payload.requester_agent_id,
        required_capabilities=payload.required_capabilities,
        issue_id=payload.issue_id,
        target_agent_id=payload.target_agent_id,
    )


@router.get(
    "/tasks/{task_id}/help-requests",
    response_model=list[HelpRequest],
    summary="List help requests for a task",
)
def list_help_requests(
    task_id: str,
    project_id: str = Query(..., description="Project ID"),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[HelpRequest]:
    return engine.list_help_requests(project_id=project_id, task_id=task_id)


# =========================================================================
# Coordinator Diagnostics & Scheduling
# =========================================================================


@router.post(
    "/schedule",
    response_model=list[AssignmentDecision],
    summary="Run deterministic scheduling round for a project",
)
def schedule_tasks(
    payload: ScheduleRequest,
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[AssignmentDecision]:
    return engine.schedule_tasks(payload.project_id)


@router.get(
    "/status",
    response_model=dict[str, Any],
    summary="Get overall coordinator diagnostic health",
)
def get_coordinator_status(
    project_id: str | None = Query(default=None),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> dict[str, Any]:
    return engine.get_status(project_id=project_id)


@router.get(
    "/events",
    response_model=list[CoordinationEvent],
    summary="List coordinator audit events",
)
def list_coordinator_events(
    project_id: str = Query(..., description="Project ID"),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    engine: CoordinatorEngine = Depends(get_coordinator_engine),
) -> list[CoordinationEvent]:
    return engine.list_events(project_id=project_id, event_type=event_type, limit=limit)
