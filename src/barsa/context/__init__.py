"""Context engine interfaces (Token-efficient memory retrieval and context packing)."""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from barsa.models.memory import MemoryItem


@runtime_checkable
class ContextEngine(Protocol):
    """Protocol for token-efficient memory retrieval and context compaction.

    Full implementation scheduled for Phase 5 (Smart Context Engine).
    """

    @abstractmethod
    async def retrieve_context(
        self,
        project_id: str,
        query: str,
        token_budget: int = 4000,
    ) -> list[MemoryItem]:
        """Retrieve most relevant memory items within a token budget."""
        ...
