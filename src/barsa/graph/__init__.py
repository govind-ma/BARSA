"""Graph module interfaces (Knowledge graph connecting tasks, decisions, agents, and artifacts)."""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GraphEngine(Protocol):
    """Protocol for graph database operations (FalkorDB / Cypher queries).

    Full implementation scheduled for Phase 4 (Knowledge Graph).
    """

    @abstractmethod
    async def add_node(self, node_type: str, node_id: str, properties: dict[str, Any]) -> None:
        """Add a graph node representing a task, decision, agent, or artifact."""
        ...

    @abstractmethod
    async def add_edge(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Add a typed edge between two graph entities."""
        ...

    @abstractmethod
    async def query(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a graph query."""
        ...
