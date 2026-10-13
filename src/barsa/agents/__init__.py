"""Agent coordinator interfaces (Capability-based task distribution across AI models)."""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentCoordinator(Protocol):
    """Protocol for capability-based agent distribution and handoffs.

    Full implementation scheduled for Phase 6 (Agent Coordinator).
    """

    @abstractmethod
    async def match_agent(self, task_description: str, required_capabilities: list[str]) -> str:
        """Find the optimal agent provider/model for a given task."""
        ...

    @abstractmethod
    async def handoff_task(
        self, task_id: str, from_agent: str, to_agent: str, context: dict[str, Any]
    ) -> None:
        """Coordinate work progress handoff between two AI agents."""
        ...
