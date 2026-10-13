"""Storage provider factory and registry."""

from typing import Any

from barsa.core.config import Settings, StorageProviderType
from barsa.core.exceptions import StorageError
from barsa.storage.protocol import StorageProvider
from barsa.storage.sqlite import SQLiteStorageProvider

# Internal registry mapping provider types to factory functions
_REGISTRY: dict[StorageProviderType, Any] = {}
_INSTANCES: dict[str, StorageProvider] = {}


def register_storage_provider(provider_type: StorageProviderType, provider_cls: Any) -> None:
    """Register a concrete storage provider class."""
    _REGISTRY[provider_type] = provider_cls


def get_storage_provider(settings: Settings) -> StorageProvider:
    """Instantiate the active storage provider according to application configuration.

    In Phase 3, 'local' uses the SQLiteStorageProvider.
    """
    settings.ensure_data_dir()
    provider_type = settings.storage_provider

    if provider_type == StorageProviderType.LOCAL:
        key = str(settings.db_path)
        if key not in _INSTANCES:
            provider = SQLiteStorageProvider(
                db_path=settings.db_path,
                artifacts_dir=settings.artifacts_dir,
                max_artifact_size=settings.max_artifact_size_bytes,
            )
            provider.initialize()
            _INSTANCES[key] = provider
        return _INSTANCES[key]

    if provider_type in _REGISTRY:
        factory = _REGISTRY[provider_type]
        return factory(settings)

    msg = (
        f"Storage provider '{provider_type}' is not currently configured. "
        f"Supported configuration types: {[p.value for p in StorageProviderType]}"
    )
    raise StorageError(
        message=msg,
        code="STORAGE_PROVIDER_NOT_IMPLEMENTED",
        status_code=501,
        details={"configured_provider": provider_type.value},
    )
