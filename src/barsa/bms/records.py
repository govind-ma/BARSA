"""Core record types for the Barsa Memory Standard (BMS v0.1)."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from barsa.bms.base import BMSRecord, MetadataExtensibleModel, utc_now

# ============================================================================
# Enums
# ============================================================================


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class KnowledgeType(StrEnum):
    FACT = "fact"
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    REFERENCE = "reference"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"


class DecisionStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ArtifactType(StrEnum):
    SOURCE_CODE = "source_code"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    SPECIFICATION = "specification"
    DATASET = "dataset"
    IMAGE = "image"
    MODEL = "model"
    OTHER = "other"


class RelationshipType(StrEnum):
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"
    CREATED_BY = "created_by"
    RELATED_TO = "related_to"
    SUPPORTS = "supports"
    BLOCKS = "blocks"


class CheckpointStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class CommitOperation(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# ============================================================================
# Core Records
# ============================================================================


class Workspace(MetadataExtensibleModel):
    """Represents a user-controlled or team-controlled knowledge space."""

    record_type: Literal["workspace"] = "workspace"
    name: Annotated[
        str, Field(min_length=1, max_length=256, description="Human-readable workspace name")
    ]
    owner_id: Annotated[
        str, Field(min_length=1, max_length=128, description="Owner identifier (user or org)")
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]
    description: Annotated[
        str | None, Field(default=None, description="Optional workspace description")
    ] = None

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


class Project(MetadataExtensibleModel):
    """Represents an individual project inside a workspace."""

    record_type: Literal["project"] = "project"
    workspace_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of parent workspace")
    ]
    name: Annotated[str, Field(min_length=1, max_length=256, description="Project name")]
    status: Annotated[
        ProjectStatus, Field(default=ProjectStatus.ACTIVE, description="Current project status")
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]
    updated_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC last-update timestamp")
    ]
    description: Annotated[
        str | None, Field(default=None, description="Optional project description")
    ] = None
    goals: Annotated[
        list[str], Field(default_factory=list, description="List of primary project goals")
    ]

    @field_validator("created_at", "updated_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


class KnowledgeRecord(BMSRecord):
    """Represents an individual claim, concept, fact, or piece of project knowledge."""

    record_type: Literal["knowledge"] = "knowledge"
    project_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of associated project")
    ]
    content: Annotated[
        str, Field(min_length=1, description="Structured knowledge content or markdown")
    ]
    knowledge_type: Annotated[KnowledgeType, Field(description="Categorization of knowledge")]
    verification_status: Annotated[
        VerificationStatus,
        Field(default=VerificationStatus.UNVERIFIED, description="Verification state"),
    ]
    created_by: Annotated[
        str, Field(min_length=1, max_length=128, description="Author agent ID or user ID")
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


class DecisionRecord(BMSRecord):
    """Represents an architectural, technical, or business decision."""

    record_type: Literal["decision"] = "decision"
    project_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of associated project")
    ]
    title: Annotated[str, Field(min_length=1, max_length=256, description="Decision summary title")]
    decision: Annotated[str, Field(min_length=1, description="Description of the adopted decision")]
    rationale: Annotated[
        str, Field(min_length=1, description="Justification and technical rationale")
    ]
    status: Annotated[
        DecisionStatus, Field(default=DecisionStatus.PROPOSED, description="Decision status")
    ]
    created_by: Annotated[
        str, Field(min_length=1, max_length=128, description="Author agent or user ID")
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]
    alternatives: Annotated[
        list[str], Field(default_factory=list, description="Considered alternatives")
    ]
    evidence_refs: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="References to knowledge or artifact IDs supporting this decision",
        ),
    ]

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


class TaskRecord(BMSRecord):
    """Represents a discrete task or unit of work."""

    record_type: Literal["task"] = "task"
    project_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of associated project")
    ]
    title: Annotated[str, Field(min_length=1, max_length=256, description="Task title")]
    description: Annotated[
        str, Field(default="", description="Detailed task requirements and scope")
    ]
    status: Annotated[
        TaskStatus, Field(default=TaskStatus.TODO, description="Task execution status")
    ]
    priority: Annotated[
        TaskPriority, Field(default=TaskPriority.MEDIUM, description="Task priority")
    ]
    dependencies: Annotated[
        list[str], Field(default_factory=list, description="IDs of tasks that must precede this")
    ]
    assigned_agent_id: Annotated[
        str | None,
        Field(default=None, description="Optional assigned agent ID; null when unassigned"),
    ] = None
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]
    updated_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC last-update timestamp")
    ]

    @field_validator("created_at", "updated_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)

    @field_validator("dependencies")
    @classmethod
    def validate_no_self_dependency(cls, v: list[str], info: Any) -> list[str]:
        current_id = info.data.get("id")
        if current_id and current_id in v:
            msg = f"Task '{current_id}' cannot list itself as a dependency."
            raise ValueError(msg)
        return v


class AgentRecord(MetadataExtensibleModel):
    """Represents an AI agent, model configuration, or human collaborator."""

    record_type: Literal["agent"] = "agent"
    name: Annotated[
        str, Field(min_length=1, max_length=128, description="Human-readable agent name")
    ]
    provider: Annotated[
        str,
        Field(
            min_length=1,
            max_length=64,
            description="Provider or runtime name (e.g., 'anthropic', 'openai', 'google', 'local')",
        ),
    ]
    capabilities: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="List of declared capabilities (e.g. 'coding', 'reasoning')",
        ),
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]
    model: Annotated[
        str | None, Field(default=None, description="Model identifier (e.g. 'claude-3-7-sonnet')")
    ] = None
    description: Annotated[
        str | None, Field(default=None, description="Agent role description")
    ] = None

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


class ArtifactReference(BMSRecord):
    """Represents an external or locally stored resource (source file, doc, spec, dataset)."""

    record_type: Literal["artifact"] = "artifact"
    project_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of associated project")
    ]
    artifact_type: Annotated[ArtifactType, Field(description="Categorization of the artifact")]
    uri: Annotated[
        str, Field(min_length=1, description="URI or relative file path pointing to resource")
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]
    content_hash: Annotated[
        str | None,
        Field(default=None, description="Cryptographic hash (e.g. SHA-256) of artifact content"),
    ] = None
    size_bytes: Annotated[
        int | None, Field(default=None, ge=0, description="Size in bytes if known")
    ] = None
    media_type: Annotated[
        str | None,
        Field(
            default=None, description="MIME media type (e.g., 'text/markdown', 'application/json')"
        ),
    ] = None
    repository_revision: Annotated[
        str | None,
        Field(default=None, description="Git commit hash or repository revision"),
    ] = None

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


class RelationshipRecord(BMSRecord):
    """Represents graph-compatible connections between records."""

    record_type: Literal["relationship"] = "relationship"
    project_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of associated project")
    ]
    source_id: Annotated[str, Field(min_length=1, max_length=128, description="Origin record ID")]
    target_id: Annotated[str, Field(min_length=1, max_length=128, description="Target record ID")]
    relationship_type: Annotated[
        RelationshipType,
        Field(description="Directed relationship type between source and target"),
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)

    @field_validator("target_id")
    @classmethod
    def validate_no_self_relationship(cls, v: str, info: Any) -> str:
        source = info.data.get("source_id")
        if source and source == v:
            msg = f"Self-referencing relationship not allowed for source/target '{v}'"
            raise ValueError(msg)
        return v


class ResumeCheckpoint(BMSRecord):
    """Critical state snapshot enabling any compatible AI agent to resume paused work."""

    record_type: Literal["checkpoint"] = "checkpoint"
    project_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of associated project")
    ]
    task_id: Annotated[
        str,
        Field(min_length=1, max_length=128, description="ID of the task currently being resumed"),
    ]
    status: Annotated[
        CheckpointStatus, Field(description="Current status of the checkpoint workstream")
    ]
    completed_actions: Annotated[
        list[str],
        Field(default_factory=list, description="Concrete actions successfully completed so far"),
    ]
    pending_actions: Annotated[
        list[str],
        Field(default_factory=list, description="Pending actions scheduled for execution"),
    ]
    next_action: Annotated[
        str,
        Field(min_length=1, description="Immediate next action the resuming agent must take"),
    ]
    blockers: Annotated[
        list[str],
        Field(
            default_factory=list, description="Known blockers or missing inputs preventing progress"
        ),
    ]
    decision_refs: Annotated[
        list[str],
        Field(default_factory=list, description="IDs of decision records guiding this checkpoint"),
    ]
    artifact_refs: Annotated[
        list[str],
        Field(default_factory=list, description="IDs of artifact references relevant to this work"),
    ]
    base_revision: Annotated[
        str,
        Field(
            min_length=1, description="Base commit hash or state revision this checkpoint builds on"
        ),
    ]
    created_by: Annotated[
        str,
        Field(
            min_length=1,
            max_length=128,
            description="Agent or user ID that generated the checkpoint",
        ),
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]

    # Optional fields
    environment_description: Annotated[
        str | None,
        Field(
            default=None,
            description="Details of execution environment (Python 3.12, Windows, etc.)",
        ),
    ] = None
    verification_results: Annotated[
        dict[str, Any],
        Field(
            default_factory=dict, description="Test results, lint outcomes, or validation status"
        ),
    ]
    summary: Annotated[
        str | None,
        Field(default=None, description="Executive narrative summary of the current work state"),
    ] = None
    context_refs: Annotated[
        list[str],
        Field(default_factory=list, description="IDs of knowledge records or context references"),
    ]

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


class CommitChange(BMSRecord):
    """Represents a discrete mutation in a memory commit."""

    operation: Annotated[CommitOperation, Field(description="Mutation operation type")]
    record_id: Annotated[str, Field(min_length=1, max_length=128, description="Target record ID")]
    record_type: Annotated[
        str, Field(min_length=1, max_length=64, description="Target record type name")
    ]
    before_revision: Annotated[
        str | None,
        Field(default=None, description="State hash or revision before change; null for creates"),
    ] = None
    after_revision: Annotated[
        str | None,
        Field(default=None, description="State hash or revision after change; null for deletes"),
    ] = None


class MemoryCommit(BMSRecord):
    """Structured representation of a point-in-time memory state snapshot."""

    record_type: Literal["commit"] = "commit"
    project_id: Annotated[
        str, Field(min_length=1, max_length=128, description="ID of associated project")
    ]
    parent_commit_ids: Annotated[
        list[str],
        Field(default_factory=list, description="List of parent commit IDs in the DAG"),
    ]
    author_id: Annotated[
        str, Field(min_length=1, max_length=128, description="Agent ID or user ID author")
    ]
    message: Annotated[
        str, Field(min_length=1, max_length=512, description="Commit message summarizing changes")
    ]
    created_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC creation timestamp")
    ]
    changes: Annotated[
        list[CommitChange],
        Field(default_factory=list, description="List of changes in this commit"),
    ]

    @field_validator("created_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)


# Type union representing any BMS record
AnyBMSRecord = (
    Workspace
    | Project
    | KnowledgeRecord
    | DecisionRecord
    | TaskRecord
    | AgentRecord
    | ArtifactReference
    | RelationshipRecord
    | ResumeCheckpoint
    | MemoryCommit
)

RECORD_TYPE_MAP: dict[str, type[BMSRecord]] = {
    "workspace": Workspace,
    "project": Project,
    "knowledge": KnowledgeRecord,
    "decision": DecisionRecord,
    "task": TaskRecord,
    "agent": AgentRecord,
    "artifact": ArtifactReference,
    "relationship": RelationshipRecord,
    "checkpoint": ResumeCheckpoint,
    "commit": MemoryCommit,
}
