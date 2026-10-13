"""Workspaces and Projects API endpoints (v1)."""

from fastapi import APIRouter, Depends, Query, status

from barsa.api.deps import get_storage
from barsa.bms.base import generate_uuid_str
from barsa.bms.records import Project, Workspace
from barsa.core.exceptions import ResourceNotFoundError
from barsa.models.storage_api import (
    ProjectCreateRequest,
    ProjectUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
)
from barsa.storage.protocol import StorageProvider

router = APIRouter(tags=["Workspaces & Projects"])


# =============================================================================
# Workspaces
# =============================================================================


@router.post(
    "/workspaces",
    response_model=Workspace,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
def create_workspace(
    req: WorkspaceCreateRequest,
    storage: StorageProvider = Depends(get_storage),
) -> Workspace:
    ws = Workspace(
        id=req.id or generate_uuid_str(),
        name=req.name,
        owner_id=req.owner_id,
        description=req.description,
        metadata=req.metadata,
    )
    return storage.create_workspace(ws)


@router.get(
    "/workspaces",
    response_model=list[Workspace],
    summary="List all workspaces",
)
def list_workspaces(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    storage: StorageProvider = Depends(get_storage),
) -> list[Workspace]:
    return storage.list_workspaces(limit=limit, offset=offset)


@router.get(
    "/workspaces/{workspace_id}",
    response_model=Workspace,
    summary="Get a workspace by ID",
)
def get_workspace(
    workspace_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> Workspace:
    ws = storage.get_workspace(workspace_id)
    if not ws:
        raise ResourceNotFoundError(f"Workspace '{workspace_id}' not found.", "Workspace", workspace_id)
    return ws


@router.patch(
    "/workspaces/{workspace_id}",
    response_model=Workspace,
    summary="Update a workspace",
)
def update_workspace(
    workspace_id: str,
    req: WorkspaceUpdateRequest,
    storage: StorageProvider = Depends(get_storage),
) -> Workspace:
    ws = storage.get_workspace(workspace_id)
    if not ws:
        raise ResourceNotFoundError(f"Workspace '{workspace_id}' not found.", "Workspace", workspace_id)

    if req.name is not None:
        ws.name = req.name
    if req.description is not None:
        ws.description = req.description
    if req.metadata is not None:
        ws.metadata = req.metadata

    return storage.update_workspace(ws, expected_revision=req.expected_revision)


@router.delete(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
)
def delete_workspace(
    workspace_id: str,
    cascade: bool = Query(default=False),
    storage: StorageProvider = Depends(get_storage),
) -> None:
    deleted = storage.delete_workspace(workspace_id, cascade=cascade)
    if not deleted:
        raise ResourceNotFoundError(f"Workspace '{workspace_id}' not found.", "Workspace", workspace_id)


# =============================================================================
# Projects
# =============================================================================


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project in a workspace",
)
def create_project(
    workspace_id: str,
    req: ProjectCreateRequest,
    storage: StorageProvider = Depends(get_storage),
) -> Project:
    project = Project(
        id=req.id or generate_uuid_str(),
        workspace_id=workspace_id,
        name=req.name,
        status=req.status,
        description=req.description,
        goals=req.goals,
        metadata=req.metadata,
    )
    return storage.create_project(project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=list[Project],
    summary="List projects in a workspace",
)
def list_projects_in_workspace(
    workspace_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    storage: StorageProvider = Depends(get_storage),
) -> list[Project]:
    if not storage.get_workspace(workspace_id):
        raise ResourceNotFoundError(f"Workspace '{workspace_id}' not found.", "Workspace", workspace_id)
    return storage.list_projects(workspace_id, limit=limit, offset=offset)


@router.get(
    "/projects/{project_id}",
    response_model=Project,
    summary="Get a project by ID",
)
def get_project(
    project_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> Project:
    project = storage.get_project(project_id)
    if not project:
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)
    return project


@router.patch(
    "/projects/{project_id}",
    response_model=Project,
    summary="Update a project",
)
def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    storage: StorageProvider = Depends(get_storage),
) -> Project:
    project = storage.get_project(project_id)
    if not project:
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)

    if req.name is not None:
        project.name = req.name
    if req.status is not None:
        project.status = req.status
    if req.description is not None:
        project.description = req.description
    if req.goals is not None:
        project.goals = req.goals
    if req.metadata is not None:
        project.metadata = req.metadata

    return storage.update_project(project, expected_revision=req.expected_revision)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
def delete_project(
    project_id: str,
    storage: StorageProvider = Depends(get_storage),
) -> None:
    deleted = storage.delete_project(project_id)
    if not deleted:
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)
