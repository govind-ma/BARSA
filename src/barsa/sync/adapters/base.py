"""Abstract Base Class for BYOS Remote Storage Adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from barsa.sync.models import RemoteBranchRef, RepositoryManifest


class RemoteStorageAdapter(ABC):
    """Protocol for remote content-addressed storage and ref synchronization."""

    @abstractmethod
    async def initialize(
        self,
        repository_id: str,
        project_id: str,
        encryption_enabled: bool = False,
    ) -> RepositoryManifest:
        """Initialize remote repository layout and write root repository.json and metadata."""

    @abstractmethod
    async def check_connectivity(self) -> bool:
        """Verify reachability and authentication to the remote storage target."""

    @abstractmethod
    async def read_manifest(self) -> RepositoryManifest | None:
        """Retrieve and parse the current repository.json manifest."""

    @abstractmethod
    async def write_manifest(self, manifest: RepositoryManifest) -> None:
        """Write updated repository manifest."""

    @abstractmethod
    async def get_branch_ref(self, branch_name: str) -> RemoteBranchRef | None:
        """Fetch remote branch reference and its current concurrency token / etag."""

    @abstractmethod
    async def update_branch_ref(
        self,
        branch_name: str,
        commit_id: str,
        expected_etag: str | None = None,
    ) -> RemoteBranchRef:
        """Conditionally update a remote branch reference using optimistic concurrency."""

    @abstractmethod
    async def list_branch_refs(self) -> list[RemoteBranchRef]:
        """Enumerate all active branch references in the remote repository."""

    @abstractmethod
    async def object_exists(self, content_hash: str) -> bool:
        """Check whether an immutable content-addressed object already exists remotely."""

    @abstractmethod
    async def put_object(self, content_hash: str, data: bytes, object_type: str = "object") -> str:
        """Upload an immutable content-addressed object. Returns the canonical content hash."""

    @abstractmethod
    async def get_object(self, content_hash: str) -> bytes:
        """Download an immutable content-addressed object. Verifies SHA-256 integrity."""

    @abstractmethod
    async def list_objects(self, prefix: str = "") -> list[str]:
        """List content hashes of stored immutable objects."""

    @abstractmethod
    async def delete_object(self, content_hash: str) -> bool:
        """Remove an object from storage if supported."""

    async def close(self) -> None:  # noqa: B027
        """Release underlying connections or handles."""
