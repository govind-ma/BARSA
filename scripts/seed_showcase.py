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

def main():
    settings = get_settings()
    storage = get_storage_provider(settings)
    storage.initialize()

    # 1. Workspace
    ws_id = "default"
    ws = storage.get_workspace(ws_id)
    if not ws:
        ws = Workspace(
            id=ws_id,
            name="Production Workspace",
            owner_id="admin",
            description="Core engineering workspace for collaborative AI workflows.",
        )
        storage.create_workspace(ws)
        print("Created workspace:", ws_id)
    else:
        print("Workspace exists:", ws_id)

    # 2. Project
    proj_id = "incident-commander"
    proj = storage.get_project(proj_id)
    if not proj:
        proj = Project(
            id=proj_id,
            workspace_id=ws_id,
            name="Autonomous Incident Commander & Self-Healing SRE",
            description="High-concurrency microservices incident triage, automated circuit breaking, and distributed failover coordination powered by collaborative AI agents.",
            goals=[
                "Sub-15 second automated triage and isolation during production gateway surges.",
                "Zero cascading database lock starvation via distributed Redis Redlock circuit breakers.",
                "Seamless architectural context handover between Claude (Architecture), ChatGPT (Code), and Kimi (Security/QA)."
            ]
        )
        storage.create_project(proj)
        print("Created project:", proj_id)
    else:
        print("Project exists:", proj_id)

    # 3. Memory Records (ADR, Knowledge, Checkpoint)
    r1 = DecisionRecord(
        id="rec-adr-004",
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
    storage.create_record(r1)
    print("Created Decision Record:", r1.id)

    r2 = KnowledgeRecord(
        id="rec-log-signature",
        project_id=proj_id,
        content="Incident Diagnostic Signature: NGINX upstream timed out (110: Connection timed out) while connecting to upstream payment-rpc at 10.0.4.12:8080 under 14,200 req/sec burst load.",
        knowledge_type=KnowledgeType.OBSERVATION,
        verification_status=VerificationStatus.VERIFIED,
        created_by="kimi-auditor",
    )
    storage.create_record(r2)
    print("Created Knowledge Record:", r2.id)

    r3 = ResumeCheckpoint(
        id="rec-checkpoint-002",
        project_id=proj_id,
        task_id="task-02-circuit-breaker-design",
        status=CheckpointStatus.COMPLETED,
        completed_actions=[
            "Ingress NGINX logs analyzed across all 8 gateway pods",
            "504 Gateway Timeout root cause identified as SQL connection pool exhaustion",
            "ADR-004 circuit breaker specification authored and verified with zero security flaws"
        ],
        pending_actions=[
            "Implement Redis Token Bucket Circuit Breaker in FastAPI on the checkout service",
            "Execute automated chaos testing with 25,000 req/sec synthetic load"
        ],
        next_action="Implement Redis Token Bucket Circuit Breaker in FastAPI on the checkout service",
        blockers=[],
        base_revision="c1a2f3e4",
        created_by="kimi-auditor",
    )
    storage.create_record(r3)
    print("Created Resume Checkpoint:", r3.id)

    # 4. Coordination Tasks
    coord = CoordinatorEngine(storage)
    tasks = [
        CoordinationTask(
            task_id="task-01-log-triage",
            project_id=proj_id,
            title="Analyze Ingress Gateway Logs & Identify Bottleneck",
            description="Trace error spikes across NGINX ingress and isolate 504 Gateway Timeouts to database connection pool saturation.",
            status=CoordinationTaskStatus.COMPLETED,
            priority=Priority.CRITICAL,
            assigned_agent_id="kimi-auditor",
        ),
        CoordinationTask(
            task_id="task-02-circuit-breaker-design",
            project_id=proj_id,
            title="Design Circuit Breaker & Fallback Topology (ADR-004)",
            description="Formalize sliding window token bucket specification and define degraded mode fallback response.",
            status=CoordinationTaskStatus.COMPLETED,
            priority=Priority.HIGH,
            assigned_agent_id="claude-architect",
        ),
        CoordinationTask(
            task_id="task-03-fastapi-circuit-breaker",
            project_id=proj_id,
            title="Implement Redis Token Bucket Circuit Breaker in FastAPI",
            description="Implement atomic Lua script for Redis token bucket rate limiting and register middleware on the /checkout RPC route.",
            status=CoordinationTaskStatus.RUNNING,
            priority=Priority.HIGH,
            assigned_agent_id="chatgpt-engineer",
        ),
        CoordinationTask(
            task_id="task-04-chaos-testing",
            project_id=proj_id,
            title="Automated Chaos Testing & Gateway Load Verification",
            description="Simulate 25,000 req/sec payment traffic surge to verify zero dropped requests and automatic recovery.",
            status=CoordinationTaskStatus.READY,
            priority=Priority.MEDIUM,
            assigned_agent_id=None,
        )
    ]
    for t in tasks:
        try:
            coord.create_task(t)
            print("Created Coordination Task:", t.task_id)
        except Exception as e:
            print("Task already exists or notice:", e)

    # 5. Git-style Memory Commit
    vc = VersionControlEngine(storage)
    changes = [
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id=r1.id,
            record_type="decision",
            after_state=r1.model_dump(mode="json"),
        ),
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id=r2.id,
            record_type="knowledge",
            after_state=r2.model_dump(mode="json"),
        ),
        MemoryChange(
            operation=ChangeOperation.CREATE,
            record_id=r3.id,
            record_type="checkpoint",
            after_state=r3.model_dump(mode="json"),
        ),
    ]
    try:
        commit = vc.create_commit(
            project_id=proj_id,
            branch_name="main",
            author_id="claude-architect",
            author_type=AuthorType.AGENT,
            message="feat(sre): triage gateway timeout anomaly and commit ADR-004 circuit breaker specification",
            changes=changes,
        )
        print("Created Commit:", commit.commit_id)
    except Exception as e:
        print("Commit note:", e)

    print("\n--- SHOWCASE PROJECT CREATED SUCCESSFULLY! ---")

if __name__ == "__main__":
    main()
