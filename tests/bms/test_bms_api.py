"""Tests for BMS API endpoints."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from barsa.bms.serialization import import_package


@pytest.mark.asyncio
async def test_api_bms_version(client: AsyncClient) -> None:
    """Test GET /api/v1/bms/version."""
    response = await client.get("/api/v1/bms/version")
    assert response.status_code == 200
    data = response.json()
    assert data["bms_version"] == "0.1"
    assert "workspace" in data["supported_record_types"]
    assert "checkpoint" in data["supported_record_types"]
    assert "commit" in data["supported_record_types"]


@pytest.mark.asyncio
async def test_api_bms_schema(client: AsyncClient) -> None:
    """Test GET /api/v1/bms/schema/{record_type} for valid and invalid types."""
    # Valid record type
    resp_task = await client.get("/api/v1/bms/schema/task")
    assert resp_task.status_code == 200
    schema = resp_task.json()
    assert schema["title"] == "BMS v0.1 TaskRecord"
    assert "properties" in schema

    # Package schema
    resp_pkg = await client.get("/api/v1/bms/schema/package")
    assert resp_pkg.status_code == 200
    schema_pkg = resp_pkg.json()
    assert schema_pkg["title"] == "BMS v0.1 BarsaMemoryPackage"

    # Invalid record type
    resp_invalid = await client.get("/api/v1/bms/schema/unknown_model")
    assert resp_invalid.status_code == 404


@pytest.mark.asyncio
async def test_api_validate_record_endpoint(client: AsyncClient) -> None:
    """Test POST /api/v1/bms/validate/record with valid and invalid payloads."""
    # Valid payload
    valid_payload = {
        "record_type": "decision",
        "id": "dec-100",
        "project_id": "prj-100",
        "title": "Use PostgreSQL",
        "decision": "Use PostgreSQL for relational storage",
        "rationale": "High ACID reliability",
        "status": "approved",
        "created_by": "agent-architect",
        "created_at": "2026-10-13T12:00:00Z",
        "schema_version": "0.1",
    }
    resp = await client.post("/api/v1/bms/validate/record", json=valid_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["record_type"] == "decision"
    assert data["record_id"] == "dec-100"

    # Invalid payload (missing rationale & decision)
    invalid_payload = {
        "record_type": "decision",
        "id": "dec-101",
        "project_id": "prj-100",
        "title": "Incomplete Decision",
        "schema_version": "0.1",
    }
    resp_err = await client.post("/api/v1/bms/validate/record", json=invalid_payload)
    assert resp_err.status_code == 422
    err_data = resp_err.json()
    assert err_data["valid"] is False
    assert len(err_data["errors"]) > 0


@pytest.mark.asyncio
async def test_api_validate_package_endpoint(client: AsyncClient) -> None:
    """Test POST /api/v1/bms/validate/package with full example package."""
    example_path = Path("examples") / "bms" / "spring_boot_project.json"
    pkg = import_package(example_path)

    resp = await client.post("/api/v1/bms/validate/package", json=pkg.model_dump(mode="json"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["record_type"] == "package"
    assert data["record_id"] == "prj-order-service"
    assert data["details"]["record_counts"]["tasks"] == 2
