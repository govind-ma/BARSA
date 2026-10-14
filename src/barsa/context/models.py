"""Pydantic models and schemas for the Barsa Smart Context Engine (Phase 8)."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContextLevel(StrEnum):
    """Supported context retrieval levels."""

    ESSENTIAL = "essential"  # Level 1: Project identity, active task, latest checkpoint, blockers, approved decisions
    WORKING = "working"  # Level 2: + Dependencies, requirements, working knowledge, artifacts
    DETAILED = "detailed"  # Level 3: + Historical commits, older checkpoints, superseded decisions
    ADAPTIVE = "adaptive"  # Dynamic selection based on query, budget, and task state


class CompletenessStatus(StrEnum):
    """Context package completeness indicator."""

    SUFFICIENT = "sufficient"  # All required and relevant context fits within the budget
    PARTIAL = "partial"  # Essential context included, but some optional relevant records were omitted
    INSUFFICIENT = "insufficient"  # Budget too small even for mandatory Level 1 essential context
    STALE = "stale"  # Context built while graph projection or underlying cache was lagging behind HEAD


class ContextRequest(BaseModel):
    """Validated request model for building an optimized context package."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_\-\.]{1,128}$",
        description="Target project identifier",
    )
    task_id: str | None = Field(
        default=None,
        max_length=128,
        description="Optional active task ID to anchor retrieval context",
    )
    query: str | None = Field(
        default=None,
        max_length=2000,
        description="Natural language query or intent to focus relevance ranking",
    )
    max_context_tokens: int = Field(
        default=4000,
        ge=100,
        le=128000,
        description="Strict upper bound on total context tokens",
    )
    context_level: ContextLevel = Field(
        default=ContextLevel.ADAPTIVE,
        description="Desired retrieval depth level",
    )
    include_history: bool = Field(
        default=False,
        description="Whether to include historical commits and superseded records",
    )
    known_revision: str | None = Field(
        default=None,
        max_length=128,
        description="Commit ID cached by client for incremental delta synchronization",
    )
    target_model: str | None = Field(
        default=None,
        max_length=64,
        description="Optional model identifier for specialized tokenization (e.g. gpt-4o, claude-3-7-sonnet)",
    )
    reserved_overhead_tokens: int = Field(
        default=200,
        ge=0,
        le=5000,
        description="Tokens reserved for JSON framing and model response margin",
    )


class TokenUsageMetadata(BaseModel):
    """Detailed token usage report and estimation metadata."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(..., ge=0, description="Measured or estimated token count")
    budget: int = Field(..., ge=1, description="Allocated max token budget")
    method: str = Field(..., description="Method used: exact or estimated")
    tokenizer: str = Field(..., description="Tokenizer identifier")
    reserved_margin: int = Field(default=0, ge=0, description="Tokens reserved for response overhead")
    utilization_percent: float = Field(..., ge=0.0, description="Percentage of budget used (count / budget * 100)")


class RankingExplanation(BaseModel):
    """Algorithmic ranking explanation for an included or candidate record."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    record_type: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class IncrementalSyncMetadata(BaseModel):
    """Metadata regarding incremental revision synchronization."""

    model_config = ConfigDict(extra="forbid")

    is_incremental: bool
    known_revision: str | None = None
    authoritative_revision: str
    rebase_required: bool = False
    added_records: list[str] = Field(default_factory=list)
    modified_records: list[str] = Field(default_factory=list)
    deleted_records: list[str] = Field(default_factory=list)
    details: str = ""


class BarsaContextPackage(BaseModel):
    """Structured, token-optimized context package (BMS Context Package v0.1)."""

    model_config = ConfigDict(extra="forbid")

    context_format_version: str = Field(default="0.1", description="Context specification version")
    project_id: str
    authoritative_commit: str
    task_id: str | None = None
    goal: str = ""

    # Level 1 — Essential Context
    current_task: dict[str, Any] | None = None
    latest_checkpoint: dict[str, Any] | None = None
    completed: list[str] = Field(default_factory=list)
    pending: list[str] = Field(default_factory=list)
    next_action: str | None = None
    blockers: list[str] = Field(default_factory=list)
    approved_decisions: list[dict[str, Any]] = Field(default_factory=list)

    # Level 2 — Relevant Working Knowledge
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    working_knowledge: list[dict[str, Any]] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    # Level 3 — Historical Context (on request)
    historical_context: list[dict[str, Any]] = Field(default_factory=list)

    # Budget & Omission Information
    omitted_record_refs: list[str] = Field(default_factory=list)
    ranking_explanations: list[RankingExplanation] = Field(default_factory=list)
    incremental_sync: IncrementalSyncMetadata | None = None

    # Quality, Token & Completeness Metadata
    token_usage: TokenUsageMetadata
    completeness: CompletenessStatus
    completeness_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ContextEstimateResponse(BaseModel):
    """Response returned by token estimation endpoint."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    estimated_tokens: int
    budget: int
    fits_budget: bool
    tokenizer: str
    estimation_method: str
    candidate_records_count: int
    mandatory_tokens: int
    recommended_level: ContextLevel


class ContextStatusResponse(BaseModel):
    """Response returned by context status endpoint."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    authoritative_commit: str
    graph_projection_status: str
    applied_graph_commit: str | None = None
    is_graph_fresh: bool = True
    total_records_count: int = 0
    active_tasks_count: int = 0
    approved_decisions_count: int = 0
    latest_checkpoint_id: str | None = None
