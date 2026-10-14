"""Comprehensive test suite for Phase 5 FalkorDB Knowledge Graph Engine."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from barsa.bms.records import (
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
from barsa.core.exceptions import StorageError
from barsa.graph.memory import InMemoryGraphProvider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.models.graph import (
    GraphNode,
    GraphNodeType,
    GraphRelationship,
    GraphRelationshipType,
    OutboxEventStatus,
    ProjectionStatus,
)
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


@pytest.fixture
def storage(tmp_path: Path) -> SQLiteStorageProvider:
    """Fixture providing initialized SQLiteStorageProvider."""
    db_path = tmp_path / "barsa_graph_test.db"
    artifacts_dir = tmp_path / "artifacts"
    provider = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
    provider.initialize()
    return provider


@pytest.fixture
def vc(storage: SQLiteStorageProvider) -> VersionControlEngine:
    """Fixture providing VersionControlEngine backed by SQLiteStorageProvider."""
    return VersionControlEngine(storage)


@pytest.fixture
def graph_mem() -> InMemoryGraphProvider:
    """Fixture providing in-memory graph provider."""
    return InMemoryGraphProvider()


@pytest.fixture
def worker(storage: SQLiteStorageProvider, graph_mem: InMemoryGraphProvider) -> GraphProjectionWorker:
    """Fixture providing GraphProjectionWorker."""
    return GraphProjectionWorker(storage, graph_mem)


@pytest.fixture
def retrieval(graph_mem: InMemoryGraphProvider) -> GraphRetrievalService:
    """Fixture providing GraphRetrievalService."""
    return GraphRetrievalService(graph_mem)


@pytest.fixture
def seeded_project(storage: SQLiteStorageProvider) -> tuple[Workspace, Project]:
    """Fixture creating workspace and project."""
    ws = Workspace(id="ws-graph-1", name="Graph WS", owner_id="user-1")
    storage.create_workspace(ws)
    proj = Project(id="proj-graph-1", workspace_id="ws-graph-1", name="Graph Project")
    storage.create_project(proj)
    return ws, proj


def test_graph_node_and_relationship_mapping(graph_mem: InMemoryGraphProvider) -> None:
    """1. Graph model mapping and basic operations."""
    proj_id = "p-1"
    node1 = GraphNode(
        id="p-1:task-1",
        raw_id="task-1",
        project_id=proj_id,
        node_type=GraphNodeType.TASK,
        properties={"title": "Implement auth", "status": "todo"},
    )
    node2 = GraphNode(
        id="p-1:req-1",
        raw_id="req-1",
        project_id=proj_id,
        node_type=GraphNodeType.REQUIREMENT,
        properties={"title": "Must support JWT", "status": "verified"},
    )
    graph_mem.upsert_node(node1)
    graph_mem.upsert_node(node2)

    rel = GraphRelationship(
        source_id="p-1:task-1",
        target_id="p-1:req-1",
        rel_type=GraphRelationshipType.IMPLEMENTS,
        project_id=proj_id,
    )
    graph_mem.upsert_relationship(rel)

    fetched_node = graph_mem.get_node(proj_id, "task-1")
    assert fetched_node is not None
    assert fetched_node.properties["title"] == "Implement auth"

    neighbors = graph_mem.get_neighbors(proj_id, "task-1", direction="out")
    assert len(neighbors) == 1
    assert neighbors[0]["neighbor"]["id"] == "p-1:req-1"


def test_task_dependency_cycle_detection(worker: GraphProjectionWorker) -> None:
    """2. Cycle detection prevents cyclic task dependencies."""
    cyclic_tasks = {
        "t-1": {"id": "t-1", "dependencies": ["t-2"]},
        "t-2": {"id": "t-2", "dependencies": ["t-3"]},
        "t-3": {"id": "t-3", "dependencies": ["t-1"]},
    }
    with pytest.raises(StorageError) as exc_info:
        worker._validate_task_dependencies(cyclic_tasks)
    assert "Cyclic task dependency detected" in str(exc_info.value)


def test_task_self_dependency_prohibited(worker: GraphProjectionWorker) -> None:
    """3. Prevent accidental self-dependencies."""
    self_tasks = {
        "t-self": {"id": "t-self", "dependencies": ["t-self"]},
    }
    with pytest.raises(StorageError) as exc_info:
        worker._validate_task_dependencies(self_tasks)
    assert "self-dependency prohibited" in str(exc_info.value)


def test_transactional_outbox_event_creation(
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    seeded_project: tuple[Workspace, Project],
) -> None:
    """4. Outbox events are automatically created upon commit creation on main."""
    _, proj = seeded_project
    main = vc.initialize_project_main_branch(proj.id)

    # Initial root commit already created an outbox event
    events = worker.fetch_pending_outbox_events(proj.id)
    assert len(events) >= 1
    assert events[0].commit_id == main.head_commit_id
    assert events[0].status == OutboxEventStatus.PENDING

    # Create new commit on main
    kn = KnowledgeRecord(
        id="kn-outbox-1",
        project_id=proj.id,
        content="JWT Auth Fact",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="agent-1",
    )
    c1 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="kn-outbox-1",
                record_type="knowledge",
                after_state=kn.model_dump(mode="json"),
            )
        ],
        message="Add JWT knowledge",
        author_id="agent-1",
    )

    events_after = worker.fetch_pending_outbox_events(proj.id)
    assert any(e.commit_id == c1.commit_id for e in events_after)


def test_idempotent_event_projection_and_freshness(
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    graph_mem: InMemoryGraphProvider,
    seeded_project: tuple[Workspace, Project],
) -> None:
    """5. Projection worker applies events idempotently and tracks revision freshness."""
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    kn = KnowledgeRecord(
        id="kn-fresh-1",
        project_id=proj.id,
        content="System Requirement: JWT",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="agent-arch",
    )
    c1 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="kn-fresh-1",
                record_type="knowledge",
                after_state=kn.model_dump(mode="json"),
            )
        ],
        message="Commit JWT knowledge",
        author_id="agent-arch",
    )

    # Before processing: Status should report LAGGING or pending
    status_before = worker.get_projection_status(proj.id)
    assert status_before.is_fresh is False or status_before.status == ProjectionStatus.LAGGING

    # Process events
    processed = worker.process_pending_events(proj.id)
    assert processed > 0

    # After processing: Graph is fresh
    status_after = worker.get_projection_status(proj.id)
    assert status_after.is_fresh is True
    assert status_after.status == ProjectionStatus.UP_TO_DATE
    assert status_after.applied_commit_id == c1.commit_id

    # Verify node in graph
    node = graph_mem.get_node(proj.id, "kn-fresh-1")
    assert node is not None
    assert node.properties["content"] == "System Requirement: JWT"

    # Re-running process_pending_events does not duplicate
    processed_again = worker.process_pending_events(proj.id)
    assert processed_again == 0


def test_unmerged_feature_branch_does_not_modify_graph_projection(
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    graph_mem: InMemoryGraphProvider,
    seeded_project: tuple[Workspace, Project],
) -> None:
    """6. Feature branches do not emit outbox events or alter the main graph projection."""
    _, proj = seeded_project
    main = vc.initialize_project_main_branch(proj.id)
    worker.process_pending_events(proj.id)

    # Create feature branch
    vc.create_branch(proj.id, "feature/experimental", start_commit_id=main.head_commit_id)

    kn_exp = KnowledgeRecord(
        id="kn-experimental-1",
        project_id=proj.id,
        content="Experimental unmerged idea",
        knowledge_type=KnowledgeType.HYPOTHESIS,
        verification_status=VerificationStatus.UNVERIFIED,
        created_by="agent-exp",
    )
    vc.create_commit(
        project_id=proj.id,
        branch_name="feature/experimental",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id="kn-experimental-1",
                record_type="knowledge",
                after_state=kn_exp.model_dump(mode="json"),
            )
        ],
        message="Experimental commit",
        author_id="agent-exp",
    )

    # Verify no outbox event was generated for experimental branch
    events = worker.fetch_pending_outbox_events(proj.id)
    assert not any(e.payload.get("branch_name") == "feature/experimental" for e in events)

    # Verify experimental node is NOT in the main graph
    exp_node = graph_mem.get_node(proj.id, "kn-experimental-1")
    assert exp_node is None


def test_project_overview_and_task_dependencies_query(
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    retrieval: GraphRetrievalService,
    seeded_project: tuple[Workspace, Project],
) -> None:
    """7. Project overview and task dependency graph queries."""
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    # Add Task 1 (auth) and Task 2 (refresh token depends on Task 1)
    t1 = TaskRecord(
        id="task-login",
        project_id=proj.id,
        title="Implement Login Auth",
        status=TaskStatus.COMPLETED,
        priority=TaskPriority.HIGH,
        dependencies=[],
    )
    t2 = TaskRecord(
        id="task-refresh",
        project_id=proj.id,
        title="Implement Refresh Token Endpoint",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        dependencies=["task-login"],
    )
    dec = DecisionRecord(
        id="dec-spring",
        project_id=proj.id,
        title="Use Spring Security and JWT",
        decision="Adopt standard JWT tokens with 15min expiry",
        rationale="Industry standard security and stateless scaling",
        status=DecisionStatus.APPROVED,
        created_by="agent-architect",
    )
    # Requirement via knowledge record
    req = KnowledgeRecord(
        id="req-jwt",
        project_id=proj.id,
        content="The application must support JWT authentication.",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="agent-research",
    )

    vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t1.id,
                record_type="task",
                after_state=t1.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t2.id,
                record_type="task",
                after_state=t2.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=dec.id,
                record_type="decision",
                after_state=dec.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=req.id,
                record_type="knowledge",
                after_state=req.model_dump(mode="json"),
            ),
        ],
        message="Setup project tasks, decision, and requirement",
        author_id="lead-agent",
    )

    worker.process_pending_events(proj.id)

    # Query overview
    overview = retrieval.get_project_overview(proj.id)
    assert len(overview.active_tasks) == 2
    assert len(overview.approved_decisions) == 1

    # Query task dependencies for task-refresh
    deps_res = retrieval.get_task_dependencies(proj.id, "task-refresh")
    assert any(d.get("raw_id") == "task-login" or d.get("id") == f"{proj.id}:task-login" for d in deps_res.dependencies)


def test_resume_context_query(
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    retrieval: GraphRetrievalService,
    seeded_project: tuple[Workspace, Project],
) -> None:
    """8. Resume context query retrieves connected task, checkpoint, decisions, and dependencies."""
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    t1 = TaskRecord(id="t-login", project_id=proj.id, title="Login", status=TaskStatus.COMPLETED)
    t2 = TaskRecord(
        id="t-refresh",
        project_id=proj.id,
        title="Refresh Token",
        status=TaskStatus.IN_PROGRESS,
        dependencies=["t-login"],
    )
    chk = ResumeCheckpoint(
        id="chk-1",
        project_id=proj.id,
        task_id="t-refresh",
        status=CheckpointStatus.ACTIVE,
        next_action="Implement TokenRevocationFilter",
        base_revision="c-base",
        created_by="agent-coder",
        completed_actions=["Created auth controller"],
        pending_actions=["Write revocation tests"],
    )
    rel = RelationshipRecord(
        id="rel-supports-1",
        project_id=proj.id,
        source_id="t-refresh",
        target_id="dec-1",
        relationship_type=RelationshipType.SUPPORTS,
    )

    vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t1.id,
                record_type="task",
                after_state=t1.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t2.id,
                record_type="task",
                after_state=t2.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=chk.id,
                record_type="checkpoint",
                after_state=chk.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=rel.id,
                record_type="relationship",
                after_state=rel.model_dump(mode="json"),
            ),
        ],
        message="Setup resume context",
        author_id="agent-coder",
    )
    worker.process_pending_events(proj.id)

    resume = retrieval.get_resume_context(proj.id, "t-refresh")
    assert resume.task is not None
    assert resume.latest_checkpoint is not None
    assert resume.latest_checkpoint["properties"]["next_action"] == "Implement TokenRevocationFilter"
    assert any(d.get("raw_id") == "t-login" or d.get("id") == f"{proj.id}:t-login" for d in resume.dependencies)


def test_multi_project_isolation(
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    retrieval: GraphRetrievalService,
    storage: SQLiteStorageProvider,
    seeded_project: tuple[Workspace, Project],
) -> None:
    """9. Strict project boundaries prevent cross-project record retrieval."""
    ws, p1 = seeded_project
    p2 = Project(id="proj-graph-2", workspace_id=ws.id, name="Project 2")
    storage.create_project(p2)

    vc.initialize_project_main_branch(p1.id)
    vc.initialize_project_main_branch(p2.id)

    # Add secret task to p1
    t_secret = TaskRecord(id="task-secret", project_id=p1.id, title="Secret P1 Plan")
    vc.create_commit(
        project_id=p1.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t_secret.id,
                record_type="task",
                after_state=t_secret.model_dump(mode="json"),
            )
        ],
        message="P1 Secret",
        author_id="agent-secret",
    )
    worker.process_pending_events(p1.id)

    # Verify p2 cannot see p1's task
    node_p2 = retrieval.get_node(p2.id, "task-secret")
    assert node_p2 is None

    p2_overview = retrieval.get_project_overview(p2.id)
    assert len(p2_overview.active_tasks) == 0


def test_graph_rebuild_from_authoritative_state(
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    graph_mem: InMemoryGraphProvider,
    seeded_project: tuple[Workspace, Project],
) -> None:
    """10. Administrative rebuild reconstructs entire graph from authoritative SQLite commit."""
    _, proj = seeded_project
    vc.initialize_project_main_branch(proj.id)

    kn = KnowledgeRecord(
        id="kn-rebuild-1",
        project_id=proj.id,
        content="Rebuildable Fact",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="admin",
    )
    c1 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=kn.id,
                record_type="knowledge",
                after_state=kn.model_dump(mode="json"),
            )
        ],
        message="Add rebuild fact",
        author_id="admin",
    )
    worker.process_pending_events(proj.id)

    # Simulate graph loss / corruption
    graph_mem.clear_project_graph(proj.id)
    assert graph_mem.get_node(proj.id, "kn-rebuild-1") is None

    # Rebuild
    rebuild_meta = worker.rebuild_project_graph(proj.id)
    assert rebuild_meta.status == ProjectionStatus.UP_TO_DATE
    assert rebuild_meta.applied_commit_id == c1.commit_id

    # Node restored
    restored_node = graph_mem.get_node(proj.id, "kn-rebuild-1")
    assert restored_node is not None
    assert restored_node.properties["content"] == "Rebuildable Fact"


@pytest.mark.asyncio
async def test_graph_api_endpoints_integration(client: AsyncClient) -> None:
    """11. REST API endpoints under /api/v1/projects/{project_id}/graph."""
    # 1. Create Workspace and Project
    ws_resp = await client.post("/api/v1/workspaces", json={"name": "Graph API WS", "owner_id": "test-user"})
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    p_resp = await client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Graph API Project"})
    assert p_resp.status_code == 201
    proj_id = p_resp.json()["id"]

    # 2. Check initial graph status
    status_resp = await client.get(f"/api/v1/projects/{proj_id}/graph/status")
    assert status_resp.status_code == 200
    assert "status" in status_resp.json()

    # 3. Create Commit on main
    kn_data = KnowledgeRecord(
        id="kn-api-test",
        project_id=proj_id,
        content="API Knowledge Node",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="api-agent",
    ).model_dump(mode="json")

    commit_payload = {
        "branch": "main",
        "message": "Add graph API knowledge",
        "author_id": "api-agent",
        "changes": [
            {
                "operation": "create",
                "record_id": "kn-api-test",
                "record_type": "knowledge",
                "after_state": kn_data,
            }
        ],
    }
    c_resp = await client.post(f"/api/v1/projects/{proj_id}/versioning/commits", json=commit_payload)
    assert c_resp.status_code == 201

    # 4. Overview endpoint automatically projects pending events
    overview_resp = await client.get(f"/api/v1/projects/{proj_id}/graph/overview")
    assert overview_resp.status_code == 200
    ov_data = overview_resp.json()
    assert ov_data["project_id"] == proj_id

    # 5. Get node endpoint
    node_resp = await client.get(f"/api/v1/projects/{proj_id}/graph/nodes/kn-api-test")
    assert node_resp.status_code == 200
    node_data = node_resp.json()
    assert node_data["raw_id"] == "kn-api-test"

    # 6. Rebuild endpoint
    rebuild_resp = await client.post(f"/api/v1/projects/{proj_id}/graph/rebuild")
    assert rebuild_resp.status_code == 200
    assert rebuild_resp.json()["status"] == "UP_TO_DATE"
