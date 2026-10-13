"""Storage package for Barsa."""

from barsa.storage.factory import get_storage_provider, register_storage_provider
from barsa.storage.protocol import StorageProvider

__all__ = ["StorageProvider", "get_storage_provider", "register_storage_provider"]
