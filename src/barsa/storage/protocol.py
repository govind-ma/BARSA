"""Storage provider abstractions and protocols for BARSA.

Decouples Barsa business logic and BMS domain models from physical persistence.
Implementations can be SQLite, PostgreSQL, cloud object storage, or in-memory stores.
"""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.records import AnyBMSRecord, Project, Workspace


@runtime_checkable
class StorageProvider(Protocol):
    """Protocol defining the core contract for any Barsa storage backend."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the storage provider (e.g., 'sqlite', 'memory', 's3')."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the storage backend is reachable and initialized."""
        ...

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the storage provider backend (create tables, verify schema)."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Gracefully release connections, file handles, and locks."""
        ...

    # --- Workspace Operations ---
    @abstractmethod
    def create_workspace(self, workspace: Workspace) -> Workspace:
        """Create a new workspace."""
        ...

    @abstractmethod
    def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Retrieve a workspace by its unique ID."""
        ...

    @abstractmethod
    def list_workspaces(self, limit: int = 100, offset: int = 0) -> list[Workspace]:
        """List workspaces with pagination."""
        ...

    @abstractmethod
    def update_workspace(self, workspace: Workspace, expected_revision: int | None = None) -> Workspace:
        """Update workspace metadata with optional revision check."""
        ...

    @abstractmethod
    def delete_workspace(self, workspace_id: str, cascade: bool = False) -> bool:
        """Delete a workspace.

        If cascade is False and workspace contains projects, raises ConflictError.
        """
        ...

    # --- Project Operations ---
    @abstractmethod
    def create_project(self, project: Project) -> Project:
        """Create a new project within a workspace."""
        ...

    @abstractmethod
    def get_project(self, project_id: str) -> Project | None:
        """Retrieve a project by its unique ID."""
        ...

    @abstractmethod
    def list_projects(self, workspace_id: str, limit: int = 100, offset: int = 0) -> list[Project]:
        """List projects belonging to a workspace."""
        ...

    @abstractmethod
    def update_project(self, project: Project, expected_revision: int | None = None) -> Project:
        """Update project metadata with optional revision check."""
        ...

    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        """Delete a project and its scoped records/relationships."""
        ...

    # --- BMS Record Operations ---
    @abstractmethod
    def create_record(self, record: AnyBMSRecord) -> tuple[AnyBMSRecord, int]:
        """Persist a new BMS record. Returns (record, initial_revision)."""
        ...

    @abstractmethod
    def get_record(self, project_id: str, record_id: str) -> tuple[AnyBMSRecord, int] | None:
        """Retrieve a BMS record by project ID and record ID. Returns (record, revision)."""
        ...

    @abstractmethod
    def list_records(
        self,
        project_id: str,
        record_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[AnyBMSRecord, int]]:
        """List BMS records in a project with optional type filter. Returns list of (record, revision)."""
        ...

    @abstractmethod
    def update_record(
        self,
        record: AnyBMSRecord,
        expected_revision: int,
    ) -> tuple[AnyBMSRecord, int]:
        """Update an existing BMS record with compare-and-swap optimistic concurrency."""
        ...

    @abstractmethod
    def delete_record(
        self,
        project_id: str,
        record_id: str,
        expected_revision: int | None = None,
    ) -> bool:
        """Delete a record by ID with optional revision check."""
        ...

    # --- Package Import & Export ---
    @abstractmethod
    def save_package(self, package: BarsaMemoryPackage) -> None:
        """Atomically persist a complete BarsaMemoryPackage in a single transaction."""
        ...

    @abstractmethod
    def load_package(self, project_id: str) -> BarsaMemoryPackage | None:
        """Read and construct a consistent BarsaMemoryPackage snapshot for a project."""
        ...

    # --- Diagnostics & Stats ---
    @abstractmethod
    def get_storage_stats(self) -> dict[str, Any]:
        """Return storage metadata and stats (disk usage, record counts)."""
        ...
