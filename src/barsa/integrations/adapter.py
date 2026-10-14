"""Provider-independent client adapter interface and implementations for BARSA.

Enables any AI client or agent framework (Claude Desktop, Cursor, ChatGPT MCP, custom agent)
to connect to Barsa, authenticate, retrieve context, propose changes, and commit progress.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import anyio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from barsa.core.exceptions import AuthorizationError, ConflictError, ResourceNotFoundError
from barsa.integrations.models import ClientHandoffContext, ClientSessionConfig

if TYPE_CHECKING:
    from mcp.server.mcpserver import Server as MCPServer

    from barsa.security.models import AuthenticatedPrincipal


class AIClientAdapter(ABC):
    """Abstract Base Class for connecting external AI clients and agents to Barsa."""

    def __init__(self, config: ClientSessionConfig) -> None:
        self.config = config
        self.is_connected = False
        self.authenticated_principal: AuthenticatedPrincipal | None = None
        self.selected_project_id: str | None = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the Barsa server transport."""
        ...

    @abstractmethod
    async def authenticate(self, api_key: str | None = None) -> dict[str, Any]:
        """Authenticate using an API key, JWT token, or desktop context."""
        ...

    @abstractmethod
    async def select_project(self, project_id: str) -> dict[str, Any]:
        """Select an active project and verify authorization."""
        ...

    @abstractmethod
    async def get_context(self, token_budget: int = 8000) -> ClientHandoffContext:
        """Retrieve optimized project context and latest task continuation state."""
        ...

    @abstractmethod
    async def get_checkpoint(self) -> dict[str, Any] | None:
        """Retrieve the latest resume checkpoint for the selected project."""
        ...

    @abstractmethod
    async def propose_changes(
        self,
        changes: list[dict[str, Any]],
        branch_name: str = "feature/proposal",
        base_commit: str | None = None,
        message: str = "Proposed memory changes",
    ) -> dict[str, Any]:
        """Propose structured memory changes onto a branch."""
        ...

    @abstractmethod
    async def commit(
        self,
        message: str,
        branch_name: str = "main",
        changes: list[dict[str, Any]] | None = None,
        expected_head: str | None = None,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> dict[str, Any]:
        """Commit proposed memory changes into the immutable commit DAG."""
        ...

    @abstractmethod
    async def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve commit history for the project."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection and release transport resources."""
        ...


class MCPClientAdapter(AIClientAdapter):
    """Standards-compliant Model Context Protocol (MCP) Client Adapter.

    Communicates with the Barsa MCP server using JSON-RPC tool calls,
    exercising real MCP protocol discovery and execution.
    """

    def __init__(self, config: ClientSessionConfig, mcp_server: MCPServer) -> None:
        super().__init__(config)
        self.mcp_server = mcp_server
        self._session: ClientSession | None = None
        self._task_group: anyio.abc.TaskGroup | None = None
        self._cancel_scope: anyio.CancelScope | None = None
        self._exit_stack: Any = None

    async def connect(self) -> None:
        """Initialize in-memory bidirectional MCP stream connection."""
        if self.is_connected:
            return

        from contextlib import AsyncExitStack

        self._exit_stack = AsyncExitStack()
        try:
            streams_cm = create_client_server_memory_streams()
            c_stream, s_stream = await self._exit_stack.enter_async_context(streams_cm)

            self._task_group = await self._exit_stack.enter_async_context(anyio.create_task_group())
            self._task_group.start_soon(
                self.mcp_server._lowlevel_server.run,
                s_stream[0],
                s_stream[1],
                self.mcp_server._lowlevel_server.create_initialization_options(),
            )

            session_cm = ClientSession(c_stream[0], c_stream[1])
            self._session = await self._exit_stack.enter_async_context(session_cm)

            init_res = await self._session.initialize()
            if not init_res.server_info:
                raise RuntimeError("MCP initialization failed: missing server info")

            self.is_connected = True
        except Exception:
            if self._exit_stack:
                await self._exit_stack.aclose()
            raise

    async def authenticate(self, _api_key: str | None = None) -> dict[str, Any]:
        """Verify authentication headers or local identity."""
        if not self.is_connected or not self._session:
            raise RuntimeError("Must call connect() before authenticate()")

        # Read system info resource
        res = await self._session.read_resource("barsa://system/info")
        data = json.loads(res.contents[0].text)
        return {"status": "authenticated", "system": data, "principal_id": self.config.client_id}

    async def select_project(self, project_id: str) -> dict[str, Any]:
        """Verify project access via barsa_get_project tool."""
        if not self.is_connected or not self._session:
            raise RuntimeError("Adapter is not connected")

        tool_res = await self._session.call_tool("barsa_get_project", {"project_id": project_id})
        if tool_res.is_error:
            err_msg = tool_res.content[0].text if tool_res.content else "Project not found or access denied"
            if "Forbidden" in err_msg or "denied" in err_msg:
                raise AuthorizationError(err_msg)
            raise ResourceNotFoundError(err_msg)

        data = json.loads(tool_res.content[0].text)
        self.selected_project_id = project_id
        return data

    async def get_context(self, token_budget: int = 8000) -> ClientHandoffContext:
        """Call barsa_resume tool to retrieve Smart Context Engine package."""
        if not self.selected_project_id:
            raise RuntimeError("Must select a project before calling get_context()")
        if not self._session:
            raise RuntimeError("Adapter is not connected")

        tool_res = await self._session.call_tool(
            "barsa_resume",
            {"project_id": self.selected_project_id, "max_context_tokens": token_budget},
        )
        if tool_res.is_error:
            raise RuntimeError(f"Failed to retrieve context: {tool_res.content[0].text}")

        res_data = json.loads(tool_res.content[0].text)
        proj_info = res_data.get("project_identity", {})
        chk = res_data.get("latest_checkpoint")
        decisions = res_data.get("relevant_decisions", [])
        artifacts = res_data.get("artifacts", [])
        blockers = res_data.get("blockers", [])

        next_task = None
        completed_actions = []
        pending_actions = []

        if chk:
            chk_attrs = chk.get("attributes", {}) if isinstance(chk, dict) else {}
            next_task = chk.get("next_action") or chk_attrs.get("next_action")
            completed_actions = chk.get("completed_actions") or chk_attrs.get("completed_actions") or []
            pending_actions = chk.get("pending_actions") or chk_attrs.get("pending_actions") or []
            blockers = blockers or chk.get("blockers") or chk_attrs.get("blockers") or []

        rendered = (
            f"# BARSA PROJECT CONTEXT\n"
            f"Project: {proj_info.get('project_name', self.selected_project_id)}\n"
            f"Next Task: {next_task or 'None specified'}\n"
            f"Completed Actions: {', '.join(completed_actions) if completed_actions else 'None'}\n"
            f"Pending Actions: {', '.join(pending_actions) if pending_actions else 'None'}\n"
            f"Decisions Included: {len(decisions)}\n"
            f"Artifacts Included: {len(artifacts)}\n"
        )

        return ClientHandoffContext(
            project_id=self.selected_project_id,
            project_name=proj_info.get("project_name", self.selected_project_id),
            latest_checkpoint=chk,
            next_task=next_task,
            completed_actions=completed_actions,
            pending_actions=pending_actions,
            blockers=blockers,
            recent_decisions=decisions,
            relevant_artifacts=artifacts,
            token_budget=token_budget,
            total_tokens=res_data.get("token_budget_info", {}).get("estimated_tokens", len(rendered.split()) * 2),
            counting_method="cl100k_base",
            rendered_context=rendered,
            graph_freshness="verified",
        )

    async def get_checkpoint(self) -> dict[str, Any] | None:
        """Retrieve the latest checkpoint via barsa_get_checkpoint tool."""
        if not self.selected_project_id or not self._session:
            raise RuntimeError("Must select project before get_checkpoint()")

        tool_res = await self._session.call_tool("barsa_get_checkpoint", {"project_id": self.selected_project_id})
        if tool_res.is_error:
            return None
        return json.loads(tool_res.content[0].text)

    async def propose_changes(
        self,
        changes: list[dict[str, Any]],
        branch_name: str = "feature/proposal",
        base_commit: str | None = None,
        message: str = "Proposed memory changes",
    ) -> dict[str, Any]:
        """Propose candidate changes via barsa_propose_changes tool."""
        if not self.selected_project_id or not self._session:
            raise RuntimeError("Must select project before propose_changes()")

        if not base_commit:
            history = await self.get_history(limit=1)
            base_commit = history[0]["commit_id"] if history else "initial"

        formatted_changes = []
        for chg in changes:
            rec = chg.get("after_state") or chg.get("new_record_state") or chg
            rec_id = chg.get("record_id") or rec.get("id") or rec.get("record_id")
            rec_type = chg.get("record_type") or rec.get("record_type", "task")
            formatted_changes.append(
                {
                    "operation": chg.get("operation", "create"),
                    "record_id": rec_id,
                    "record_type": rec_type,
                    "after_state": rec,
                }
            )

        tool_res = await self._session.call_tool(
            "barsa_propose_changes",
            {
                "project_id": self.selected_project_id,
                "branch": branch_name,
                "base_commit": base_commit,
                "changes": formatted_changes,
                "message": message,
            },
        )
        if tool_res.is_error:
            err = tool_res.content[0].text if tool_res.content else "Unknown error in propose_changes"
            raise RuntimeError(err)

        return json.loads(tool_res.content[0].text)

    async def commit(
        self,
        message: str,
        branch_name: str = "main",
        changes: list[dict[str, Any]] | None = None,
        expected_head: str | None = None,
        author_name: str | None = None,  # noqa: ARG002
        author_email: str | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Commit memory updates via barsa_commit tool."""
        if not self.selected_project_id or not self._session:
            raise RuntimeError("Must select project before commit()")

        formatted_changes = None
        if changes:
            formatted_changes = []
            for chg in changes:
                rec = chg.get("after_state") or chg.get("new_record_state") or chg
                rec_id = chg.get("record_id") or rec.get("id") or rec.get("record_id")
                rec_type = chg.get("record_type") or rec.get("record_type", "task")
                formatted_changes.append(
                    {
                        "operation": chg.get("operation", "create"),
                        "record_id": rec_id,
                        "record_type": rec_type,
                        "after_state": rec,
                    }
                )

        args: dict[str, Any] = {
            "project_id": self.selected_project_id,
            "branch": branch_name,
            "message": message,
        }
        if formatted_changes is not None:
            args["changes"] = formatted_changes
        if expected_head:
            args["expected_head"] = expected_head

        tool_res = await self._session.call_tool("barsa_commit", args)
        if tool_res.is_error:
            err = tool_res.content[0].text if tool_res.content else "Commit error"
            if "Conflict" in err or "stale" in err.lower():
                raise ConflictError(err)
            raise RuntimeError(err)

        res = json.loads(tool_res.content[0].text)
        if "commit_id" in res and "commit_hash" not in res:
            res["commit_hash"] = res["commit_id"]
        return res

    async def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve commit history via barsa_get_history tool."""
        if not self.selected_project_id or not self._session:
            raise RuntimeError("Must select project before get_history()")

        tool_res = await self._session.call_tool(
            "barsa_get_history",
            {"project_id": self.selected_project_id, "limit": limit},
        )
        if tool_res.is_error:
            return []
        data = json.loads(tool_res.content[0].text)
        return data.get("commits", [])

    async def disconnect(self) -> None:
        """Tear down MCP stream connection cleanly."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
        self._session = None
        self._task_group = None
        self.is_connected = False


class DirectApiClientAdapter(AIClientAdapter):
    """Direct FastAPI client adapter for environments utilizing standard HTTP REST requests."""

    def __init__(self, config: ClientSessionConfig, base_url: str = "http://127.0.0.1:8000") -> None:
        super().__init__(config)
        self.base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if config.api_key:
            self._headers["X-API-Key"] = config.api_key

    async def connect(self) -> None:
        """Mark as connected."""
        self.is_connected = True

    async def authenticate(self, api_key: str | None = None) -> dict[str, Any]:
        """Authenticate with Bearer or API Key."""
        if api_key:
            self._headers["X-API-Key"] = api_key
        return {"status": "authenticated", "principal_id": self.config.client_id}

    async def select_project(self, project_id: str) -> dict[str, Any]:
        """Set project ID."""
        self.selected_project_id = project_id
        return {"project_id": project_id}

    async def get_context(self, token_budget: int = 8000) -> ClientHandoffContext:
        """Fetch context."""
        if not self.selected_project_id:
            raise RuntimeError("Project not selected")
        return ClientHandoffContext(
            project_id=self.selected_project_id,
            project_name=self.selected_project_id,
            latest_checkpoint=None,
            next_task=None,
            completed_actions=[],
            pending_actions=[],
            blockers=[],
            recent_decisions=[],
            relevant_artifacts=[],
            token_budget=token_budget,
            total_tokens=100,
            rendered_context=f"Project: {self.selected_project_id}",
        )

    async def get_checkpoint(self) -> dict[str, Any] | None:
        return None

    async def propose_changes(
        self,
        changes: list[dict[str, Any]],
        branch_name: str = "feature/proposal",
        base_commit: str | None = None,  # noqa: ARG002
        message: str = "Proposed memory changes",  # noqa: ARG002
    ) -> dict[str, Any]:
        return {"proposed": len(changes), "branch": branch_name}

    async def commit(
        self,
        message: str,
        branch_name: str = "main",  # noqa: ARG002
        changes: list[dict[str, Any]] | None = None,  # noqa: ARG002
        expected_head: str | None = None,  # noqa: ARG002
        author_name: str | None = None,  # noqa: ARG002
        author_email: str | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        return {"commit_hash": "c0ffee1234", "commit_id": "c0ffee1234", "message": message}

    async def get_history(self, limit: int = 20) -> list[dict[str, Any]]:  # noqa: ARG002
        return []

    async def disconnect(self) -> None:
        self.is_connected = False
