"""Tests for Storage API endpoints (workspaces, projects, records, artifacts, packages)."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from barsa.bms.serialization import import_package


@pytest.mark.asyncio
async def test_workspace_and_project_api_lifecycle(client: AsyncClient) -> None:
    """Test full workspace and project REST API workflow."""
    # 1. Create Workspace
    ws_payload = {
        "id": "ws-api-1",
        "name": "API Test Workspace",
        "owner_id": "user-dev-1",
        "description": "Created via API",
    }
    resp = await client.post("/api/v1/workspaces", json=ws_payload)
    assert resp.status_code == 201
    assert resp.json()["id"] == "ws-api-1"

    # 2. Get Workspace
    resp = await client.get("/api/v1/workspaces/ws-api-1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "API Test Workspace"

    # 3. List Workspaces
    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    assert any(w["id"] == "ws-api-1" for w in resp.json())

    # 4. Create Project
    prj_payload = {
        "id": "prj-api-1",
        "name": "API Test Project",
        "status": "active",
        "goals": ["Test API endpoints"],
    }
    resp = await client.post("/api/v1/workspaces/ws-api-1/projects", json=prj_payload)
    assert resp.status_code == 201
    assert resp.json()["id"] == "prj-api-1"

    # 5. Get Project
    resp = await client.get("/api/v1/projects/prj-api-1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "API Test Project"


@pytest.mark.asyncio
async def test_records_api_concurrency(client: AsyncClient) -> None:
    """Test memory record creation, retrieval, and optimistic locking via REST."""
    # Setup WS & Project
    await client.post("/api/v1/workspaces", json={"id": "ws-rec", "name": "Rec WS", "owner_id": "u1"})
    await client.post("/api/v1/workspaces/ws-rec/projects", json={"id": "prj-rec", "name": "Rec Prj"})

    # 1. Create Task Record
    task_payload = {
        "record_type": "task",
        "id": "task-api-1",
        "title": "Build Cache Layer",
        "status": "todo",
        "priority": "high",
        "dependencies": [],
        "created_at": "2026-10-13T10:00:00Z",
        "updated_at": "2026-10-13T10:00:00Z",
        "schema_version": "0.1",
    }
    resp = await client.post("/api/v1/projects/prj-rec/records", json=task_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["revision"] == 1
    assert data["record_id"] == "task-api-1"

    # 2. Get Record
    resp = await client.get("/api/v1/projects/prj-rec/records/task-api-1")
    assert resp.status_code == 200
    assert resp.json()["record"]["title"] == "Build Cache Layer"

    # 3. Update with valid revision -> 200 OK
    task_payload["title"] = "Build Cache Layer (Revised)"
    resp = await client.put(
        "/api/v1/projects/prj-rec/records/task-api-1",
        json={"record": task_payload, "expected_revision": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["revision"] == 2

    # 4. Update with stale revision -> 409 Conflict
    resp_conflict = await client.put(
        "/api/v1/projects/prj-rec/records/task-api-1",
        json={"record": task_payload, "expected_revision": 1},
    )
    assert resp_conflict.status_code == 409
    assert resp_conflict.json()["code"] == "CONFLICT_ERROR"


@pytest.mark.asyncio
async def test_package_import_and_export_api(client: AsyncClient) -> None:
    """Test package import and export via REST API."""
    example_path = Path("examples") / "bms" / "multi_agent_research.json"
    pkg = import_package(example_path)

    # 1. Import Package
    resp = await client.post("/api/v1/projects/import", json=pkg.model_dump(mode="json"))
    assert resp.status_code == 201
    assert resp.json()["project_id"] == "prj-genomics-variant-analysis"

    # 2. Duplicate Import Rejection
    resp_dup = await client.post("/api/v1/projects/import", json=pkg.model_dump(mode="json"))
    assert resp_dup.status_code == 409

    # 3. Export Package
    resp_exp = await client.get("/api/v1/projects/prj-genomics-variant-analysis/export")
    assert resp_exp.status_code == 200
    exported_data = resp_exp.json()
    assert exported_data["format"] == "barsa-memory-package"
    assert exported_data["project"]["id"] == "prj-genomics-variant-analysis"
    assert len(exported_data["records"]["knowledge"]) == 2
