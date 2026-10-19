"""API response schemas for health and system status."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Payload returned by the /health endpoint."""

    status: str = Field(default="healthy", description="Service status (e.g., healthy, degraded)")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Running environment")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Current server UTC timestamp")


class PlatformFeatures(BaseModel):
    """Feature support flags across current and future roadmap phases."""

    bms_standard: bool = Field(default=True, description="Barsa Memory Standard (BMS) model specifications")
    local_storage: bool = Field(default=True, description="Local-first data directory support")
    cloud_storage_adapters: bool = Field(default=False, description="Remote S3 / GitHub cloud storage adapters")
    git_versioning: bool = Field(default=False, description="Git-style memory commits and DAG branching")
    falkordb_graph: bool = Field(default=False, description="FalkorDB knowledge graph integration")
    smart_context_engine: bool = Field(default=False, description="Smart Context retrieval engine")
    agent_coordinator: bool = Field(default=False, description="Agent capability coordinator")
    mcp_server: bool = Field(default=False, description="Model Context Protocol (MCP) tool server")


class PlatformInfoResponse(BaseModel):
    """Payload returned by the /api/v1/info endpoint."""

    app_name: str = Field(..., description="Platform name")
    version: str = Field(..., description="Platform version")
    description: str = Field(..., description="Platform description")
    current_phase: str = Field(default="Phase 1: Project Foundation", description="Current development phase")
    storage_provider: str = Field(..., description="Configured storage provider")
    data_dir: str = Field(..., description="Configured local data directory")
    features: PlatformFeatures = Field(..., description="Current supported and roadmap features")
    falkordb_status: str = Field(default="connected", description="FalkorDB connection status")
    documentation_url: str = Field(default="/docs", description="Interactive API documentation path")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional environment metadata")


class ErrorResponse(BaseModel):
    """Standardized error envelope returned on API errors."""

    error: str = Field(..., description="Human-readable error summary")
    code: str = Field(..., description="Machine-readable error code")
    status_code: int = Field(..., description="HTTP status code")
    details: dict[str, Any] = Field(default_factory=dict, description="Detailed contextual diagnostics")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp of the error")
