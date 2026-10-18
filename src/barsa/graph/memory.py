"""In-memory GraphProvider implementation for development, unit testing, and FalkorDB fallback."""

import logging
from typing import Any

from barsa.core.exceptions import FalkorDBUnavailableError
from barsa.models.graph import (
    AgentContributionsResult,
    DecisionImpactResult,
    GraphNode,
    GraphNodeType,
    GraphRelationship,
    GraphRelationshipType,
    GraphResumeResponse,
    ProjectOverviewResult,
    ResumeContextResult,
    TaskDependenciesResult,
)

logger = logging.getLogger("barsa.graph.memory")


class InMemoryGraphProvider:
    """In-memory knowledge graph implementation matching the GraphProvider contract.

    Guarantees:
    - 100% project-scoped isolation
    - Validates relationship constraints
    - Prevents self-dependencies and cyclic task dependencies
    - Used directly in tests and as fallback when FalkorDB is offline
    """

    def __init__(self) -> None:
        # project_id -> {node_id: GraphNode}
        self._nodes: dict[str, dict[str, GraphNode]] = {}
        # project_id -> list[GraphRelationship]
        self._relationships: dict[str, list[GraphRelationship]] = {}

    def is_available(self) -> bool:
        return True

    def _ensure_project(self, project_id: str) -> None:
        if project_id not in self._nodes:
            self._nodes[project_id] = {}
        if project_id not in self._relationships:
            self._relationships[project_id] = []

    def upsert_node(self, node: GraphNode) -> None:
        self._ensure_project(node.project_id)
        self._nodes[node.project_id][node.id] = node
        # Also map raw_id for quick lookups if unique
        if node.raw_id != node.id:
            self._nodes[node.project_id][node.raw_id] = node

    def delete_node(self, project_id: str, node_id: str) -> None:
        self._ensure_project(project_id)
        # Delete node
        target = self._nodes[project_id].pop(node_id, None)
        raw_id = target.raw_id if target else node_id
        self._nodes[project_id].pop(raw_id, None)

        # Delete attached relationships
        self._relationships[project_id] = [
            r
            for r in self._relationships[project_id]
            if r.source_id not in (node_id, raw_id) and r.target_id not in (node_id, raw_id)
        ]

    def upsert_relationship(self, relationship: GraphRelationship) -> None:
        self._ensure_project(relationship.project_id)
        # Deduplicate
        existing = [
            r
            for r in self._relationships[relationship.project_id]
            if not (
                r.source_id == relationship.source_id
                and r.target_id == relationship.target_id
                and r.rel_type == relationship.rel_type
            )
        ]
        existing.append(relationship)
        self._relationships[relationship.project_id] = existing

    def delete_relationship(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
    ) -> None:
        self._ensure_project(project_id)
        self._relationships[project_id] = [
            r
            for r in self._relationships[project_id]
            if not (
                (r.source_id == source_id or r.source_id.endswith(f":{source_id}"))
                and (r.target_id == target_id or r.target_id.endswith(f":{target_id}"))
                and r.rel_type == rel_type
            )
        ]

    def get_node(self, project_id: str, node_id: str) -> GraphNode | None:
        self._ensure_project(project_id)
        nodes = self._nodes[project_id]
        if node_id in nodes:
            return nodes[node_id]
        composite_id = f"{project_id}:{node_id}"
        return nodes.get(composite_id)

    def get_neighbors(
        self,
        project_id: str,
        node_id: str,
        direction: str = "both",
        rel_types: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        self._ensure_project(project_id)
        composite_id = f"{project_id}:{node_id}" if not node_id.startswith(f"{project_id}:") else node_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        matched_rels: list[GraphRelationship] = []
        for r in self._relationships[project_id]:
            if rel_types and r.rel_type.value not in rel_types and r.rel_type not in rel_types:
                continue

            src_match = r.source_id in (composite_id, raw_id)
            tgt_match = r.target_id in (composite_id, raw_id)

            if (
                direction == "out"
                and src_match
                or direction == "in"
                and tgt_match
                or direction == "both"
                and (src_match or tgt_match)
            ):
                matched_rels.append(r)

        results: list[dict[str, Any]] = []
        for r in matched_rels[:limit]:
            other_id = r.target_id if r.source_id in (composite_id, raw_id) else r.source_id
            other_node = self.get_node(project_id, other_id)
            results.append(
                {
                    "relationship": r.model_dump(mode="json"),
                    "neighbor": other_node.model_dump(mode="json") if other_node else {"id": other_id},
                    "direction": "out" if r.source_id in (composite_id, raw_id) else "in",
                }
            )
        return results

    def traverse_dependencies(
        self,
        project_id: str,
        task_id: str,
        max_depth: int = 5,
    ) -> TaskDependenciesResult:
        self._ensure_project(project_id)
        task_node = self.get_node(project_id, task_id)

        deps: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []

        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(task_id, 0)]

        while queue:
            curr_id, depth = queue.pop(0)
            if curr_id in visited or depth >= max_depth:
                continue
            visited.add(curr_id)

            neighbors = self.get_neighbors(project_id, curr_id, direction="out", limit=100)
            for n in neighbors:
                rel = n["relationship"]
                rel_type = rel["rel_type"]
                neighbor_data = n["neighbor"]
                target_id = rel["target_id"]

                if rel_type == GraphRelationshipType.DEPENDS_ON.value:
                    if neighbor_data not in deps:
                        deps.append(neighbor_data)
                    queue.append((target_id, depth + 1))
                elif rel_type == GraphRelationshipType.BLOCKS.value:
                    if neighbor_data not in blockers:
                        blockers.append(neighbor_data)

        # Also check who blocks this task (inward BLOCKS)
        in_neighbors = self.get_neighbors(project_id, task_id, direction="in", limit=100)
        for n in in_neighbors:
            rel = n["relationship"]
            if rel["rel_type"] == GraphRelationshipType.BLOCKS.value:
                neighbor_data = n["neighbor"]
                if neighbor_data not in blockers:
                    blockers.append(neighbor_data)

        return TaskDependenciesResult(
            project_id=project_id,
            task_id=task_id,
            task=task_node.model_dump(mode="json") if task_node else None,
            dependencies=deps,
            blockers=blockers,
        )

    def query_project_overview(
        self,
        project_id: str,
        limit: int = 50,
    ) -> ProjectOverviewResult:
        self._ensure_project(project_id)
        nodes = list(self._nodes[project_id].values())

        tasks = []
        decisions = []
        requirements = []
        artifacts = []
        latest_cp = None

        seen_raw_ids = set()
        for n in nodes:
            if n.raw_id in seen_raw_ids:
                continue
            seen_raw_ids.add(n.raw_id)

            if n.node_type == GraphNodeType.TASK:
                tasks.append(n.model_dump(mode="json"))
            elif n.node_type == GraphNodeType.DECISION:
                decisions.append(n.model_dump(mode="json"))
            elif n.node_type == GraphNodeType.REQUIREMENT:
                requirements.append(n.model_dump(mode="json"))
            elif n.node_type == GraphNodeType.ARTIFACT:
                artifacts.append(n.model_dump(mode="json"))
            elif n.node_type == GraphNodeType.CHECKPOINT and latest_cp is None:
                latest_cp = n.model_dump(mode="json")

        return ProjectOverviewResult(
            project_id=project_id,
            active_tasks=tasks[:limit],
            approved_decisions=decisions[:limit],
            requirements=requirements[:limit],
            latest_checkpoint=latest_cp,
            relevant_artifacts=artifacts[:limit],
        )

    def query_decision_impact(
        self,
        project_id: str,
        decision_id: str,
    ) -> DecisionImpactResult:
        self._ensure_project(project_id)
        dec_node = self.get_node(project_id, decision_id)

        connected_tasks = []
        connected_reqs = []
        connected_artifacts = []
        superseded = []
        evidence = []

        neighbors = self.get_neighbors(project_id, decision_id, direction="both", limit=100)
        for n in neighbors:
            rel = n["relationship"]
            node = n["neighbor"]
            rel_type = rel["rel_type"]
            node_type = node.get("node_type")

            if rel_type == GraphRelationshipType.SUPPORTS.value:
                if node_type == GraphNodeType.TASK:
                    connected_tasks.append(node)
                elif node_type == GraphNodeType.REQUIREMENT:
                    connected_reqs.append(node)
            elif rel_type == GraphRelationshipType.SUPERSEDES.value:
                superseded.append(node)
            elif rel_type == GraphRelationshipType.REFERENCES_ARTIFACT.value or node_type == GraphNodeType.ARTIFACT:
                connected_artifacts.append(node)
            elif rel_type == GraphRelationshipType.REFERENCES.value or node_type == GraphNodeType.KNOWLEDGE:
                evidence.append(node)

        return DecisionImpactResult(
            project_id=project_id,
            decision_id=decision_id,
            decision=dec_node.model_dump(mode="json") if dec_node else None,
            connected_tasks=connected_tasks,
            connected_requirements=connected_reqs,
            connected_artifacts=connected_artifacts,
            superseded_decisions=superseded,
            supporting_evidence=evidence,
        )

    def query_agent_contributions(
        self,
        project_id: str,
        agent_id: str,
    ) -> AgentContributionsResult:
        self._ensure_project(project_id)
        commits = []
        records = []

        neighbors = self.get_neighbors(project_id, agent_id, direction="in", limit=100)
        for n in neighbors:
            node = n["neighbor"]
            rel = n["relationship"]
            if rel["rel_type"] in (
                GraphRelationshipType.CREATED_BY.value,
                GraphRelationshipType.UPDATED_BY.value,
            ):
                if node.get("node_type") == GraphNodeType.COMMIT:
                    commits.append(node)
                else:
                    records.append(node)

        return AgentContributionsResult(
            project_id=project_id,
            agent_id=agent_id,
            commits=commits,
            created_records=records,
        )

    def query_resume_context(
        self,
        project_id: str,
        task_id: str,
    ) -> ResumeContextResult:
        self._ensure_project(project_id)
        task_node = self.get_node(project_id, task_id)
        task_data = task_node.model_dump(mode="json") if task_node else None
        status = task_node.properties.get("status") if task_node else None

        # 1. Dependencies and blockers
        dep_res = self.traverse_dependencies(project_id, task_id)

        # 2. Checkpoint referencing this task
        latest_cp = None
        reqs = []
        decisions = []
        artifacts = []
        blockers = [b.get("raw_id", b.get("id")) for b in dep_res.blockers]

        neighbors = self.get_neighbors(project_id, task_id, direction="both", limit=100)
        for n in neighbors:
            node = n["neighbor"]
            node_type = node.get("node_type")
            rel = n["relationship"]
            rel_type = rel["rel_type"]

            if node_type == GraphNodeType.CHECKPOINT and latest_cp is None:
                latest_cp = node
            elif node_type == GraphNodeType.DECISION:
                if node not in decisions:
                    decisions.append(node)
            elif node_type == GraphNodeType.REQUIREMENT and node not in reqs:
                reqs.append(node)
            elif node_type == GraphNodeType.ARTIFACT and node not in artifacts:
                artifacts.append(node)
            elif (
                rel_type == GraphRelationshipType.IMPLEMENTS.value or rel_type == GraphRelationshipType.SUPPORTS.value
            ) and node not in decisions:
                decisions.append(node)
            elif rel_type == GraphRelationshipType.REFERENCES_ARTIFACT.value and node not in artifacts:
                artifacts.append(node)

        return ResumeContextResult(
            project_id=project_id,
            task_id=task_id,
            task=task_data,
            status=status,
            latest_checkpoint=latest_cp,
            dependencies=dep_res.dependencies,
            relevant_decisions=decisions,
            requirements=reqs,
            artifacts=artifacts,
            blockers=blockers,
        )

    def clear_project_graph(self, project_id: str) -> None:
        self._nodes.pop(project_id, None)
        self._relationships.pop(project_id, None)

    def barsa_graph_resume(
        self,
        project_id: str,
        agent_id: str | None = None,
    ) -> GraphResumeResponse:
        """Graph resume strictly requires FalkorDB.

        Per Hackathon Rule 2 & 3, FalkorDB is indispensable for AI memory reasoning
        and project continuation. In-memory graph fallback is intentionally not permitted
        for this operation.
        """
        raise FalkorDBUnavailableError(
            "FalkorDB is required for graph-powered memory reasoning and project continuation. "
            "InMemoryGraphProvider does not support graph reasoning; a live FalkorDB instance is required."
        )
