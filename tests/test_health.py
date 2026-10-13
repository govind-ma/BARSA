"""Tests for health and platform info endpoints."""

import pytest
from httpx import AsyncClient

from barsa.core.config import Settings


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient, test_settings: Settings) -> None:
    """Test GET /health returns service status, app name, and version."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == test_settings.app_name
    assert data["version"] == test_settings.app_version
    assert data["environment"] == "testing"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_info_endpoint(client: AsyncClient, test_settings: Settings) -> None:
    """Test GET /api/v1/info returns platform information and supported features."""
    response = await client.get("/api/v1/info")
    assert response.status_code == 200

    data = response.json()
    assert data["app_name"] == test_settings.app_name
    assert data["version"] == test_settings.app_version
    assert data["current_phase"] == "Phase 1: Project Foundation"
    assert data["storage_provider"] == "local"
    assert "features" in data

    features = data["features"]
    assert features["bms_standard"] is True
    assert features["local_storage"] is True
    # Future features must not be claimed as implemented
    assert features["falkordb_graph"] is False
    assert features["git_versioning"] is False
    assert features["mcp_server"] is False
    assert features["cloud_storage_adapters"] is False


@pytest.mark.asyncio
async def test_not_found_error_handler(client: AsyncClient) -> None:
    """Test centralized error handler on 404 routes."""
    response = await client.get("/nonexistent-endpoint")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert data["code"] == "HTTP_404"
    assert data["status_code"] == 404
