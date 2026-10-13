"""Tests for SQLite storage engine, transactions, concurrency, and backups."""

import io
from pathlib import Path

import pytest

from barsa.bms.records import (
    ArtifactType,
    KnowledgeRecord,
    KnowledgeType,
    Project,
    ProjectStatus,
    TaskRecord,
    TaskStatus,
    Workspace,
)
from barsa.bms.serialization import import_package
from barsa.core.config import Settings
from barsa.core.exceptions import (
    ConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from barsa.storage.backup import create_backup, restore_backup
from barsa.storage.sqlite import SQLiteStorageProvider


@pytest.fixture
def sqlite_store(tmp_path: Path) -> SQLiteStorageProvider:
    """Fixture creating an initialized SQLiteStorageProvider in a temp directory."""
    db_file = tmp_path / "barsa.db"
    artifacts_folder = tmp_path / "artifacts"
    provider = SQLiteStorageProvider(db_path=db_file, artifacts_dir=artifacts_folder)
    provider.initialize()
    return provider


def test_database_initialization_and_integrity(sqlite_store: SQLiteStorageProvider) -> None:
    """Test database schema creation and PRAGMA integrity check."""
    assert sqlite_store.is_available
    check = sqlite_store.check_integrity()
    assert check["integrity_ok"] is True
    assert check["foreign_key_violations"] == 0


def test_workspace_crud_operations(sqlite_store: SQLiteStorageProvider) -> None:
    """Test workspace create, get, list, update, and delete operations."""
    ws = Workspace(
        id="ws-test-1",
        name="Test Workspace",
        owner_id="owner-1",
        description="Workspace for testing",
    )
    created = sqlite_store.create_workspace(ws)
    assert created.id == "ws-test-1"

    # Duplicate ID check
    with pytest.raises(ConflictError):
        sqlite_store.create_workspace(ws)

    # Retrieval
    retrieved = sqlite_store.get_workspace("ws-test-1")
    assert retrieved is not None
    assert retrieved.name == "Test Workspace"

    # List
    all_ws = sqlite_store.list_workspaces()
    assert len(all_ws) >= 1
    assert any(w.id == "ws-test-1" for w in all_ws)

    # Update
    ws.description = "Updated description"
    updated = sqlite_store.update_workspace(ws, expected_revision=1)
    assert updated.description == "Updated description"

    # Update with wrong revision
    with pytest.raises(ConflictError):
        sqlite_store.update_workspace(ws, expected_revision=1)

    # Delete
    deleted = sqlite_store.delete_workspace("ws-test-1")
    assert deleted is True
    assert sqlite_store.get_workspace("ws-test-1") is None


def test_project_crud_and_workspace_cascade_check(sqlite_store: SQLiteStorageProvider) -> None:
    """Test project operations, foreign key to workspace, and deletion protection."""
    ws = Workspace(id="ws-proj-test", name="Parent WS", owner_id="user-1")
    sqlite_store.create_workspace(ws)

    # Project referencing non-existent workspace must fail
    with pytest.raises(ResourceNotFoundError):
        sqlite_store.create_project(
            Project(
                id="prj-ghost",
                workspace_id="ws-nonexistent",
                name="Ghost Project",
            )
        )

    # Valid project
    prj = Project(
        id="prj-1",
        workspace_id=ws.id,
        name="Project Alpha",
        status=ProjectStatus.ACTIVE,
        goals=["Goal 1"],
    )
    sqlite_store.create_project(prj)

    # Deleting workspace with projects without cascade must raise ConflictError
    with pytest.raises(ConflictError, match="Cannot delete workspace"):
        sqlite_store.delete_workspace(ws.id, cascade=False)

    # Cascade delete
    assert sqlite_store.delete_workspace(ws.id, cascade=True) is True
    assert sqlite_store.get_project("prj-1") is None


def test_bms_record_storage_and_optimistic_concurrency(sqlite_store: SQLiteStorageProvider) -> None:
    """Test record persistence, project scoping, and atomic compare-and-swap revisions."""
    ws = Workspace(id="ws-bms", name="BMS WS", owner_id="user-1")
    sqlite_store.create_workspace(ws)
    prj = Project(id="prj-bms", workspace_id=ws.id, name="BMS Project")
    sqlite_store.create_project(prj)

    task = TaskRecord(
        id="task-01",
        project_id=prj.id,
        title="Setup Auth",
        description="Implement token check",
        status=TaskStatus.TODO,
    )

    # Create
    saved_task, rev1 = sqlite_store.create_record(task)
    assert rev1 == 1
    assert saved_task.id == "task-01"

    # Duplicate in same project must raise ConflictError
    with pytest.raises(ConflictError):
        sqlite_store.create_record(task)

    # Agent A updates at revision 1 -> succeeds, becomes revision 2
    task.status = TaskStatus.IN_PROGRESS
    updated_task, rev2 = sqlite_store.update_record(task, expected_revision=1)
    assert rev2 == 2
    assert updated_task.status == TaskStatus.IN_PROGRESS

    # Agent B attempts update with stale revision 1 -> ConflictError
    task.status = TaskStatus.COMPLETED
    with pytest.raises(ConflictError, match="Conflict updating record"):
        sqlite_store.update_record(task, expected_revision=1)

    # Agent B retries with revision 2 -> succeeds, becomes revision 3
    _, rev3 = sqlite_store.update_record(task, expected_revision=2)
    assert rev3 == 3

    # Project isolation: query from another project returns None
    assert sqlite_store.get_record("other-prj", "task-01") is None


def test_artifact_storage_and_hash_deduplication(sqlite_store: SQLiteStorageProvider) -> None:
    """Test artifact file streaming, SHA-256 computation, and content-addressed storage."""
    ws = Workspace(id="ws-art", name="Art WS", owner_id="u1")
    sqlite_store.create_workspace(ws)
    prj = Project(id="prj-art", workspace_id=ws.id, name="Art Prj")
    sqlite_store.create_project(prj)

    file_content = b"console.log('Hello Barsa');\n"
    stream = io.BytesIO(file_content)

    ref = sqlite_store.artifacts.save_artifact_bytes(
        project_id=prj.id,
        artifact_id="art-code-01",
        file_obj=stream,
        artifact_type=ArtifactType.SOURCE_CODE,
        media_type="text/javascript",
        filename_hint="index.js",
    )

    assert ref.content_hash is not None
    assert ref.size_bytes == len(file_content)

    # Verify blob path
    blob_path = sqlite_store.artifacts.get_artifact_path(ref.content_hash)
    assert blob_path.exists()
    assert blob_path.read_bytes() == file_content

    # Save artifact record in database
    sqlite_store.create_record(ref)
    retrieved_tuple = sqlite_store.get_record(prj.id, "art-code-01")
    assert retrieved_tuple is not None
    rec, _ = retrieved_tuple
    assert rec.record_type == "artifact"


def test_artifact_oversized_rejection(tmp_path: Path) -> None:
    """Test that artifacts exceeding max size are rejected and cleaned up."""
    provider = SQLiteStorageProvider(
        db_path=tmp_path / "barsa.db",
        artifacts_dir=tmp_path / "artifacts",
        max_artifact_size=100,  # Max 100 bytes
    )
    provider.initialize()

    large_bytes = io.BytesIO(b"x" * 500)
    with pytest.raises(ValidationError, match="Artifact exceeds maximum allowed size"):
        provider.artifacts.save_artifact_bytes(
            project_id="prj-1",
            artifact_id="art-oversized",
            file_obj=large_bytes,
        )


def test_package_import_export_roundtrip_in_storage(sqlite_store: SQLiteStorageProvider) -> None:
    """Test saving and loading full BarsaMemoryPackage in SQLite storage."""
    spring_boot_path = Path("examples") / "bms" / "spring_boot_project.json"
    pkg = import_package(spring_boot_path)

    # 1. Save package to database
    sqlite_store.save_package(pkg)

    # 2. Existing project collision check on re-import
    with pytest.raises(ConflictError, match="already exists"):
        sqlite_store.save_package(pkg)

    # 3. Load package from database
    loaded_pkg = sqlite_store.load_package(pkg.project.id)
    assert loaded_pkg is not None
    assert loaded_pkg.workspace.id == pkg.workspace.id
    assert loaded_pkg.project.id == pkg.project.id
    assert len(loaded_pkg.records.tasks) == len(pkg.records.tasks)
    assert len(loaded_pkg.records.decisions) == len(pkg.records.decisions)
    assert loaded_pkg.latest_checkpoint_id == pkg.latest_checkpoint_id


def test_persistence_across_restarts(tmp_path: Path) -> None:
    """Test that data survives database connection restarts."""
    db_file = tmp_path / "persistent.db"
    art_dir = tmp_path / "artifacts"

    # Session 1: create workspace and project
    p1 = SQLiteStorageProvider(db_path=db_file, artifacts_dir=art_dir)
    p1.initialize()
    ws = Workspace(id="ws-restart", name="Restart WS", owner_id="u1")
    p1.create_workspace(ws)
    prj = Project(id="prj-restart", workspace_id=ws.id, name="Restart Prj")
    p1.create_project(prj)
    kn = KnowledgeRecord(
        id="kn-restart",
        project_id=prj.id,
        content="Persistent knowledge across process restarts",
        knowledge_type=KnowledgeType.FACT,
        created_by="agent-1",
    )
    p1.create_record(kn)
    p1.close()

    # Session 2: re-open database
    p2 = SQLiteStorageProvider(db_path=db_file, artifacts_dir=art_dir)
    p2.initialize()
    loaded_ws = p2.get_workspace("ws-restart")
    assert loaded_ws is not None
    assert loaded_ws.name == "Restart WS"

    record_tuple = p2.get_record("prj-restart", "kn-restart")
    assert record_tuple is not None
    rec, rev = record_tuple
    assert rev == 1
    assert rec.id == "kn-restart"
    p2.close()


def test_backup_and_restore(tmp_path: Path) -> None:
    """Test full backup creation and restoration."""
    data_dir = tmp_path / "barsa_data"
    settings = Settings(data_dir=data_dir)
    settings.ensure_data_dir()

    provider = SQLiteStorageProvider(db_path=settings.db_path, artifacts_dir=settings.artifacts_dir)
    provider.initialize()

    ws = Workspace(id="ws-backup", name="Backup WS", owner_id="u1")
    provider.create_workspace(ws)
    prj = Project(id="prj-backup", workspace_id=ws.id, name="Backup Prj")
    provider.create_project(prj)

    # Create backup
    backup_file = create_backup(settings)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    # Modify database after backup
    ws.name = "Mutated After Backup"
    provider.update_workspace(ws)
    assert provider.get_workspace(ws.id).name == "Mutated After Backup"

    # Close active connection to release file locks before restoring
    provider.close()

    # Restore backup
    restore_result = restore_backup(settings, backup_file, confirm_overwrite=True)
    assert restore_result["integrity"]["integrity_ok"] is True

    # Fresh provider verification
    provider_restored = SQLiteStorageProvider(db_path=settings.db_path, artifacts_dir=settings.artifacts_dir)
    provider_restored.initialize()
    restored_ws = provider_restored.get_workspace(ws.id)
    assert restored_ws is not None
    assert restored_ws.name == "Backup WS"
