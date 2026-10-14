"""Read-only MCP resource definitions for Barsa."""

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.records import RECORD_TYPE_MAP
from barsa.core.config import Settings
from barsa.graph.protocol import GraphProvider
from barsa.storage.protocol import StorageProvider
from barsa.versioning.engine import VersionControlEngine


def generate_bms_schema_bundle() -> dict[str, Any]:
    """Generate in-memory JSON schemas for all BMS record types."""
    schemas = {}
    for name, model_cls in RECORD_TYPE_MAP.items():
        schemas[name] = model_cls.model_json_schema()
    schemas["package"] = BarsaMemoryPackage.model_json_schema()
    return schemas


def register_resources(
    server: MCPServer,
    settings: Settings,
    storage: StorageProvider,
    vc: VersionControlEngine,
    graph: GraphProvider,
) -> None:
    """Register all standard read-only MCP resources on the server instance."""

    @server.resource("barsa://system/info")
    def get_system_info() -> str:
        """System information, active providers, and operational configuration."""
        info = {
            "application": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment.value,
            "storage_provider": settings.storage_provider.value,
            "graph_enabled": settings.graph_enabled,
            "graph_provider": getattr(graph, "provider_name", "unknown"),
            "graph_available": graph.is_available(),
        }
        return json.dumps(info, indent=2)

    @server.resource("barsa://bms/schema/version")
    def get_bms_version() -> str:
        """Current supported Barsa Memory Standard (BMS) version."""
        return "0.1.0"

    @server.resource("barsa://bms/schema/records")
    def get_bms_records_schema() -> str:
        """Comprehensive JSON Schema definitions for BMS core record types."""
        schemas = generate_bms_schema_bundle()
        return json.dumps(schemas, indent=2)

    @server.resource("barsa://projects/{project_id}/overview")
    def get_project_overview_resource(project_id: str) -> str:
        """Project identity, current main commit, and summary counts."""
        proj = storage.get_project(project_id)
        if not proj:
            return json.dumps({"error": f"Project '{project_id}' not found."})

        head_commit = None
        try:
            main_b = vc.get_branch(project_id, "main")
            if main_b:
                head_commit = main_b.head_commit_id
        except Exception:
            pass

        data: dict[str, Any] = {
            "project_id": proj.id,
            "project_name": proj.name,
            "workspace_id": proj.workspace_id,
            "status": proj.status.value if hasattr(proj.status, "value") else str(proj.status),
            "description": proj.description,
            "head_commit": head_commit,
        }
        return json.dumps(data, indent=2)

    @server.resource("barsa://projects/{project_id}/checkpoints/latest")
    def get_latest_checkpoint_resource(project_id: str) -> str:
        """Latest checkpoint record for the specified project."""
        proj = storage.get_project(project_id)
        if not proj:
            return json.dumps({"error": f"Project '{project_id}' not found."})

        cps = storage.list_records(project_id, record_type="checkpoint")
        if not cps:
            return json.dumps({"project_id": project_id, "latest_checkpoint": None})

        matching = [(c[0] if isinstance(c, tuple) else c).model_dump(mode="json") for c in cps]
        matching.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return json.dumps({"project_id": project_id, "latest_checkpoint": matching[0]}, indent=2)
