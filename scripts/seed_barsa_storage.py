"""Seed authoritative SQLite storage (.barsa/barsa.db) and FalkorDB Cloud for Project ATLAS."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root and src to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "demo" / "project-atlas"))

from barsa.bms.records import (
    CheckpointStatus,
    DecisionRecord,
    DecisionStatus,
    KnowledgeRecord,
    KnowledgeType,
    Project,
    ProjectStatus,
    ResumeCheckpoint,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    VerificationStatus,
    Workspace,
)
from barsa.core.config import get_settings
from barsa.graph.factory import get_graph_provider, reset_graph_instances
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.factory import get_storage_provider
from barsa.versioning.engine import VersionControlEngine
from generate_atlas_dataset import get_atlas_dataset
from seed_and_verify_atlas import seed_atlas_graph

def seed_storage_and_cloud():
    settings = get_settings()
    print(f"Using settings db_path: {settings.db_path}")
    print(f"Using FalkorDB host: {settings.falkordb_host}:{settings.falkordb_port} ({settings.falkordb_graph_prefix})")

    storage = get_storage_provider(settings)
    storage.initialize()
    vc = VersionControlEngine(storage)

    dataset = get_atlas_dataset()
    pid = "proj-atlas"
    wid = "ws-atlas"

    # 1. Workspace
    try:
        ws = storage.get_workspace(wid)
        print(f"Workspace {wid} already exists: {ws.name}")
    except Exception:
        ws = Workspace(
            id=wid,
            name=dataset["workspace"]["name"],
            owner_id=dataset["workspace"]["owner_id"],
            description=dataset["workspace"]["description"],
        )
        storage.create_workspace(ws)
        print(f"Created Workspace {wid}")

    # 2. Project
    try:
        proj = storage.get_project(pid)
        print(f"Project {pid} already exists: {proj.name}")
    except Exception:
        proj = Project(
            id=pid,
            workspace_id=wid,
            name=dataset["project"]["name"],
            description=dataset["project"]["description"],
            goals=dataset["project"]["goals"],
            status=ProjectStatus.ACTIVE,
        )
        storage.create_project(proj)
        print(f"Created Project {pid}")

    # 3. Main branch in VC
    branch = vc.get_branch(pid, "main")
    if not branch:
        vc.initialize_project_main_branch(pid, author_id="agent-architect")
        print("Initialized main branch for proj-atlas")

    changes: list[MemoryChange] = []

    # 4. Tasks (60)
    existing_records = {r[0].id if isinstance(r, tuple) else r.id for r in storage.list_records(pid)}
    print(f"Existing records in storage: {len(existing_records)}")

    for t in dataset["tasks"]:
        tid = t["id"]
        status_map = {
            "completed": TaskStatus.COMPLETED,
            "in_progress": TaskStatus.IN_PROGRESS,
            "todo": TaskStatus.TODO,
            "blocked": TaskStatus.BLOCKED,
        }
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }
        tr = TaskRecord(
            id=tid,
            project_id=pid,
            title=t["title"],
            description=t.get("description", f"Requirement module: {t.get('module_id')}"),
            status=status_map.get(t["status"], TaskStatus.TODO),
            priority=priority_map.get(t.get("priority", "medium"), TaskPriority.MEDIUM),
            dependencies=t.get("dependencies", []),
            assigned_agent_id=t.get("assigned_agent_id"),
        )
        if tid not in existing_records:
            storage.create_record(tr)
            changes.append(MemoryChange(record_id=tid, record_type="task", operation=ChangeOperation.CREATE, after_state=tr.model_dump(mode="json")))

    # 5. Decisions (12)
    for d in dataset["decisions"]:
        did = d["id"]
        dr = DecisionRecord(
            id=did,
            project_id=pid,
            title=d["title"],
            decision=d["decision"],
            rationale=d["rationale"],
            status=DecisionStatus.APPROVED,
            created_by="agent-architect",
        )
        if did not in existing_records:
            storage.create_record(dr)
            changes.append(MemoryChange(record_id=did, record_type="decision", operation=ChangeOperation.CREATE, after_state=dr.model_dump(mode="json")))

    # 6. Knowledge (15)
    for k in dataset["knowledge"]:
        kid = k["id"]
        kr = KnowledgeRecord(
            id=kid,
            project_id=pid,
            content=f"{k['title']}: {k.get('content', '')}",
            knowledge_type=KnowledgeType.REFERENCE,
            verification_status=VerificationStatus.VERIFIED,
            created_by="agent-architect",
        )
        if kid not in existing_records:
            storage.create_record(kr)
            changes.append(MemoryChange(record_id=kid, record_type="knowledge", operation=ChangeOperation.CREATE, after_state=kr.model_dump(mode="json")))

    # 7. Checkpoints (8)
    for cp in dataset["checkpoints"]:
        cpid = cp["id"]
        cpr = ResumeCheckpoint(
            id=cpid,
            project_id=pid,
            task_id=cp["task_id"],
            status=CheckpointStatus.ACTIVE if cp["status"] == "in_progress" else CheckpointStatus.COMPLETED,
            completed_actions=cp.get("completed_actions", []),
            pending_actions=cp.get("pending_actions", []),
            next_action=cp.get("next_action", "Proceed to next task"),
            blockers=cp.get("blockers", []),
            decision_refs=cp.get("decision_refs", []),
            artifact_refs=cp.get("artifact_refs", []),
            base_revision=cp.get("base_revision", "init"),
            created_by=cp.get("agent_id", "agent-orchestrator"),
        )
        if cpid not in existing_records:
            storage.create_record(cpr)
            changes.append(MemoryChange(record_id=cpid, record_type="checkpoint", operation=ChangeOperation.CREATE, after_state=cpr.model_dump(mode="json")))

    print(f"Total new records inserted into SQLite: {len(changes)}")

    # 8. Create a baseline commit if changes exist
    if changes:
        try:
            head = vc.get_branch(pid, "main")
            parent_ids = [head.head_commit_id] if (head and head.head_commit_id) else []
            commit = vc.create_commit(
                project_id=pid,
                author_id="agent-orchestrator",
                message="Initial seed of Project ATLAS tasks, decisions, knowledge and checkpoints",
                parent_commit_ids=parent_ids,
                changes=changes,
                branch_name="main",
            )
            print(f"Created baseline commit: {commit.commit_id}")
        except Exception as e:
            print(f"Commit creation notice: {e}")

    # 9. Verify FalkorDB Cloud Graph
    reset_graph_instances()
    graph = get_graph_provider(settings)
    if graph.is_available():
        print("Connected to FalkorDB Cloud graph.")
        # Ensure TASK-017 is 'todo' so it is recommended as the next task
        g = graph._get_graph(pid)
        g.query(f"MATCH (t:Task {{id: '{pid}:TASK-017'}}) SET t.status = 'todo'")
        # Ensure no accidental blockers on TASK-017
        g.query(f"MATCH (t:Task {{id: '{pid}:TASK-017'}})-[r:BLOCKED_BY]->() DELETE r")
        g.query(f"MATCH ()-[r:BLOCKED_BY]->(t:Task {{id: '{pid}:TASK-017'}}) DELETE r")
        print("Reset TASK-017 to 'todo' with zero blockers in FalkorDB Cloud.")
    else:
        print("Warning: FalkorDB is not reachable.")

if __name__ == "__main__":
    seed_storage_and_cloud()
