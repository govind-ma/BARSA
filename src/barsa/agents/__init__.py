"""Agent coordinator interfaces (Capability-based task distribution across AI models)."""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentCoordinator(Protocol):
    """Protocol for capability-based agent distribution and handoffs."""

    @abstractmethod
    async def match_agent(self, task_description: str, required_capabilities: list[str]) -> str:
        """Find the optimal agent provider/model for a given task."""
        ...

    @abstractmethod
    async def handoff_task(self, task_id: str, from_agent: str, to_agent: str, context: dict[str, Any]) -> None:
        """Coordinate work progress handoff between two AI agents."""
        ...


class DefaultAgentCoordinator:
    """Adapter bridging AgentCoordinator protocol to CoordinatorEngine."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    async def match_agent(self, task_description: str, required_capabilities: list[str]) -> str:
        from barsa.coordination.matching import CapabilityMatcher
        from barsa.coordination.models import CoordinationTask

        task = CoordinationTask(
            task_id="handoff-query",
            project_id="default",
            title=task_description,
            required_capabilities=required_capabilities,
        )
        agents = self.engine.list_agents()
        decision = CapabilityMatcher.match_task_to_agents(task, agents)
        if decision.assigned_agent_id:
            return decision.assigned_agent_id
        if agents:
            return agents[0].agent_id
        return "default-agent"

    async def handoff_task(self, task_id: str, from_agent: str, to_agent: str, context: dict[str, Any]) -> None:
        self.engine.add_comment(
            project_id=context.get("project_id", "default"),
            task_id=task_id,
            author_agent_id=from_agent,
            content=f"Handoff to {to_agent}: {context.get('note', '')}",
        )


__all__ = ["AgentCoordinator", "DefaultAgentCoordinator"]
