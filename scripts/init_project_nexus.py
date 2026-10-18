"""Initialize Project NEXUS in BARSA Authoritative Storage (.barsa/barsa.db) and FalkorDB Cloud.

Sets up:
- Workspace: ws-nexus
- Project: proj-nexus
- 10 Interconnected Microservices
- Service Dependencies in FalkorDB
- Core Tasks (TASK-NX-001 to TASK-NX-012)
- Architectural Decisions (ADR-NX-001, ADR-NX-002)
- Baseline Checkpoint (CP-NX-001)
- Git-style Memory Commit on branch 'main'
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from barsa.bms.records import (
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
from barsa.core.config import get_settings
from barsa.graph.factory import get_graph_provider, reset_graph_instances
from barsa.models.graph import GraphNode, GraphNodeType, GraphRelationship, GraphRelationshipType
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.factory import get_storage_provider
from barsa.versioning.engine import VersionControlEngine

PROJECT_ID = "proj-nexus"
WORKSPACE_ID = "ws-nexus"

SERVICES = [
    {"id": "SRV-GATEWAY", "name": "API Gateway", "criticality": "tier-1", "deps": ["SRV-AUTH", "SRV-USER", "SRV-ORDER"]},
    {"id": "SRV-AUTH", "name": "Authentication Service", "criticality": "tier-1", "deps": ["SRV-DB"]},
    {"id": "SRV-USER", "name": "User Service", "criticality": "tier-2", "deps": ["SRV-DB"]},
    {"id": "SRV-PAYMENT", "name": "Payment Service", "criticality": "tier-1", "deps": ["SRV-DB", "SRV-MQ"]},
    {"id": "SRV-INVENTORY", "name": "Inventory Service", "criticality": "tier-2", "deps": ["SRV-DB"]},
    {"id": "SRV-ORDER", "name": "Order Service", "criticality": "tier-1", "deps": ["SRV-PAYMENT", "SRV-INVENTORY", "SRV-MQ"]},
    {"id": "SRV-NOTIF", "name": "Notification Service", "criticality": "tier-3", "deps": ["SRV-MQ"]},
    {"id": "SRV-ANALYTICS", "name": "Analytics Service", "criticality": "tier-3", "deps": ["SRV-MQ", "SRV-DB"]},
    {"id": "SRV-DB", "name": "Database Cluster", "criticality": "tier-0", "deps": []},
    {"id": "SRV-MQ", "name": "Message Queue (Kafka)", "criticality": "tier-0", "deps": []},
]

TASKS = [
    {
        "id": "TASK-NX-001",
        "title": "Service Registry & Graph Schema Specification",
        "description": "Define Pydantic and FalkorDB models for interconnected microservices, criticality tiers, and dependency edges.",
        "status": "completed",
        "priority": "critical",
        "dependencies": [],
        "assigned_agent_id": "claude-architect",
    },
    {
        "id": "TASK-NX-002",
        "title": "FalkorDB Cypher Blast Radius & Cascade Impact Queries",
        "description": "Implement Cypher query to trace downstream affected services and calculate incident blast radius score.",
        "status": "completed",
        "priority": "critical",
        "dependencies": ["TASK-NX-001"],
        "assigned_agent_id": "claude-backend",
    },
    {
        "id": "TASK-NX-003",
        "title": "FastAPI Incident Ingestion & Service Dependency Endpoints",
        "description": "Expose POST /incidents and GET /incidents/{id}/impact querying FalkorDB graph.",
        "status": "in_progress",
        "priority": "critical",
        "dependencies": ["TASK-NX-002"],
        "assigned_agent_id": "claude-backend",
    },
    {
        "id": "TASK-NX-004",
        "title": "Dynamic Severity & Recovery Priority Calculation Engine",
        "description": "Calculate incident severity based on Tier-0/Tier-1 blast radius rather than static operator labels.",
        "status": "todo",
        "priority": "high",
        "dependencies": ["TASK-NX-003"],
        "assigned_agent_id": "chatgpt-engineer",
    },
    {
        "id": "TASK-NX-005",
        "title": "Automated Remediation Task Generator & Agent Capability Routing",
        "description": "Generate isolated recovery tasks for affected services and match with qualified SRE/DevOps engineers.",
        "status": "todo",
        "priority": "high",
        "dependencies": ["TASK-NX-004"],
        "assigned_agent_id": "chatgpt-engineer",
    },
    {
        "id": "TASK-NX-006",
        "title": "React Incident Topology Visualization & Blast Radius Dashboard",
        "description": "Interactive visual dependency graph showing failing nodes in red, degraded in orange, healthy in green.",
        "status": "todo",
        "priority": "medium",
        "dependencies": ["TASK-NX-003"],
        "assigned_agent_id": "chatgpt-frontend",
    },
]

DECISIONS = [
    {
        "id": "ADR-NX-001",
        "title": "FalkorDB Graph Traversal for Downstream Cascade Analysis",
        "decision": "Use FalkorDB Labeled Property Graph to evaluate cascading microservice blast radius via multi-hop DEPENDS_ON Cypher queries.",
        "rationale": "Microservice cascades are recursive DAG traversals. Relational joins degrade exponentially while Cypher traverses sub-millisecond.",
    },
    {
        "id": "ADR-NX-002",
        "title": "Dynamic Severity Derivation from Dependency Criticality",
        "decision": "Severity is dynamically computed from the maximum criticality tier of all downstream services affected by the incident.",
        "rationale": "Static human severity labeling frequently underestimates systemic cascade failures until user impact is catastrophic.",
    },
]

def init_nexus():
    settings = get_settings()
    storage = get_storage_provider(settings)
    storage.initialize()
    vc = VersionControlEngine(storage)

    print(f"Initializing Project NEXUS in {settings.db_path}...")

    # 1. Workspace
    ws = storage.get_workspace(WORKSPACE_ID)
    if not ws:
        ws = Workspace(
            id=WORKSPACE_ID,
            name="NEXUS Global Operations Workspace",
            owner_id="operations-lead",
            description="Intelligent Incident Management & Recovery Collaboration Space",
        )
        storage.create_workspace(ws)
    print(f"Workspace {WORKSPACE_ID} ready.")

    # 2. Project
    proj = storage.get_project(PROJECT_ID)
    if not proj:
        proj = Project(
            id=PROJECT_ID,
            workspace_id=WORKSPACE_ID,
            name="NEXUS — Intelligent Incident Management & Recovery Platform",
            description="Autonomous incident triage, blast-radius graph reasoning, and remediation coordination across interconnected services.",
            goals=[
                "Sub-millisecond cascade impact calculation using FalkorDB",
                "Dynamic incident severity classification based on service criticality",
                "Automated recovery task routing to specialized engineers and AI agents",
                "Cross-AI memory persistence across Claude and ChatGPT sessions",
            ],
            status=ProjectStatus.ACTIVE,
        )
        storage.create_project(proj)
    print(f"Project {PROJECT_ID} ready.")

    # 3. Main branch
    branch = vc.get_branch(PROJECT_ID, "main")
    if not branch:
        vc.initialize_project_main_branch(PROJECT_ID, author_id="claude-architect")
        print("Initialized main branch for proj-nexus.")

    changes = []
    existing = {r[0].id if isinstance(r, tuple) else r.id for r in storage.list_records(PROJECT_ID)}

    # 4. Tasks
    status_map = {
        "completed": TaskStatus.COMPLETED,
        "in_progress": TaskStatus.IN_PROGRESS,
        "todo": TaskStatus.TODO,
        "blocked": TaskStatus.BLOCKED,
    }
    priority_map = {
        "critical": TaskPriority.CRITICAL,
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW,
    }

    for t in TASKS:
        tid = t["id"]
        tr = TaskRecord(
            id=tid,
            project_id=PROJECT_ID,
            title=t["title"],
            description=t["description"],
            status=status_map[t["status"]],
            priority=priority_map[t["priority"]],
            dependencies=t["dependencies"],
            assigned_agent_id=t.get("assigned_agent_id"),
        )
        if tid not in existing:
            storage.create_record(tr)
            changes.append(MemoryChange(record_id=tid, record_type="task", operation=ChangeOperation.CREATE, after_state=tr.model_dump(mode="json")))

    # 5. Decisions
    for d in DECISIONS:
        did = d["id"]
        dr = DecisionRecord(
            id=did,
            project_id=PROJECT_ID,
            title=d["title"],
            decision=d["decision"],
            rationale=d["rationale"],
            status=DecisionStatus.APPROVED,
            created_by="claude-architect",
        )
        if did not in existing:
            storage.create_record(dr)
            changes.append(MemoryChange(record_id=did, record_type="decision", operation=ChangeOperation.CREATE, after_state=dr.model_dump(mode="json")))

    # 6. Checkpoint CP-NX-001 (Claude completed TASK-NX-001 & 002, in progress on TASK-NX-003)
    cpid = "CP-NX-001"
    cpr = ResumeCheckpoint(
        id=cpid,
        project_id=PROJECT_ID,
        task_id="TASK-NX-003",
        status=CheckpointStatus.ACTIVE,
        completed_actions=[
            "Specified service topology graph schema and criticality levels (Tier-0 to Tier-3)",
            "Implemented and verified FalkorDB downstream blast radius Cypher query",
            "Designed FastAPI REST endpoints for incident triage",
        ],
        pending_actions=[
            "Finalize incident ingestion payload validation in FastAPI",
            "Implement TASK-NX-004: Dynamic severity derivation engine based on affected services",
            "Wire automated recovery task generation (TASK-NX-005)",
        ],
        next_action="Implement TASK-NX-004: Compute dynamic severity using downstream graph blast radius",
        blockers=[],
        decision_refs=["ADR-NX-001", "ADR-NX-002"],
        artifact_refs=["src/nexus/models.py", "src/nexus/graph.py", "tests/test_blast_radius.py"],
        base_revision="commit-nx-init",
        created_by="claude-architect",
    )
    if cpid not in existing:
        storage.create_record(cpr)
        changes.append(MemoryChange(record_id=cpid, record_type="checkpoint", operation=ChangeOperation.CREATE, after_state=cpr.model_dump(mode="json")))

    print(f"Stored {len(changes)} memory records in SQLite.")

    # 7. Commit
    if changes:
        try:
            head = vc.get_branch(PROJECT_ID, "main")
            parents = [head.head_commit_id] if (head and head.head_commit_id) else []
            commit = vc.create_commit(
                project_id=PROJECT_ID,
                author_id="claude-architect",
                message="feat(nexus): initial architecture, graph dependency model and baseline checkpoint CP-NX-001",
                parent_commit_ids=parents,
                changes=changes,
                branch_name="main",
            )
            print(f"Created baseline memory commit: {commit.commit_id}")
        except Exception as e:
            print(f"Commit note: {e}")

    # 8. Seed FalkorDB Cloud Graph for Project NEXUS
    reset_graph_instances()
    graph = get_graph_provider(settings)
    if graph.is_available():
        print("Connected to FalkorDB Cloud. Seeding NEXUS topology graph...")
        pid = PROJECT_ID
        graph.clear_project_graph(pid)

        # Project node
        graph.upsert_node(
            GraphNode(
                id=f"{pid}:project",
                raw_id="project",
                project_id=pid,
                node_type=GraphNodeType.PROJECT,
                properties={"name": "Project NEXUS", "status": "active"},
            )
        )

        # Service nodes
        for srv in SERVICES:
            graph.upsert_node(
                GraphNode(
                    id=f"{pid}:{srv['id']}",
                    raw_id=srv["id"],
                    project_id=pid,
                    node_type=GraphNodeType.KNOWLEDGE,
                    properties={"name": srv["name"], "criticality": srv["criticality"], "type": "service"},
                )
            )

        # Service dependency relationships
        for srv in SERVICES:
            for dep in srv["deps"]:
                graph.upsert_relationship(
                    GraphRelationship(
                        source_id=f"{pid}:{srv['id']}",
                        target_id=f"{pid}:{dep}",
                        rel_type=GraphRelationshipType.DEPENDS_ON,
                        project_id=pid,
                    )
                )

        # Tasks nodes & HAS_TASK
        for t in TASKS:
            graph.upsert_node(
                GraphNode(
                    id=f"{pid}:{t['id']}",
                    raw_id=t["id"],
                    project_id=pid,
                    node_type=GraphNodeType.TASK,
                    properties={"title": t["title"], "status": t["status"], "priority": t["priority"]},
                )
            )
            graph.upsert_relationship(
                GraphRelationship(
                    source_id=f"{pid}:project",
                    target_id=f"{pid}:{t['id']}",
                    rel_type=GraphRelationshipType.HAS_TASK,
                    project_id=pid,
                )
            )
            for dep in t["dependencies"]:
                graph.upsert_relationship(
                    GraphRelationship(
                        source_id=f"{pid}:{t['id']}",
                        target_id=f"{pid}:{dep}",
                        rel_type=GraphRelationshipType.DEPENDS_ON,
                        project_id=pid,
                    )
                )

        # Decisions
        for d in DECISIONS:
            graph.upsert_node(
                GraphNode(
                    id=f"{pid}:{d['id']}",
                    raw_id=d["id"],
                    project_id=pid,
                    node_type=GraphNodeType.DECISION,
                    properties={"title": d["title"], "decision": d["decision"], "status": "approved"},
                )
            )

        print("FalkorDB Cloud successfully populated with Project NEXUS topology!")
    else:
        print("Warning: FalkorDB is offline.")

if __name__ == "__main__":
    init_nexus()
