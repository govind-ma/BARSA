from collections.abc import Generator
from typing import Any

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


def get_version_control(
    storage: StorageProvider = Depends(get_storage),
) -> Generator[Any, None, None]:
    """Dependency that provides the VersionControlEngine."""
    from barsa.storage.sqlite import SQLiteStorageProvider
    from barsa.versioning.engine import VersionControlEngine

    if not isinstance(storage, SQLiteStorageProvider):
        raise RuntimeError("VersionControlEngine currently requires SQLiteStorageProvider")
    yield VersionControlEngine(storage)
