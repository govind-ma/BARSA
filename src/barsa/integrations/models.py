"""Data models and evaluation structures for Phase 12 Cross-AI Integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class TransportType(StrEnum):
    """Supported transport mechanisms between AI clients and Barsa."""

    MCP_STREAM = "mcp_stream"
    MCP_STDIO = "mcp_stdio"
    DIRECT_API = "direct_api"


class AIProvider(StrEnum):
    """Recognized AI providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class ClientSessionConfig:
    """Configuration for an independent AI client session."""

    client_id: str
    provider: AIProvider = AIProvider.ANTHROPIC
    model: str = "claude-3-5-sonnet"
    api_key: str | None = None
    transport: TransportType = TransportType.MCP_STREAM
    environment: str = "local"


@dataclass
class ClientHandoffContext:
    """Standardized memory context package delivered to an incoming AI agent."""

    project_id: str
    project_name: str
    latest_checkpoint: dict[str, Any] | None
    next_task: str | None
    completed_actions: list[str]
    pending_actions: list[str]
    blockers: list[str]
    recent_decisions: list[dict[str, Any]]
    relevant_artifacts: list[dict[str, Any]]
    token_budget: int
    total_tokens: number_or_int = 0
    counting_method: str = "cl100k_base"
    rendered_context: str = ""
    graph_freshness: str = "verified"


# Type alias for token count
number_or_int = int


@dataclass
class TaskContinuationResult:
    """Structured record of task execution and continuation by a receiving agent."""

    agent_id: str
    provider: str
    model: str
    starting_checkpoint_id: str | None
    task_id: str
    task_title: str
    action_performed: str
    test_results: dict[str, Any]
    new_commit_hash: str
    new_checkpoint_id: str
    execution_time_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ContinuityEvaluationRubric:
    """Rubric evaluating the depth and accuracy of agent context continuation."""

    goal_identification: bool
    architecture_identification: bool
    completed_work_identification: bool
    next_task_identification: bool
    artifact_verification: bool
    no_incorrect_assumptions: bool
    task_continuation_success: bool
    score_percentage: float
    notes: list[str] = field(default_factory=list)


@dataclass
class TokenBenchmarkResult:
    """Benchmark comparing context efficiency across three distinct prompting conditions."""

    condition: str  # "full_history", "manual_summary", "barsa_optimized"
    input_tokens: int
    output_tokens: int
    context_retrieval_tokens: int
    total_tokens: int
    latency_seconds: float
    task_continuation_success: bool
    missing_critical_info: list[str] = field(default_factory=list)
