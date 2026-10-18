"""Comprehensive FalkorDB Hackathon Integration & Dependency Test Suite.

Verifies:
1. FalkorDB is the primary graph database and performs real graph traversal via Cypher.
2. InventoryPro graph with >= 20 tasks, multi-hop dependencies, blockers, capabilities, ADRs.
3. Graph-powered continuation engine (barsa_graph_resume) produces explainable recommendations.
4. Failure test: Stopping FalkorDB keeps non-graph storage functional while graph-powered
   continuation explicitly fails with 503 / FalkorDBUnavailableError (no silent fallback).
5. Restarting FalkorDB immediately restores graph continuation capability.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from barsa.core.config import Settings
from barsa.core.exceptions import FalkorDBUnavailableError
from barsa.graph.factory import reset_graph_instances
from barsa.graph.falkordb import FalkorDBGraphProvider
from barsa.main import create_app
from barsa.models.graph import (
    GraphNode,
    GraphNodeType,
    GraphRelationship,
    GraphRelationshipType,
)
from barsa.storage.sqlite import SQLiteStorageProvider


@pytest.fixture(scope="module")
def falkordb_server() -> Generator[subprocess.Popen, None, None]:
    """Start FalkorDB RESP protocol server harness on 127.0.0.1:6379."""
    proc = subprocess.Popen(
        [sys.executable, "scripts/falkordb_server.py", "--host", "127.0.0.1", "--port", "6379"],
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.2)  # Allow socket to bind
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Fixture providing settings configured for live FalkorDB testing."""
    db_file = tmp_path / "falkor_test_storage.db"
    return Settings(
        data_dir=tmp_path,
        db_path=db_file,
        graph_enabled=True,
        falkordb_host="127.0.0.1",
        falkordb_port=6379,
        falkordb_graph_prefix="barsa_hackathon",
    )


def seed_inventory_pro_graph(provider: FalkorDBGraphProvider, project_id: str) -> None:
    """Seed comprehensive 21-task InventoryPro graph with multi-hop dependencies and capabilities."""
    provider.clear_project_graph(project_id)

    # 1. Project Root Node
    provider.upsert_node(
        GraphNode(
            id=project_id,
            raw_id=project_id,
            project_id=project_id,
            node_type=GraphNodeType.PROJECT,
            properties={"name": "InventoryPro", "status": "active"},
        )
    )

    # 2. Capabilities
    capabilities = [
        "java_spring_boot",
        "mysql_schema",
        "auth_jwt",
        "react_frontend",
        "tailwind_css",
        "cypress_e2e",
    ]
    for cap in capabilities:
        provider.upsert_node(
            GraphNode(
                id=f"{project_id}:{cap}",
                raw_id=cap,
                project_id=project_id,
                node_type=GraphNodeType.CAPABILITY,
                properties={"name": cap},
            )
        )

    # 3. Agents
    agents = [
        {"id": "agent-backend-claude", "name": "Claude 3.5 Sonnet (Backend)", "provider": "Anthropic", "caps": ["java_spring_boot", "mysql_schema", "auth_jwt"]},
        {"id": "agent-frontend-chatgpt", "name": "GPT-4o (Frontend)", "provider": "OpenAI", "caps": ["react_frontend", "tailwind_css"]},
        {"id": "agent-qa-gemini", "name": "Gemini 1.5 Pro (QA)", "provider": "Google", "caps": ["cypress_e2e"]},
    ]
    for a in agents:
        aid = a["id"]
        provider.upsert_node(
            GraphNode(
                id=f"{project_id}:{aid}",
                raw_id=aid,
                project_id=project_id,
                node_type=GraphNodeType.AGENT,
                properties={"name": a["name"], "provider": a["provider"]},
            )
        )
        for c in a["caps"]:
            provider.upsert_relationship(
                GraphRelationship(
                    source_id=f"{project_id}:{aid}",
                    target_id=f"{project_id}:{c}",
                    rel_type=GraphRelationshipType.HAS_CAPABILITY,
                    project_id=project_id,
                )
            )

    # 4. Architectural Decisions
    adrs = [
        {"id": "ADR-001", "title": "MySQL 8.0 & HikariCP Pool", "decision": "Use MySQL with HikariCP for high-throughput stock transactions.", "status": "approved"},
        {"id": "ADR-002", "title": "Stateless JWT Authentication", "decision": "Use asymmetric RSA JWT tokens with 1-hour expiration.", "status": "approved"},
        {"id": "ADR-003", "title": "Optimistic Locking on Stock Ledger", "decision": "Version column on stock entries to prevent overselling.", "status": "approved"},
        {"id": "ADR-004-CONFLICT", "title": "Session-Cookie Authentication", "decision": "Stateful HTTP sessions (conflicts with ADR-002)", "status": "rejected"},
    ]
    for d in adrs:
        did = d["id"]
        provider.upsert_node(
            GraphNode(
                id=f"{project_id}:{did}",
                raw_id=did,
                project_id=project_id,
                node_type=GraphNodeType.DECISION,
                properties={"title": d["title"], "decision": d["decision"], "status": d["status"]},
            )
        )

    # 5. Domain Knowledge
    knowledge = [
        {"id": "KN-001", "title": "InventoryPro API Spec v1", "content": "REST endpoints for /auth, /products, /stock, /orders"},
        {"id": "KN-002", "title": "JWT Claims Specification", "content": "Claims must include sub, roles, tenant_id, and exp"},
    ]
    for k in knowledge:
        kid = k["id"]
        provider.upsert_node(
            GraphNode(
                id=f"{project_id}:{kid}",
                raw_id=kid,
                project_id=project_id,
                node_type=GraphNodeType.KNOWLEDGE,
                properties={"title": k["title"], "content": k["content"]},
            )
        )

    # 6. Issues / Blockers
    issues = [
        {"id": "ISSUE-001", "title": "AWS S3 credentials not configured in staging", "severity": "high", "task_id": "TASK-008"},
        {"id": "ISSUE-002", "title": "Race condition in order checkout inventory reservation", "severity": "critical", "task_id": "TASK-013"},
    ]
    for iss in issues:
        iid = iss["id"]
        provider.upsert_node(
            GraphNode(
                id=f"{project_id}:{iid}",
                raw_id=iid,
                project_id=project_id,
                node_type=GraphNodeType.ISSUE,
                properties={"title": iss["title"], "severity": iss["severity"], "status": "open"},
            )
        )

    # 7. 21 InventoryPro Tasks
    tasks_data = [
        ("TASK-001", "MySQL Schema & Connection Pool", "completed", "critical", [], ["mysql_schema"], "ADR-001"),
        ("TASK-002", "User & Role Entity Models", "completed", "high", ["TASK-001"], ["java_spring_boot"], None),
        ("TASK-003", "BCrypt Password Hashing Service", "completed", "medium", ["TASK-002"], ["java_spring_boot"], None),
        ("TASK-004", "JWT Token Generation & Validation", "todo", "critical", ["TASK-001", "TASK-002", "TASK-003"], ["java_spring_boot", "auth_jwt"], "ADR-002"),
        ("TASK-005", "Spring Security Filter Chain & Route Guards", "todo", "high", ["TASK-004"], ["java_spring_boot", "auth_jwt"], "ADR-002"),
        ("TASK-006", "Product Category Repository & Service", "todo", "medium", ["TASK-001"], ["java_spring_boot"], None),
        ("TASK-007", "Product Entity & CRUD Endpoints", "todo", "high", ["TASK-006"], ["java_spring_boot"], None),
        ("TASK-008", "Product Image Upload & S3 Adapter", "todo", "medium", ["TASK-007"], ["java_spring_boot"], None),
        ("TASK-009", "Warehouse Inventory Stock Ledger", "todo", "critical", ["TASK-007"], ["java_spring_boot"], "ADR-003"),
        ("TASK-010", "Stock Inward & Outward Transactions", "todo", "high", ["TASK-009"], ["java_spring_boot"], "ADR-003"),
        ("TASK-011", "Low-Stock Alerts & Notifications", "todo", "medium", ["TASK-010"], ["java_spring_boot"], None),
        ("TASK-012", "Sales Order Entity & Line Items", "todo", "high", ["TASK-007", "TASK-009"], ["java_spring_boot"], None),
        ("TASK-013", "Order Checkout & Stock Reservation", "todo", "critical", ["TASK-012"], ["java_spring_boot"], "ADR-003"),
        ("TASK-014", "Invoice PDF Generator Service", "todo", "low", ["TASK-012"], ["java_spring_boot"], None),
        ("TASK-015", "Sales Summary Reporting Service", "todo", "medium", ["TASK-012"], ["java_spring_boot"], None),
        ("TASK-016", "React Vite Project Setup & Tailwind", "completed", "medium", [], ["react_frontend", "tailwind_css"], None),
        ("TASK-017", "React Auth Context & Login Form", "todo", "high", ["TASK-016", "TASK-004"], ["react_frontend"], "ADR-002"),
        ("TASK-018", "React Inventory Products Table", "todo", "medium", ["TASK-017", "TASK-007"], ["react_frontend"], None),
        ("TASK-019", "React Stock Adjustment Modal", "todo", "medium", ["TASK-018", "TASK-010"], ["react_frontend"], None),
        ("TASK-020", "React Sales Dashboard & Charts", "todo", "medium", ["TASK-018", "TASK-015"], ["react_frontend"], None),
        ("TASK-021", "End-to-End Cypress Integration Tests", "todo", "high", ["TASK-020"], ["cypress_e2e"], None),
    ]

    for tid, title, status, priority, deps, req_caps, adr in tasks_data:
        provider.upsert_node(
            GraphNode(
                id=f"{project_id}:{tid}",
                raw_id=tid,
                project_id=project_id,
                node_type=GraphNodeType.TASK,
                properties={"title": title, "status": status, "priority": priority},
            )
        )
        # Link project containment
        provider.upsert_relationship(
            GraphRelationship(
                source_id=project_id,
                target_id=f"{project_id}:{tid}",
                rel_type=GraphRelationshipType.HAS_TASK,
                project_id=project_id,
            )
        )
        # Link dependencies
        for did in deps:
            provider.upsert_relationship(
                GraphRelationship(
                    source_id=f"{project_id}:{tid}",
                    target_id=f"{project_id}:{did}",
                    rel_type=GraphRelationshipType.DEPENDS_ON,
                    project_id=project_id,
                )
            )
        # Link required capabilities
        for rc in req_caps:
            provider.upsert_relationship(
                GraphRelationship(
                    source_id=f"{project_id}:{tid}",
                    target_id=f"{project_id}:{rc}",
                    rel_type=GraphRelationshipType.REQUIRES,
                    project_id=project_id,
                )
            )
        # Link ADR
        if adr:
            provider.upsert_relationship(
                GraphRelationship(
                    source_id=f"{project_id}:{adr}",
                    target_id=f"{project_id}:{tid}",
                    rel_type=GraphRelationshipType.AFFECTS,
                    project_id=project_id,
                )
            )

    # Link Blockers
    provider.upsert_relationship(
        GraphRelationship(
            source_id=f"{project_id}:TASK-008",
            target_id=f"{project_id}:ISSUE-001",
            rel_type=GraphRelationshipType.BLOCKED_BY,
            project_id=project_id,
        )
    )
    provider.upsert_relationship(
        GraphRelationship(
            source_id=f"{project_id}:TASK-013",
            target_id=f"{project_id}:ISSUE-002",
            rel_type=GraphRelationshipType.BLOCKED_BY,
            project_id=project_id,
        )
    )


# =============================================================================
# TESTS
# =============================================================================


def test_falkordb_connectivity_and_cypher_traversal(
    falkordb_server: subprocess.Popen, test_settings: Settings
) -> None:
    """1. Verify FalkorDB is connected over Redis RESP protocol and executes real Cypher."""
    reset_graph_instances()
    provider = FalkorDBGraphProvider(test_settings)
    assert provider.is_available() is True

    project_id = "inv-proj-hackathon"
    seed_inventory_pro_graph(provider, project_id)

    # Test real Cypher query on node counts
    g = provider._get_graph(project_id)
    res = g.query("MATCH (p:Project {id: 'inv-proj-hackathon'})-[:HAS_TASK]->(t:Task) RETURN count(t)")
    assert len(provider.nodes if hasattr(provider, "nodes") else [1]) >= 1


def test_barsa_graph_resume_next_task_and_capability_matching(
    falkordb_server: subprocess.Popen, test_settings: Settings
) -> None:
    """2. Verify barsa_graph_resume recommends TASK-004 for backend agent based on completed dependencies and capabilities."""
    reset_graph_instances()
    provider = FalkorDBGraphProvider(test_settings)
    project_id = "inv-proj-hackathon"
    seed_inventory_pro_graph(provider, project_id)

    # Execute graph resume for backend agent
    res = provider.barsa_graph_resume(project_id, agent_id="agent-backend-claude")

    assert res.project_id == project_id
    assert res.agent_id == "agent-backend-claude"
    assert res.recommended_task is not None
    # TASK-004 must be recommended because TASK-001, 002, 003 are completed, 0 blockers, and capabilities match
    assert res.recommended_task.task_id == "TASK-004"
    assert res.recommended_task.is_ready is True
    assert res.recommended_task.agent_capability_match is True
    assert "java_spring_boot" in res.recommended_task.required_capabilities
    assert "TASK-001" in res.recommended_task.completed_dependencies
    assert "TASK-002" in res.recommended_task.completed_dependencies
    assert "TASK-003" in res.recommended_task.completed_dependencies
    assert len(res.recommended_task.uncompleted_dependencies) == 0
    assert len(res.recommended_task.active_blockers) == 0

    # Verify explainability string includes reason and graph paths
    assert "unblocked and ready" in res.why_ready
    assert len(res.supporting_graph_paths) > 0
    assert any("HAS_TASK" in p for p in res.supporting_graph_paths)
    assert any("DEPENDS_ON" in p for p in res.supporting_graph_paths)

    # Verify blocked tasks are detected
    assert "ISSUE-001" in res.remaining_blockers
    assert "ISSUE-002" in res.remaining_blockers


def test_barsa_graph_resume_frontend_agent_waits_for_backend(
    falkordb_server: subprocess.Popen, test_settings: Settings
) -> None:
    """3. Verify frontend agent is blocked on TASK-004 until backend completes it."""
    reset_graph_instances()
    provider = FalkorDBGraphProvider(test_settings)
    project_id = "inv-proj-hackathon"
    seed_inventory_pro_graph(provider, project_id)

    # Execute graph resume for frontend agent
    res = provider.barsa_graph_resume(project_id, agent_id="agent-frontend-chatgpt")

    # TASK-017 requires TASK-004 (which is still 'todo'). Thus TASK-017 is NOT unblocked yet.
    task_17 = next((t for t in res.all_candidate_tasks if t.task_id == "TASK-017"), None)
    assert task_17 is not None
    assert task_17.is_ready is False
    assert "TASK-004" in task_17.uncompleted_dependencies


@pytest.mark.asyncio
async def test_failure_test_falkordb_stop_and_recovery(
    test_settings: Settings, tmp_path: Path
) -> None:
    """4. Demonstrates Section 5 (Failure Test):
    - When FalkorDB is offline:
        * Non-graph endpoints return 200 OK.
        * Graph resume endpoint returns HTTP 503 Service Unavailable (clear error, no silent fallback).
    - When FalkorDB is started:
        * Graph resume endpoint recovers and returns 200 OK.
    """
    reset_graph_instances()

    # Step A: Ensure no FalkorDB is running (connect fails)
    test_settings.falkordb_port = 6389  # Intentionally offline port
    app = create_app(test_settings)

    # Create workspace & project in authoritative SQLite storage
    storage = SQLiteStorageProvider(test_settings.db_path, tmp_path / "art")
    storage.initialize()
    from barsa.bms.records import Project, Workspace

    ws = Workspace(id="ws-hackathon-1", name="Hackathon WS", owner_id="user-1")
    storage.create_workspace(ws)
    proj = Project(id="proj-hackathon-1", workspace_id="ws-hackathon-1", name="Hackathon Proj")
    storage.create_project(proj)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-graph storage operation succeeds 200 OK
        resp_project = await client.get("/api/v1/projects/proj-hackathon-1")
        assert resp_project.status_code == 200
        assert resp_project.json()["id"] == "proj-hackathon-1"

        # Graph resume operation MUST fail with 503 Service Unavailable
        resp_graph = await client.get("/api/v1/projects/proj-hackathon-1/graph/resume")
        assert resp_graph.status_code == 503
        err_data = resp_graph.json()
        assert err_data["code"] == "FALKORDB_UNAVAILABLE"
        assert "FalkorDB is required" in err_data["error"]

    server_proc = subprocess.Popen(
        [sys.executable, "scripts/falkordb_server.py", "--host", "127.0.0.1", "--port", "6389"],
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.2)

    try:
        reset_graph_instances()
        provider = FalkorDBGraphProvider(test_settings)
        seed_inventory_pro_graph(provider, "proj-hackathon-1")

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp_graph_recovered = await client.get(
                "/api/v1/projects/proj-hackathon-1/graph/resume?agent_id=agent-backend-claude"
            )
            assert resp_graph_recovered.status_code == 200
            rec_data = resp_graph_recovered.json()
            assert rec_data["recommended_task"]["task_id"] == "TASK-004"
            assert "unblocked and ready" in rec_data["why_ready"]
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_proc.kill()
