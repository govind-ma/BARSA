"""Graph projection worker and synchronization engine (Phase 5)."""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any

from barsa.bms.base import generate_uuid_str, utc_now
from barsa.core.exceptions import StorageError
from barsa.graph.protocol import GraphProvider
from barsa.models.graph import (
    GraphNode,
    GraphNodeType,
    GraphProjectionMetadata,
    GraphRelationship,
    GraphRelationshipType,
    OutboxEvent,
    OutboxEventStatus,
    ProjectionStatus,
)
from barsa.storage.sqlite import SQLiteStorageProvider

logger = logging.getLogger("barsa.graph.projection")


class GraphProjectionWorker:
    """Asynchronous/synchronous worker that projects authoritative commits into the knowledge graph.

    Guarantees:
    - Exactly-once / idempotent projection: applies state deterministically based on commit state
    - Causal ordering: processes outbox events by created_at / sequence
    - Automatic validation: prevents self-dependencies and cyclic task dependencies
    - Tracks project graph revision and freshness
    """

    def __init__(self, storage: SQLiteStorageProvider, graph_provider: GraphProvider) -> None:
        self.storage = storage
        self.graph = graph_provider

    def _get_conn(self) -> sqlite3.Connection:
        return self.storage._get_connection()

    # =========================================================================
    # Outbox Event Emission & Retrieval
    # =========================================================================

    def emit_commit_approved_event(
        self,
        project_id: str,
        commit_id: str,
        branch_name: str,
        resulting_state_hash: str,
    ) -> OutboxEvent:
        """Atomically record an outbox event in SQLite for an approved main commit."""
        conn = self._get_conn()
        event_id = generate_uuid_str()
        now = utc_now()
        payload = {
            "project_id": project_id,
            "commit_id": commit_id,
            "branch_name": branch_name,
            "resulting_state_hash": resulting_state_hash,
        }

        conn.execute(
            """
            INSERT INTO graph_outbox (
                event_id, project_id, commit_id, event_type, payload_json, status, created_at
            ) VALUES (?, ?, ?, 'COMMIT_APPROVED', ?, 'PENDING', ?);
            """,
            (event_id, project_id, commit_id, json.dumps(payload), now.isoformat()),
        )

        return OutboxEvent(
            event_id=event_id,
            project_id=project_id,
            commit_id=commit_id,
            event_type="COMMIT_APPROVED",
            payload=payload,
            status=OutboxEventStatus.PENDING,
            created_at=now,
        )

    def fetch_pending_outbox_events(self, project_id: str | None = None, limit: int = 50) -> list[OutboxEvent]:
        """Fetch unapplied pending or failed outbox events in causal order."""
        conn = self._get_conn()
        sql = "SELECT * FROM graph_outbox WHERE status IN ('PENDING', 'FAILED') AND retry_count < 5"
        params: list[Any] = []
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        sql += " ORDER BY created_at ASC LIMIT ?;"
        params.append(limit)

        cur = conn.execute(sql, tuple(params))
        events = []
        for r in cur.fetchall():
            events.append(
                OutboxEvent(
                    event_id=r["event_id"],
                    project_id=r["project_id"],
                    commit_id=r["commit_id"],
                    event_type=r["event_type"],
                    payload=json.loads(r["payload_json"]),
                    status=OutboxEventStatus(r["status"]),
                    retry_count=r["retry_count"],
                    last_error=r["last_error"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    processed_at=datetime.fromisoformat(r["processed_at"]) if r["processed_at"] else None,
                )
            )
        return events

    # =========================================================================
    # Projection Execution
    # =========================================================================

    def process_pending_events(self, project_id: str | None = None) -> int:
        """Process all pending outbox events across projects or for a specific project."""
        events = self.fetch_pending_outbox_events(project_id=project_id)
        processed_count = 0
        for ev in events:
            success = self.project_event(ev)
            if success:
                processed_count += 1
        return processed_count

    def project_event(self, event: OutboxEvent) -> bool:
        """Project a single outbox event into the knowledge graph with error handling and retry tracking."""
        conn = self._get_conn()

        # Mark event as PROCESSING
        conn.execute(
            "UPDATE graph_outbox SET status = 'PROCESSING' WHERE event_id = ?;",
            (event.event_id,),
        )
        conn.commit()

        try:
            if not self.graph.is_available():
                raise StorageError("Knowledge graph provider is offline")

            self._apply_commit_projection(event.project_id, event.commit_id)

            now = utc_now()
            conn.execute(
                "UPDATE graph_outbox SET status = 'COMPLETED', processed_at = ?, last_error = NULL WHERE event_id = ?;",
                (now.isoformat(), event.event_id),
            )
            conn.commit()
            return True
        except Exception as err:
            logger.error("Failed to project outbox event %s: %s", event.event_id, err, exc_info=True)
            now = utc_now()
            conn.execute(
                """
                UPDATE graph_outbox
                SET status = 'FAILED', retry_count = retry_count + 1, last_error = ?, processed_at = ?
                WHERE event_id = ?;
                """,
                (str(err), now.isoformat(), event.event_id),
            )
            # Update projection status to LAGGING or ERROR
            conn.execute(
                """
                INSERT INTO graph_projections (
                    project_id, applied_commit_id, applied_revision, applied_state_hash,
                    status, last_projected_at, last_error
                ) VALUES (?, ?, 0, '', 'ERROR', ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET status = 'ERROR', last_error = ?;
                """,
                (event.project_id, event.commit_id, now.isoformat(), str(err), str(err)),
            )
            conn.commit()
            return False

    def _apply_commit_projection(self, project_id: str, commit_id: str) -> None:
        """Idempotently project the authoritative snapshot state of a commit into the graph."""
        conn = self._get_conn()

        # 1. Fetch commit details
        cur_c = conn.execute(
            "SELECT * FROM commits WHERE project_id = ? AND commit_id = ?;",
            (project_id, commit_id),
        )
        c_row = cur_c.fetchone()
        if not c_row:
            raise StorageError(f"Commit '{commit_id}' not found for project '{project_id}'")

        # 2. Fetch all active records at this commit from commit_record_states
        cur_s = conn.execute(
            """
            SELECT record_id, record_type, record_data_json
            FROM commit_record_states
            WHERE project_id = ? AND commit_id = ? AND record_data_json IS NOT NULL;
            """,
            (project_id, commit_id),
        )
        records = [json.loads(r["record_data_json"]) for r in cur_s.fetchall()]

        # 3. Clear existing project graph to guarantee deterministic idempotency
        self.graph.clear_project_graph(project_id)

        # 4. Upsert Project and Workspace nodes
        cur_p = conn.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
        p_row = cur_p.fetchone()
        if p_row:
            p_node = GraphNode(
                id=project_id,
                raw_id=project_id,
                project_id=project_id,
                node_type=GraphNodeType.PROJECT,
                properties={"name": p_row["name"], "workspace_id": p_row["workspace_id"]},
            )
            self.graph.upsert_node(p_node)

            # Workspace node
            cur_w = conn.execute("SELECT * FROM workspaces WHERE id = ?;", (p_row["workspace_id"],))
            w_row = cur_w.fetchone()
            if w_row:
                w_node = GraphNode(
                    id=w_row["id"],
                    raw_id=w_row["id"],
                    project_id=project_id,
                    node_type=GraphNodeType.WORKSPACE,
                    properties={"name": w_row["name"], "owner_id": w_row["owner_id"]},
                )
                self.graph.upsert_node(w_node)
                self.graph.upsert_relationship(
                    GraphRelationship(
                        source_id=w_row["id"],
                        target_id=project_id,
                        rel_type=GraphRelationshipType.HAS_PROJECT,
                        project_id=project_id,
                    )
                )

        # 5. Upsert Commit Node
        commit_node = GraphNode(
            id=f"{project_id}:{commit_id}",
            raw_id=commit_id,
            project_id=project_id,
            node_type=GraphNodeType.COMMIT,
            properties={
                "message": c_row["message"],
                "author_id": c_row["author_id"],
                "created_at": c_row["created_at"],
                "resulting_state_hash": c_row["resulting_state_hash"],
            },
        )
        self.graph.upsert_node(commit_node)

        # 6. Upsert records and classify node types
        node_count = 3  # Project, Workspace, Commit
        rel_count = 1  # HAS_PROJECT
        task_nodes_map: dict[str, dict[str, Any]] = {}
        relationships_to_create: list[GraphRelationship] = []

        for rdata in records:
            rid = rdata.get("id")
            rtype = rdata.get("record_type", "")
            composite_id = f"{project_id}:{rid}"

            # Determine GraphNodeType
            if rtype == "task":
                gtype = GraphNodeType.TASK
                task_nodes_map[rid] = rdata
                props = {
                    "title": rdata.get("title", ""),
                    "status": rdata.get("status", "todo"),
                    "priority": rdata.get("priority", "medium"),
                }
            elif rtype == "decision":
                gtype = GraphNodeType.DECISION
                props = {
                    "title": rdata.get("title", ""),
                    "status": rdata.get("status", "proposed"),
                    "rationale": rdata.get("rationale", ""),
                    "decision": rdata.get("decision", ""),
                }
            elif rtype == "knowledge":
                k_type = str(rdata.get("knowledge_type", ""))
                content_str = str(rdata.get("content", "")).lower()
                if k_type == "requirement" or "requirement" in content_str or rid.startswith("req"):
                    gtype = GraphNodeType.REQUIREMENT

                    props = {
                        "title": rdata.get("title") or rdata.get("content", "")[:128],
                        "status": rdata.get("verification_status", "verified"),
                        "content": rdata.get("content", ""),
                    }
                else:
                    gtype = GraphNodeType.KNOWLEDGE
                    props = {
                        "knowledge_type": k_type or "fact",
                        "verification_status": rdata.get("verification_status", "unverified"),
                        "content": rdata.get("content", ""),
                    }
            elif rtype == "agent":
                gtype = GraphNodeType.AGENT
                props = {
                    "name": rdata.get("name", ""),
                    "provider": rdata.get("provider", ""),
                    "model": rdata.get("model", ""),
                }
            elif rtype == "checkpoint":
                gtype = GraphNodeType.CHECKPOINT
                props = {
                    "task_id": rdata.get("task_id", ""),
                    "status": rdata.get("status", "active"),
                    "next_action": rdata.get("next_action", ""),
                    "base_revision": rdata.get("base_revision", ""),
                }
            elif rtype == "artifact":
                gtype = GraphNodeType.ARTIFACT
                props = {
                    "artifact_type": rdata.get("artifact_type", "other"),
                    "uri": rdata.get("uri", ""),
                    "content_hash": rdata.get("content_hash", ""),
                }
            elif rtype == "relationship":
                # Handle explicit BMS RelationshipRecord
                src = f"{project_id}:{rdata['source_id']}"
                tgt = f"{project_id}:{rdata['target_id']}"
                bms_rel_type = rdata.get("relationship_type", "").upper()
                if bms_rel_type in GraphRelationshipType.__members__:
                    relationships_to_create.append(
                        GraphRelationship(
                            source_id=src,
                            target_id=tgt,
                            rel_type=GraphRelationshipType(bms_rel_type),
                            project_id=project_id,
                        )
                    )
                continue
            else:
                continue

            node = GraphNode(
                id=composite_id,
                raw_id=rid,
                project_id=project_id,
                node_type=gtype,
                properties=props,
            )
            self.graph.upsert_node(node)
            node_count += 1

            # Default project containment relationship
            rel_type_map = {
                GraphNodeType.TASK: GraphRelationshipType.HAS_TASK,
                GraphNodeType.DECISION: GraphRelationshipType.SUPPORTS,
                GraphNodeType.KNOWLEDGE: GraphRelationshipType.HAS_KNOWLEDGE,
                GraphNodeType.REQUIREMENT: GraphRelationshipType.HAS_REQUIREMENT,
            }
            if gtype in rel_type_map:
                relationships_to_create.append(
                    GraphRelationship(
                        source_id=project_id,
                        target_id=composite_id,
                        rel_type=rel_type_map[gtype],
                        project_id=project_id,
                    )
                )

            # Link author/created_by
            created_by = rdata.get("created_by")
            if created_by:
                agent_composite = f"{project_id}:{created_by}"
                relationships_to_create.append(
                    GraphRelationship(
                        source_id=composite_id,
                        target_id=agent_composite,
                        rel_type=GraphRelationshipType.CREATED_BY,
                        project_id=project_id,
                    )
                )

            # Link Checkpoint -> Task, Decisions, Artifacts
            if gtype == GraphNodeType.CHECKPOINT:
                if rdata.get("task_id"):
                    t_comp = f"{project_id}:{rdata['task_id']}"
                    relationships_to_create.append(
                        GraphRelationship(
                            source_id=composite_id,
                            target_id=t_comp,
                            rel_type=GraphRelationshipType.HAS_CHECKPOINT,
                            project_id=project_id,
                        )
                    )
                for dref in rdata.get("decision_refs", []):
                    relationships_to_create.append(
                        GraphRelationship(
                            source_id=composite_id,
                            target_id=f"{project_id}:{dref}",
                            rel_type=GraphRelationshipType.SUPPORTS,
                            project_id=project_id,
                        )
                    )
                for aref in rdata.get("artifact_refs", []):
                    relationships_to_create.append(
                        GraphRelationship(
                            source_id=composite_id,
                            target_id=f"{project_id}:{aref}",
                            rel_type=GraphRelationshipType.REFERENCES_ARTIFACT,
                            project_id=project_id,
                        )
                    )

        # 7. Validate Task Dependencies and Cycles
        self._validate_task_dependencies(task_nodes_map)

        # Add task dependency edges
        for tid, tdata in task_nodes_map.items():
            deps = tdata.get("dependencies", [])
            for did in deps:
                relationships_to_create.append(
                    GraphRelationship(
                        source_id=f"{project_id}:{tid}",
                        target_id=f"{project_id}:{did}",
                        rel_type=GraphRelationshipType.DEPENDS_ON,
                        project_id=project_id,
                    )
                )

        # 8. Upsert all relationships
        for rel in relationships_to_create:
            self.graph.upsert_relationship(rel)
            rel_count += 1

        # 9. Update graph projection tracking in SQLite
        now = utc_now()
        conn.execute(
            """
            INSERT INTO graph_projections (
                project_id, applied_commit_id, applied_revision, applied_state_hash,
                node_count, relationship_count, status, last_projected_at, last_error
            ) VALUES (?, ?, 1, ?, ?, ?, 'UP_TO_DATE', ?, NULL)
            ON CONFLICT(project_id) DO UPDATE SET
                applied_commit_id = excluded.applied_commit_id,
                applied_revision = applied_revision + 1,
                applied_state_hash = excluded.applied_state_hash,
                node_count = excluded.node_count,
                relationship_count = excluded.relationship_count,
                status = 'UP_TO_DATE',
                last_projected_at = excluded.last_projected_at,
                last_error = NULL;
            """,
            (
                project_id,
                commit_id,
                c_row["resulting_state_hash"],
                node_count,
                rel_count,
                now.isoformat(),
            ),
        )
        conn.commit()
        logger.info(
            "Successfully projected project '%s' graph at commit %s (%d nodes, %d relationships)",
            project_id,
            commit_id[:8],
            node_count,
            rel_count,
        )

    def _validate_task_dependencies(self, tasks_map: dict[str, dict[str, Any]]) -> None:
        """Validate no self-dependencies and no cyclic dependencies exist in tasks."""
        # 1. No self dependency
        for tid, tdata in tasks_map.items():
            deps = tdata.get("dependencies", [])
            if tid in deps:
                raise StorageError(f"Task '{tid}' lists itself as a dependency (self-dependency prohibited)")

        # 2. Cycle detection via DFS
        visited: dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node: str, path: list[str]) -> None:
            visited[node] = 1
            node_data = tasks_map.get(node)
            if node_data:
                for dep in node_data.get("dependencies", []):
                    if dep in tasks_map:
                        if visited.get(dep) == 1:
                            cycle_path = " -> ".join(path + [dep])
                            raise StorageError(f"Cyclic task dependency detected: {cycle_path}")
                        if visited.get(dep, 0) == 0:
                            dfs(dep, path + [dep])
            visited[node] = 2

        for t in tasks_map:
            if visited.get(t, 0) == 0:
                dfs(t, [t])

    # =========================================================================
    # Status & Rebuild
    # =========================================================================

    def get_projection_status(self, project_id: str) -> GraphProjectionMetadata:
        """Expose current projection status, applied revision, and synchronization freshness."""
        conn = self._get_conn()

        # Get authoritative branch HEAD
        cur_b = conn.execute(
            "SELECT head_commit_id FROM branches WHERE project_id = ? AND name = 'main';",
            (project_id,),
        )
        b_row = cur_b.fetchone()
        auth_head = b_row["head_commit_id"] if b_row else None

        cur_p = conn.execute(
            "SELECT * FROM graph_projections WHERE project_id = ?;",
            (project_id,),
        )
        p_row = cur_p.fetchone()

        if not self.graph.is_available():
            status = ProjectionStatus.UNAVAILABLE
        elif not p_row or auth_head and p_row["applied_commit_id"] != auth_head:
            status = ProjectionStatus.LAGGING
        else:
            status = ProjectionStatus(p_row["status"])

        if p_row:
            applied_cid = p_row["applied_commit_id"]
            applied_rev = p_row["applied_revision"]
            applied_hash = p_row["applied_state_hash"]
            node_cnt = p_row["node_count"]
            rel_cnt = p_row["relationship_count"]
            last_dt = datetime.fromisoformat(p_row["last_projected_at"])
            last_err = p_row["last_error"]
        else:
            applied_cid = ""
            applied_rev = 0
            applied_hash = ""
            node_cnt = 0
            rel_cnt = 0
            last_dt = utc_now()
            last_err = None

        is_fresh = (status == ProjectionStatus.UP_TO_DATE) and (applied_cid == auth_head if auth_head else True)

        return GraphProjectionMetadata(
            project_id=project_id,
            applied_commit_id=applied_cid,
            applied_revision=applied_rev,
            applied_state_hash=applied_hash,
            node_count=node_cnt,
            relationship_count=rel_cnt,
            status=status,
            last_projected_at=last_dt,
            last_error=last_err,
            authoritative_commit_id=auth_head,
            is_fresh=is_fresh,
        )

    def rebuild_project_graph(self, project_id: str) -> GraphProjectionMetadata:
        """Administrative rebuild operation reconstructs project graph from authoritative main HEAD."""
        conn = self._get_conn()
        cur_b = conn.execute(
            "SELECT head_commit_id FROM branches WHERE project_id = ? AND name = 'main';",
            (project_id,),
        )
        b_row = cur_b.fetchone()
        if not b_row:
            raise StorageError(f"Project '{project_id}' does not have a main branch to rebuild from")

        head_commit_id = b_row["head_commit_id"]

        # Mark status REBUILDING
        now = utc_now()
        conn.execute(
            """
            INSERT INTO graph_projections (
                project_id, applied_commit_id, applied_revision, applied_state_hash,
                status, last_projected_at
            ) VALUES (?, ?, 0, '', 'REBUILDING', ?)
            ON CONFLICT(project_id) DO UPDATE SET status = 'REBUILDING';
            """,
            (project_id, head_commit_id, now.isoformat()),
        )
        conn.commit()

        # Re-apply projection
        self._apply_commit_projection(project_id, head_commit_id)
        return self.get_projection_status(project_id)
