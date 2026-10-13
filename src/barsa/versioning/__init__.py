"""Versioning interfaces and protocol definitions (Git-inspired DAG commits, branches, diffs)."""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from barsa.models.memory import MemoryCommit


@runtime_checkable
class VersioningEngine(Protocol):
    """Protocol for memory versioning operations.

    Full implementation scheduled for Phase 3 (Git-inspired versioning).
    """

    @abstractmethod
    async def create_commit(
        self,
        project_id: str,
        message: str,
        author: dict[str, str],
        parent_id: str | None = None,
    ) -> MemoryCommit:
        """Create a new point-in-time memory commit."""
        ...

    @abstractmethod
    async def create_branch(self, project_id: str, branch_name: str, target_commit_id: str) -> None:
        """Create a new memory branch."""
        ...

    @abstractmethod
    async def diff(self, project_id: str, from_commit: str, to_commit: str) -> dict[str, Any]:
        """Compute the diff between two memory snapshots."""
        ...
