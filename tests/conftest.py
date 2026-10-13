"""Shared pytest fixtures."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from barsa.core.config import Settings
from barsa.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Return test settings with isolated temporary data directory."""
    return Settings(
        app_name="BARSA-Test",
        app_version="0.1.0-test",
        environment="testing",  # type: ignore[arg-type]
        debug=True,
        data_dir=tmp_path / "barsa_test_data",
        storage_provider="local",  # type: ignore[arg-type]
        log_level="DEBUG",
    )


@pytest.fixture
async def client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Return an async test client configured with test_settings."""
    app = create_app(test_settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
