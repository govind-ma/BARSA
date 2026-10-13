"""Storage provider factory and registry."""

from barsa.core.config import Settings, StorageProviderType
from barsa.core.exceptions import StorageError
from barsa.storage.protocol import StorageProvider

# Internal registry mapping provider types to factory functions
_REGISTRY: dict[StorageProviderType, type[StorageProvider]] = {}


def register_storage_provider(
    provider_type: StorageProviderType, provider_cls: type[StorageProvider]
) -> None:
    """Register a concrete storage provider class."""
    _REGISTRY[provider_type] = provider_cls


def get_storage_provider(settings: Settings) -> StorageProvider:
    """Instantiate the active storage provider according to application configuration.

    In Phase 1, concrete storage implementations are decoupled; when instantiated,
    registered providers will be created, or an explicit informative error is raised.
    """
    provider_type = settings.storage_provider
    if provider_type not in _REGISTRY:
        msg = (
            f"Storage provider '{provider_type}' is registered as an interface for Phase 1. "
            f"Supported configuration types: {[p.value for p in StorageProviderType]}"
        )
        raise StorageError(
            message=msg,
            code="STORAGE_PROVIDER_NOT_IMPLEMENTED",
            status_code=501,
            details={"configured_provider": provider_type.value},
        )
    return _REGISTRY[provider_type]()  # type: ignore[call-arg]
