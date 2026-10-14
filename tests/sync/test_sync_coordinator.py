"""Tests for SyncCoordinator push, pull, status reporting, and history."""

from pathlib import Path

import pytest

from barsa.bms.records import KnowledgeRecord, KnowledgeType, Project, ProjectStatus, Workspace
from barsa.models.versioning import AuthorType, ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.sync.models import RemoteCreate, RemoteProviderType, SyncOperation, SyncStatus
from barsa.sync.service import SyncService
from barsa.versioning.engine import VersionControlEngine


@pytest.fixture
def storage(tmp_path: Path) -> SQLiteStorageProvider:
    db_file = tmp_path / "barsa_sync_test.db"
    artifacts_dir = tmp_path / "artifacts"
    provider = SQLiteStorageProvider(db_path=db_file, artifacts_dir=artifacts_dir)
    provider.initialize()
    return provider


@pytest.fixture
def vc(storage: SQLiteStorageProvider) -> VersionControlEngine:
    return VersionControlEngine(storage)


@pytest.fixture
def sync_service(storage: SQLiteStorageProvider) -> SyncService:
    return SyncService(storage=storage)


def setup_project(storage: SQLiteStorageProvider) -> str:
    """Helper to insert workspace and project."""
    ws_id = "ws-sync-01"
    proj_id = "proj-sync-01"
    if not storage.get_workspace(ws_id):
        storage.create_workspace(Workspace(id=ws_id, name="Sync WS", owner_id="user-1"))
    if not storage.get_project(proj_id):
        storage.create_project(Project(id=proj_id, workspace_id=ws_id, name="Sync Proj", status=ProjectStatus.ACTIVE))
    return proj_id


@pytest.mark.asyncio
async def test_coordinator_push_and_status(
    storage: SQLiteStorageProvider,
    vc: VersionControlEngine,
    sync_service: SyncService,
    tmp_path: Path,
):
    """Verify push uploads commits and objects, updating sync status to up_to_date."""
    proj_id = setup_project(storage)
    remote_dir = tmp_path / "remote_storage"
    remote_dir.mkdir()

    # 1. Create remote
    remote_resp = sync_service.create_remote(
        project_id=proj_id,
        req=RemoteCreate(
            name="origin",
            provider_type=RemoteProviderType.LOCAL,
            local_path=str(remote_dir),
            encryption_enabled=False,
        ),
    )
    remote_id = remote_resp.id

    # 2. Make an initial commit
    kr = KnowledgeRecord(
        id="fact-001",
        project_id=proj_id,
        content="Knowledge A",
        knowledge_type=KnowledgeType.FACT,
        created_by="agent-1",
    )
    change = MemoryChange(
        operation=ChangeOperation.CREATE,
        record_id=kr.id,
        record_type="knowledge",
        after_state=kr.model_dump(mode="json"),
    )
    commit = vc.create_commit(
        project_id=proj_id,
        branch_name="main",
        changes=[change],
        message="Initial sync commit",
        author_id="agent-1",
        author_type=AuthorType.AGENT,
    )
    assert commit is not None

    # 3. Check status before push (should be ahead or uninitialized)
    status_report = await sync_service.get_status(remote_id=remote_id, branch_name="main")
    assert status_report.status in (SyncStatus.AHEAD, SyncStatus.IDLE, SyncStatus.DIVERGED)

    # 4. Push to remote
    push_res = await sync_service.push(remote_id=remote_id, branch_name="main")
    assert push_res.success is True
    assert push_res.objects_uploaded > 0
    assert push_res.local_head_commit_id == commit.commit_id

    # 5. Check status after push (should be UP_TO_DATE)
    status_after = await sync_service.get_status(remote_id=remote_id, branch_name="main")
    assert status_after.status == SyncStatus.UP_TO_DATE
    assert status_after.remote_head_commit_id == commit.commit_id

    # 6. Verify history was recorded
    history = sync_service.get_history(remote_id=remote_id)
    assert len(history) >= 1
    assert history[0]["operation"] == SyncOperation.PUSH.value
    assert history[0]["status"] == "success"


@pytest.mark.asyncio
async def test_coordinator_pull_into_fresh_storage(
    storage: SQLiteStorageProvider,
    vc: VersionControlEngine,
    sync_service: SyncService,
    tmp_path: Path,
):
    """Verify pulling commits and BMS records into a fresh secondary storage installation."""
    proj_id = setup_project(storage)
    remote_dir = tmp_path / "shared_remote"
    remote_dir.mkdir()

    # Device A setup & commit
    sync_service.create_remote(
        project_id=proj_id,
        req=RemoteCreate(
            name="origin",
            provider_type=RemoteProviderType.LOCAL,
            local_path=str(remote_dir),
            encryption_enabled=False,
        ),
    )
    rem_a = sync_service.list_remotes(proj_id)[0]

    kr = KnowledgeRecord(
        id="fact-pull-001",
        project_id=proj_id,
        content="Device A Knowledge Payload",
        knowledge_type=KnowledgeType.FACT,
        created_by="agent-device-a",
    )
    ch = MemoryChange(
        operation=ChangeOperation.CREATE,
        record_id=kr.id,
        record_type="knowledge",
        after_state=kr.model_dump(mode="json"),
    )
    commit = vc.create_commit(
        project_id=proj_id,
        branch_name="main",
        changes=[ch],
        message="Device A first commit",
        author_id="agent-device-a",
        author_type=AuthorType.AGENT,
    )
    push_res = await sync_service.push(rem_a.id, branch_name="main")
    assert push_res.success is True

    # Device B (fresh independent storage)
    storage_b = SQLiteStorageProvider(
        db_path=tmp_path / "device_b.db",
        artifacts_dir=tmp_path / "device_b_artifacts",
    )
    storage_b.initialize()
    setup_project(storage_b)
    sync_service_b = SyncService(storage=storage_b)

    rem_b_resp = sync_service_b.create_remote(
        project_id=proj_id,
        req=RemoteCreate(
            name="origin",
            provider_type=RemoteProviderType.LOCAL,
            local_path=str(remote_dir),
            encryption_enabled=False,
        ),
    )

    # Pull on Device B
    pull_res = await sync_service_b.pull(rem_b_resp.id, branch_name="main")
    assert pull_res.success is True
    assert pull_res.objects_downloaded > 0
    assert pull_res.remote_head_commit_id == commit.commit_id

    # Verify Device B now has the record in active storage
    rec_b = storage_b.get_record(proj_id, "fact-pull-001")
    assert rec_b is not None
    record_obj, _ = rec_b
    assert record_obj.id == "fact-pull-001"
    assert record_obj.content == "Device A Knowledge Payload"
