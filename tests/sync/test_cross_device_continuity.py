"""Cross-device portability and memory continuity integration tests."""

from pathlib import Path

import pytest

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
    Workspace,
)
from barsa.models.versioning import AuthorType, ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.sync.models import RemoteCreate, RemoteProviderType
from barsa.sync.service import SyncService
from barsa.versioning.engine import VersionControlEngine


def init_device(base_dir: Path, db_name: str) -> tuple[SQLiteStorageProvider, VersionControlEngine, SyncService]:
    storage = SQLiteStorageProvider(db_path=base_dir / f"{db_name}.db", artifacts_dir=base_dir / f"{db_name}_art")
    storage.initialize()
    vc = VersionControlEngine(storage)
    service = SyncService(storage=storage)
    return storage, vc, service


@pytest.mark.asyncio
async def test_cross_device_complete_continuity(tmp_path: Path):
    """Device A (author memory & push) -> Device B (fresh pull, inspect, extend & push) -> Device A (pull & verify)."""
    proj_id = "proj-mars-rover"
    ws_id = "ws-space"
    remote_dir = tmp_path / "mars_byos_remote"
    remote_dir.mkdir()

    # -------------------------------------------------------------
    # Step 1: Device A prepares memory and pushes to remote
    # -------------------------------------------------------------
    store_a, vc_a, sync_a = init_device(tmp_path, "device_a")
    store_a.create_workspace(Workspace(id=ws_id, name="Space Ops", owner_id="user-nasa"))
    store_a.create_project(Project(id=proj_id, workspace_id=ws_id, name="Mars Rover", status=ProjectStatus.ACTIVE))

    rem_a = sync_a.create_remote(
        project_id=proj_id,
        req=RemoteCreate(
            name="central-byos",
            provider_type=RemoteProviderType.LOCAL,
            local_path=str(remote_dir),
            encryption_enabled=True,
        ),
    )

    # Device A records
    kr1 = KnowledgeRecord(
        id="fact-terrain-01",
        project_id=proj_id,
        content="Gale Crater has high basalt concentration and loose sand dunes.",
        knowledge_type=KnowledgeType.FACT,
        created_by="agent-curiosity",
    )
    dec1 = DecisionRecord(
        id="dec-route-01",
        project_id=proj_id,
        title="Route Choice: Eastern Ridge",
        decision="Traverse via eastern ridge to avoid wheel slip.",
        rationale="Ridge slope is 12 degrees vs 26 degrees on western dunes.",
        status=DecisionStatus.APPROVED,
        created_by="agent-curiosity",
    )
    chk1 = ResumeCheckpoint(
        id="chk-sol-142",
        project_id=proj_id,
        task_id="task-traverse",
        status=CheckpointStatus.ACTIVE,
        next_action="Sample basalt at Waypoint 4",
        base_revision="rev-1",
        created_by="agent-curiosity",
        summary="Completed 120m traverse. Parked facing north for solar recharge.",
        completed_actions=["Navigated eastern ridge 120m"],
        pending_actions=["Sample basalt at Waypoint 4", "Inspect wheel tread"],
    )

    changes_a = [
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id=kr1.id,
            record_type="knowledge",
            after_state=kr1.model_dump(mode="json"),
        ),
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id=dec1.id,
            record_type="decision",
            after_state=dec1.model_dump(mode="json"),
        ),
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id=chk1.id,
            record_type="checkpoint",
            after_state=chk1.model_dump(mode="json"),
        ),
    ]

    commit_a1 = vc_a.create_commit(
        project_id=proj_id,
        branch_name="main",
        changes=changes_a,
        message="Sol 142 traverse complete",
        author_id="agent-curiosity",
        author_type=AuthorType.AGENT,
    )
    assert commit_a1 is not None

    # Push to encrypted remote
    passphrase = "MissionToMarsSecureKey2026!"
    push_res_a = await sync_a.push(rem_a.id, branch_name="main", passphrase=passphrase)
    assert push_res_a.success is True
    assert push_res_a.objects_uploaded > 0

    # -------------------------------------------------------------
    # Step 2: Device B (Perseverance) starts with zero local memory
    # -------------------------------------------------------------
    store_b, vc_b, sync_b = init_device(tmp_path, "device_b")
    store_b.create_workspace(Workspace(id=ws_id, name="Space Ops", owner_id="user-nasa"))
    store_b.create_project(Project(id=proj_id, workspace_id=ws_id, name="Mars Rover", status=ProjectStatus.ACTIVE))

    rem_b = sync_b.create_remote(
        project_id=proj_id,
        req=RemoteCreate(
            name="central-byos",
            provider_type=RemoteProviderType.LOCAL,
            local_path=str(remote_dir),
            encryption_enabled=True,
        ),
    )

    # Pull and decrypt
    pull_res_b = await sync_b.pull(rem_b.id, branch_name="main", passphrase=passphrase)
    assert pull_res_b.success is True
    assert pull_res_b.objects_downloaded > 0

    # Device B verifies memory continuity
    retrieved_kr, _ = store_b.get_record(proj_id, "fact-terrain-01")
    assert retrieved_kr is not None
    assert "basalt concentration" in retrieved_kr.content

    retrieved_dec, _ = store_b.get_record(proj_id, "dec-route-01")
    assert retrieved_dec is not None
    assert retrieved_dec.status == DecisionStatus.APPROVED

    retrieved_chk, _ = store_b.get_record(proj_id, "chk-sol-142")
    assert retrieved_chk is not None
    assert "Waypoint 4" in retrieved_chk.next_action

    # Device B acts on recommended steps: adds Task and completes it
    task1 = TaskRecord(
        id="task-drill-01",
        project_id=proj_id,
        title="Sample basalt rock core",
        status=TaskStatus.COMPLETED,
        priority=TaskPriority.HIGH,
        assigned_agent_id="agent-perseverance",
    )
    change_b = MemoryChange(
        operation=ChangeOperation.CREATE,
        record_id=task1.id,
        record_type="task",
        after_state=task1.model_dump(mode="json"),
    )
    commit_b1 = vc_b.create_commit(
        project_id=proj_id,
        branch_name="main",
        changes=[change_b],
        message="Completed core sample at Waypoint 4",
        author_id="agent-perseverance",
        author_type=AuthorType.AGENT,
    )
    push_res_b = await sync_b.push(rem_b.id, branch_name="main", passphrase=passphrase)
    assert push_res_b.success is True

    # -------------------------------------------------------------
    # Step 3: Device A pulls updates back and confirms full state
    # -------------------------------------------------------------
    pull_res_a2 = await sync_a.pull(rem_a.id, branch_name="main", passphrase=passphrase)
    assert pull_res_a2.success is True
    assert pull_res_a2.remote_head_commit_id == commit_b1.commit_id

    # Verify Device A now has the task completed by Device B
    retrieved_task, _ = store_a.get_record(proj_id, "task-drill-01")
    assert retrieved_task is not None
    assert retrieved_task.status == TaskStatus.COMPLETED
    assert retrieved_task.assigned_agent_id == "agent-perseverance"
