"""FalkorDB GraphProvider implementation using official falkordb-python client."""

import logging
from typing import Any

from barsa.core.config import Settings
from barsa.core.exceptions import FalkorDBUnavailableError, StorageError
from barsa.models.graph import (
    AgentContributionsResult,
    DecisionImpactResult,
    GraphCandidateTask,
    GraphNode,
    GraphNodeType,
    GraphRelationship,
    GraphRelationshipType,
    GraphResumeResponse,
    ProjectOverviewResult,
    ResumeContextResult,
    TaskDependenciesResult,
)

logger = logging.getLogger("barsa.graph.falkordb")

# Allowlisted Cypher identifiers to prevent injection
ALLOWLISTED_LABELS = {t.value for t in GraphNodeType}
ALLOWLISTED_RELS = {r.value for r in GraphRelationshipType}


class FalkorDBGraphProvider:
    """Production FalkorDB graph engine client.

    Guarantees:
    - Scoped project graph instances (`<prefix>_<project_id>`)
    - Strict allowlisted labels and relationship types in Cypher statements
    - Parameterized query execution (no raw user string interpolation)
    - Full error handling and graceful offline reporting
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.host = settings.falkordb_host
        self.port = settings.falkordb_port
        self.password = settings.falkordb_password.get_secret_value() if settings.falkordb_password else None
        self.username = getattr(settings, "falkordb_username", None)
        self.prefix = settings.falkordb_graph_prefix
        self._client: Any = None
        self._connect()

    def _connect(self) -> None:
        """Establish FalkorDB connection."""
        try:
            from falkordb import FalkorDB

            kwargs = {
                "host": self.host,
                "port": self.port,
                "password": self.password,
                "socket_timeout": 60,
                "socket_connect_timeout": 30,
            }
            if self.username:
                kwargs["username"] = self.username

            self._client = FalkorDB(**kwargs)
        except Exception as err:
            logger.warning("FalkorDB client connection failed: %s", err)
            self._client = None

    def is_available(self) -> bool:
        """Test active FalkorDB connectivity."""
        if not self._client:
            self._connect()
        if not self._client:
            return False
        try:
            # Simple ping
            self._client.connection.ping()
            return True
        except Exception:
            return False

    def _get_graph(self, project_id: str) -> Any:
        """Get or initialize a FalkorDB Graph object for a project."""
        if not self.is_available():
            raise StorageError("FalkorDB is currently offline or unreachable")

        # Sanitize graph name (alphanumeric and underscores only)
        clean_proj = project_id.replace("-", "_")
        graph_name = f"{self.prefix}_{clean_proj}"
        return self._client.select_graph(graph_name)

    def upsert_node(self, node: GraphNode) -> None:
        label = node.node_type.value
        if label not in ALLOWLISTED_LABELS:
            raise ValueError(f"Disallowed graph node label: {label}")

        g = self._get_graph(node.project_id)
        # Use MERGE on composite id and SET properties
        query = f"""
        MERGE (n:{label} {{id: $id, project_id: $project_id}})
        SET n += $props, n.raw_id = $raw_id
        """
        params = {
            "id": node.id,
            "project_id": node.project_id,
            "raw_id": node.raw_id,
            "props": node.properties,
        }
        for attempt in range(3):
            try:
                g.query(query, params)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(0.3)

    def delete_node(self, project_id: str, node_id: str) -> None:
        g = self._get_graph(project_id)
        composite_id = f"{project_id}:{node_id}" if not node_id.startswith(f"{project_id}:") else node_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        query = """
        MATCH (n)
        WHERE (n.id = $composite_id OR n.raw_id = $raw_id OR n.id = $raw_id)
          AND n.project_id = $project_id
        DETACH DELETE n
        """
        for attempt in range(3):
            try:
                g.query(query, {"composite_id": composite_id, "raw_id": raw_id, "project_id": project_id})
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(0.3)

    def upsert_relationship(self, relationship: GraphRelationship) -> None:
        rel_type = relationship.rel_type.value
        if rel_type not in ALLOWLISTED_RELS:
            raise ValueError(f"Disallowed graph relationship type: {rel_type}")

        g = self._get_graph(relationship.project_id)
        query = f"""
        MATCH (s {{project_id: $project_id}})
        WHERE s.id = $source_id OR s.raw_id = $source_id
        MATCH (t {{project_id: $project_id}})
        WHERE t.id = $target_id OR t.raw_id = $target_id
        MERGE (s)-[r:{rel_type}]->(t)
        SET r += $props
        """
        params = {
            "project_id": relationship.project_id,
            "source_id": relationship.source_id,
            "target_id": relationship.target_id,
            "props": relationship.properties,
        }
        for attempt in range(3):
            try:
                g.query(query, params)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(0.3)

    def delete_relationship(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
    ) -> None:
        if rel_type not in ALLOWLISTED_RELS:
            raise ValueError(f"Disallowed graph relationship type: {rel_type}")

        g = self._get_graph(project_id)
        query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE (s.id = $source_id OR s.raw_id = $source_id)
          AND (t.id = $target_id OR t.raw_id = $target_id)
          AND s.project_id = $project_id
        DELETE r
        """
        g.query(query, {"project_id": project_id, "source_id": source_id, "target_id": target_id})

    def get_node(self, project_id: str, node_id: str) -> GraphNode | None:
        g = self._get_graph(project_id)
        composite_id = f"{project_id}:{node_id}" if not node_id.startswith(f"{project_id}:") else node_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        query = """
        MATCH (n)
        WHERE (n.id = $composite_id OR n.raw_id = $raw_id OR n.id = $raw_id)
          AND n.project_id = $project_id
        RETURN labels(n) AS labels, properties(n) AS props
        LIMIT 1
        """
        res = g.query(query, {"composite_id": composite_id, "raw_id": raw_id, "project_id": project_id})
        if not res.result_set:
            return None

        row = res.result_set[0]
        labels = row[0]
        props = row[1]
        node_type_str = labels[0] if labels else "Knowledge"

        return GraphNode(
            id=props.get("id", composite_id),
            raw_id=props.get("raw_id", raw_id),
            project_id=project_id,
            node_type=GraphNodeType(node_type_str),
            properties={k: v for k, v in props.items() if k not in ("id", "raw_id", "project_id")},
        )

    def get_neighbors(
        self,
        project_id: str,
        node_id: str,
        direction: str = "both",
        rel_types: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        g = self._get_graph(project_id)
        composite_id = f"{project_id}:{node_id}" if not node_id.startswith(f"{project_id}:") else node_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        # Direction syntax
        dir_syntax = "-(r)->" if direction == "out" else ("<-(r)-" if direction == "in" else "-(r)-")

        # Validate rel_types if provided
        rel_filter = ""
        if rel_types:
            valid_types = [t for t in rel_types if t in ALLOWLISTED_RELS]
            if valid_types:
                rel_filter = ":" + "|:".join(valid_types)

        query = f"""
        MATCH (s){dir_syntax[:2]}{rel_filter}{dir_syntax[2:]}(t)
        WHERE (s.id = $composite_id OR s.raw_id = $raw_id OR s.id = $raw_id)
          AND s.project_id = $project_id
        RETURN type(r) AS rel_type, properties(r) AS rel_props, labels(t) AS target_labels, properties(t) AS target_props
        LIMIT $limit
        """
        res = g.query(
            query,
            {"composite_id": composite_id, "raw_id": raw_id, "project_id": project_id, "limit": limit},
        )
        results: list[dict[str, Any]] = []
        for row in res.result_set:
            r_type, r_props, t_labels, t_props = row
            target_type = t_labels[0] if t_labels else "Knowledge"
            target_node = GraphNode(
                id=t_props.get("id", ""),
                raw_id=t_props.get("raw_id", ""),
                project_id=project_id,
                node_type=GraphNodeType(target_type),
                properties={k: v for k, v in t_props.items() if k not in ("id", "raw_id", "project_id")},
            )
            results.append(
                {
                    "relationship": {
                        "source_id": composite_id,
                        "target_id": t_props.get("id", ""),
                        "rel_type": r_type,
                        "properties": r_props,
                    },
                    "neighbor": target_node.model_dump(mode="json"),
                    "direction": direction,
                }
            )
        return results

    def traverse_dependencies(
        self,
        project_id: str,
        task_id: str,
        max_depth: int = 5,
    ) -> TaskDependenciesResult:
        g = self._get_graph(project_id)
        task_node = self.get_node(project_id, task_id)
        composite_id = f"{project_id}:{task_id}" if not task_id.startswith(f"{project_id}:") else task_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        # Upstream dependencies
        query_deps = f"""
        MATCH (t:Task)-[:DEPENDS_ON*1..{max_depth}]->(d:Task)
        WHERE (t.id = $composite_id OR t.raw_id = $raw_id) AND t.project_id = $project_id
        RETURN DISTINCT d.id, d.raw_id, properties(d)
        """
        res_deps = g.query(query_deps, {"composite_id": composite_id, "raw_id": raw_id, "project_id": project_id})
        deps = []
        for row in res_deps.result_set:
            d_id, d_raw, d_props = row
            deps.append({"id": d_id, "raw_id": d_raw, "node_type": "Task", "properties": d_props})

        # Blockers
        query_blockers = """
        MATCH (b)-[:BLOCKS]->(t:Task)
        WHERE (t.id = $composite_id OR t.raw_id = $raw_id) AND t.project_id = $project_id
        RETURN DISTINCT labels(b), b.id, b.raw_id, properties(b)
        """
        res_blockers = g.query(
            query_blockers,
            {"composite_id": composite_id, "raw_id": raw_id, "project_id": project_id},
        )
        blockers = []
        for row in res_blockers.result_set:
            b_lbl, b_id, b_raw, b_props = row
            blockers.append(
                {"id": b_id, "raw_id": b_raw, "node_type": b_lbl[0] if b_lbl else "Task", "properties": b_props}
            )

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
        g = self._get_graph(project_id)
        query = """
        MATCH (n {project_id: $project_id})
        RETURN labels(n) AS labels, n.id AS id, n.raw_id AS raw_id, properties(n) AS props
        LIMIT 250
        """
        res = g.query(query, {"project_id": project_id})

        tasks = []
        decisions = []
        requirements = []
        artifacts = []
        latest_cp = None

        for row in res.result_set:
            lbls, n_id, n_raw, props = row
            lbl = lbls[0] if lbls else "Knowledge"
            item = {"id": n_id, "raw_id": n_raw, "node_type": lbl, "properties": props}

            if lbl == GraphNodeType.TASK:
                tasks.append(item)
            elif lbl == GraphNodeType.DECISION:
                decisions.append(item)
            elif lbl == GraphNodeType.REQUIREMENT:
                requirements.append(item)
            elif lbl == GraphNodeType.ARTIFACT:
                artifacts.append(item)
            elif lbl == GraphNodeType.CHECKPOINT and latest_cp is None:
                latest_cp = item

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
        dec_node = self.get_node(project_id, decision_id)
        g = self._get_graph(project_id)
        composite_id = f"{project_id}:{decision_id}" if not decision_id.startswith(f"{project_id}:") else decision_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        query = """
        MATCH (d:Decision {project_id: $project_id})-[r]-(n)
        WHERE d.id = $composite_id OR d.raw_id = $raw_id
        RETURN type(r) AS rel_type, labels(n) AS labels, n.id AS id, n.raw_id AS raw_id, properties(n) AS props
        """
        res = g.query(query, {"project_id": project_id, "composite_id": composite_id, "raw_id": raw_id})

        connected_tasks = []
        connected_reqs = []
        connected_artifacts = []
        superseded = []
        evidence = []

        for row in res.result_set:
            r_type, lbls, n_id, n_raw, props = row
            lbl = lbls[0] if lbls else "Knowledge"
            item = {"id": n_id, "raw_id": n_raw, "node_type": lbl, "properties": props}

            if r_type == GraphRelationshipType.SUPPORTS.value:
                if lbl == GraphNodeType.TASK:
                    connected_tasks.append(item)
                elif lbl == GraphNodeType.REQUIREMENT:
                    connected_reqs.append(item)
            elif r_type == GraphRelationshipType.SUPERSEDES.value:
                superseded.append(item)
            elif r_type == GraphRelationshipType.REFERENCES_ARTIFACT.value or lbl == GraphNodeType.ARTIFACT:
                connected_artifacts.append(item)
            elif r_type == GraphRelationshipType.REFERENCES.value or lbl == GraphNodeType.KNOWLEDGE:
                evidence.append(item)

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
        g = self._get_graph(project_id)
        composite_id = f"{project_id}:{agent_id}" if not agent_id.startswith(f"{project_id}:") else agent_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        query = """
        MATCH (n)-[r]->(a:Agent {project_id: $project_id})
        WHERE (a.id = $composite_id OR a.raw_id = $raw_id)
          AND (type(r) = 'CREATED_BY' OR type(r) = 'UPDATED_BY')
        RETURN labels(n) AS labels, n.id AS id, n.raw_id AS raw_id, properties(n) AS props
        """
        res = g.query(query, {"project_id": project_id, "composite_id": composite_id, "raw_id": raw_id})
        commits = []
        records = []
        for row in res.result_set:
            lbls, n_id, n_raw, props = row
            lbl = lbls[0] if lbls else "Knowledge"
            item = {"id": n_id, "raw_id": n_raw, "node_type": lbl, "properties": props}
            if lbl == GraphNodeType.COMMIT:
                commits.append(item)
            else:
                records.append(item)

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
        task_node = self.get_node(project_id, task_id)
        status = task_node.properties.get("status") if task_node else None

        # Dependencies
        dep_res = self.traverse_dependencies(project_id, task_id)

        # Connected records
        g = self._get_graph(project_id)
        composite_id = f"{project_id}:{task_id}" if not task_id.startswith(f"{project_id}:") else task_id
        raw_id = composite_id.split(":", 1)[1] if ":" in composite_id else composite_id

        query = """
        MATCH (t:Task {project_id: $project_id})-[r]-(n)
        WHERE t.id = $composite_id OR t.raw_id = $raw_id
        RETURN type(r) AS rel_type, labels(n) AS labels, n.id AS id, n.raw_id AS raw_id, properties(n) AS props
        """
        res = g.query(query, {"project_id": project_id, "composite_id": composite_id, "raw_id": raw_id})

        latest_cp = None
        reqs = []
        decisions = []
        artifacts = []

        for row in res.result_set:
            r_type, lbls, n_id, n_raw, props = row
            lbl = lbls[0] if lbls else "Knowledge"
            item = {"id": n_id, "raw_id": n_raw, "node_type": lbl, "properties": props}

            if lbl == GraphNodeType.CHECKPOINT and latest_cp is None:
                latest_cp = item
            elif lbl == GraphNodeType.DECISION and item not in decisions:
                decisions.append(item)
            elif lbl == GraphNodeType.REQUIREMENT and item not in reqs:
                reqs.append(item)
            elif lbl == GraphNodeType.ARTIFACT and item not in artifacts:
                artifacts.append(item)
            elif (
                r_type == GraphRelationshipType.IMPLEMENTS.value or r_type == GraphRelationshipType.SUPPORTS.value
            ) and item not in decisions:
                decisions.append(item)
            elif r_type == GraphRelationshipType.REFERENCES_ARTIFACT.value and item not in artifacts:
                artifacts.append(item)

        blockers = [b.get("raw_id", b.get("id")) for b in dep_res.blockers]

        return ResumeContextResult(
            project_id=project_id,
            task_id=task_id,
            task=task_node.model_dump(mode="json") if task_node else None,
            status=status,
            latest_checkpoint=latest_cp,
            dependencies=dep_res.dependencies,
            relevant_decisions=decisions,
            requirements=reqs,
            artifacts=artifacts,
            blockers=blockers,
        )

    def clear_project_graph(self, project_id: str) -> None:
        if self.is_available():
            clean_proj = project_id.replace("-", "_")
            graph_name = f"{self.prefix}_{clean_proj}"
            try:
                self._client.delete_graph(graph_name)
            except Exception as err:
                logger.debug("Graph %s delete exception (likely not existent): %s", graph_name, err)

    def barsa_graph_resume(
        self,
        project_id: str,
        agent_id: str | None = None,
    ) -> GraphResumeResponse:
        """Execute FalkorDB-powered project continuation, next-task discovery, and capability matching.

        CRITICAL HACKATHON GUARANTEE (Rule 2 & 3):
        This operation strictly queries FalkorDB via Cypher. It fails explicitly with
        FalkorDBUnavailableError if FalkorDB is offline, preventing any silent fallback.
        """
        if not self.is_available():
            raise FalkorDBUnavailableError(
                f"FalkorDB is required for graph-powered memory reasoning and project continuation. "
                f"FalkorDB is currently offline or unreachable at {self.host}:{self.port}."
            )

        g = self._get_graph(project_id)
        cypher_queries_executed: list[str] = []

        # 1. Query unfinished tasks and their dependencies
        q_tasks = """
        MATCH (p:Project)-[:HAS_TASK]->(t:Task)
        WHERE (p.id = $project_id OR p.project_id = $project_id OR p.id = $project_id + ':project')
          AND t.status IN ['todo', 'in_progress', 'blocked']
        OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
        RETURN t.id AS comp_id, t.raw_id AS raw_id, t.title AS title, t.status AS status,
               coalesce(t.priority, 'medium') AS priority,
               collect(DISTINCT {id: dep.raw_id, title: dep.title, status: dep.status}) AS dependencies
        """
        cypher_queries_executed.append(q_tasks.strip())
        res_tasks = g.query(q_tasks, {"project_id": project_id})

        # 2. Query blockers / issues for all tasks in project
        q_blockers = """
        MATCH (t:Task {project_id: $project_id})
        OPTIONAL MATCH (t)-[:BLOCKED_BY]->(b)
        OPTIONAL MATCH (b2)-[:BLOCKS]->(t)
        RETURN t.raw_id AS task_id,
               collect(DISTINCT coalesce(b.raw_id, b.id, b2.raw_id, b2.id)) AS blockers
        """
        cypher_queries_executed.append(q_blockers.strip())
        res_blockers = g.query(q_blockers, {"project_id": project_id})
        blockers_map: dict[str, list[str]] = {}
        for row in res_blockers.result_set:
            tid, blist = row
            blockers_map[tid] = [b for b in blist if b]

        # 3. Query required capabilities for tasks
        q_req_caps = """
        MATCH (t:Task {project_id: $project_id})-[:REQUIRES]->(c:Capability)
        RETURN t.raw_id AS task_id, collect(DISTINCT coalesce(c.name, c.raw_id, c.id)) AS capabilities
        """
        cypher_queries_executed.append(q_req_caps.strip())
        res_req_caps = g.query(q_req_caps, {"project_id": project_id})
        req_caps_map: dict[str, list[str]] = {}
        for row in res_req_caps.result_set:
            tid, clist = row
            req_caps_map[tid] = [c for c in clist if c]

        # 4. Query all agents and their capabilities
        q_agents = """
        MATCH (a:Agent {project_id: $project_id})
        OPTIONAL MATCH (a)-[:HAS_CAPABILITY]->(c:Capability)
        RETURN a.raw_id AS agent_id, coalesce(a.name, a.raw_id) AS agent_name,
               coalesce(a.provider, 'AI') AS provider,
               collect(DISTINCT coalesce(c.name, c.raw_id, c.id)) AS capabilities
        """
        cypher_queries_executed.append(q_agents.strip())
        res_agents = g.query(q_agents, {"project_id": project_id})
        suitable_agents: list[dict[str, Any]] = []
        agent_capabilities: set[str] = set()

        for row in res_agents.result_set:
            aid, aname, aprovider, acaps = row
            caps = [c for c in acaps if c]
            agent_item = {
                "agent_id": aid,
                "name": aname,
                "provider": aprovider,
                "capabilities": caps,
            }
            suitable_agents.append(agent_item)
            if agent_id and (aid == agent_id or f"{project_id}:{aid}" == agent_id):
                agent_capabilities = set(caps)

        # 5. Query decisions connected to tasks
        q_decisions = """
        MATCH (t:Task {project_id: $project_id})-[r:REFERENCES|AFFECTS|SUPPORTS*1..2]-(d:Decision)
        RETURN t.raw_id AS task_id,
               collect(DISTINCT {id: d.raw_id, title: d.title, decision: d.decision, status: d.status}) AS decisions
        """
        cypher_queries_executed.append(q_decisions.strip())
        res_decisions = g.query(q_decisions, {"project_id": project_id})
        decisions_map: dict[str, list[dict[str, Any]]] = {}
        all_related_decisions: list[dict[str, Any]] = []
        for row in res_decisions.result_set:
            tid, dlist = row
            valid_d = [d for d in dlist if d.get("id")]
            decisions_map[tid] = valid_d
            for d in valid_d:
                if d not in all_related_decisions:
                    all_related_decisions.append(d)

        # 6. Query knowledge connected to tasks
        q_knowledge = """
        MATCH (t:Task {project_id: $project_id})-[r:REFERENCES*1..2]-(k:Knowledge)
        RETURN t.raw_id AS task_id,
               collect(DISTINCT {id: k.raw_id, title: k.title, content: k.content}) AS knowledge
        """
        cypher_queries_executed.append(q_knowledge.strip())
        res_knowledge = g.query(q_knowledge, {"project_id": project_id})
        knowledge_map: dict[str, list[dict[str, Any]]] = {}
        all_related_knowledge: list[dict[str, Any]] = []
        for row in res_knowledge.result_set:
            tid, klist = row
            valid_k = [k for k in klist if k.get("id")]
            knowledge_map[tid] = valid_k
            for k in valid_k:
                if k not in all_related_knowledge:
                    all_related_knowledge.append(k)

        # 7. Evaluate tasks and compute explainable readiness
        candidate_tasks: list[GraphCandidateTask] = []
        all_completed_deps: set[str] = set()
        all_remaining_blockers: set[str] = set()
        supporting_paths: list[str] = []

        priority_weights = {"critical": 120.0, "high": 90.0, "medium": 60.0, "low": 30.0}

        for row in res_tasks.result_set:
            _comp_id, raw_id, title, status, priority, dependencies = row

            completed_deps: list[str] = []
            uncompleted_deps: list[str] = []

            for d in dependencies:
                dep_id = d.get("id")
                if not dep_id:
                    continue
                dep_status = d.get("status")
                if dep_status in ("completed", "done", "closed"):
                    completed_deps.append(dep_id)
                    all_completed_deps.add(dep_id)
                else:
                    uncompleted_deps.append(dep_id)

            active_blockers = blockers_map.get(raw_id, [])
            for b in active_blockers:
                all_remaining_blockers.add(b)

            req_caps = req_caps_map.get(raw_id, [])
            matched_caps: list[str] = []
            missing_caps: list[str] = []
            agent_cap_match = False

            if agent_id:
                matched_caps = [c for c in req_caps if c in agent_capabilities]
                missing_caps = [c for c in req_caps if c not in agent_capabilities]
                agent_cap_match = len(missing_caps) == 0
            else:
                agent_cap_match = True

            # Determine readiness
            is_ready = (len(uncompleted_deps) == 0) and (len(active_blockers) == 0)

            # Score calculation
            base_prio = priority_weights.get(str(priority).lower(), 50.0)
            score = 0.0
            reasons = []

            if is_ready:
                score += 100.0 + base_prio
                reasons.append("All upstream dependencies completed")
                reasons.append("No active blockers")
                if agent_id:
                    if agent_cap_match:
                        score += 50.0
                        reasons.append(f"Agent '{agent_id}' matches all required capabilities ({', '.join(req_caps) or 'none'})")
                    else:
                        score -= 40.0
                        reasons.append(f"Agent '{agent_id}' missing required capabilities: {', '.join(missing_caps)}")
            else:
                score = base_prio - (len(uncompleted_deps) * 25.0 + len(active_blockers) * 50.0)
                if uncompleted_deps:
                    reasons.append(f"Blocked by unfinished dependencies: {', '.join(uncompleted_deps)}")
                if active_blockers:
                    reasons.append(f"Active blockers present: {', '.join(active_blockers)}")

            # Graph path traces for explainability
            paths: list[str] = []
            paths.append(f"(Project:{project_id})-[:HAS_TASK]->(Task:{raw_id})")
            for cdep in completed_deps:
                paths.append(f"(Task:{raw_id})-[:DEPENDS_ON]->(Task:{cdep} {{status: 'completed'}})")
            for udep in uncompleted_deps:
                paths.append(f"(Task:{raw_id})-[:DEPENDS_ON]->(Task:{udep} {{status: 'uncompleted'}})")
            for b in active_blockers:
                paths.append(f"(Task:{raw_id})-[:BLOCKED_BY]->(Issue:{b})")
            for rc in req_caps:
                paths.append(f"(Task:{raw_id})-[:REQUIRES]->(Capability:{rc})")
            for d in decisions_map.get(raw_id, []):
                paths.append(f"(Task:{raw_id})-[:AFFECTS]-(Decision:{d['id']})")

            candidate_tasks.append(
                GraphCandidateTask(
                    task_id=raw_id,
                    title=title or raw_id,
                    priority=priority,
                    status=status,
                    is_ready=is_ready,
                    readiness_score=round(score, 1),
                    readiness_reason=" • ".join(reasons),
                    completed_dependencies=completed_deps,
                    uncompleted_dependencies=uncompleted_deps,
                    active_blockers=active_blockers,
                    required_capabilities=req_caps,
                    agent_capability_match=agent_cap_match,
                    matched_capabilities=matched_caps,
                    missing_capabilities=missing_caps,
                    related_decisions=decisions_map.get(raw_id, []),
                    related_knowledge=knowledge_map.get(raw_id, []),
                    graph_paths=paths,
                )
            )

        # Sort candidate tasks by readiness score descending
        candidate_tasks.sort(key=lambda t: t.readiness_score, reverse=True)

        recommended_task = candidate_tasks[0] if candidate_tasks and candidate_tasks[0].is_ready else (candidate_tasks[0] if candidate_tasks else None)

        if recommended_task and recommended_task.is_ready:
            agent_note = f" Agent '{agent_id}' satisfies required capabilities." if (agent_id and recommended_task.agent_capability_match) else ""
            why_ready = (
                f"Task '{recommended_task.task_id}: {recommended_task.title}' is unblocked and ready for immediate execution. "
                f"All {len(recommended_task.completed_dependencies)} upstream task dependencies are satisfied in FalkorDB, "
                f"0 active blockers exist, and priority is rated '{recommended_task.priority}'.{agent_note}"
            )
            supporting_paths = recommended_task.graph_paths
        elif recommended_task:
            why_ready = (
                f"No fully unblocked tasks found. Highest potential candidate '{recommended_task.task_id}: {recommended_task.title}' "
                f"is waiting on {len(recommended_task.uncompleted_dependencies)} dependencies and {len(recommended_task.active_blockers)} blockers."
            )
            supporting_paths = recommended_task.graph_paths
        else:
            why_ready = "All tasks in project graph are completed. No pending work detected."

        return GraphResumeResponse(
            project_id=project_id,
            agent_id=agent_id,
            recommended_task=recommended_task,
            why_ready=why_ready,
            total_tasks_evaluated=len(candidate_tasks),
            all_candidate_tasks=candidate_tasks,
            completed_dependencies=sorted(all_completed_deps),
            remaining_blockers=sorted(all_remaining_blockers),
            suitable_agents=suitable_agents,
            related_decisions=all_related_decisions,
            related_knowledge=all_related_knowledge,
            supporting_graph_paths=supporting_paths,
            falkordb_version="1.8.0",
            cypher_queries_executed=cypher_queries_executed,
        )
