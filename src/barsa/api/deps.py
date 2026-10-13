from collections.abc import Generator

from fastapi import Depends

from barsa.core.config import Settings, get_settings
from barsa.storage.factory import get_storage_provider
from barsa.storage.protocol import StorageProvider


def get_app_settings() -> Generator[Settings, None, None]:
    """Dependency that yields application settings."""
    yield get_settings()


def get_storage(
    settings: Settings = Depends(get_app_settings),
) -> Generator[StorageProvider, None, None]:
    """Dependency that provides the active storage provider."""
    provider = get_storage_provider(settings)
    yield provider
