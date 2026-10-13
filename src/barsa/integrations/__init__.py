"""Integrations module for AI clients and MCP server."""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AIIntegrationAdapter(Protocol):
    """Protocol for AI assistant integrations (ChatGPT, Claude, Gemini, coding agents).

    Full implementation scheduled for Phase 8 (MCP Server & Integrations).
    """

    @property
    @abstractmethod
    def client_name(self) -> str:
        """Name of the integrated AI client."""
        ...

    @abstractmethod
    async def export_context(self, project_id: str) -> dict[str, Any]:
        """Format and export memory context for the target AI client."""
        ...
