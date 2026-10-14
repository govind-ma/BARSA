"""Comprehensive test suite for Phase 4 Git-Style Memory Version Control."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import AsyncClient

from barsa.bms.records import (
    KnowledgeRecord,
    KnowledgeType,
    Project,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    VerificationStatus,
    Workspace,
)
from barsa.core.exceptions import ConflictError
from barsa.models.versioning import (
    AuthorType,
    ChangeOperation,
    ConflictStatus,
    ConflictType,
    MemoryChange,
    ReviewStatus,
    compute_commit_id,
)
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.diff import compute_state_diff
from barsa.versioning.engine import VersionControlEngine
from barsa.versioning.merge import three_way_merge_states


def make_valid_knowledge(
    record_id: str,
    project_id: str,
    content: str,
    created_at: datetime = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC),
) -> dict:
    """Helper to generate valid BMS v0.1 KnowledgeRecord dictionary."""
    rec = KnowledgeRecord(
        id=record_id,
        project_id=project_id,
        content=content,
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="test-agent",
        created_at=created_at,
    )
    return rec.model_dump(mode="json")


def make_valid_task(record_id: str, project_id: str, title: str, status: TaskStatus = TaskStatus.TODO) -> dict:
    """Helper to generate valid BMS v0.1 TaskRecord dictionary."""
    rec = TaskRecord(
        id=record_id,
        project_id=project_id,
        title=title,
        status=status,
        priority=TaskPriority.HIGH,
        created_by="test-agent",
    )
    return rec.model_dump(mode="json")


@pytest.fixture
def storage(tmp_path: Path) -> SQLiteStorageProvider:
    """Fixture providing initialized SQLiteStorageProvider."""
    db_path = tmp_path / "barsa_vc_test.db"
    artifacts_dir = tmp_path / "artifacts"
    provider = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
    provider.initialize()
    return provider


@pytest.fixture
def vc(storage: SQLiteStorageProvider) -> VersionControlEngine:
    """Fixture providing VersionControlEngine backed by SQLiteStorageProvider."""
    return VersionControlEngine(storage)


@pytest.fixture
def seeded_project(storage: SQLiteStorageProvider) -> tuple[Workspace, Project]:
    """Fixture creating workspace and project."""
    ws = Workspace(id="ws-vc-1", name="VC Workspace", owner_id="user-1")
    storage.create_workspace(ws)
    proj = Project(id="proj-vc-1", workspace_id="ws-vc-1", name="VC Project")
    storage.create_project(proj)
    return ws, proj


def test_initial_main_branch_creation(vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    branch = vc.initialize_project_main_branch(proj.id)

    assert branch.name == "main"
    assert branch.project_id == proj.id
    assert branch.head_commit_id is not None

    root_commit = vc.get_commit(proj.id, branch.head_commit_id)
    assert root_commit is not None
    assert root_commit.parent_commit_ids == []
    assert root_commit.changes == []
    assert "initial" in root_commit.metadata


def test_commit_deterministic_hash_calculation(seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    kn_data = make_valid_knowledge("kn-1", proj.id, "Test Fact")
    changes = [
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id="kn-1",
            record_type="knowledge",
            after_state=kn_data,
        )
    ]
    hash1 = compute_commit_id(
        project_id=proj.id,
        parent_commit_ids=["c-0"],
        author_id="agent-1",
        author_type=AuthorType.AGENT,
        message="Add fact",
        created_at=now,
        changes=changes,
        resulting_state_hash="state-hash-abc",
        metadata={"step": 1},
    )
    hash2 = compute_commit_id(
        project_id=proj.id,
        parent_commit_ids=["c-0"],
        author_id="agent-1",
        author_type=AuthorType.AGENT,
        message="Add fact",
        created_at=now,
        changes=changes,
        resulting_state_hash="state-hash-abc",
        metadata={"step": 1},
    )
    assert hash1 == hash2
    assert len(hash1) == 64


def test_commit_persists_and_reconstructs_across_provider_restarts(
    tmp_path: Path, seeded_project: tuple[Workspace, Project]
) -> None:
    _, proj = seeded_project
    db_path = tmp_path / "restart_test.db"
    artifacts_dir = tmp_path / "restart_artifacts"
    store1 = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
    store1.initialize()

    ws = Workspace(id="ws-restart", name="Restart WS", owner_id="user-1")
    store1.create_workspace(ws)
    p = Project(id="proj-restart", workspace_id="ws-restart", name="Restart Proj")
    store1.create_project(p)

    vc1 = VersionControlEngine(store1)
    kn_data = make_valid_knowledge("kn-restart-1", "proj-restart", "Persistent Fact")
    chg = MemoryChange(
        operation=ChangeOperation.CREATE,
        record_id="kn-restart-1",
        record_type="knowledge",
        after_state=kn_data,
    )
    c1 = vc1.create_commit(
        project_id="proj-restart",
        branch_name="main",
        changes=[chg],
        message="First commit",
        author_id="agent-persist",
    )

    # Close and open fresh provider
    store2 = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
    store2.initialize()
    vc2 = VersionControlEngine(store2)

    c_fetched = vc2.get_commit("proj-restart", c1.commit_id)
    assert c_fetched is not None
    assert c_fetched.message == "First commit"

    state = vc2.reconstruct_project_state("proj-restart", c1.commit_id)
    assert "kn-restart-1" in state
    assert state["kn-restart-1"]["content"] == "Persistent Fact"


def test_branch_creation_and_isolation(vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    main = vc.initialize_project_main_branch(proj.id)

    feature = vc.create_branch(proj.id, "feature/rag", start_commit_id=main.head_commit_id)
    assert feature.name == "feature/rag"
    assert feature.head_commit_id == main.head_commit_id

    # Commit on feature branch
    kn_data = make_valid_knowledge("kn-rag-1", proj.id, "RAG architecture")
    chg = MemoryChange(
        operation=ChangeOperation.CREATE,
        record_id="kn-rag-1",
        record_type="knowledge",
        after_state=kn_data,
    )
    c_feat = vc.create_commit(
        project_id=proj.id,
        branch_name="feature/rag",
        changes=[chg],
        message="Add RAG note",
        author_id="agent-feature",
    )

    # Verify feature HEAD advanced while main remained unchanged
    main_after = vc.get_branch(proj.id, "main")
    feat_after = vc.get_branch(proj.id, "feature/rag")
    assert main_after is not None and feat_after is not None
    assert main_after.head_commit_id == main.head_commit_id
    assert feat_after.head_commit_id == c_feat.commit_id


def test_stale_branch_head_rejection_cas(vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    main = vc.initialize_project_main_branch(proj.id)

    # Commit 1
    kn1 = make_valid_knowledge("kn-cas-1", proj.id, "Commit 1")
    chg1 = MemoryChange(
        operation=ChangeOperation.CREATE,
        record_id="kn-cas-1",
        record_type="knowledge",
        after_state=kn1,
    )
    vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[chg1],
        message="Commit 1",
        author_id="agent-1",
        expected_head_commit_id=main.head_commit_id,
    )

    # Commit 2 specifying stale head (main.head_commit_id instead of c1.commit_id)
    kn2 = make_valid_knowledge("kn-cas-2", proj.id, "Commit 2")
    chg2 = MemoryChange(
        operation=ChangeOperation.CREATE,
        record_id="kn-cas-2",
        record_type="knowledge",
        after_state=kn2,
    )
    with pytest.raises(ConflictError) as exc_info:
        vc.create_commit(
            project_id=proj.id,
            branch_name="main",
            changes=[chg2],
            message="Commit 2 with stale head",
            author_id="agent-2",
            expected_head_commit_id=main.head_commit_id,
        )
    assert "Stale HEAD" in str(exc_info.value)


def test_field_level_and_record_level_diffs(seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    state_a = {
        "tsk-1": {
            "id": "tsk-1",
            "record_type": "task",
            "title": "Build UI",
            "status": "todo",
            "metadata": {"driver": "standard"},
        },
        "kn-1": {"id": "kn-1", "record_type": "knowledge", "content": "DB Fact"},
    }
    state_b = {
        "tsk-1": {
            "id": "tsk-1",
            "record_type": "task",
            "title": "Build UI with Next.js",
            "status": "in_progress",
            "metadata": {"driver": "standard", "mode": "WAL"},
        },
        "kn-2": {"id": "kn-2", "record_type": "knowledge", "content": "Caching Fact"},
    }

    diff = compute_state_diff(
        project_id=proj.id,
        from_commit_id="c-a",
        to_commit_id="c-b",
        from_state=state_a,
        to_state=state_b,
    )

    assert "kn-1" in diff.removed_records
    assert "kn-2" in diff.added_records
    assert "tsk-1" in diff.modified_records

    rec_diff = next(r for r in diff.changes if r.record_id == "tsk-1")
    paths = {f.path for f in rec_diff.fields}
    assert "/title" in paths
    assert "/status" in paths
    assert "/metadata/mode" in paths


def test_three_way_merge_independent_clean_changes(
    vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]
) -> None:
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    rec_a_base = make_valid_knowledge("rec-a", proj.id, "Initial A")
    rec_b_base = make_valid_knowledge("rec-b", proj.id, "Initial B")

    chg_base = [
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id="rec-a",
            record_type="knowledge",
            after_state=rec_a_base,
        ),
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id="rec-b",
            record_type="knowledge",
            after_state=rec_b_base,
        ),
    ]
    base_commit = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=chg_base,
        message="Base state",
        author_id="admin",
    )

    # Branch 1 updates A
    vc.create_branch(proj.id, "branch-1", start_commit_id=base_commit.commit_id)
    rec_a_v1 = make_valid_knowledge("rec-a", proj.id, "Updated A in B1")
    vc.create_commit(
        project_id=proj.id,
        branch_name="branch-1",
        changes=[
            MemoryChange(
                operation=ChangeOperation.UPDATE,
                record_id="rec-a",
                record_type="knowledge",
                before_state=rec_a_base,
                after_state=rec_a_v1,
            )
        ],
        message="Update A",
        author_id="agent-1",
    )

    # Branch 2 updates B
    vc.create_branch(proj.id, "branch-2", start_commit_id=base_commit.commit_id)
    rec_b_v2 = make_valid_knowledge("rec-b", proj.id, "Updated B in B2")
    vc.create_commit(
        project_id=proj.id,
        branch_name="branch-2",
        changes=[
            MemoryChange(
                operation=ChangeOperation.UPDATE,
                record_id="rec-b",
                record_type="knowledge",
                before_state=rec_b_base,
                after_state=rec_b_v2,
            )
        ],
        message="Update B",
        author_id="agent-2",
    )

    # Merge proposal from branch-1 into branch-2
    prop = vc.create_merge_proposal(
        project_id=proj.id,
        title="Merge branch-1 into branch-2",
        source_branch="branch-1",
        target_branch="branch-2",
        author_id="agent-1",
    )
    conflicts = vc.list_conflicts(proj.id, proposal_id=prop.proposal_id)
    assert len(conflicts) == 0

    # Execute merge
    merge_commit = vc.execute_merge(proj.id, prop.proposal_id, author_id="merger")
    assert len(merge_commit.parent_commit_ids) == 2

    # Verify merged state contains both updates
    merged_state = vc.reconstruct_project_state(proj.id, merge_commit.commit_id)
    assert merged_state["rec-a"]["content"] == "Updated A in B1"
    assert merged_state["rec-b"]["content"] == "Updated B in B2"


def test_three_way_merge_identical_changes(seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    base_state = {"rec-1": make_valid_knowledge("rec-1", proj.id, "Original")}
    src_state = {"rec-1": make_valid_knowledge("rec-1", proj.id, "Adopted Content")}
    tgt_state = {"rec-1": make_valid_knowledge("rec-1", proj.id, "Adopted Content")}

    res = three_way_merge_states(
        project_id=proj.id,
        base_state=base_state,
        source_state=src_state,
        target_state=tgt_state,
        source_branch="src",
        target_branch="tgt",
    )
    assert res.can_merge_cleanly is True
    assert len(res.conflicts) == 0
    assert res.merged_state["rec-1"]["content"] == "Adopted Content"


def test_three_way_merge_detects_conflict_and_resolution(
    vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]
) -> None:
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    # Base commit with record C
    rec_c_base = make_valid_knowledge("rec-c", proj.id, "Base Content General")
    base_commit = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="rec-c",
                record_type="knowledge",
                after_state=rec_c_base,
            )
        ],
        message="Base commit",
        author_id="admin",
    )

    # Branch A modifies content to 'Base Content Frontend'
    rec_c_ui = make_valid_knowledge("rec-c", proj.id, "Base Content Frontend")
    vc.create_branch(proj.id, "feat-ui", start_commit_id=base_commit.commit_id)
    vc.create_commit(
        project_id=proj.id,
        branch_name="feat-ui",
        changes=[
            MemoryChange(
                operation=ChangeOperation.UPDATE,
                record_id="rec-c",
                record_type="knowledge",
                before_state=rec_c_base,
                after_state=rec_c_ui,
            )
        ],
        message="Categorize as Frontend",
        author_id="agent-ui",
    )

    # Branch main modifies content to 'Base Content Backend'
    rec_c_be = make_valid_knowledge("rec-c", proj.id, "Base Content Backend")
    vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.UPDATE,
                record_id="rec-c",
                record_type="knowledge",
                before_state=rec_c_base,
                after_state=rec_c_be,
            )
        ],
        message="Categorize as Backend",
        author_id="agent-backend",
    )

    # Create proposal to merge feat-ui into main
    prop = vc.create_merge_proposal(
        project_id=proj.id,
        title="Merge UI changes",
        source_branch="feat-ui",
        target_branch="main",
        author_id="agent-ui",
    )

    conflicts = vc.list_conflicts(proj.id, proposal_id=prop.proposal_id)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.SAME_FIELD_UPDATE
    assert conflicts[0].resolution_status == ConflictStatus.UNRESOLVED

    # Attempting to execute merge with unresolved conflict fails
    with pytest.raises(ConflictError) as exc_info:
        vc.execute_merge(proj.id, prop.proposal_id, author_id="merger")
    assert "unresolved conflict" in str(exc_info.value)

    # Resolve conflict explicitly with Fullstack category
    rec_c_resolved = make_valid_knowledge("rec-c", proj.id, "Base Content Fullstack")
    resolved = vc.resolve_conflict(
        project_id=proj.id,
        conflict_id=conflicts[0].conflict_id,
        resolved_by="lead-architect",
        resolved_value=rec_c_resolved,
    )
    assert resolved.resolution_status == ConflictStatus.RESOLVED

    # Now execute merge cleanly
    merge_commit = vc.execute_merge(proj.id, prop.proposal_id, author_id="lead-architect")
    merged_state = vc.reconstruct_project_state(proj.id, merge_commit.commit_id)
    assert merged_state["rec-c"]["content"] == "Base Content Fullstack"


def test_delete_vs_update_conflict_detection(seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    base_state = {"rec-d": make_valid_knowledge("rec-d", proj.id, "Important spec")}
    src_state = {}  # deleted in src
    tgt_state = {"rec-d": make_valid_knowledge("rec-d", proj.id, "Important spec updated")}

    res = three_way_merge_states(
        project_id=proj.id,
        base_state=base_state,
        source_state=src_state,
        target_state=tgt_state,
        source_branch="src",
        target_branch="tgt",
    )
    assert res.can_merge_cleanly is False
    assert len(res.conflicts) == 1
    assert res.conflicts[0].conflict_type == ConflictType.DELETE_VS_UPDATE


def test_review_comments_and_formal_reviews(
    vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]
) -> None:
    _, proj = seeded_project
    main = vc.initialize_project_main_branch(proj.id)
    vc.create_branch(proj.id, "feat-auth", start_commit_id=main.head_commit_id)

    prop = vc.create_merge_proposal(
        project_id=proj.id,
        title="Auth feature proposal",
        source_branch="feat-auth",
        target_branch="main",
        author_id="agent-auth",
    )

    # Add comment
    comment = vc.add_review_comment(
        project_id=proj.id,
        proposal_id=prop.proposal_id,
        author_id="reviewer-1",
        author_type=AuthorType.HUMAN,
        content="Looks solid, please ensure token expiry is configurable.",
    )
    assert comment.content.startswith("Looks solid")

    # Submit formal review
    review = vc.submit_review(
        project_id=proj.id,
        proposal_id=prop.proposal_id,
        reviewer_id="lead-dev",
        status=ReviewStatus.APPROVED,
        summary="Approved for merge.",
    )
    assert review["status"] == "approved"

    # Verify comments and reviews attached to proposal
    prop_fetched = vc.get_merge_proposal(proj.id, prop.proposal_id)
    assert prop_fetched is not None
    assert len(prop_fetched.comments) == 1
    assert len(prop_fetched.reviews) == 1


def test_historical_time_travel_and_restore(
    vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]
) -> None:
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    # Commit 1: Add Record 1
    rec1_v1 = make_valid_knowledge("rec-1", proj.id, "Content 1")
    c1 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="rec-1",
                record_type="knowledge",
                after_state=rec1_v1,
            )
        ],
        message="Add record 1",
        author_id="agent-1",
    )

    # Commit 2: Modify Record 1 and add Record 2
    rec1_v2 = make_valid_knowledge("rec-1", proj.id, "Content 1 Modified")
    rec2 = make_valid_knowledge("rec-2", proj.id, "Content 2")
    c2 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.UPDATE,
                record_id="rec-1",
                record_type="knowledge",
                before_state=rec1_v1,
                after_state=rec1_v2,
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="rec-2",
                record_type="knowledge",
                after_state=rec2,
            ),
        ],
        message="Update 1, add 2",
        author_id="agent-2",
    )

    # Verify time travel to c1
    state_at_c1 = vc.reconstruct_project_state(proj.id, c1.commit_id)
    assert state_at_c1["rec-1"]["content"] == "Content 1"
    assert "rec-2" not in state_at_c1

    # Verify time travel to c2
    state_at_c2 = vc.reconstruct_project_state(proj.id, c2.commit_id)
    assert state_at_c2["rec-1"]["content"] == "Content 1 Modified"
    assert "rec-2" in state_at_c2

    # Restore main branch state back to c1 without destroying history
    c_restore = vc.restore_commit_state(
        project_id=proj.id,
        target_branch="main",
        restore_from_commit_id=c1.commit_id,
        author_id="admin-restore",
    )
    assert c_restore.commit_id != c1.commit_id
    assert c_restore.parent_commit_ids == [c2.commit_id]

    # Current state should now match c1 exactly
    current_state = vc.reconstruct_project_state(proj.id, c_restore.commit_id)
    assert current_state["rec-1"]["content"] == "Content 1"
    assert "rec-2" not in current_state

    # History contains all 4 commits (root + c1 + c2 + restore)
    history = vc.get_history(proj.id, branch_name="main")
    assert len(history) == 4


def test_cross_project_isolation(
    vc: VersionControlEngine, storage: SQLiteStorageProvider, seeded_project: tuple[Workspace, Project]
) -> None:
    ws, proj1 = seeded_project
    proj2 = Project(id="proj-vc-2", workspace_id=ws.id, name="Project 2")
    storage.create_project(proj2)

    vc.initialize_project_main_branch(proj1.id)
    vc.initialize_project_main_branch(proj2.id)

    # Commit on proj1
    rec_p1 = make_valid_knowledge("rec-p1", proj1.id, "P1 Secret Fact")
    c1 = vc.create_commit(
        project_id=proj1.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="rec-p1",
                record_type="knowledge",
                after_state=rec_p1,
            )
        ],
        message="P1 Commit",
        author_id="p1-agent",
    )

    # Verify proj2 cannot see or reconstruct proj1 commit
    assert vc.get_commit(proj2.id, c1.commit_id) is None
    p2_history = vc.get_history(proj2.id)
    assert not any(c.commit_id == c1.commit_id for c in p2_history)


def test_main_branch_deletion_protection(vc: VersionControlEngine, seeded_project: tuple[Workspace, Project]) -> None:
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    with pytest.raises(ConflictError) as exc_info:
        vc.delete_branch(proj.id, "main")
    assert "protected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_versioning_api_endpoints_integration(client: AsyncClient) -> None:
    # 1. Create Workspace and Project
    ws_resp = await client.post("/api/v1/workspaces", json={"name": "API VC WS", "owner_id": "test-user"})
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    p_resp = await client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "API VC Project"})
    assert p_resp.status_code == 201
    proj_id = p_resp.json()["id"]

    # 2. List Branches (initializes main)
    branches_resp = await client.get(f"/api/v1/projects/{proj_id}/versioning/branches")
    assert branches_resp.status_code == 200
    branches = branches_resp.json()
    assert len(branches) == 1
    assert branches[0]["name"] == "main"
    root_commit_id = branches[0]["head_commit_id"]

    # 3. Create Commit on main with valid BMS record
    kn_data = make_valid_knowledge("kn-api-1", proj_id, "API Knowledge Fact")
    commit_payload = {
        "branch": "main",
        "message": "Add API Knowledge",
        "author_id": "api-agent",
        "author_type": "agent",
        "changes": [
            {
                "operation": "create",
                "record_id": "kn-api-1",
                "record_type": "knowledge",
                "after_state": kn_data,
            }
        ],
    }
    c_resp = await client.post(f"/api/v1/projects/{proj_id}/versioning/commits", json=commit_payload)
    assert c_resp.status_code == 201
    c1 = c_resp.json()
    assert c1["commit_id"] is not None

    # 4. Create Feature Branch
    b_resp = await client.post(
        f"/api/v1/projects/{proj_id}/versioning/branches",
        json={"name": "feature/ui-layer", "start_commit_id": c1["commit_id"]},
    )
    assert b_resp.status_code == 201

    # 5. Diff between root and c1
    diff_resp = await client.get(
        f"/api/v1/projects/{proj_id}/versioning/diff",
        params={"from_commit": root_commit_id, "to_commit": c1["commit_id"]},
    )
    assert diff_resp.status_code == 200
    diff = diff_resp.json()
    assert "kn-api-1" in diff["added_records"]

    # 6. Merge Proposal
    prop_resp = await client.post(
        f"/api/v1/projects/{proj_id}/versioning/merge-proposals",
        json={
            "title": "Merge UI Layer",
            "source_branch": "feature/ui-layer",
            "target_branch": "main",
            "author_id": "agent-ui",
        },
    )
    assert prop_resp.status_code == 201
    prop_id = prop_resp.json()["proposal_id"]

    # 7. Add Comment
    comm_resp = await client.post(
        f"/api/v1/projects/{proj_id}/versioning/merge-proposals/{prop_id}/comments",
        json={"author_id": "reviewer", "content": "LGTM"},
    )
    assert comm_resp.status_code == 201

    # 8. Submit Review
    rev_resp = await client.post(
        f"/api/v1/projects/{proj_id}/versioning/merge-proposals/{prop_id}/reviews",
        json={"reviewer_id": "lead", "status": "approved", "summary": "Ship it"},
    )
    assert rev_resp.status_code == 201

    # 9. Execute Clean Merge
    merge_resp = await client.post(
        f"/api/v1/projects/{proj_id}/versioning/merge-proposals/{prop_id}/merge",
        json={"author_id": "lead"},
    )
    assert merge_resp.status_code == 200

    # 10. Test Restore Endpoint
    restore_resp = await client.post(
        f"/api/v1/projects/{proj_id}/versioning/restore",
        json={
            "target_branch": "main",
            "restore_from_commit_id": root_commit_id,
            "author_id": "admin",
            "message": "Reset to root",
        },
    )
    assert restore_resp.status_code == 201
