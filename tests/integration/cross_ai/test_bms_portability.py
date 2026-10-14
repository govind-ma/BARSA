"""BMS Package export, import, and cross-storage portability tests (Phase 12)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from barsa.bms.records import (
    CheckpointStatus,
    DecisionRecord,
    DecisionStatus,
    KnowledgeRecord,
    KnowledgeType,
    Project,
    ResumeCheckpoint,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    VerificationStatus,
    Workspace,
)
from barsa.bms.serialization import export_package, import_package
from barsa.core.config import Settings
from barsa.core.exceptions import ConflictError, StorageError
from barsa.storage.factory import get_storage_provider

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def dual_storage_env(tmp_path: Path):
    """Provides two strictly independent SQLite storage instances."""
    dir_1 = tmp_path / "storage_instance_1"
    dir_2 = tmp_path / "storage_instance_2"

    settings_1 = Settings(
        app_name="BARSA-Storage-1",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=dir_1,
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings_1.ensure_data_dir()
    storage_1 = get_storage_provider(settings_1)

    settings_2 = Settings(
        app_name="BARSA-Storage-2",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=dir_2,
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings_2.ensure_data_dir()
    storage_2 = get_storage_provider(settings_2)

    yield {
        "storage_1": storage_1,
        "storage_2": storage_2,
        "tmp_path": tmp_path,
    }

    storage_1.close()
    storage_2.close()


def test_bms_export_and_import_between_isolated_storages(dual_storage_env: dict) -> None:
    """Export project from Storage 1, import into empty Storage 2, and verify byte-for-byte fidelity."""
    storage_1 = dual_storage_env["storage_1"]
    storage_2 = dual_storage_env["storage_2"]
    tmp_path: Path = dual_storage_env["tmp_path"]

    proj_id = "proj-portable-alpha"
    ws_id = "ws-portable-1"

    # 1. Populate Storage 1 with rich project memory
    ws = storage_1.create_workspace(Workspace(id=ws_id, name="Portable Workspace", owner_id="architect"))
    proj = storage_1.create_project(
        Project(
            id=proj_id,
            name="Portable Microservice Memory",
            workspace_id=ws.id,
            description="Self-contained project package for cross-instance migration",
        )
    )

    dec = storage_1.create_record(
        DecisionRecord(
            id="dec-arch-event-driven",
            project_id=proj_id,
            title="Adopt Event-Driven Architecture",
            decision="Use event streams for inter-service communication",
            rationale="Decouples services and ensures eventual consistency",
            status=DecisionStatus.APPROVED,
            created_by="agent-architect",
        )
    )[0]

    task = storage_1.create_record(
        TaskRecord(
            id="task-setup-kafka",
            project_id=proj_id,
            title="Configure Event Bus",
            description="Setup schema registry and connection pools",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
        )
    )[0]

    know = storage_1.create_record(
        KnowledgeRecord(
            id="k-kafka-partitions",
            project_id=proj_id,
            content="Partition key MUST be tenant_id to guarantee in-order delivery.",
            knowledge_type=KnowledgeType.FACT,
            verification_status=VerificationStatus.VERIFIED,
            created_by="agent-researcher",
        )
    )[0]

    storage_1.create_record(
        ResumeCheckpoint(
            id="chk-migration-checkpoint",
            project_id=proj_id,
            task_id="task-setup-kafka",
            status=CheckpointStatus.ACTIVE,
            completed_actions=["Created event schema", "Configured producer pool"],
            pending_actions=["Implement consumer retry topic"],
            next_action="Implement consumer dead-letter queue",
            blockers=[],
            decision_refs=[dec.id],
            artifact_refs=[],
            base_revision="rev-001",
            created_by="agent-committer",
        )
    )[0]

    # 2. Export Package from Storage 1
    pkg = storage_1.load_package(proj_id)
    assert pkg is not None
    assert pkg.project.id == proj_id

    export_file = tmp_path / "portable_project_pkg.json"
    export_package(pkg, export_file)
    assert export_file.exists()
    assert export_file.stat().st_size > 0

    # 3. Verify Storage 2 is completely empty initially
    assert storage_2.get_project(proj_id) is None
    assert storage_2.get_workspace(ws_id) is None

    # 4. Import Package into Storage 2
    imported_pkg = import_package(export_file)
    assert imported_pkg.project.id == proj_id
    storage_2.save_package(imported_pkg)

    # 5. Verify records in Storage 2 match Storage 1 exactly
    proj_2 = storage_2.get_project(proj_id)
    assert proj_2 is not None
    assert proj_2.name == proj.name
    assert proj_2.description == proj.description

    ws_2 = storage_2.get_workspace(ws_id)
    assert ws_2 is not None
    assert ws_2.name == ws.name

    dec_res = storage_2.get_record(proj_id, "dec-arch-event-driven")
    assert dec_res is not None
    assert dec_res[0].decision == dec.decision

    task_res = storage_2.get_record(proj_id, "task-setup-kafka")
    assert task_res is not None
    assert task_res[0].status == task.status

    know_res = storage_2.get_record(proj_id, "k-kafka-partitions")
    assert know_res is not None
    assert know_res[0].content == know.content

    chk_res = storage_2.get_record(proj_id, "chk-migration-checkpoint")
    assert chk_res is not None
    assert chk_res[0].next_action == "Implement consumer dead-letter queue"
    assert chk_res[0].completed_actions == ["Created event schema", "Configured producer pool"]


def test_bms_duplicate_import_conflict(dual_storage_env: dict) -> None:
    """Verify importing an existing project into storage raises ConflictError."""
    storage_1 = dual_storage_env["storage_1"]
    proj_id = "proj-dup-test"
    ws = storage_1.create_workspace(Workspace(id="ws-dup", name="Dup WS", owner_id="owner"))
    storage_1.create_project(Project(id=proj_id, name="Dup Proj", workspace_id=ws.id))

    pkg = storage_1.load_package(proj_id)
    assert pkg is not None

    # Attempting to save the package into the same storage instance where project exists
    with pytest.raises(ConflictError, match="already exists"):
        storage_1.save_package(pkg)


def test_bms_corrupt_package_rejection(dual_storage_env: dict) -> None:
    """Verify save_package rejects corrupt/tampered packages with validation errors."""
    storage_1 = dual_storage_env["storage_1"]
    storage_2 = dual_storage_env["storage_2"]

    proj_id = "proj-corrupt-test"
    ws = storage_1.create_workspace(Workspace(id="ws-corrupt", name="Corrupt WS", owner_id="owner"))
    storage_1.create_project(Project(id=proj_id, name="Corrupt Proj", workspace_id=ws.id))

    pkg = storage_1.load_package(proj_id)
    assert pkg is not None

    # Tamper with project workspace reference to create invalid referential integrity
    pkg.project.workspace_id = "mismatched-workspace-id"

    with pytest.raises(StorageError, match="Cannot import invalid package"):
        storage_2.save_package(pkg)
