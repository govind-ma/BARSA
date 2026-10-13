"""Barsa Memory Standard (BMS) core models and metadata schemas.

The BMS defines a provider-independent structured memory format representing
project context, tasks, decisions, and artifacts created across various AI assistants.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryItemType(StrEnum):
    """Categorization of structured memory records."""

    TASK = "task"
    DECISION = "decision"
    CONTEXT = "context"
    ARTIFACT = "artifact"
    CONVERSATION = "conversation"
    NOTE = "note"


class AgentIdentity(BaseModel):
    """Identity of the AI assistant or user that generated the memory record."""

    provider: str = Field(..., description="Provider name (e.g., anthropic, openai, google, local)")
    model: str = Field(..., description="Model identifier (e.g., claude-3-7-sonnet, gpt-4o)")
    role: str = Field(default="assistant", description="Role (e.g., architect, coder, reviewer, user)")
    agent_id: str | None = Field(default=None, description="Optional unique agent session ID")


class MemoryItem(BaseModel):
    """A single atomic unit of shared project memory in the BMS standard."""

    id: UUID = Field(default_factory=uuid4, description="Unique memory item ID")
    project_id: str = Field(..., description="Project identifier")
    type: MemoryItemType = Field(..., description="Type of memory entry")
    title: str = Field(..., min_length=1, max_length=256, description="Human-readable title")
    content: str = Field(..., description="Memory body text or serialized markdown/JSON")
    author: AgentIdentity = Field(..., description="Agent or user author identity")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update timestamp")


class MemoryCommit(BaseModel):
    """A point-in-time snapshot/commit of memory state (for Git-inspired versioning)."""

    commit_id: UUID = Field(default_factory=uuid4, description="Unique commit ID")
    project_id: str = Field(..., description="Project identifier")
    parent_commit_id: UUID | None = Field(default=None, description="Parent commit ID in DAG")
    message: str = Field(..., min_length=1, max_length=512, description="Commit message summarizing changes")
    author: AgentIdentity = Field(..., description="Author of the commit")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Commit timestamp")
    item_count: int = Field(default=0, ge=0, description="Number of items included in this commit")
