"""Graph protocol interface for BARSA Knowledge Graph engines."""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from barsa.models.graph import (
    AgentContributionsResult,
    DecisionImpactResult,
    GraphNode,
    GraphRelationship,
    GraphResumeResponse,
    ProjectOverviewResult,
    ResumeContextResult,
    TaskDependenciesResult,
)


@runtime_checkable
class GraphProvider(Protocol):
    """Protocol defining the operations supported by knowledge graph backends."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the underlying graph database is reachable and active."""
        ...

    @abstractmethod
    def upsert_node(self, node: GraphNode) -> None:
        """Upsert a single typed node into the project graph."""
        ...

    @abstractmethod
    def delete_node(self, project_id: str, node_id: str) -> None:
        """Delete a node and its attached relationships from the project graph."""
        ...

    @abstractmethod
    def upsert_relationship(self, relationship: GraphRelationship) -> None:
        """Upsert a typed directed relationship between two nodes in the project graph."""
        ...

    @abstractmethod
    def delete_relationship(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
    ) -> None:
        """Delete a specific relationship between two nodes."""
        ...

    @abstractmethod
    def get_node(self, project_id: str, node_id: str) -> GraphNode | None:
        """Retrieve a node by its composite or raw ID within a project."""
        ...

    @abstractmethod
    def get_neighbors(
        self,
        project_id: str,
        node_id: str,
        direction: str = "both",  # "in", "out", "both"
        rel_types: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve connected neighbor nodes and edges."""
        ...

    @abstractmethod
    def traverse_dependencies(
        self,
        project_id: str,
        task_id: str,
        max_depth: int = 5,
    ) -> TaskDependenciesResult:
        """Traverse upstream dependencies and blockers for a task."""
        ...

    @abstractmethod
    def query_project_overview(
        self,
        project_id: str,
        limit: int = 50,
    ) -> ProjectOverviewResult:
        """Retrieve high-level overview of project tasks, decisions, requirements, and artifacts."""
        ...

    @abstractmethod
    def query_decision_impact(
        self,
        project_id: str,
        decision_id: str,
    ) -> DecisionImpactResult:
        """Find tasks, requirements, artifacts, and decisions impacted by a decision."""
        ...

    @abstractmethod
    def query_agent_contributions(
        self,
        project_id: str,
        agent_id: str,
    ) -> AgentContributionsResult:
        """Retrieve commits and records created/updated by an agent in a project."""
        ...

    @abstractmethod
    def query_resume_context(
        self,
        project_id: str,
        task_id: str,
    ) -> ResumeContextResult:
        """Retrieve full structured context to resume work on a task."""
        ...

    @abstractmethod
    def barsa_graph_resume(
        self,
        project_id: str,
        agent_id: str | None = None,
    ) -> GraphResumeResponse:
        """Execute FalkorDB-powered project continuation, next-task discovery, and capability matching."""
        ...

    @abstractmethod
    def clear_project_graph(self, project_id: str) -> None:
        """Remove all nodes and relationships for a specific project graph."""
        ...
