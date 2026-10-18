"""PROJECT ATLAS — Cross-Session Continuity Demo (Section 9).

Demonstrates:
1. Agent A (e.g. Claude / Backend Lead) works on TASK-017 and saves Checkpoint CP-004.
2. Checkpoint captures completed actions, pending actions, exact next action, and ADR references.
3. Checkpoint is committed and projected into FalkorDB knowledge graph.
4. Agent B (e.g. fresh ChatGPT / QA Engineer) joins with zero conversational context.
5. Agent B queries barsa_resume / barsa_get_checkpoint to retrieve exact execution state.
6. Proves seamless cross-provider / cross-agent handover without context loss or prompt bloat.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from barsa.bms.records import (
    CheckpointStatus,
    Project,
    ResumeCheckpoint,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    Workspace,
)
from barsa.core.config import Settings
from barsa.graph.falkordb import FalkorDBGraphProvider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.models.versioning import AuthorType, ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine

PROJECT_ID = "proj-atlas-session"
WORKSPACE_ID = "ws-atlas-session"


def main():
    print("=" * 80)
    print("PROJECT ATLAS — CROSS-SESSION & CROSS-AGENT HANDOVER DEMO (SECTION 9)")
    print("=" * 80)

    db_path = ROOT_DIR / "data" / "atlas_session.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    storage = SQLiteStorageProvider(db_path, ROOT_DIR / "data" / "art")
    storage.initialize()
    vc = VersionControlEngine(storage)

    # FalkorDB settings & services
    settings = Settings(
        db_path=str(db_path),
        graph_enabled=True,
        falkordb_host=os.getenv("BARSA_FALKORDB_HOST", "127.0.0.1"),
        falkordb_port=int(os.getenv("BARSA_FALKORDB_PORT", "6389")),
        falkordb_graph_prefix="barsa_session",
    )
    graph_provider = FalkorDBGraphProvider(settings)
    retrieval = GraphRetrievalService(graph_provider)
    worker = GraphProjectionWorker(storage, graph_provider)

    # 1. Setup Workspace & Project
    ws = Workspace(id=WORKSPACE_ID, name="ATLAS Session Space", owner_id="org-atlas")
    storage.create_workspace(ws)
    proj = Project(id=PROJECT_ID, workspace_id=WORKSPACE_ID, name="Project ATLAS (Session Demo)")
    storage.create_project(proj)
    main_branch = vc.initialize_project_main_branch(PROJECT_ID)
    print(f"\n[Step 1] Initialized project on main branch: {main_branch.head_commit_id[:12]}...")

    # 2. Agent A (Backend Lead): Working on TASK-017
    print("\n[Step 2] Agent A ('agent-backend') begins implementation of TASK-017...")
    task = TaskRecord(
        id="TASK-017",
        project_id=PROJECT_ID,
        title="Atomic Stock Reservation Service",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.CRITICAL,
        description="Implement high-concurrency stock reservation with optimistic concurrency (ADR-004).",
    )
    storage.create_record(task)
    change_task = MemoryChange(
        record_id="TASK-017",
        record_type="task",
        operation=ChangeOperation.CREATE,
        after_state=task.model_dump(mode="json"),
    )
    commit_task = vc.create_commit(
        project_id=PROJECT_ID,
        branch_name="main",
        changes=[change_task],
        message="TASK-017: Set status to in_progress",
        author_id="agent-backend",
        author_type=AuthorType.AGENT,
    )

    # 3. Agent A saves structured checkpoint CP-004 before session end
    print("\n[Step 3] Agent A pauses work and saves structured checkpoint CP-004...")
    checkpoint = ResumeCheckpoint(
        id="CP-004",
        project_id=PROJECT_ID,
        task_id="TASK-017",
        status=CheckpointStatus.PAUSED,
        completed_actions=[
            "Created StockReservationEntity JPA model with @Version column",
            "Added Flyway V4 migration script for stock_reservations table",
            "Configured Spring Data repository with custom pessimistic lock fallback",
        ],
        pending_actions=[
            "Implement @Retryable service method with exponential backoff",
            "Publish StockReservedApplicationEvent to Kafka topic",
            "Write MockMvc integration tests for concurrent reservation race",
        ],
        next_action="Implement @Retryable StockReservationService.reserveStock() with 3 retries and 50ms backoff",
        blockers=[],
        decision_refs=["ADR-004"],
        artifact_refs=["ART-004"],
        base_revision=commit_task.commit_id,
        created_by="agent-backend",
        environment_description="Java 21 / Spring Boot 3.3 / Maven / MySQL 8.0",
    )
    storage.create_record(checkpoint)

    change_cp = MemoryChange(
        record_id="CP-004",
        record_type="checkpoint",
        operation=ChangeOperation.CREATE,
        after_state=checkpoint.model_dump(mode="json"),
    )
    commit_cp = vc.create_commit(
        project_id=PROJECT_ID,
        branch_name="main",
        changes=[change_cp],
        message="Save checkpoint CP-004: In-progress stock reservation logic",
        author_id="agent-backend",
        author_type=AuthorType.AGENT,
    )
    print(f"-> Checkpoint CP-004 committed at {commit_cp.commit_id[:12]}")

    # Project into FalkorDB
    try:
        worker.process_pending_events(PROJECT_ID)
        print("-> Projected checkpoint and task into FalkorDB knowledge graph.")
    except Exception as e:
        print(f"-> Projection notice: {e}")

    # 4. Agent A session terminates (clean memory purge)
    print("\n[Step 4] Agent A session completely terminated. Conversational buffer wiped.")

    # 5. Agent B (Fresh ChatGPT / QA Engineer) arrives with ZERO prior context
    print("\n[Step 5] Agent B ('agent-qa') starts a fresh session and calls barsa_resume...")
    from barsa.mcp.tools import get_checkpoint_tool, resume_tool

    # Query via MCP tool
    cp_data = get_checkpoint_tool(storage, PROJECT_ID, task_id="TASK-017")
    print(f"\n[Step 6] Agent B successfully retrieved checkpoint:")
    print(f"   Checkpoint ID   : {cp_data['checkpoint_id']}")
    print(f"   Associated Task : {cp_data['task_id']}")
    print(f"   Created By      : {cp_data['created_by']}")
    print(f"   Status          : {cp_data['status']}")
    print(f"   Completed Steps : {len(cp_data['completed_actions'])}")
    for action in cp_data["completed_actions"]:
        print(f"     [x] {action}")
    print(f"   Pending Steps   : {len(cp_data['pending_actions'])}")
    for action in cp_data["pending_actions"]:
        print(f"     [ ] {action}")
    print(f"\n   >>> IMMEDIATE NEXT ACTION <<<")
    print(f"   '{cp_data['next_action']}'")
    print(f"   Governing Decisions : {cp_data['decision_refs']}")

    assert cp_data["checkpoint_id"] == "CP-004"
    assert "StockReservationService.reserveStock()" in cp_data["next_action"]
    assert "ADR-004" in cp_data["decision_refs"]

    print("\n" + "=" * 80)
    print("CROSS-SESSION CONTINUATION VERIFIED: ZERO CONTEXT LOSS, EXACT HANDOVER ACHIEVED!")
    print("=" * 80)


if __name__ == "__main__":
    main()
