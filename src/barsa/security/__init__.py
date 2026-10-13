"""Security, authentication, and authorization interfaces."""

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class SecurityProvider(Protocol):
    """Protocol for project isolation, role-based authorization, and approvals.

    Full implementation scheduled for Phase 7 (Security & Isolation).
    """

    @abstractmethod
    async def verify_project_access(self, user_or_agent_id: str, project_id: str) -> bool:
        """Check whether user or agent is permitted to read/write project memories."""
        ...
