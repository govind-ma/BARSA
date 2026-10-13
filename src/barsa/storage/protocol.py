"""Storage provider abstractions and protocols.

Decouples Barsa's memory standard and runtime from concrete storage engines.
Enables local-first operations and future support for GitHub, S3, or cloud storage.
"""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from barsa.models.memory import MemoryCommit, MemoryItem


@runtime_checkable
class StorageProvider(Protocol):
    """Protocol defining the required interface for any Barsa storage backend.

    Implementations can be local filesystem, in-memory, Git repository,
    S3 object storage, or custom enterprise providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the storage provider (e.g., 'local', 'memory', 's3', 'github')."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the storage backend is reachable and healthy."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage provider backend (create directories, test connections)."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Gracefully release any connections or locks held by the provider."""
        ...

    @abstractmethod
    async def save_item(self, item: MemoryItem) -> None:
        """Persist a single memory item."""
        ...

    @abstractmethod
    async def get_item(self, project_id: str, item_id: str) -> MemoryItem | None:
        """Retrieve a memory item by project ID and item ID."""
        ...

    @abstractmethod
    async def list_items(
        self,
        project_id: str,
        item_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryItem]:
        """List memory items for a project with optional type filter and pagination."""
        ...

    @abstractmethod
    async def delete_item(self, project_id: str, item_id: str) -> bool:
        """Delete a memory item by ID."""
        ...

    @abstractmethod
    async def save_commit(self, commit: MemoryCommit) -> None:
        """Persist a memory commit."""
        ...

    @abstractmethod
    async def get_commit(self, project_id: str, commit_id: str) -> MemoryCommit | None:
        """Retrieve a memory commit by ID."""
        ...

    @abstractmethod
    async def list_commits(self, project_id: str, limit: int = 50) -> list[MemoryCommit]:
        """List chronological commit history for a project."""
        ...

    @abstractmethod
    async def get_storage_stats(self) -> dict[str, Any]:
        """Return storage metadata and statistics (e.g., total items, disk usage)."""
        ...
