"""FastAPI dependencies."""

from collections.abc import Generator

from barsa.core.config import Settings, get_settings


def get_app_settings() -> Generator[Settings, None, None]:
    """Dependency that yields application settings."""
    yield get_settings()
