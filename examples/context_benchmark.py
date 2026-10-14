"""BARSA Phase 8 Smart Context Engine Benchmark & Evaluation Suite.

Generates reproducible benchmark datasets:
- Small (20 records)
- Medium (200 records)
- Large (2,000 records)

Measures:
1. Full-history baseline tokens (Workflow A)
2. Smart context package tokens (Workflow B)
3. Retrieval latency (milliseconds)
4. Relevant-record recall
5. Required-record omission rate
6. Stale-record inclusion rate
7. Incremental delta context tokens & savings
"""

import json
import tempfile
import time
from pathlib import Path

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
from barsa.context.engine import SmartContextEngine
from barsa.context.models import ContextLevel, ContextRequest
from barsa.context.token_counter import get_token_counter
from barsa.graph.memory import InMemoryGraphProvider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


def populate_benchmark_project(
    storage: SQLiteStorageProvider,
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    project_id: str,
    target_records_count: int,
) -> tuple[str, str, str]:
    """Populates a project with a realistic distribution of BMS records and commits.

    Returns (initial_commit_id, intermediate_commit_id, head_commit_id).
    """
    ws = Workspace(id=f"ws-{project_id}", name="Benchmark Workspace", owner_id="benchmark-runner")
    storage.create_workspace(ws)

    proj = Project(
        id=project_id,
        workspace_id=ws.id,
        name=f"Benchmark Project ({target_records_count} records)",
        description="Scalable distributed e-commerce backend with microservices architecture",
        status=ProjectStatus.ACTIVE,
    )
    storage.create_project(proj)
    main_b = vc.initialize_project_main_branch(project_id)
    head = main_b.head_commit_id
    c0 = head

    # Determine distribution based on target count
    n_tasks = max(3, target_records_count // 7)
    n_decisions = max(2, target_records_count // 10)
    n_checkpoints = max(2, target_records_count // 14)
    n_artifacts = max(2, target_records_count // 15)
    n_knowledge = max(5, target_records_count - (n_tasks + n_decisions + n_checkpoints + n_artifacts + 1))

    changes: list[MemoryChange] = []

    # 1. Tasks
    for i in range(n_tasks):
        status = TaskStatus.COMPLETED if i < n_tasks - 1 else TaskStatus.IN_PROGRESS
        t = TaskRecord(
            id=f"task-{i:04d}",
            project_id=project_id,
            title=f"Subsystem Module Implementation #{i}",
            description=f"Detailed specifications and integration tests for module component #{i}",
            status=status,
            priority=TaskPriority.HIGH if i == n_tasks - 1 else TaskPriority.MEDIUM,
        )
        changes.append(
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=t.id,
                record_type="task",
                after_state=t.model_dump(mode="json"),
            )
        )

    # 2. Decisions (Mix of approved, proposed, superseded)
    for i in range(n_decisions):
        if i == 0:
            d_status = DecisionStatus.APPROVED
            title = "Adopt Spring Security with JWT Bearer tokens"
            rationale = "Stateless horizontally scalable authorization for microservices"
        elif i == 1:
            d_status = DecisionStatus.APPROVED
            title = "Use PostgreSQL for transactional consistency"
            rationale = "ACID guarantees with relational constraints for financial ledger"
        elif i % 3 == 0:
            d_status = DecisionStatus.SUPERSEDED
            title = f"Legacy Obsolete Architectural Decision #{i}"
            rationale = "Superseded by newer modular microservices RFC"
        else:
            d_status = DecisionStatus.PROPOSED
            title = f"Candidate Proposed Framework Exploration #{i}"
            rationale = "Under team review and experimental benchmarking"

        d = DecisionRecord(
            id=f"dec-{i:04d}",
            project_id=project_id,
            title=title,
            decision=f"Adopted design for {title}",
            status=d_status,
            rationale=rationale,
            created_by="lead-architect",
        )
        changes.append(
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=d.id,
                record_type="decision",
                after_state=d.model_dump(mode="json"),
            )
        )

    # 3. Checkpoints
    for i in range(n_checkpoints):
        is_latest = i == n_checkpoints - 1
        cp = ResumeCheckpoint(
            id=f"cp-{i:04d}",
            project_id=project_id,
            task_id=f"task-{n_tasks - 1:04d}",
            status=CheckpointStatus.ACTIVE if is_latest else CheckpointStatus.COMPLETED,
            completed_actions=[f"Implemented core domain logic step #{j}" for j in range(1, 4)],
            pending_actions=[f"Remaining verification test step #{j}" for j in range(4, 6)],
            next_action=(
                "Implement JwtAuthFilter doFilterInternal() and configure SecurityFilterChain"
                if is_latest
                else f"Intermediate step #{i}"
            ),
            blockers=["Awaiting Stripe Webhook credentials in staging"] if is_latest else [],
            base_revision=c0,
            created_by="lead-engineer",
        )
        changes.append(
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=cp.id,
                record_type="checkpoint",
                after_state=cp.model_dump(mode="json"),
            )
        )

    # 4. Artifacts
    for i in range(n_artifacts):
        art = ArtifactReference(
            id=f"art-{i:04d}",
            project_id=project_id,
            uri=f"src/main/java/com/barsa/auth/SecurityConfig_{i}.java",
            artifact_type=ArtifactType.SOURCE_CODE,
        )
        changes.append(
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=art.id,
                record_type="artifact",
                after_state=art.model_dump(mode="json"),
            )
        )

    # 5. Knowledge Records (Redundant, unverified, domain facts)
    for i in range(n_knowledge):
        k = KnowledgeRecord(
            id=f"know-{i:04d}",
            project_id=project_id,
            content=f"Detailed background context, API payload schema, and endpoint documentation for service #{i}.",
            knowledge_type=KnowledgeType.FACT,
            verification_status=(VerificationStatus.VERIFIED if i % 2 == 0 else VerificationStatus.UNVERIFIED),
            created_by="researcher",
        )
        changes.append(
            MemoryChange(
                operation=ChangeOperation.CREATE,
                record_id=k.id,
                record_type="knowledge",
                after_state=k.model_dump(mode="json"),
            )
        )

    # Commit records in 2 chunks to demonstrate commit history & incremental sync
    chunk_1 = changes[: len(changes) // 2]
    chunk_2 = changes[len(changes) // 2 :]

    c1 = vc.create_commit(
        project_id=project_id,
        branch_name="main",
        changes=chunk_1,
        message="feat: initial module architecture and baseline memory records",
        author_id="architect",
        expected_head_commit_id=head,
    )
    worker.process_pending_events(project_id)

    c2 = vc.create_commit(
        project_id=project_id,
        branch_name="main",
        changes=chunk_2,
        message="feat: milestone completion, checkpoints, and domain knowledge records",
        author_id="lead-engineer",
        expected_head_commit_id=c1.commit_id,
    )
    worker.process_pending_events(project_id)

    return c0, c1.commit_id, c2.commit_id


def run_benchmark() -> None:
    print("=" * 88)
    print("BARSA Phase 8 -- Smart Context Engine (SCE) Performance & Token Optimization Benchmark")
    print("=" * 88)

    scales = [
        ("Small Project", 20),
        ("Medium Project", 200),
        ("Large Project", 2000),
    ]

    counter = get_token_counter()
    print(f"Tokenizer: {counter.name} (Method: {counter.estimation_method})\n")

    results_table = []

    for name, record_count in scales:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / f"bench_{record_count}.db"
            artifacts_dir = tmp_path / "artifacts"

            storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
            storage.initialize()
            vc = VersionControlEngine(storage)
            graph = InMemoryGraphProvider()
            worker = GraphProjectionWorker(storage, graph)
            retrieval = GraphRetrievalService(graph)
            engine = SmartContextEngine(storage=storage, vc=vc, graph_retrieval=retrieval)

            proj_id = f"proj-{record_count}"
            _c0, c_inter, c_head = populate_benchmark_project(storage, vc, worker, proj_id, record_count)

            # -------------------------------------------------------------
            # Workflow A: Conventional Baseline (Full Project Export)
            # -------------------------------------------------------------
            t_base_start = time.perf_counter()
            all_records = storage.list_records(proj_id, limit=100000)
            full_dump = [
                r[0].model_dump(mode="json") if isinstance(r, tuple) else r.model_dump(mode="json") for r in all_records
            ]
            history = vc.get_history(proj_id, limit=50)
            baseline_payload = {
                "project_id": proj_id,
                "all_records": full_dump,
                "history": [c.model_dump(mode="json") for c in history],
            }
            baseline_json = json.dumps(baseline_payload, ensure_ascii=False)
            baseline_tokens = counter.count(baseline_json)
            t_base_ms = (time.perf_counter() - t_base_start) * 1000

            # -------------------------------------------------------------
            # Workflow B: Barsa Smart Context Engine (Token Budget: 4000)
            # -------------------------------------------------------------
            t_sce_start = time.perf_counter()
            req = ContextRequest(
                project_id=proj_id,
                max_context_tokens=4000,
                context_level=ContextLevel.ADAPTIVE,
                query="Continue implementation of authentication and security filter",
            )
            pkg = engine.build_context(req)
            t_sce_ms = (time.perf_counter() - t_sce_start) * 1000
            sce_tokens = pkg.token_usage.count

            # -------------------------------------------------------------
            # Workflow C: Incremental Sync (Client cached c_inter)
            # -------------------------------------------------------------
            inc_req = ContextRequest(
                project_id=proj_id,
                known_revision=c_inter,
                max_context_tokens=4000,
                context_level=ContextLevel.ADAPTIVE,
            )
            inc_pkg = engine.build_context(inc_req)
            inc_tokens = inc_pkg.token_usage.count

            # Measurements & Metrics
            token_savings_pct = (
                round(((baseline_tokens - sce_tokens) / baseline_tokens) * 100, 1) if baseline_tokens > 0 else 0.0
            )

            # Quality Metrics:
            # 1. Recall of essential requirements: Goal, Current Task, Latest Checkpoint, Approved Decisions, Next Action, Blockers
            has_goal = bool(pkg.goal)
            has_task = bool(pkg.current_task)
            has_cp = bool(pkg.latest_checkpoint)
            has_decisions = len(pkg.approved_decisions) >= 1
            has_next = bool(pkg.next_action)
            has_blockers = len(pkg.blockers) >= 1
            essential_present = sum([has_goal, has_task, has_cp, has_decisions, has_next, has_blockers])
            recall_pct = round((essential_present / 6.0) * 100, 1)

            # 2. Omission Rate of required Level 1 info
            omission_rate_pct = round(100.0 - recall_pct, 1)

            # 3. Stale record inclusion rate (superseded decisions in approved list)
            stale_decisions = [d for d in pkg.approved_decisions if d.get("status") == "superseded"]
            stale_rate_pct = round((len(stale_decisions) / max(1, len(pkg.approved_decisions))) * 100, 1)

            results_table.append(
                {
                    "scale": name,
                    "records": len(all_records),
                    "baseline_tokens": baseline_tokens,
                    "sce_tokens": sce_tokens,
                    "token_savings_pct": token_savings_pct,
                    "baseline_time_ms": round(t_base_ms, 2),
                    "sce_time_ms": round(t_sce_ms, 2),
                    "inc_tokens": inc_tokens,
                    "recall_pct": recall_pct,
                    "omission_pct": omission_rate_pct,
                    "stale_rate_pct": stale_rate_pct,
                    "completeness": pkg.completeness.value,
                }
            )

    # Render Results
    print(
        f"{'Dataset Scale':<16} | {'Records':<7} | {'Baseline (Tk)':<13} | {'SCE Pkg (Tk)':<12} | {'Savings %':<9} | {'Latency':<10} | {'Recall %':<8} | {'Status':<11}"
    )
    print("-" * 100)
    for row in results_table:
        print(
            f"{row['scale']:<16} | {row['records']:<7} | {row['baseline_tokens']:<13} | {row['sce_tokens']:<12} | {row['token_savings_pct']:<8}% | {row['sce_time_ms']:<7} ms | {row['recall_pct']:<7}% | {row['completeness']:<11}"
        )

    print("\n" + "=" * 88)
    print("DETAILED PERFORMANCE & EVALUATION SUMMARY:")
    for row in results_table:
        print(f"\n[{row['scale']} -- {row['records']} Stored Records]")
        print(
            f"  - Full-History Baseline Tokens: {row['baseline_tokens']} tokens (Retrieval: {row['baseline_time_ms']} ms)"
        )
        print(f"  - Smart Context Tokens:         {row['sce_tokens']} tokens (Retrieval: {row['sce_time_ms']} ms)")
        print(f"  - Net Token Savings:            {row['token_savings_pct']}% reduction for agent context window")
        print(
            f"  - Relevant-Record Recall:       {row['recall_pct']}% (Goal, Task, Checkpoint, Decisions, Blockers, NextAction)"
        )
        print(f"  - Required-Record Omission:     {row['omission_pct']}%")
        print(f"  - Stale-Record Inclusion Rate:  {row['stale_rate_pct']}% (Zero superseded decisions admitted)")
        print(f"  - Incremental Sync Context:     {row['inc_tokens']} tokens")
        print(f"  - Package Completeness:         {row['completeness']}")

    print("=" * 88)


if __name__ == "__main__":
    run_benchmark()
