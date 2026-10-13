"""Portable Barsa Memory Package definition (BMS v0.1)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator

from barsa.bms.base import BMS_FORMAT_IDENTIFIER, BMS_VERSION, BMSBaseModel, utc_now
from barsa.bms.records import (
    AgentRecord,
    ArtifactReference,
    DecisionRecord,
    KnowledgeRecord,
    MemoryCommit,
    Project,
    RelationshipRecord,
    ResumeCheckpoint,
    TaskRecord,
    Workspace,
)


class PackageRecords(BMSBaseModel):
    """Collection of categorized BMS records contained within a package."""

    knowledge: Annotated[list[KnowledgeRecord], Field(default_factory=list)]
    decisions: Annotated[list[DecisionRecord], Field(default_factory=list)]
    tasks: Annotated[list[TaskRecord], Field(default_factory=list)]
    agents: Annotated[list[AgentRecord], Field(default_factory=list)]
    artifacts: Annotated[list[ArtifactReference], Field(default_factory=list)]
    checkpoints: Annotated[list[ResumeCheckpoint], Field(default_factory=list)]


class BarsaMemoryPackage(BMSBaseModel):
    """Standard portable container for cross-agent project memory exchange."""

    format: Annotated[
        Literal[BMS_FORMAT_IDENTIFIER],
        Field(default=BMS_FORMAT_IDENTIFIER, description="Format identifier constant"),
    ]
    bms_version: Annotated[str, Field(default=BMS_VERSION, description="BMS version identifier")]
    exported_at: Annotated[
        datetime, Field(default_factory=utc_now, description="UTC export timestamp")
    ]
    workspace: Annotated[Workspace, Field(description="Root workspace record")]
    project: Annotated[Project, Field(description="Associated project record")]
    records: Annotated[
        PackageRecords, Field(default_factory=PackageRecords, description="All project records")
    ]
    relationships: Annotated[
        list[RelationshipRecord],
        Field(default_factory=list, description="Graph relationships between records"),
    ]
    latest_checkpoint_id: Annotated[
        str | None,
        Field(default=None, description="Optional ID of the most recent active resume checkpoint"),
    ] = None
    commits: Annotated[
        list[MemoryCommit],
        Field(default_factory=list, description="Optional chronological memory commits"),
    ]

    @field_validator("bms_version")
    @classmethod
    def check_bms_version(cls, v: str) -> str:
        if v != BMS_VERSION:
            msg = f"Unsupported BMS package version '{v}'. Supported version is '{BMS_VERSION}'"
            raise ValueError(msg)
        return v

    @field_validator("exported_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        return cls.ensure_utc(v)
