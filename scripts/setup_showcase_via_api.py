import httpx
import sys

API_BASE = "http://127.0.0.1:8000/api/v1"

def setup():
    client = httpx.Client(timeout=10.0)

    # 1. Health Check
    res = client.get("http://127.0.0.1:8000/health")
    if res.status_code != 200:
        print("Backend not healthy:", res.status_code)
        sys.exit(1)
    print("Backend is healthy!")

    # 2. Workspace
    ws_id = "default"
    client.post(f"{API_BASE}/workspaces", json={
        "id": ws_id,
        "name": "Production Workspace",
        "description": "Core workspace for multi-agent coordination."
    })

    # 3. Project
    proj_id = "ecommerce-engine"
    p_res = client.post(f"{API_BASE}/workspaces/{ws_id}/projects", json={
        "id": proj_id,
        "name": "E-Commerce Microservices Engine",
        "description": "High-scale event-driven checkout flow with inventory reservation, token auth, and distributed payment locks.",
        "status": "active",
        "goals": [
            "Achieve 10k orders/sec during flash sales without inventory overselling",
            "Sub-50ms stock reservation latency with Redis Redlock",
            "Full zero-trust JWT token revocation on logout"
        ]
    })
    print("Project response:", p_res.status_code)

    # 4. Memory Records (Decision, Knowledge, Checkpoint)
    # 4a. Decision (ADR)
    adr_payload = {
        "id": "rec-adr-001",
        "project_id": proj_id,
        "record_type": "decision",
        "title": "ADR-001: Distributed Stock Locking with Redis Redlock",
        "decision": "Use Redis Redlock with 5-second TTL and automatic release on payment confirmation.",
        "rationale": "Prevents PostgreSQL row-lock thread pool starvation during flash sales surges.",
        "status": "approved",
        "created_by": "claude-architect",
        "alternatives": ["PostgreSQL SELECT FOR UPDATE", "Optimistic concurrency version columns"],
        "metadata": {
            "tags": ["architecture", "redis", "concurrency", "adr"]
        }
    }
    r1 = client.post(f"{API_BASE}/projects/{proj_id}/records", json=adr_payload)
    print("Record 1 (ADR):", r1.status_code, r1.text[:100])

    # 4b. Knowledge Record
    jwt_payload = {
        "id": "rec-jwt-spec",
        "project_id": proj_id,
        "record_type": "knowledge",
        "content": "RS256 asymmetric signatures with 15-minute access token lifespan and secure HTTP-only refresh rotation verified by security audit.",
        "knowledge_type": "fact",
        "verification_status": "verified",
        "created_by": "kimi-auditor",
        "metadata": {
            "tags": ["security", "auth", "jwt", "tokens"]
        }
    }
    r2 = client.post(f"{API_BASE}/projects/{proj_id}/records", json=jwt_payload)
    print("Record 2 (Knowledge):", r2.status_code, r2.text[:100])

    # 4c. Checkpoint Record
    checkpoint_payload = {
        "id": "rec-checkpoint-001",
        "project_id": proj_id,
        "record_type": "checkpoint",
        "task_id": "task-02-auth",
        "status": "completed",
        "completed_actions": [
            "Generated PostgreSQL schema migrations for Products and Orders",
            "Implemented RS256 token verification middleware",
            "Ran security audit for timing leak attacks on HMAC compare"
        ],
        "pending_actions": [
            "Implement Redis Redlock stock reservation endpoint",
            "Wire Stripe webhook idempotency keys"
        ],
        "next_action": "Implement Stock Reservation API with Distributed Locks in FastAPI",
        "blockers": [],
        "created_by": "kimi-auditor",
        "metadata": {
            "title": "Milestone 1: Core Engine & Auth Verified",
            "summary": "All foundational auth middleware, schema migrations, and concurrency models verified with zero race conditions.",
            "tags": ["milestone", "checkpoint", "auth", "verified"]
        }
    }
    r3 = client.post(f"{API_BASE}/projects/{proj_id}/records", json=checkpoint_payload)
    print("Record 3 (Checkpoint):", r3.status_code, r3.text[:100])

    # 5. Coordination Tasks
    t3 = client.post(f"{API_BASE}/coordination/tasks", json={
        "task_id": "task-03-stock-api",
        "project_id": proj_id,
        "title": "Stock Reservation API with Distributed Locks",
        "description": "Implement atomic inventory reservation using Redis Redlock with automatic release timer and compensation rollback.",
        "status": "running",
        "priority": "high",
        "assigned_agent_id": "chatgpt-engineer"
    })
    print("Task 3 (In Progress / Running):", t3.status_code)

    t4 = client.post(f"{API_BASE}/coordination/tasks", json={
        "task_id": "task-04-stripe-webhook",
        "project_id": proj_id,
        "title": "Stripe Webhook & Order Processing",
        "description": "Process payment_intent.succeeded events and confirm finalized stock reservation.",
        "status": "ready",
        "priority": "medium",
        "assigned_agent_id": None
    })
    print("Task 4 (Ready / Backlog):", t4.status_code)

    # 6. Version Control Commit
    commit_payload = {
        "branch": "main",
        "author": "Claude Architect <claude@barsa.ai>",
        "message": "feat(core): scaffold ecommerce engine with auth middleware and Redis lock ADR",
        "changes": [
            {
                "record_id": "rec-adr-001",
                "operation": "create",
                "record_type": "decision"
            },
            {
                "record_id": "rec-jwt-spec",
                "operation": "create",
                "record_type": "knowledge"
            },
            {
                "record_id": "rec-checkpoint-001",
                "operation": "create",
                "record_type": "checkpoint"
            }
        ]
    }
    c_res = client.post(f"{API_BASE}/projects/{proj_id}/versioning/commits", json=commit_payload)
    print("Version Commit:", c_res.status_code, c_res.text[:100])

    print("\n--- SHOWCASE SEEDING COMPLETE! ---")

if __name__ == "__main__":
    setup()
