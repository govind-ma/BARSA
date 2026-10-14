"""FastMCP / MCPServer initialization and tool registration for Barsa."""

import logging
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from barsa.core.config import Settings, get_settings
from barsa.graph.factory import get_graph_provider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.protocol import GraphProvider
from barsa.graph.retrieval import GraphRetrievalService
from barsa.mcp.errors import BarsaMCPError
from barsa.mcp.prompts import register_prompts
from barsa.mcp.resources import register_resources
from barsa.mcp.tools import (
    commit_tool,
    get_checkpoint_tool,
    get_diff_tool,
    get_graph_context_tool,
    get_history_tool,
    get_memory_tool,
    get_project_tool,
    list_conflicts_tool,
    list_projects_tool,
    propose_changes_tool,
    resume_tool,
    search_memory_tool,
)
from barsa.storage.factory import get_storage_provider
from barsa.storage.protocol import StorageProvider
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine

logger = logging.getLogger("barsa.mcp.server")


def create_mcp_server(
    settings: Settings | None = None,
    storage: StorageProvider | None = None,
    vc: VersionControlEngine | None = None,
    worker: GraphProjectionWorker | None = None,
    retrieval: GraphRetrievalService | None = None,
    graph: GraphProvider | None = None,
) -> MCPServer:
    """Create and configure the Barsa MCP server with all tools, resources, and prompts."""
    current_settings = settings or get_settings()

    # 1. Initialize core storage & version control
    if storage is None:
        storage = get_storage_provider(current_settings)
    if not isinstance(storage, SQLiteStorageProvider):
        raise RuntimeError("Barsa MCP server currently requires SQLiteStorageProvider.")

    if vc is None:
        vc = VersionControlEngine(storage)

    # 2. Initialize knowledge graph and projection worker
    if graph is None:
        graph = get_graph_provider(current_settings)
    if worker is None:
        worker = GraphProjectionWorker(storage, graph)
    if retrieval is None:
        retrieval = GraphRetrievalService(graph)

    # 3. Create MCPServer instance
    server = MCPServer(
        name="barsa-mcp-server",
        version=current_settings.app_version,
        description="Universal AI Memory and Collaboration Infrastructure MCP Server",
    )

    # =========================================================================
    # Register 12 Standard MCP Tools
    # =========================================================================

    @server.tool(
        name="barsa_list_projects",
        description="List projects accessible to the current identity with their status and latest main commit.",
    )
    def barsa_list_projects(
        workspace_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        try:
            return list_projects_tool(
                storage=storage,
                vc=vc,
                workspace_id=workspace_id,
                limit=limit,
                offset=offset,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_list_projects")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_project",
        description="Retrieve project overview, goals, current status, metadata, and current main revision.",
    )
    def barsa_get_project(project_id: str) -> dict[str, Any]:
        try:
            return get_project_tool(storage=storage, vc=vc, project_id=project_id)
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_project")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_search_memory",
        description="Search structured memory and graph entities for a project using keyword and attribute matching.",
    )
    def barsa_search_memory(
        project_id: str,
        query: str,
        record_types: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        try:
            return search_memory_tool(
                storage=storage,
                worker=worker,
                graph=graph,
                project_id=project_id,
                query=query,
                record_types=record_types,
                limit=limit,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_search_memory")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_memory",
        description="Retrieve an exact memory record by ID, or its historical snapshot at a specific commit.",
    )
    def barsa_get_memory(
        project_id: str,
        record_id: str,
        commit_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            return get_memory_tool(
                storage=storage,
                vc=vc,
                project_id=project_id,
                record_id=record_id,
                commit_id=commit_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_memory")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_checkpoint",
        description="Retrieve the latest relevant checkpoint or an explicitly requested checkpoint for a task.",
    )
    def barsa_get_checkpoint(
        project_id: str,
        task_id: str | None = None,
        checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            return get_checkpoint_tool(
                storage=storage,
                project_id=project_id,
                task_id=task_id,
                checkpoint_id=checkpoint_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_checkpoint")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_resume",
        description="Generate a structured resume package containing project identity, task, checkpoint, decisions, and artifacts.",
    )
    def barsa_resume(
        project_id: str,
        task_id: str | None = None,
        max_context_tokens: int | None = None,
        expected_revision: str | None = None,
    ) -> dict[str, Any]:
        try:
            return resume_tool(
                storage=storage,
                retrieval=retrieval,
                worker=worker,
                vc=vc,
                project_id=project_id,
                task_id=task_id,
                max_context_tokens=max_context_tokens,
                expected_revision=expected_revision,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_resume")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_history",
        description="Retrieve version-control commit history and revision metadata for a branch.",
    )
    def barsa_get_history(
        project_id: str,
        branch: str = "main",
        limit: int = 50,
    ) -> dict[str, Any]:
        try:
            return get_history_tool(
                vc=vc,
                storage=storage,
                project_id=project_id,
                branch=branch,
                limit=limit,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_history")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_diff",
        description="Compute and retrieve structured diff between two commits in project memory.",
    )
    def barsa_get_diff(
        project_id: str,
        from_commit: str,
        to_commit: str,
    ) -> dict[str, Any]:
        try:
            return get_diff_tool(
                vc=vc,
                storage=storage,
                project_id=project_id,
                from_commit=from_commit,
                to_commit=to_commit,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_diff")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_propose_changes",
        description="Validate proposed memory changes and commit to an isolated feature branch without modifying main.",
    )
    def barsa_propose_changes(
        project_id: str,
        branch: str,
        base_commit: str,
        changes: list[dict[str, Any]],
        message: str,
    ) -> dict[str, Any]:
        try:
            return propose_changes_tool(
                storage=storage,
                vc=vc,
                project_id=project_id,
                branch=branch,
                base_commit=base_commit,
                changes=changes,
                message=message,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_propose_changes")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_commit",
        description="Commit validated changes to a branch through the version-control engine with optimistic concurrency.",
    )
    def barsa_commit(
        project_id: str,
        branch: str = "main",
        expected_head: str | None = None,
        changes: list[dict[str, Any]] | None = None,
        message: str = "",
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            return commit_tool(
                storage=storage,
                vc=vc,
                worker=worker,
                project_id=project_id,
                branch=branch,
                expected_head=expected_head,
                changes=changes,
                message=message,
                operation_id=operation_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_commit")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_list_conflicts",
        description="List merge conflicts, divergent branch states, or concurrency issues in project memory.",
    )
    def barsa_list_conflicts(
        project_id: str,
        status: str | None = None,
    ) -> dict[str, Any]:
        try:
            return list_conflicts_tool(
                vc=vc,
                storage=storage,
                project_id=project_id,
                status=status,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_list_conflicts")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_graph_context",
        description="Retrieve relevant graph-connected entities, dependencies, and freshness metadata.",
    )
    def barsa_get_graph_context(
        project_id: str,
        task_id: str | None = None,
        depth: int = 2,
        limit: int = 50,
    ) -> dict[str, Any]:
        try:
            return get_graph_context_tool(
                retrieval=retrieval,
                worker=worker,
                graph=graph,
                storage=storage,
                project_id=project_id,
                task_id=task_id,
                depth=depth,
                limit=limit,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_graph_context")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    # =========================================================================
    # Register Resources & Prompts
    # =========================================================================
    register_resources(server, current_settings, storage, vc, graph)
    register_prompts(server)

    logger.info("Barsa MCP server created with 12 tools, 5 resources, and 3 prompts.")
    return server
