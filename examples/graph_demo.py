"""BARSA Phase 5 Knowledge Graph Demonstration Scenario.

Demonstrates:
1. Research Agent commits requirements.
2. Architecture Agent commits decision linked to requirements.
3. Coding Agent commits tasks implementing the decision and creates a resume checkpoint.
4. Query: 'What is the full context needed to resume task X?' -> Returns decision, requirements,
   artifacts, and checkpoint in a single graph traversal.
5. Update: Decision is modified -> Graph reflects the change, previous versions preserved in version control.
6. Offline: FalkorDB is shut down/unavailable -> System continues operating with SQLite only,
   outbox events queue up, and graph rebuilds/catches up cleanly.
"""

import tempfile
from pathlib import Path

from barsa.bms.records import (
    ArtifactReference,
    ArtifactType,
    CheckpointStatus,
    DecisionRecord,
    DecisionStatus,
    KnowledgeRecord,
    KnowledgeType,
    Project,
    RelationshipRecord,
    RelationshipType,
    ResumeCheckpoint,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    VerificationStatus,
    Workspace,
)
from barsa.graph.memory import InMemoryGraphProvider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


def run_demonstration() -> None:
    print("=" * 70)
    print("BARSA Knowledge Graph Engine — Multi-Agent Collaboration Demo")
    print("=" * 70)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "barsa_demo.db"
        artifacts_dir = tmp_path / "artifacts"

        # 0. Initialize Storage, VC, and Graph
        storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
        storage.initialize()
        try:
            vc = VersionControlEngine(storage)
            graph = InMemoryGraphProvider()
            worker = GraphProjectionWorker(storage, graph)
            retrieval = GraphRetrievalService(graph)

            # Create Workspace and Project
            ws = storage.create_workspace(Workspace(id="ws-enterprise", name="Enterprise Workspace", owner_id="user-1"))
            proj = storage.create_project(
                Project(
                    id="proj-auth-svc", name="Auth Microservice", workspace_id=ws.id, description="OAuth2 & JWT Service"
                )
            )
            vc.initialize_project_main_branch(proj.id)
            worker.process_pending_events(proj.id)

            print(f"\n[INIT] Initialized Project: {proj.name} ({proj.id})")

            # -------------------------------------------------------------
            # Step 1: Research Agent commits requirements
            # -------------------------------------------------------------
            print("\n--- STEP 1: Research Agent commits requirements ---")
            req_record = KnowledgeRecord(
                id="req-jwt-security",
                project_id=proj.id,
                content="System Requirement: Stateless authentication with cryptographic signature verification and under 50ms latency.",
                knowledge_type=KnowledgeType.FACT,
                verification_status=VerificationStatus.VERIFIED,
                created_by="research-agent-01",
            )
            c1 = vc.create_commit(
                project_id=proj.id,
                branch_name="main",
                changes=[
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=req_record.id,
                        record_type="knowledge",
                        after_state=req_record.model_dump(mode="json"),
                    )
                ],
                message="Add authentication latency and security requirements",
                author_id="research-agent-01",
            )
            worker.process_pending_events(proj.id)
            print(f"Commit {c1.commit_id[:10]} authored by research-agent-01")
            print(f"Graph projected requirement node: {req_record.id}")

            # -------------------------------------------------------------
            # Step 2: Architecture Agent commits decision linked to requirement
            # -------------------------------------------------------------
            print("\n--- STEP 2: Architecture Agent commits architectural decision ---")
            dec_record = DecisionRecord(
                id="dec-ed25519-jwt",
                project_id=proj.id,
                title="Adopt Ed25519 asymmetric keys for JWT validation",
                decision="Approved for core auth tokens",
                rationale="Ed25519 provides ultra-fast signature verification satisfying the <50ms requirement.",
                status=DecisionStatus.APPROVED,
                created_by="arch-agent-02",
            )
            rel_dec_req = RelationshipRecord(
                id="rel-dec-req",
                project_id=proj.id,
                source_id=dec_record.id,
                target_id=req_record.id,
                relationship_type=RelationshipType.SUPPORTS,
            )
            c2 = vc.create_commit(
                project_id=proj.id,
                branch_name="main",
                changes=[
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=dec_record.id,
                        record_type="decision",
                        after_state=dec_record.model_dump(mode="json"),
                    ),
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=rel_dec_req.id,
                        record_type="relationship",
                        after_state=rel_dec_req.model_dump(mode="json"),
                    ),
                ],
                message="Architectural decision: Use Ed25519 for JWT",
                author_id="arch-agent-02",
            )
            worker.process_pending_events(proj.id)
            print(f"Commit {c2.commit_id[:10]} authored by arch-agent-02")
            print(f"Graph projected decision node: {dec_record.id} linked to {req_record.id}")

            # -------------------------------------------------------------
            # Step 3: Coding Agent commits tasks implementing the decision and a checkpoint
            # -------------------------------------------------------------
            print("\n--- STEP 3: Coding Agent commits task and resume checkpoint ---")
            task_record = TaskRecord(
                id="task-jwt-verifier",
                project_id=proj.id,
                title="Implement Ed25519 JWT Token Verifier",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                assigned_agent_id="coding-agent-03",
                dependencies=[],
            )
            art_record = ArtifactReference(
                id="art-jwt-src",
                project_id=proj.id,
                artifact_type=ArtifactType.SOURCE_CODE,
                uri="src/auth/jwt_verifier.py",
                content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                media_type="text/x-python",
                size_bytes=1024,
            )
            cp_record = ResumeCheckpoint(
                id="cp-jwt-progress",
                project_id=proj.id,
                task_id="task-jwt-verifier",
                status=CheckpointStatus.ACTIVE,
                completed_actions=["Parsed key bytes and header algorithms"],
                pending_actions=["Implement signature validation", "Write expired token unit tests"],
                next_action="Write unit tests for signature validation",
                blockers=[],
                decision_refs=[dec_record.id],
                artifact_refs=[art_record.id],
                base_revision=c2.commit_id,
                created_by="coding-agent-03",
            )
            rel_task_dec = RelationshipRecord(
                id="rel-task-dec",
                project_id=proj.id,
                source_id=task_record.id,
                target_id=dec_record.id,
                relationship_type=RelationshipType.IMPLEMENTS,
            )
            rel_task_req = RelationshipRecord(
                id="rel-task-req",
                project_id=proj.id,
                source_id=task_record.id,
                target_id=req_record.id,
                relationship_type=RelationshipType.IMPLEMENTS,
            )
            c3 = vc.create_commit(
                project_id=proj.id,
                branch_name="main",
                changes=[
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=task_record.id,
                        record_type="task",
                        after_state=task_record.model_dump(mode="json"),
                    ),
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=art_record.id,
                        record_type="artifact",
                        after_state=art_record.model_dump(mode="json"),
                    ),
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=cp_record.id,
                        record_type="checkpoint",
                        after_state=cp_record.model_dump(mode="json"),
                    ),
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=rel_task_dec.id,
                        record_type="relationship",
                        after_state=rel_task_dec.model_dump(mode="json"),
                    ),
                    MemoryChange(
                        operation=ChangeOperation.CREATE,
                        record_id=rel_task_req.id,
                        record_type="relationship",
                        after_state=rel_task_req.model_dump(mode="json"),
                    ),
                ],
                message="Task implementation, artifact reference, and working checkpoint",
                author_id="coding-agent-03",
            )
            worker.process_pending_events(proj.id)
            print(f"Commit {c3.commit_id[:10]} authored by coding-agent-03")
            print(f"Graph projected task {task_record.id} and checkpoint {cp_record.id}")

            # -------------------------------------------------------------
            # Step 4: Semantic Query: What is the full context needed to resume task?
            # -------------------------------------------------------------
            print("\n--- STEP 4: Query: Resume Context for 'task-jwt-verifier' ---")
            context = retrieval.get_resume_context(proj.id, "task-jwt-verifier")
            task_props = context.task.get("properties", {}) if context.task else {}
            print(f"Target Task:       {task_props.get('title')} [{task_props.get('status')}]")
            if context.latest_checkpoint:
                cp = context.latest_checkpoint
                cp_props = cp.get("properties", {})
                print(f"Latest Checkpoint: {cp.get('raw_id')}")
                print(f"  Status:          {cp_props.get('status')}")
                print(f"  Next Action:     {cp_props.get('next_action')}")
            print(f"Decisions Linked:  {len(context.relevant_decisions)}")
            for d in context.relevant_decisions:
                d_props = d.get("properties", {})
                print(f"  - Decision {d.get('raw_id')}: {d_props.get('title')}")
            print(f"Requirements:      {len(context.requirements)}")
            for r in context.requirements:
                r_props = r.get("properties", {})
                print(f"  - Requirement {r.get('raw_id')}: {r_props.get('content')}")

            # -------------------------------------------------------------
            # Step 5: Update Decision -> Graph updates, history preserved
            # -------------------------------------------------------------
            print("\n--- STEP 5: Decision update -> Graph updates, VC preserves history ---")
            updated_dec = dec_record.model_copy(
                update={"status": DecisionStatus.SUPERSEDED, "decision": "Replaced by Post-Quantum lattice auth"}
            )
            c4 = vc.create_commit(
                project_id=proj.id,
                branch_name="main",
                changes=[
                    MemoryChange(
                        operation=ChangeOperation.UPDATE,
                        record_id=dec_record.id,
                        record_type="decision",
                        before_state=dec_record.model_dump(mode="json"),
                        after_state=updated_dec.model_dump(mode="json"),
                    )
                ],
                message="Deprecate Ed25519 decision in favor of post-quantum",
                author_id="arch-agent-02",
            )
            worker.process_pending_events(proj.id)
            print(f"Commit {c4.commit_id[:10]} updated decision to SUPERSEDED")

            # Check graph node
            node_after = graph.get_node(proj.id, dec_record.id)
            assert node_after is not None
            print(f"Graph node updated status: {node_after.properties.get('status')}")
            print(f"Graph node updated decision: {node_after.properties.get('decision')}")

            # Verify historical version control log
            commits = vc.get_history(proj.id, "main")
            print(f"Authoritative commits in history: {len(commits)}")
            for c in commits:
                print(f"  - {c.commit_id[:10]} | {c.author_id} | {c.message}")

            # -------------------------------------------------------------
            # Step 6: Offline Resilience & Rebuild
            # -------------------------------------------------------------
            print("\n--- STEP 6: Offline Simulation and Full State Rebuild ---")
            # Simulate offline graph: wipe out the graph entirely
            graph.clear_project_graph(proj.id)
            assert graph.get_node(proj.id, "task-jwt-verifier") is None
            print("Graph was cleared to simulate database restart or offline recovery.")

            # Rebuild graph from authoritative SQLite store
            print("Executing worker.rebuild_project_graph()...")
            rebuild_meta = worker.rebuild_project_graph(proj.id)
            print(f"Rebuild completed with status: {rebuild_meta.status}")
            print(f"Rebuild applied commit: {rebuild_meta.applied_commit_id[:10]}")

            restored_task = graph.get_node(proj.id, "task-jwt-verifier")
            assert restored_task is not None
            print(f"Verified restored task node in graph: {restored_task.properties.get('title')}")

            print("\n" + "=" * 70)
            print("DEMONSTRATION COMPLETED SUCCESSFULLY")
            print("=" * 70)
        finally:
            storage.close()


if __name__ == "__main__":
    run_demonstration()
