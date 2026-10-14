"""3-Agent Collaboration (Research -> Architecture -> Coding) and Conflict Handling Test (Phase 12)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from barsa.bms.base import BMS_VERSION
from barsa.bms.records import (
    DecisionRecord,
    DecisionStatus,
    KnowledgeRecord,
    KnowledgeType,
    Project,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    VerificationStatus,
    Workspace,
)
from barsa.core.config import Settings
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.factory import get_storage_provider
from barsa.versioning.engine import VersionControlEngine

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def collab_env(tmp_path: Path):
    """Isolated environment for multi-agent collaboration."""
    data_dir = tmp_path / "barsa_collab_data"
    settings = Settings(
        app_name="BARSA-Collab-Test",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        data_dir=data_dir,
        storage_provider="local",  # type: ignore[arg-type]
        graph_enabled=False,
    )
    settings.ensure_data_dir()

    storage = get_storage_provider(settings)
    vc = VersionControlEngine(storage)

    ws = storage.create_workspace(Workspace(id="ws-collab-1", name="Collaboration WS", owner_id="lead-architect"))
    proj = storage.create_project(
        Project(
            id="proj-collab-1",
            name="Distributed Caching System",
            workspace_id=ws.id,
            description="Collaborative design and implementation of distributed cache",
        )
    )
    vc.initialize_project_main_branch(proj.id)

    yield {
        "storage": storage,
        "vc": vc,
        "project": proj,
        "tmp_path": tmp_path,
    }
    storage.close()


def test_three_agent_collaboration_and_conflict_resolution(collab_env: dict) -> None:
    """Demonstrate Research -> Architecture -> Conflict Resolution -> Coding workflow."""
    vc: VersionControlEngine = collab_env["vc"]
    proj_id: str = collab_env["project"].id

    # =========================================================================
    # Step 1: Research Agent (Agent 1)
    # =========================================================================
    know_rec = KnowledgeRecord(
        id="k-caching-benchmarks",
        schema_version=BMS_VERSION,
        project_id=proj_id,
        content="Benchmark indicates Redis handles sub-millisecond latencies with persistent backup, whereas Memcached lacks native replication.",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="research-agent-1",
    ).model_dump(mode="json")

    commit_research = vc.create_commit(
        project_id=proj_id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="k-caching-benchmarks",
                record_type="knowledge",
                after_state=know_rec,
            )
        ],
        message="feat(research): add caching benchmarks and performance findings",
        author_id="research-agent-1",
    )
    assert commit_research.commit_id is not None

    # =========================================================================
    # Step 2: Architecture Agent A (Agent 2a) proposes Redis on feature/redis
    # =========================================================================
    vc.create_branch(proj_id, "feature/redis", start_commit_id=commit_research.commit_id)

    dec_redis = DecisionRecord(
        id="dec-cache-strategy",
        schema_version=BMS_VERSION,
        project_id=proj_id,
        title="Adopt Redis Cluster for Distributed Caching",
        decision="Use Redis Cluster 7.2 with master-replica replication",
        rationale="Built-in failover, pub-sub capabilities, and persistent snapshots",
        status=DecisionStatus.APPROVED,
        created_by="arch-agent-2a",
    ).model_dump(mode="json")

    vc.create_commit(
        project_id=proj_id,
        branch_name="feature/redis",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="dec-cache-strategy",
                record_type="decision",
                after_state=dec_redis,
            )
        ],
        message="feat(arch): standardize on Redis Cluster",
        author_id="arch-agent-2a",
    )

    # =========================================================================
    # Step 3: Architecture Agent B (Agent 2b) concurrently proposes Memcached
    # =========================================================================
    vc.create_branch(proj_id, "feature/memcached", start_commit_id=commit_research.commit_id)

    dec_memcached = DecisionRecord(
        id="dec-cache-strategy",
        schema_version=BMS_VERSION,
        project_id=proj_id,
        title="Adopt Memcached for In-Memory Caching",
        decision="Use Memcached cluster with client-side hashing",
        rationale="Simpler architecture with pure multithreaded in-memory storage",
        status=DecisionStatus.APPROVED,
        created_by="arch-agent-2b",
    ).model_dump(mode="json")

    vc.create_commit(
        project_id=proj_id,
        branch_name="feature/memcached",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="dec-cache-strategy",
                record_type="decision",
                after_state=dec_memcached,
            )
        ],
        message="feat(arch): propose Memcached alternative",
        author_id="arch-agent-2b",
    )

    # =========================================================================
    # Step 4: Merge feature/redis into main
    # =========================================================================
    prop_redis = vc.create_merge_proposal(
        project_id=proj_id,
        title="Merge Redis Architecture into Main",
        source_branch="feature/redis",
        target_branch="main",
        author_id="arch-agent-2a",
    )
    conflicts_redis = vc.list_conflicts(proj_id, proposal_id=prop_redis.proposal_id)
    assert len(conflicts_redis) == 0

    merge_redis = vc.execute_merge(proj_id, prop_redis.proposal_id, author_id="lead-architect")
    assert merge_redis is not None

    # =========================================================================
    # Step 5: Merge feature/memcached into main -> Detects Conflict!
    # =========================================================================
    prop_memcached = vc.create_merge_proposal(
        project_id=proj_id,
        title="Merge Memcached Proposal into Main",
        source_branch="feature/memcached",
        target_branch="main",
        author_id="arch-agent-2b",
    )

    conflicts = vc.list_conflicts(proj_id, proposal_id=prop_memcached.proposal_id)
    assert len(conflicts) >= 1
    conflict = conflicts[0]
    assert conflict.affected_record_id == "dec-cache-strategy"

    # Lead architect adds review comment
    vc.add_review_comment(
        project_id=proj_id,
        proposal_id=prop_memcached.proposal_id,
        author_id="lead-architect",
        content="Discussed with team: Redis was selected because we require pub/sub and replication support.",
    )

    # Resolve conflict in favor of Redis decision
    vc.resolve_conflict(
        project_id=proj_id,
        conflict_id=conflict.conflict_id,
        resolved_by="lead-architect",
        resolved_value=dec_redis,
    )

    merge_resolved = vc.execute_merge(
        project_id=proj_id,
        proposal_id=prop_memcached.proposal_id,
        author_id="lead-architect",
    )
    assert merge_resolved is not None

    # State on main branch reflects Redis
    main_state = vc.reconstruct_project_state(proj_id, merge_resolved.commit_id)
    assert "Redis" in main_state["dec-cache-strategy"]["title"]

    # =========================================================================
    # Step 6: Coding Agent (Agent 3) implements Redis client configuration
    # =========================================================================
    task_code = TaskRecord(
        id="task-redis-config",
        schema_version=BMS_VERSION,
        project_id=proj_id,
        title="Implement RedisConnectionFactory and RedisTemplate beans",
        description="Configure Lettuce connection factory with pooled connections",
        status=TaskStatus.COMPLETED,
        priority=TaskPriority.HIGH,
        assigned_agent_id="coding-agent-3",
    ).model_dump(mode="json")

    vc.create_commit(
        project_id=proj_id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="task-redis-config",
                record_type="task",
                after_state=task_code,
            )
        ],
        message="feat(caching): implement RedisTemplate bean configuration",
        author_id="coding-agent-3",
    )

    # Verify complete DAG history across all 3 agent roles
    history = vc.get_history(proj_id, limit=20)
    messages = [c.message for c in history]
    assert any("research" in m for m in messages)
    assert any("standardize on Redis" in m or "Merge Redis" in m for m in messages)
    assert any("implement RedisTemplate" in m for m in messages)
