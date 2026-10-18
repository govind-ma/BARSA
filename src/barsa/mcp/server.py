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
    build_context_tool,
    claim_task_tool,
    commit_tool,
    get_assignment_tool,
    get_available_tasks_tool,
    get_checkpoint_tool,
    get_collaboration_messages_tool,
    get_diff_tool,
    get_graph_context_tool,
    get_history_tool,
    get_memory_tool,
    get_project_tool,
    graph_resume_tool,
    list_conflicts_tool,
    list_projects_tool,
    propose_changes_tool,
    register_agent_tool,
    report_issue_tool,
    request_help_tool,
    resume_tool,
    search_memory_tool,
    submit_task_result_tool,
    update_task_progress_tool,
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
        name="barsa_graph_resume",
        description="Execute FalkorDB graph-powered memory reasoning, multi-hop dependency traversal, next-task discovery, and agent capability matching.",
    )
    def barsa_graph_resume(
        project_id: str,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            return graph_resume_tool(
                storage=storage,
                retrieval=retrieval,
                worker=worker,
                project_id=project_id,
                agent_id=agent_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_graph_resume")
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

    @server.tool(
        name="barsa_build_context",
        description="Build an optimized, token-budgeted, graph-aware context package for AI agent task continuation.",
    )
    def barsa_build_context(
        project_id: str,
        task_id: str | None = None,
        query: str | None = None,
        max_context_tokens: int = 4000,
        context_level: str = "adaptive",
        known_revision: str | None = None,
        target_model: str | None = None,
    ) -> dict[str, Any]:
        try:
            return build_context_tool(
                storage=storage,
                vc=vc,
                retrieval=retrieval,
                project_id=project_id,
                task_id=task_id,
                query=query,
                max_context_tokens=max_context_tokens,
                context_level=context_level,
                known_revision=known_revision,
                target_model=target_model,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_build_context")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    # =========================================================================
    # Multi-Agent Coordination MCP Tools (Phase 9)
    # =========================================================================

    @server.tool(
        name="barsa_register_agent",
        description="Register an agent's identity, capabilities, and tools with the Barsa coordinator.",
    )
    def barsa_register_agent(
        agent_id: str,
        display_name: str,
        provider: str,
        model: str | None = None,
        claimed_capabilities: list[str] | None = None,
        verified_capabilities: list[str] | None = None,
        supported_tools: list[str] | None = None,
        allowed_projects: list[str] | None = None,
        maximum_concurrent_tasks: int = 2,
    ) -> dict[str, Any]:
        try:
            return register_agent_tool(
                storage=storage,
                vc=vc,
                agent_id=agent_id,
                display_name=display_name,
                provider=provider,
                model=model,
                claimed_capabilities=claimed_capabilities,
                verified_capabilities=verified_capabilities,
                supported_tools=supported_tools,
                allowed_projects=allowed_projects,
                maximum_concurrent_tasks=maximum_concurrent_tasks,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_register_agent")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_available_tasks",
        description="Discover tasks ready to be claimed within a project.",
    )
    def barsa_get_available_tasks(
        project_id: str,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return get_available_tasks_tool(
                storage=storage,
                vc=vc,
                project_id=project_id,
                agent_id=agent_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_available_tasks")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_claim_task",
        description="Atomically claim an exclusive task lease and receive a fencing token.",
    )
    def barsa_claim_task(
        task_id: str,
        agent_id: str,
        lease_duration_seconds: int | None = None,
    ) -> dict[str, Any]:
        try:
            return claim_task_tool(
                storage=storage,
                vc=vc,
                task_id=task_id,
                agent_id=agent_id,
                lease_duration_seconds=lease_duration_seconds,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_claim_task")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_update_task_progress",
        description="Report execution progress and renew task lease with a valid fencing token.",
    )
    def barsa_update_task_progress(
        task_id: str,
        agent_id: str,
        lease_token: str,
        message: str,
        progress_percent: float | None = None,
        resource_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return update_task_progress_tool(
                storage=storage,
                vc=vc,
                task_id=task_id,
                agent_id=agent_id,
                lease_token=lease_token,
                message=message,
                progress_percent=progress_percent,
                resource_usage=resource_usage,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_update_task_progress")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_submit_task_result",
        description="Submit completed task results verifying fencing token before committing.",
    )
    def barsa_submit_task_result(
        task_id: str,
        agent_id: str,
        lease_token: str,
        result: dict[str, Any],
        commit_id: str | None = None,
        requires_review: bool | None = None,
        resource_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return submit_task_result_tool(
                storage=storage,
                vc=vc,
                task_id=task_id,
                agent_id=agent_id,
                lease_token=lease_token,
                result=result,
                commit_id=commit_id,
                requires_review=requires_review,
                resource_usage=resource_usage,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_submit_task_result")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_report_issue",
        description="Report an impediment or issue encountered during task execution.",
    )
    def barsa_report_issue(
        project_id: str,
        task_id: str,
        author_agent_id: str,
        title: str,
        description: str,
        evidence: dict[str, Any] | None = None,
        required_capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            return report_issue_tool(
                storage=storage,
                vc=vc,
                project_id=project_id,
                task_id=task_id,
                author_agent_id=author_agent_id,
                title=title,
                description=description,
                evidence=evidence,
                required_capabilities=required_capabilities,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_report_issue")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_request_help",
        description="Request assistance from other agents with specific technical capabilities.",
    )
    def barsa_request_help(
        project_id: str,
        task_id: str,
        requester_agent_id: str,
        required_capabilities: list[str],
        issue_id: str | None = None,
        target_agent_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            return request_help_tool(
                storage=storage,
                vc=vc,
                project_id=project_id,
                task_id=task_id,
                requester_agent_id=requester_agent_id,
                required_capabilities=required_capabilities,
                issue_id=issue_id,
                target_agent_id=target_agent_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_request_help")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_collaboration_messages",
        description="Retrieve the collaboration message stream for a project or specific task.",
    )
    def barsa_get_collaboration_messages(
        project_id: str,
        task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return get_collaboration_messages_tool(
                storage=storage,
                vc=vc,
                project_id=project_id,
                task_id=task_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_collaboration_messages")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_assignment",
        description="Inspect current task assignment, lease token, and expiration status.",
    )
    def barsa_get_assignment(
        task_id: str,
    ) -> dict[str, Any]:
        try:
            return get_assignment_tool(
                storage=storage,
                vc=vc,
                task_id=task_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_assignment")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    # =========================================================================
    # Phase 13: BYOS & Cloud Synchronization Tools
    # =========================================================================
    from barsa.mcp.sync_tools import (
        get_sync_status_tool,
        list_remotes_tool,
        pull_remote_tool,
        push_remote_tool,
    )

    @server.tool(
        name="barsa_list_remotes",
        description="List all configured BYOS remotes (Local, S3) for a project.",
    )
    def barsa_list_remotes(
        project_id: str,
    ) -> list[dict[str, Any]]:
        try:
            return list_remotes_tool(
                storage=storage,
                settings=current_settings,
                project_id=project_id,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_list_remotes")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_get_sync_status",
        description="Inspect synchronization state between local branch and remote repository.",
    )
    async def barsa_get_sync_status(
        remote_id: str,
        branch: str = "main",
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await get_sync_status_tool(
                storage=storage,
                settings=current_settings,
                remote_id=remote_id,
                branch=branch,
                passphrase=passphrase,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_get_sync_status")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_pull_remote",
        description="Pull remote commits and content-addressed records from remote repository.",
    )
    async def barsa_pull_remote(
        remote_id: str,
        branch: str = "main",
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await pull_remote_tool(
                storage=storage,
                settings=current_settings,
                remote_id=remote_id,
                branch=branch,
                passphrase=passphrase,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_pull_remote")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    @server.tool(
        name="barsa_push_remote",
        description="Push local commits and content-addressed records to remote repository.",
    )
    async def barsa_push_remote(
        remote_id: str,
        branch: str = "main",
        force: bool = False,
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await push_remote_tool(
                storage=storage,
                settings=current_settings,
                remote_id=remote_id,
                branch=branch,
                force=force,
                passphrase=passphrase,
            )
        except BarsaMCPError as e:
            raise ToolError(f"[{e.code}] {e.message}") from e
        except Exception as e:
            logger.exception("Unexpected error in barsa_push_remote")
            raise ToolError(f"[INTERNAL_ERROR] {e}") from e

    # =========================================================================
    # Register Resources & Prompts
    # =========================================================================
    register_resources(server, current_settings, storage, vc, graph)
    register_prompts(server)

    logger.info("Barsa MCP server created with tools, resources, and prompts.")
    return server
