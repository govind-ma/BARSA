"""Graph-aware deterministic retrieval service (Phase 5)."""

import logging
from typing import Any

from barsa.graph.protocol import GraphProvider
from barsa.models.graph import (
    AgentContributionsResult,
    DecisionImpactResult,
    GraphProjectionMetadata,
    GraphResumeResponse,
    ProjectOverviewResult,
    ResumeContextResult,
    TaskDependenciesResult,
)

logger = logging.getLogger("barsa.graph.retrieval")


class GraphRetrievalService:
    """Service providing high-level, deterministic graph retrieval queries with freshness tracking."""

    def __init__(self, graph_provider: GraphProvider) -> None:
        self.graph = graph_provider

    def get_node(
        self,
        project_id: str,
        node_id: str,
        projection_metadata: GraphProjectionMetadata | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve a specific graph node."""
        node = self.graph.get_node(project_id, node_id)
        if not node:
            return None
        res = node.model_dump(mode="json")
        if projection_metadata:
            res["projection_status"] = projection_metadata.model_dump(mode="json")
        return res

    def get_neighbors(
        self,
        project_id: str,
        node_id: str,
        direction: str = "both",
        rel_types: list[str] | None = None,
        limit: int = 50,
        _projection_metadata: GraphProjectionMetadata | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve connected neighbor nodes and edges."""
        neighbors = self.graph.get_neighbors(
            project_id=project_id,
            node_id=node_id,
            direction=direction,
            rel_types=rel_types,
            limit=limit,
        )
        return neighbors

    def get_project_overview(
        self,
        project_id: str,
        limit: int = 50,
        projection_metadata: GraphProjectionMetadata | None = None,
    ) -> ProjectOverviewResult:
        """Retrieve overview of active tasks, approved decisions, requirements, and artifacts."""
        res = self.graph.query_project_overview(project_id=project_id, limit=limit)
        res.projection_status = projection_metadata
        return res

    def get_task_dependencies(
        self,
        project_id: str,
        task_id: str,
        max_depth: int = 5,
        projection_metadata: GraphProjectionMetadata | None = None,
    ) -> TaskDependenciesResult:
        """Retrieve upstream dependencies and blockers for a specific task."""
        res = self.graph.traverse_dependencies(project_id=project_id, task_id=task_id, max_depth=max_depth)
        res.projection_status = projection_metadata
        return res

    def get_decision_impact(
        self,
        project_id: str,
        decision_id: str,
        projection_metadata: GraphProjectionMetadata | None = None,
    ) -> DecisionImpactResult:
        """Retrieve connected tasks, requirements, artifacts, and decisions impacted by a decision."""
        res = self.graph.query_decision_impact(project_id=project_id, decision_id=decision_id)
        res.projection_status = projection_metadata
        return res

    def get_agent_contributions(
        self,
        project_id: str,
        agent_id: str,
        projection_metadata: GraphProjectionMetadata | None = None,
    ) -> AgentContributionsResult:
        """Retrieve commits and records created or updated by an agent in a project."""
        res = self.graph.query_agent_contributions(project_id=project_id, agent_id=agent_id)
        res.projection_status = projection_metadata
        return res

    def get_resume_context(
        self,
        project_id: str,
        task_id: str,
        projection_metadata: GraphProjectionMetadata | None = None,
    ) -> ResumeContextResult:
        """Retrieve comprehensive structured memory to resume work on a task."""
        res = self.graph.query_resume_context(project_id=project_id, task_id=task_id)
        res.projection_status = projection_metadata
        return res

    def barsa_graph_resume(
        self,
        project_id: str,
        agent_id: str | None = None,
    ) -> GraphResumeResponse:
        """Execute FalkorDB-powered project continuation, next-task discovery, and capability matching."""
        return self.graph.barsa_graph_resume(project_id=project_id, agent_id=agent_id)
