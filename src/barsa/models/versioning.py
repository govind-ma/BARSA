"""Domain models and schemas for Git-style Memory Version Control (Phase 4)."""

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from barsa.bms.base import BMS_VERSION, utc_now


class AuthorType(StrEnum):
    AGENT = "agent"
    HUMAN = "human"


class ChangeOperation(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class ProposalStatus(StrEnum):
    OPEN = "open"
    MERGED = "merged"
    REJECTED = "rejected"
    CLOSED = "closed"


class ReviewStatus(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    COMMENTED = "commented"
    REJECTED = "rejected"


class ConflictStatus(StrEnum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ConflictType(StrEnum):
    SAME_FIELD_UPDATE = "same_field_update"
    DELETE_VS_UPDATE = "delete_vs_update"
    INCOMPATIBLE_RELATIONSHIP = "incompatible_relationship"
    RECORD_COLLISION = "record_collision"


class MemoryChange(BaseModel):
    """Describes a single atomic mutation to a BMS record in a commit."""

    model_config = ConfigDict(extra="forbid")

    operation: ChangeOperation
    record_id: str
    record_type: str
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    before_hash: str | None = None
    after_hash: str | None = None

    @field_validator("before_hash", mode="before")
    @classmethod
    def compute_before_hash(cls, v: str | None, info: Any) -> str | None:
        if v:
            return v
        b_state = info.data.get("before_state")
        if b_state is not None:
            canonical = json.dumps(b_state, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return None

    @field_validator("after_hash", mode="before")
    @classmethod
    def compute_after_hash(cls, v: str | None, info: Any) -> str | None:
        if v:
            return v
        a_state = info.data.get("after_state")
        if a_state is not None:
            canonical = json.dumps(a_state, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return None


class Commit(BaseModel):
    """Immutable Git-inspired memory commit entity."""

    model_config = ConfigDict(extra="forbid")

    commit_id: str
    project_id: str
    parent_commit_ids: list[str]
    author_id: str
    author_type: AuthorType
    message: str
    created_at: datetime
    changes: list[MemoryChange]
    resulting_state_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    bms_version: str = Field(default=BMS_VERSION)


def compute_commit_id(
    project_id: str,
    parent_commit_ids: list[str],
    author_id: str,
    author_type: AuthorType,
    message: str,
    created_at: datetime,
    changes: list[MemoryChange],
    resulting_state_hash: str,
    metadata: dict[str, Any],
    bms_version: str = BMS_VERSION,
) -> str:
    """Compute deterministic SHA-256 commit ID from canonical commit content."""
    # Ensure parents are in stable sorted order for multi-parent merges
    parents = sorted(parent_commit_ids)
    changes_dict = []
    for c in changes:
        cd = c.model_dump(mode="json")
        if cd.get("after_state") and not cd.get("after_hash"):
            canonical = json.dumps(cd["after_state"], sort_keys=True, separators=(",", ":"))
            cd["after_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if cd.get("before_state") and not cd.get("before_hash"):
            canonical = json.dumps(cd["before_state"], sort_keys=True, separators=(",", ":"))
            cd["before_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        changes_dict.append(cd)
    # Sort changes by record_id and operation
    changes_dict.sort(key=lambda x: (x["record_id"], x["operation"]))

    iso_created = created_at.astimezone(UTC).isoformat()

    canonical_obj = {
        "bms_version": bms_version,
        "project_id": project_id,
        "parent_commit_ids": parents,
        "author_id": author_id,
        "author_type": author_type.value,
        "message": message,
        "created_at": iso_created,
        "changes": changes_dict,
        "resulting_state_hash": resulting_state_hash,
        "metadata": metadata,
    }
    canonical_json = json.dumps(canonical_obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class Branch(BaseModel):
    """Named reference pointing to a commit HEAD in a project DAG."""

    model_config = ConfigDict(extra="forbid")

    name: str
    project_id: str
    head_commit_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FieldDiff(BaseModel):
    """JSON-pointer field difference within a modified record."""

    path: str
    before: Any = None
    after: Any = None


class RecordDiff(BaseModel):
    """Structured record-level diff between two commit states."""

    record_id: str
    record_type: str
    operation: ChangeOperation
    fields: list[FieldDiff] = Field(default_factory=list)
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None


class CommitDiff(BaseModel):
    """Complete diff representation between two commits or revisions."""

    from_commit_id: str | None
    to_commit_id: str
    project_id: str
    added_records: list[str] = Field(default_factory=list)
    removed_records: list[str] = Field(default_factory=list)
    modified_records: list[str] = Field(default_factory=list)
    changes: list[RecordDiff] = Field(default_factory=list)


class ConflictRecord(BaseModel):
    """Persisted record of an unresolved or resolved merge conflict."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str
    project_id: str
    proposal_id: str | None = None
    source_branch: str
    target_branch: str
    affected_record_id: str
    conflict_type: ConflictType
    base_value: Any = None
    source_value: Any = None
    target_value: Any = None
    resolution_status: ConflictStatus = Field(default=ConflictStatus.UNRESOLVED)
    resolved_by: str | None = None
    resolution_timestamp: datetime | None = None
    resolved_value: Any = None


class ReviewComment(BaseModel):
    """Feedback or review comment on a merge proposal or changed record."""

    model_config = ConfigDict(extra="forbid")

    comment_id: str
    proposal_id: str
    author_id: str
    author_type: AuthorType
    content: str
    record_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class MergeProposal(BaseModel):
    """Proposal to merge a source branch into a target branch."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    project_id: str
    title: str
    description: str = ""
    source_branch: str
    target_branch: str
    source_head: str
    target_head: str
    author_id: str
    status: ProposalStatus = Field(default=ProposalStatus.OPEN)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    comments: list[ReviewComment] = Field(default_factory=list)
    reviews: list[dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# API Request / Response Models
# =============================================================================


class CommitCreateRequest(BaseModel):
    branch: str = "main"
    changes: list[MemoryChange]
    message: str = Field(..., min_length=1)
    author_id: str = Field(..., min_length=1)
    author_type: AuthorType = Field(default=AuthorType.AGENT)
    expected_head_commit_id: str | None = None
    parent_commit_ids: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BranchCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    start_commit_id: str | None = None


class MergeProposalCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    source_branch: str = Field(..., min_length=1)
    target_branch: str = Field(..., min_length=1)
    author_id: str = Field(..., min_length=1)


class ReviewCommentCreateRequest(BaseModel):
    author_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    author_type: AuthorType = Field(default=AuthorType.AGENT)
    record_id: str | None = None


class ReviewSubmitRequest(BaseModel):
    reviewer_id: str = Field(..., min_length=1)
    status: ReviewStatus
    summary: str | None = None
    reviewer_type: AuthorType = Field(default=AuthorType.HUMAN)


class ConflictResolveRequest(BaseModel):
    resolved_by: str = Field(..., min_length=1)
    resolved_value: dict[str, Any] | None = None


class MergeExecuteRequest(BaseModel):
    author_id: str = Field(..., min_length=1)


class RestoreRequest(BaseModel):
    target_branch: str = "main"
    restore_from_commit_id: str = Field(..., min_length=1)
    author_id: str = Field(..., min_length=1)
    message: str | None = None
