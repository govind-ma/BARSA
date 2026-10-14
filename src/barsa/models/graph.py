"""Domain models, schemas, and enums for FalkorDB Knowledge Graph Engine (Phase 5)."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from barsa.bms.base import utc_now

# =============================================================================
# Graph Node Types & Relationship Types
# =============================================================================


class GraphNodeType(StrEnum):
    WORKSPACE = "Workspace"
    PROJECT = "Project"
    KNOWLEDGE = "Knowledge"
    REQUIREMENT = "Requirement"
    DECISION = "Decision"
    TASK = "Task"
    AGENT = "Agent"
    CHECKPOINT = "Checkpoint"
    ARTIFACT = "Artifact"
    COMMIT = "Commit"


class GraphRelationshipType(StrEnum):
    HAS_PROJECT = "HAS_PROJECT"
    HAS_KNOWLEDGE = "HAS_KNOWLEDGE"
    HAS_REQUIREMENT = "HAS_REQUIREMENT"
    HAS_TASK = "HAS_TASK"
    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    REFERENCES = "REFERENCES"
    SUPPORTS = "SUPPORTS"
    BLOCKS = "BLOCKS"
    SUPERSEDES = "SUPERSEDES"
    CREATED_BY = "CREATED_BY"
    UPDATED_BY = "UPDATED_BY"
    HAS_CHECKPOINT = "HAS_CHECKPOINT"
    REFERENCES_ARTIFACT = "REFERENCES_ARTIFACT"
    INCLUDED_IN_COMMIT = "INCLUDED_IN_COMMIT"
    PARENT_COMMIT = "PARENT_COMMIT"


class OutboxEventStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProjectionStatus(StrEnum):
    UP_TO_DATE = "UP_TO_DATE"
    LAGGING = "LAGGING"
    REBUILDING = "REBUILDING"
    ERROR = "ERROR"
    DISABLED = "DISABLED"
    UNAVAILABLE = "UNAVAILABLE"


# =============================================================================
# Graph Entities & Nodes
# =============================================================================


class GraphNode(BaseModel):
    """Normalized graph node entity across graph providers."""

    model_config = ConfigDict(extra="forbid")

    id: str  # Globally unambiguous composite ID (e.g., "proj-1:task-2" or project_id for project)
    raw_id: str  # Native BMS record ID (e.g., "task-2")
    project_id: str
    node_type: GraphNodeType
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphRelationship(BaseModel):
    """Normalized directed graph relationship."""

    model_config = ConfigDict(extra="forbid")

    source_id: str  # Composite source node ID
    target_id: str  # Composite target node ID
    rel_type: GraphRelationshipType
    project_id: str
    properties: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Outbox & Projection Metadata
# =============================================================================


class OutboxEvent(BaseModel):
    """Transactional outbox event emitted when an approved commit advances main."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    project_id: str
    commit_id: str
    event_type: str  # 'COMMIT_APPROVED', 'REBUILD_REQUESTED'
    payload: dict[str, Any]
    status: OutboxEventStatus = OutboxEventStatus.PENDING
    retry_count: int = 0
    last_error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    processed_at: datetime | None = None


class GraphProjectionMetadata(BaseModel):
    """Tracks the projection state and synchronization lag of a project graph."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    applied_commit_id: str
    applied_revision: int
    applied_state_hash: str
    node_count: int = 0
    relationship_count: int = 0
    status: ProjectionStatus = ProjectionStatus.UP_TO_DATE
    last_projected_at: datetime = Field(default_factory=utc_now)
    last_error: str | None = None
    authoritative_commit_id: str | None = None
    lag_commits_count: int = 0
    is_fresh: bool = True


# =============================================================================
# Graph Query Results
# =============================================================================


class ProjectOverviewResult(BaseModel):
    """Overview of active tasks, decisions, requirements, latest checkpoint, and artifacts."""

    project_id: str
    active_tasks: list[dict[str, Any]] = Field(default_factory=list)
    approved_decisions: list[dict[str, Any]] = Field(default_factory=list)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    latest_checkpoint: dict[str, Any] | None = None
    relevant_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    projection_status: GraphProjectionMetadata | None = None


class TaskDependenciesResult(BaseModel):
    """Upstream dependencies and blockers for a specific task."""

    project_id: str
    task_id: str
    task: dict[str, Any] | None = None
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    projection_status: GraphProjectionMetadata | None = None


class DecisionImpactResult(BaseModel):
    """Connected tasks, requirements, artifacts, and superseded decisions affected by a decision."""

    project_id: str
    decision_id: str
    decision: dict[str, Any] | None = None
    connected_tasks: list[dict[str, Any]] = Field(default_factory=list)
    connected_requirements: list[dict[str, Any]] = Field(default_factory=list)
    connected_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    superseded_decisions: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    projection_status: GraphProjectionMetadata | None = None


class AgentContributionsResult(BaseModel):
    """Commits and records authored or updated by a specific agent in a project."""

    project_id: str
    agent_id: str
    commits: list[dict[str, Any]] = Field(default_factory=list)
    created_records: list[dict[str, Any]] = Field(default_factory=list)
    projection_status: GraphProjectionMetadata | None = None


class ResumeContextResult(BaseModel):
    """Comprehensive structured memory retrieval for continuing work on a task."""

    project_id: str
    task_id: str
    task: dict[str, Any] | None = None
    status: str | None = None
    latest_checkpoint: dict[str, Any] | None = None
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    relevant_decisions: list[dict[str, Any]] = Field(default_factory=list)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    projection_status: GraphProjectionMetadata | None = None


class GraphRebuildResponse(BaseModel):
    """Response returned when an administrative graph rebuild is initiated."""

    project_id: str
    rebuilt_nodes_count: int
    rebuilt_relationships_count: int
    applied_commit_id: str
    status: ProjectionStatus
    message: str
