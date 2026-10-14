"""Synchronization performance benchmarks for Small (20), Medium (200), and Large (2000) records."""

import time
from pathlib import Path

import pytest

from barsa.bms.records import KnowledgeRecord, KnowledgeType, Project, ProjectStatus, Workspace
from barsa.models.versioning import AuthorType, ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.sync.models import RemoteCreate, RemoteProviderType
from barsa.sync.service import SyncService
from barsa.versioning.engine import VersionControlEngine


def create_bench_dataset(
    project_id: str,
    count: int,
    prefix: str,
) -> list[MemoryChange]:
    changes = []
    for i in range(count):
        kr = KnowledgeRecord(
            id=f"{prefix}-rec-{i:05d}",
            project_id=project_id,
            content=f"Benchmark content record #{i} containing structured domain data and assertions for scalability.",
            knowledge_type=KnowledgeType.FACT,
            created_by="bench-agent",
        )
        changes.append(
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=kr.id,
                record_type="knowledge",
                after_state=kr.model_dump(mode="json"),
            )
        )
    return changes


@pytest.mark.asyncio
async def test_sync_benchmarks_small_medium_large(tmp_path: Path):
    """Benchmark sync across Small (20), Medium (200), and Large (2000) record scales."""
    db_path = tmp_path / "bench_local.db"
    art_path = tmp_path / "bench_art"
    storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=art_path)
    storage.initialize()
    vc = VersionControlEngine(storage)
    sync = SyncService(storage=storage)

    ws_id = "ws-bench"
    proj_id = "proj-bench"
    storage.create_workspace(Workspace(id=ws_id, name="Bench WS", owner_id="u-bench"))
    storage.create_project(Project(id=proj_id, workspace_id=ws_id, name="Bench Proj", status=ProjectStatus.ACTIVE))

    remote_dir = tmp_path / "remote_byos"
    remote_dir.mkdir()
    rem = sync.create_remote(
        proj_id,
        RemoteCreate(name="origin", provider_type=RemoteProviderType.LOCAL, local_path=str(remote_dir)),
    )

    scales = [
        ("small", 20),
        ("medium", 200),
        ("large", 2000),
    ]

    for scale_name, count in scales:
        branch_name = f"branch-{scale_name}"
        # Create branch from main
        vc.create_branch(proj_id, branch_name)

        # Generate dataset
        changes = create_bench_dataset(proj_id, count, scale_name)

        # Commit
        t0_commit = time.perf_counter()
        commit = vc.create_commit(
            project_id=proj_id,
            branch_name=branch_name,
            changes=changes,
            message=f"Benchmark commit for {scale_name} scale ({count} records)",
            author_id="bench-agent",
            author_type=AuthorType.AGENT,
        )
        commit_duration = time.perf_counter() - t0_commit
        assert commit_duration >= 0

        # Push to BYOS remote
        t0_push = time.perf_counter()
        push_res = await sync.push(rem.id, branch_name=branch_name)
        push_duration = time.perf_counter() - t0_push
        assert push_duration >= 0

        assert push_res.success is True
        assert push_res.objects_uploaded >= count

        # Deduplication test: re-pushing should transfer 0 new objects
        re_push = await sync.push(rem.id, branch_name=branch_name)
        assert re_push.success is True
        assert re_push.objects_uploaded == 0

        # Pull into clean secondary storage
        store_dest = SQLiteStorageProvider(
            db_path=tmp_path / f"bench_{scale_name}_dest.db", artifacts_dir=tmp_path / f"art_{scale_name}"
        )
        store_dest.initialize()
        store_dest.create_workspace(Workspace(id=ws_id, name="Bench WS", owner_id="u-bench"))
        store_dest.create_project(
            Project(id=proj_id, workspace_id=ws_id, name="Bench Proj", status=ProjectStatus.ACTIVE)
        )
        sync_dest = SyncService(storage=store_dest)
        rem_dest = sync_dest.create_remote(
            proj_id,
            RemoteCreate(name="origin", provider_type=RemoteProviderType.LOCAL, local_path=str(remote_dir)),
        )

        t0_pull = time.perf_counter()
        pull_res = await sync_dest.pull(rem_dest.id, branch_name=branch_name)
        pull_duration = time.perf_counter() - t0_pull
        assert pull_duration >= 0

        assert pull_res.success is True
        assert pull_res.objects_downloaded >= count
        assert pull_res.remote_head_commit_id == commit.commit_id

        # Verify integrity on random sampled record
        sample_id = f"{scale_name}-rec-{count // 2:05d}"
        rec, _ = store_dest.get_record(proj_id, sample_id)
        assert rec is not None
        assert rec.id == sample_id
