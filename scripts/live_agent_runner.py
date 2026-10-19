import time
import sys
from datetime import datetime, timezone

from barsa.core.config import get_settings
from barsa.storage.factory import get_storage_provider
from barsa.bms.records import (
    Workspace,
    Project,
    DecisionRecord,
    KnowledgeRecord,
    ResumeCheckpoint,
    DecisionStatus,
    KnowledgeType,
    VerificationStatus,
    CheckpointStatus,
)
from barsa.coordination.engine import CoordinatorEngine
from barsa.coordination.models import CoordinationTask, CoordinationTaskStatus, Priority
from barsa.versioning.engine import VersionControlEngine
from barsa.models.versioning import MemoryChange, ChangeOperation, AuthorType

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def print_banner(text, color="\033[96m"):
    reset = "\033[0m"
    print(f"\n{color}{'='*60}\n{text}\n{'='*60}{reset}")

def main():
    settings = get_settings()
    storage = get_storage_provider(settings)
    storage.initialize()
    coord = CoordinatorEngine(storage)
    vc = VersionControlEngine(storage)

    proj_id = "incident-commander"
    proj = storage.get_project(proj_id)
    if not proj:
        print("Project 'incident-commander' not found. Please create it first.")
        return

    print_banner("⚡ BARSA LIVE MULTI-AGENT WORKFLOW SIMULATOR", "\033[95m")
    print("This script executes REAL live agent operations against your local BARSA instance.")
    print("Watch your browser at http://localhost:5173/ as each agent completes work!\n")

    # -------------------------------------------------------------
    # PHASE 1: KIMI AUDITOR
    # -------------------------------------------------------------
    print_banner("🤖 [AGENT 1: KIMI AUDITOR] Triage & Anomaly Detection", "\033[93m")
    print(">> Kimi connecting via MCP protocol (provider: moonshot)...")
    time.sleep(1)

    print(">> Kimi claiming task 'task-01-log-triage'...")
    try:
        coord.update_task_status("task-01-log-triage", CoordinationTaskStatus.RUNNING)
        print("   [STATUS] Task status: RUNNING (Lease active)")
    except Exception as e:
        print("   Notice:", e)
    time.sleep(1.5)

    print(">> Kimi publishing verified observation to BARSA Knowledge Memory...")
    r_log = KnowledgeRecord(
        id=f"rec-log-{int(time.time())}",
        project_id=proj_id,
        content="CRITICAL ALERT: NGINX upstream timed out (110: Connection timed out) at payment gateway under 14,200 req/sec surge. Root cause: connection pool exhaustion.",
        knowledge_type=KnowledgeType.OBSERVATION,
        verification_status=VerificationStatus.VERIFIED,
        created_by="kimi-auditor",
    )
    storage.create_record(r_log)
    print(f"   [MEMORY SAVED] Record {r_log.id} stored in BMS format.")
    time.sleep(1.5)

    print(">> Kimi marking task as COMPLETED...")
    coord.update_task_status("task-01-log-triage", CoordinationTaskStatus.COMPLETED)
    print("   ✅ Task 'Analyze Ingress Gateway Logs' is now DONE!")
    time.sleep(2)

    # -------------------------------------------------------------
    # PHASE 2: CLAUDE ARCHITECT
    # -------------------------------------------------------------
    print_banner("🤖 [AGENT 2: CLAUDE ARCHITECT] System Design & ADR", "\033[94m")
    print(">> Claude Architect reading Kimi's newly published log observation...")
    time.sleep(1)
    print(">> Claude determining optimal concurrency mitigation strategy...")
    time.sleep(1.5)

    print(">> Claude authoring formal Architectural Decision Record (ADR-004)...")
    r_adr = DecisionRecord(
        id=f"rec-adr-{int(time.time())}",
        project_id=proj_id,
        title="ADR-004: Redis Rate-Limiting & Circuit Breakers for Payment Gateway",
        decision="Adopt an exponential backoff circuit breaker with a sliding-window Redis token bucket (100 req/sec limit) over synchronous database row locks.",
        rationale="During flash traffic spikes, SQL row-level locks cause thread pool starvation and 504 Gateway Timeouts across upstream services. Redis token buckets isolate payment bursts in under 2ms without degrading primary database connection pools.",
        status=DecisionStatus.APPROVED,
        created_by="claude-architect",
        alternatives=[
            "PostgreSQL SELECT FOR UPDATE locks (causes thread pool starvation)",
            "In-memory application server rate limiting (fails across horizontal replicas)"
        ],
    )
    storage.create_record(r_adr)
    print(f"   [ADR COMMITTED] {r_adr.title}")
    time.sleep(1)

    print(">> Claude committing memory mutation to Git DAG on branch 'main'...")
    try:
        commit = vc.create_commit(
            project_id=proj_id,
            branch_name="main",
            author_id="claude-architect",
            author_type=AuthorType.AGENT,
            message="feat(sre): author ADR-004 Redis token bucket circuit breaker spec",
            changes=[
                MemoryChange(
                    operation=ChangeOperation.CREATE,
                    record_id=r_adr.id,
                    record_type="decision",
                    after_state=r_adr.model_dump(mode="json"),
                )
            ]
        )
        print(f"   [GIT COMMIT] Created commit {commit.commit_id[:12]} on branch 'main'")
    except Exception as e:
        print("   Notice:", e)

    coord.update_task_status("task-02-circuit-breaker-design", CoordinationTaskStatus.COMPLETED)
    print("   ✅ Task 'Design Circuit Breaker & Fallback Topology' is now DONE!")
    time.sleep(2)

    # -------------------------------------------------------------
    # PHASE 3: CHATGPT ENGINEER
    # -------------------------------------------------------------
    print_banner("🤖 [AGENT 3: CHATGPT ENGINEER] Hotfix Implementation", "\033[92m")
    print(">> ChatGPT Engineer querying BARSA graph for recommended unblocked task...")
    time.sleep(1)
    print("   [GRAPH ENGINE] Prerequisite tasks & ADRs verified. Recommended: 'task-03-fastapi-circuit-breaker'")
    time.sleep(1)

    print(">> ChatGPT claiming task 'task-03-fastapi-circuit-breaker'...")
    coord.update_task_status("task-03-fastapi-circuit-breaker", CoordinationTaskStatus.RUNNING)
    print("   [STATUS] Task status: RUNNING (Assigned to chatgpt-engineer)")
    time.sleep(1.5)

    print(">> ChatGPT saving Milestone Checkpoint for agent resumption...")
    r_chk = ResumeCheckpoint(
        id=f"rec-chk-{int(time.time())}",
        project_id=proj_id,
        task_id="task-03-fastapi-circuit-breaker",
        status=CheckpointStatus.ACTIVE,
        completed_actions=[
            "Ingress NGINX logs analyzed across all 8 gateway pods by Kimi",
            "ADR-004 circuit breaker specification authored and verified by Claude",
            "Drafted Redis token bucket Lua script for atomic 100 req/sec rate limiting"
        ],
        pending_actions=[
            "Mount Redis token bucket middleware on /checkout endpoint",
            "Deploy hotfix to staging cluster"
        ],
        next_action="Mount Redis token bucket middleware on /checkout endpoint",
        blockers=[],
        base_revision="c1a2f3e4",
        created_by="chatgpt-engineer",
    )
    storage.create_record(r_chk)
    print("   [CHECKPOINT SAVED] Milestone saved! Any agent can now resume with one click.")

    print_banner("🎉 LIVE AGENT WORKFLOW COMPLETE! CHECK YOUR BROWSER!", "\033[95m")
    print("Go to http://localhost:5173/ and refresh to see all live changes!")

if __name__ == "__main__":
    main()
