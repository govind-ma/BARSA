"""Comprehensive test suite for Phase 8 Smart Context & Token Optimization Engine (SCE).

Covers all 23 requirements specified in Section 20:
1. Essential context retrieval.
2. Working context retrieval.
3. Detailed retrieval.
4. Ranking correctness.
5. Graph-distance ranking.
6. Mandatory information preservation.
7. Duplicate removal.
8. Contradictory information preservation.
9. Exact token counting where supported.
10. Estimated token counting fallback.
11. Budget enforcement.
12. Insufficient budget response.
13. Relevant source references.
14. Missing checkpoint handling.
15. Stale graph handling.
16. Project access isolation.
17. Incremental updates.
18. Branch-aware revision handling.
19. Invalid revision detection.
20. Serialization round trips.
21. Context completeness validation.
22. REST API endpoints.
23. MCP integration.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from barsa.api.deps import get_context_engine
from barsa.bms.records import (
    ArtifactReference,
    ArtifactType,
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
from barsa.context.budget import TokenBudgetAllocator
from barsa.context.deduplication import RecordDeduplicator
from barsa.context.engine import SmartContextEngine
from barsa.context.models import (
    BarsaContextPackage,
    CompletenessStatus,
    ContextLevel,
    ContextRequest,
)
from barsa.context.ranking import RelevanceRanker
from barsa.context.token_counter import (
    ExactMockTokenCounter,
    HeuristicTokenCounter,
)
from barsa.context.validation import ContextCompletenessValidator
from barsa.graph.memory import InMemoryGraphProvider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.main import create_app
from barsa.mcp.tools import build_context_tool
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


@pytest.fixture
def context_test_env(tmp_path: Path):
    """Fixture initializing temporary storage, version control, graph, and SmartContextEngine."""
    db_path = tmp_path / "test_context.db"
    artifacts_dir = tmp_path / "artifacts"
    storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
    storage.initialize()

    vc = VersionControlEngine(storage)
    graph = InMemoryGraphProvider()
    worker = GraphProjectionWorker(storage, graph)
    retrieval = GraphRetrievalService(graph)
    engine = SmartContextEngine(storage=storage, vc=vc, graph_retrieval=retrieval)

    ws = Workspace(id="ws-ctx-test", name="Context Test Workspace", owner_id="test-runner")
    storage.create_workspace(ws)

    proj = Project(
        id="proj-ctx-test",
        workspace_id=ws.id,
        name="Context Engine Test Project",
        description="Core test project for smart token optimization",
        status=ProjectStatus.ACTIVE,
    )
    storage.create_project(proj)
    main_b = vc.initialize_project_main_branch(proj.id)

    # Initial Task
    task1 = TaskRecord(
        id="task-auth",
        project_id=proj.id,
        title="Implement OAuth2 Token Refresh",
        description="OAuth2 bearer token refresh endpoint",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
    )
    # Approved Decision
    dec1 = DecisionRecord(
        id="dec-jwt",
        project_id=proj.id,
        title="Use JWT for Stateless Auth",
        decision="Use Spring Security 6 with JJWT library",
        rationale="High throughput, horizontally scalable",
        status=DecisionStatus.APPROVED,
        created_by="architect",
    )
    # Proposed Decision
    dec2 = DecisionRecord(
        id="dec-redis",
        project_id=proj.id,
        title="Use Redis for token revocation blacklist",
        decision="Redis cluster blacklist with TTL",
        rationale="Fast in-memory expiration",
        status=DecisionStatus.PROPOSED,
        created_by="engineer",
    )
    # Checkpoint
    cp1 = ResumeCheckpoint(
        id="cp-init",
        project_id=proj.id,
        task_id=task1.id,
        status=CheckpointStatus.ACTIVE,
        completed_actions=["Created auth controller stub", "Added JJWT dependency"],
        pending_actions=["Implement JwtAuthFilter", "Add WebSecurityConfig"],
        next_action="Implement JwtAuthFilter doFilterInternal() method",
        blockers=["Stripe client ID missing in staging"],
        base_revision=main_b.head_commit_id,
        created_by="architect",
    )
    # Artifact
    art1 = ArtifactReference(
        id="art-filter",
        project_id=proj.id,
        uri="src/main/java/com/barsa/auth/JwtAuthFilter.java",
        artifact_type=ArtifactType.SOURCE_CODE,
    )
    # Knowledge Fact
    k1 = KnowledgeRecord(
        id="know-ttl",
        project_id=proj.id,
        content="Access tokens must expire in 15 minutes; refresh tokens in 7 days.",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="architect",
    )

    c1 = vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=task1.id,
                record_type="task",
                after_state=task1.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=dec1.id,
                record_type="decision",
                after_state=dec1.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=dec2.id,
                record_type="decision",
                after_state=dec2.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=cp1.id,
                record_type="checkpoint",
                after_state=cp1.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=art1.id,
                record_type="artifact",
                after_state=art1.model_dump(mode="json"),
            ),
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=k1.id,
                record_type="knowledge",
                after_state=k1.model_dump(mode="json"),
            ),
        ],
        message="feat: baseline architecture and resume checkpoint",
        author_id="architect",
        expected_head_commit_id=main_b.head_commit_id,
    )
    worker.process_pending_events(proj.id)

    return {
        "storage": storage,
        "vc": vc,
        "graph": graph,
        "worker": worker,
        "retrieval": retrieval,
        "engine": engine,
        "project": proj,
        "commit1": c1.commit_id,
        "task1": task1,
        "dec1": dec1,
        "dec2": dec2,
        "cp1": cp1,
        "art1": art1,
        "k1": k1,
    }


# =============================================================================
# 1. Essential Context Retrieval
# =============================================================================
def test_essential_context_retrieval(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    req = ContextRequest(
        project_id=proj.id,
        context_level=ContextLevel.ESSENTIAL,
        max_context_tokens=2000,
    )
    pkg = engine.build_context(req)

    assert pkg.project_id == proj.id
    assert pkg.current_task is not None
    assert pkg.current_task["id"] == "task-auth"
    assert pkg.latest_checkpoint is not None
    assert pkg.latest_checkpoint["id"] == "cp-init"
    assert pkg.next_action == "Implement JwtAuthFilter doFilterInternal() method"
    assert "Stripe client ID missing in staging" in pkg.blockers
    assert len(pkg.approved_decisions) == 1
    assert pkg.approved_decisions[0]["id"] == "dec-jwt"
    assert pkg.completeness in (CompletenessStatus.SUFFICIENT, CompletenessStatus.PARTIAL)


# =============================================================================
# 2. Working Context Retrieval
# =============================================================================
def test_working_context_retrieval(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    req = ContextRequest(
        project_id=proj.id,
        context_level=ContextLevel.WORKING,
        max_context_tokens=4000,
    )
    pkg = engine.build_context(req)

    # Should include Level 1 + Level 2 working knowledge & references
    assert pkg.current_task is not None
    assert len(pkg.approved_decisions) >= 1
    assert "src/main/java/com/barsa/auth/JwtAuthFilter.java" in pkg.references
    assert len(pkg.working_knowledge) >= 1
    assert any("15 minutes" in wk.get("content", "") for wk in pkg.working_knowledge)


# =============================================================================
# 3. Detailed Retrieval
# =============================================================================
def test_detailed_retrieval(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    req = ContextRequest(
        project_id=proj.id,
        context_level=ContextLevel.DETAILED,
        include_history=True,
        max_context_tokens=5000,
    )
    pkg = engine.build_context(req)

    assert len(pkg.historical_context) >= 1
    assert any("baseline" in str(hc.get("message", "")).lower() for hc in pkg.historical_context)


# =============================================================================
# 4. Ranking Correctness
# =============================================================================
def test_ranking_correctness() -> None:
    ranker = RelevanceRanker()

    approved_rec = {"id": "d1", "record_type": "decision", "status": "approved", "title": "OAuth2 Standard"}
    proposed_rec = {"id": "d2", "record_type": "decision", "status": "proposed", "title": "OAuth2 Experimental"}
    superseded_rec = {"id": "d3", "record_type": "decision", "status": "superseded", "title": "Old Cookie Auth"}

    exp_app = ranker.rank_record(approved_rec)
    exp_prop = ranker.rank_record(proposed_rec)
    exp_sup = ranker.rank_record(superseded_rec)

    assert exp_app.relevance_score > exp_prop.relevance_score
    assert exp_prop.relevance_score > exp_sup.relevance_score
    assert "Approved architectural decision" in exp_app.reasons


# =============================================================================
# 5. Graph-Distance Ranking
# =============================================================================
def test_graph_distance_ranking() -> None:
    ranker = RelevanceRanker()

    rec = {"id": "t1", "record_type": "task", "title": "Security Filter"}
    exp_1hop = ranker.rank_record(rec, graph_distance=1)
    exp_2hop = ranker.rank_record(rec, graph_distance=2)
    exp_far = ranker.rank_record(rec, graph_distance=5)

    assert exp_1hop.relevance_score > exp_2hop.relevance_score
    assert exp_2hop.relevance_score > exp_far.relevance_score


# =============================================================================
# 6. Mandatory Information Preservation
# =============================================================================
def test_mandatory_information_preservation(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    req = ContextRequest(
        project_id=proj.id,
        max_context_tokens=800,  # Tight budget
        context_level=ContextLevel.ADAPTIVE,
    )
    pkg = engine.build_context(req)

    # Mandatory components must still be preserved
    assert pkg.next_action == "Implement JwtAuthFilter doFilterInternal() method"
    assert "Stripe client ID missing in staging" in pkg.blockers
    assert len(pkg.approved_decisions) >= 1


# =============================================================================
# 7. Duplicate Removal
# =============================================================================
def test_duplicate_removal() -> None:
    dedup = RecordDeduplicator()

    r1 = {"id": "k1", "title": "Database Policy", "content": "All passwords hashed with Argon2"}
    r1_dup_id = {"id": "k1", "title": "Database Policy", "content": "Modified content with same id"}
    r1_dup_content = {"id": "k2", "title": "Database Policy", "content": "All passwords hashed with Argon2"}

    unique = dedup.filter_unique([r1, r1_dup_id, r1_dup_content])
    assert len(unique) == 1
    assert unique[0]["id"] == "k1"


# =============================================================================
# 8. Contradictory Information Preservation
# =============================================================================
def test_contradictory_information_preservation() -> None:
    dedup = RecordDeduplicator()

    # Contradictory decisions must NOT be collapsed
    r1 = {
        "id": "dec-pg",
        "title": "Database Engine",
        "content": "Use PostgreSQL for relational consistency",
        "status": "approved",
    }
    r2 = {
        "id": "dec-my",
        "title": "Database Engine",
        "content": "Use MySQL for relational consistency",
        "status": "proposed",
    }

    unique = dedup.filter_unique([r1, r2])
    assert len(unique) == 2
    ids = {r["id"] for r in unique}
    assert "dec-pg" in ids and "dec-my" in ids


# =============================================================================
# 9. Exact Token Counting Where Supported
# =============================================================================
def test_exact_mock_token_counting() -> None:
    mock_counter = ExactMockTokenCounter(divisor=4, name="mock-exact")
    assert mock_counter.is_exact is True
    assert mock_counter.count("12345678") == 2
    assert mock_counter.count("1234") == 1


# =============================================================================
# 10. Estimated Token Counting Fallback
# =============================================================================
def test_heuristic_token_counting_fallback() -> None:
    counter = HeuristicTokenCounter()
    assert counter.is_exact is False
    assert "heuristic" in counter.estimation_method

    count_english = counter.count("This is a standard English sentence for token estimation.")
    assert count_english > 5

    # CJK characters increase token weight appropriately
    count_cjk = counter.count("这是一个中文句子用于分词测试。")
    assert count_cjk > 5


# =============================================================================
# 11. Budget Enforcement
# =============================================================================
def test_budget_enforcement() -> None:
    counter = ExactMockTokenCounter(divisor=1)
    allocator = TokenBudgetAllocator(counter)

    mandatory = [{"id": "m1", "text": "mand1"}]
    c1 = ({"id": "opt1", "text": "opt1_long_payload_abcdefghij"}, RelevanceRanker().rank_record({"id": "opt1"}))
    c2 = ({"id": "opt2", "text": "opt2_short"}, RelevanceRanker().rank_record({"id": "opt2"}))

    # Low budget that only fits mandatory and 1 small item
    res = allocator.allocate(
        max_tokens=60, reserved_overhead=10, mandatory_records=mandatory, candidate_optional=[c1, c2]
    )

    assert res.token_usage.count <= 60
    assert "opt1" in res.omitted_record_refs or "opt2" in res.omitted_record_refs
    assert res.completeness == CompletenessStatus.PARTIAL


# =============================================================================
# 12. Insufficient Budget Response
# =============================================================================
def test_insufficient_budget_response() -> None:
    counter = ExactMockTokenCounter(divisor=1)
    allocator = TokenBudgetAllocator(counter)

    mandatory = [{"id": "m1", "text": "a" * 500}]  # 500 chars

    res = allocator.allocate(max_tokens=100, reserved_overhead=10, mandatory_records=mandatory, candidate_optional=[])

    assert res.completeness == CompletenessStatus.INSUFFICIENT
    assert "insufficient" in res.completeness_reasons[0].lower()


# =============================================================================
# 13. Relevant Source References
# =============================================================================
def test_relevant_source_references(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    pkg = engine.build_context(ContextRequest(project_id=proj.id, context_level=ContextLevel.WORKING))
    assert len(pkg.references) >= 1
    assert "src/main/java/com/barsa/auth/JwtAuthFilter.java" in pkg.references


# =============================================================================
# 14. Missing Checkpoint Handling
# =============================================================================
def test_missing_checkpoint_handling(context_test_env: dict) -> None:
    storage: SQLiteStorageProvider = context_test_env["storage"]
    vc: VersionControlEngine = context_test_env["vc"]
    ws = context_test_env["project"].workspace_id

    # Create project with zero checkpoints
    p2 = Project(id="proj-no-cp", workspace_id=ws, name="No Checkpoint Project")
    storage.create_project(p2)
    vc.initialize_project_main_branch(p2.id)

    engine: SmartContextEngine = context_test_env["engine"]
    pkg = engine.build_context(ContextRequest(project_id=p2.id))

    assert pkg.project_id == p2.id
    assert pkg.latest_checkpoint is None
    assert pkg.next_action is None


# =============================================================================
# 15. Stale Graph Handling
# =============================================================================
def test_stale_graph_handling(context_test_env: dict) -> None:
    proj_id = context_test_env["project"].id
    status, reasons, warnings = ContextCompletenessValidator.validate_package(
        project_id=proj_id,
        target_task_id=None,
        authoritative_commit="commit-HEAD-new",
        graph_commit="commit-LAGGING-old",
        current_task=None,
        latest_checkpoint=None,
        blockers=[],
        approved_decisions=[],
        omitted_refs=[],
        base_completeness=CompletenessStatus.SUFFICIENT,
        all_included_records=[],
    )

    assert status == CompletenessStatus.STALE
    assert any("lagging" in w.lower() for w in warnings)


# =============================================================================
# 16. Project Access Isolation
# =============================================================================
def test_project_access_isolation() -> None:
    with pytest.raises(ValueError, match="Cross-project isolation violation"):
        ContextCompletenessValidator.validate_package(
            project_id="proj-A",
            target_task_id=None,
            authoritative_commit="head-1",
            graph_commit="head-1",
            current_task=None,
            latest_checkpoint=None,
            blockers=[],
            approved_decisions=[],
            omitted_refs=[],
            base_completeness=CompletenessStatus.SUFFICIENT,
            all_included_records=[{"id": "rec-1", "project_id": "proj-B-OTHER"}],
        )


# =============================================================================
# 17. Incremental Updates
# =============================================================================
def test_incremental_updates(context_test_env: dict) -> None:
    vc: VersionControlEngine = context_test_env["vc"]
    proj = context_test_env["project"]
    c1 = context_test_env["commit1"]
    engine: SmartContextEngine = context_test_env["engine"]

    # Create Commit 2
    t2 = TaskRecord(id="task-oauth-client", project_id=proj.id, title="Implement OAuth client")
    vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t2.id,
                record_type="task",
                after_state=t2.model_dump(mode="json"),
            )
        ],
        message="feat: add oauth client",
        author_id="architect",
        expected_head_commit_id=c1,
    )

    pkg = engine.build_context(ContextRequest(project_id=proj.id, known_revision=c1))
    assert pkg.incremental_sync is not None
    assert pkg.incremental_sync.is_incremental is True
    assert pkg.incremental_sync.rebase_required is False
    assert "task-oauth-client" in pkg.incremental_sync.added_records


# =============================================================================
# 18. Branch-Aware Revision Handling
# =============================================================================
def test_branch_aware_revision_handling(context_test_env: dict) -> None:
    vc: VersionControlEngine = context_test_env["vc"]
    proj = context_test_env["project"]
    c1 = context_test_env["commit1"]
    engine: SmartContextEngine = context_test_env["engine"]

    # Create diverged feature branch
    vc.create_branch(proj.id, "feature/oauth", start_commit_id=c1)
    t_feat = TaskRecord(id="task-feat", project_id=proj.id, title="Feature branch task")
    c_feat = vc.create_commit(
        project_id=proj.id,
        branch_name="feature/oauth",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t_feat.id,
                record_type="task",
                after_state=t_feat.model_dump(mode="json"),
            )
        ],
        message="feat: isolated branch commit",
        author_id="dev",
        expected_head_commit_id=c1,
    )

    # Also advance main
    t_main = TaskRecord(id="task-main-adv", project_id=proj.id, title="Main branch task")
    vc.create_commit(
        project_id=proj.id,
        branch_name="main",
        changes=[
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t_main.id,
                record_type="task",
                after_state=t_main.model_dump(mode="json"),
            )
        ],
        message="feat: advance main",
        author_id="dev",
        expected_head_commit_id=c1,
    )

    # Attempt incremental sync from diverged feature commit into main
    pkg = engine.build_context(ContextRequest(project_id=proj.id, known_revision=c_feat.commit_id))
    assert pkg.incremental_sync is not None
    assert pkg.incremental_sync.rebase_required is True
    assert pkg.incremental_sync.is_incremental is False


# =============================================================================
# 19. Invalid Revision Detection
# =============================================================================
def test_invalid_revision_detection(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    pkg = engine.build_context(ContextRequest(project_id=proj.id, known_revision="non-existent-sha-999"))
    assert pkg.incremental_sync is not None
    assert pkg.incremental_sync.rebase_required is True
    assert "does not exist" in pkg.incremental_sync.details


# =============================================================================
# 20. Serialization Round Trips
# =============================================================================
def test_serialization_round_trips(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    pkg = engine.build_context(ContextRequest(project_id=proj.id))
    raw_json = pkg.model_dump_json()

    restored = BarsaContextPackage.model_validate_json(raw_json)
    assert restored.project_id == pkg.project_id
    assert restored.token_usage.count == pkg.token_usage.count
    assert restored.authoritative_commit == pkg.authoritative_commit


# =============================================================================
# 21. Context Completeness Validation
# =============================================================================
def test_context_completeness_validation() -> None:
    status, reasons, warnings = ContextCompletenessValidator.validate_package(
        project_id="p1",
        target_task_id="t-missing",
        authoritative_commit="c1",
        graph_commit="c1",
        current_task=None,
        latest_checkpoint=None,
        blockers=["Blocker A"],
        approved_decisions=[],
        omitted_refs=["omitted-1", "omitted-2"],
        base_completeness=CompletenessStatus.SUFFICIENT,
        all_included_records=[],
    )

    assert status == CompletenessStatus.PARTIAL
    assert any("missing" in w.lower() for w in warnings)
    assert any("blocker" in r.lower() for r in reasons)


# =============================================================================
# 22. REST API Endpoints
# =============================================================================
def test_rest_api_endpoints(context_test_env: dict) -> None:
    engine: SmartContextEngine = context_test_env["engine"]
    proj = context_test_env["project"]

    app = create_app()
    app.dependency_overrides[get_context_engine] = lambda: engine

    with TestClient(app) as client:
        # 1. POST /api/v1/context/build
        res_build = client.post(
            "/api/v1/context/build",
            json={"project_id": proj.id, "max_context_tokens": 4000, "context_level": "working"},
        )
        assert res_build.status_code == 200
        data_build = res_build.json()
        assert data_build["project_id"] == proj.id
        assert data_build["next_action"] is not None

        # 2. POST /api/v1/context/estimate
        res_est = client.post(
            "/api/v1/context/estimate",
            json={"project_id": proj.id, "max_context_tokens": 4000},
        )
        assert res_est.status_code == 200
        data_est = res_est.json()
        assert data_est["fits_budget"] is True
        assert data_est["estimated_tokens"] > 0

        # 3. GET /api/v1/projects/{project_id}/context/status
        res_status = client.get(f"/api/v1/projects/{proj.id}/context/status")
        assert res_status.status_code == 200
        data_status = res_status.json()
        assert data_status["project_id"] == proj.id
        assert data_status["authoritative_commit"] == context_test_env["commit1"]


# =============================================================================
# 23. MCP Integration
# =============================================================================
def test_mcp_build_context_integration(context_test_env: dict) -> None:
    storage = context_test_env["storage"]
    vc = context_test_env["vc"]
    retrieval = context_test_env["retrieval"]
    proj = context_test_env["project"]

    result = build_context_tool(
        storage=storage,
        vc=vc,
        retrieval=retrieval,
        project_id=proj.id,
        max_context_tokens=4000,
        context_level="adaptive",
    )

    assert result["project_id"] == proj.id
    assert result["context_format_version"] == "0.1"
    assert result["next_action"] == "Implement JwtAuthFilter doFilterInternal() method"
    assert "token_usage" in result
    assert result["token_usage"]["count"] > 0
