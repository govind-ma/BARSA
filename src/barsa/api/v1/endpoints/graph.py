"""API endpoints for FalkorDB Knowledge Graph retrieval, traversal, and management (Phase 5)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from barsa.api.deps import (
    get_graph_retrieval,
    get_projection_worker,
    get_storage,
)
from barsa.core.exceptions import ResourceNotFoundError
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.models.graph import (
    AgentContributionsResult,
    DecisionImpactResult,
    GraphProjectionMetadata,
    GraphRebuildResponse,
    ProjectOverviewResult,
    ResumeContextResult,
    TaskDependenciesResult,
)
from barsa.storage.protocol import StorageProvider

logger = logging.getLogger("barsa.api.graph")

router = APIRouter(prefix="/projects/{project_id}/graph", tags=["Knowledge Graph"])


def _verify_project(project_id: str, storage: StorageProvider) -> None:
    if not storage.get_project(project_id):
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)


# =============================================================================
# Graph Status & Health
# =============================================================================


@router.get(
    "/status",
    response_model=GraphProjectionMetadata,
    summary="Get current knowledge graph projection status and synchronization lag",
)
def get_graph_status(
    project_id: str,
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
) -> GraphProjectionMetadata:
    _verify_project(project_id, storage)
    return worker.get_projection_status(project_id)


# =============================================================================
# Project Overview & Nodes
# =============================================================================


@router.get(
    "/overview",
    response_model=ProjectOverviewResult,
    summary="Get project overview of active tasks, approved decisions, requirements, and artifacts",
)
def get_project_overview(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
    retrieval: GraphRetrievalService = Depends(get_graph_retrieval),
) -> ProjectOverviewResult:
    _verify_project(project_id, storage)
    # Process any pending outbox events before read for maximum freshness
    worker.process_pending_events(project_id=project_id)
    proj_meta = worker.get_projection_status(project_id)
    return retrieval.get_project_overview(project_id, limit=limit, projection_metadata=proj_meta)


@router.get(
    "/nodes/{node_id:path}/neighbors",
    response_model=list[dict[str, Any]],
    summary="Get graph neighbors and connecting edges for a node",
)
def get_node_neighbors(
    project_id: str,
    node_id: str,
    direction: str = Query(default="both", pattern="^(in|out|both)$"),
    limit: int = Query(default=50, ge=1, le=500),
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
    retrieval: GraphRetrievalService = Depends(get_graph_retrieval),
) -> list[dict[str, Any]]:
    _verify_project(project_id, storage)
    worker.process_pending_events(project_id=project_id)
    proj_meta = worker.get_projection_status(project_id)
    return retrieval.get_neighbors(
        project_id,
        node_id,
        direction=direction,
        limit=limit,
        projection_metadata=proj_meta,
    )


@router.get(
    "/nodes/{node_id:path}",
    response_model=dict[str, Any],
    summary="Get a single graph node by ID",
)
def get_node(
    project_id: str,
    node_id: str,
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
    retrieval: GraphRetrievalService = Depends(get_graph_retrieval),
) -> dict[str, Any]:
    _verify_project(project_id, storage)
    worker.process_pending_events(project_id=project_id)
    proj_meta = worker.get_projection_status(project_id)
    node = retrieval.get_node(project_id, node_id, projection_metadata=proj_meta)
    if not node:
        raise ResourceNotFoundError(f"Graph node '{node_id}' not found.", "GraphNode", node_id)
    return node


# =============================================================================
# Graph Domain Queries
# =============================================================================


@router.get(
    "/tasks/{task_id}/dependencies",
    response_model=TaskDependenciesResult,
    summary="Get upstream dependencies and blockers for a specific task",
)
def get_task_dependencies(
    project_id: str,
    task_id: str,
    max_depth: int = Query(default=5, ge=1, le=10),
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
    retrieval: GraphRetrievalService = Depends(get_graph_retrieval),
) -> TaskDependenciesResult:
    _verify_project(project_id, storage)
    worker.process_pending_events(project_id=project_id)
    proj_meta = worker.get_projection_status(project_id)
    return retrieval.get_task_dependencies(
        project_id,
        task_id,
        max_depth=max_depth,
        projection_metadata=proj_meta,
    )


@router.get(
    "/decisions/{decision_id}/impact",
    response_model=DecisionImpactResult,
    summary="Get connected tasks, requirements, artifacts, and decisions impacted by a decision",
)
def get_decision_impact(
    project_id: str,
    decision_id: str,
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
    retrieval: GraphRetrievalService = Depends(get_graph_retrieval),
) -> DecisionImpactResult:
    _verify_project(project_id, storage)
    worker.process_pending_events(project_id=project_id)
    proj_meta = worker.get_projection_status(project_id)
    return retrieval.get_decision_impact(project_id, decision_id, projection_metadata=proj_meta)


@router.get(
    "/agents/{agent_id}/contributions",
    response_model=AgentContributionsResult,
    summary="Get commits and records authored by an agent in a project",
)
def get_agent_contributions(
    project_id: str,
    agent_id: str,
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
    retrieval: GraphRetrievalService = Depends(get_graph_retrieval),
) -> AgentContributionsResult:
    _verify_project(project_id, storage)
    worker.process_pending_events(project_id=project_id)
    proj_meta = worker.get_projection_status(project_id)
    return retrieval.get_agent_contributions(project_id, agent_id, projection_metadata=proj_meta)


@router.get(
    "/tasks/{task_id}/resume-context",
    response_model=ResumeContextResult,
    summary="Retrieve full structured context for an agent to resume work on a task",
)
def get_resume_context(
    project_id: str,
    task_id: str,
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
    retrieval: GraphRetrievalService = Depends(get_graph_retrieval),
) -> ResumeContextResult:
    _verify_project(project_id, storage)
    worker.process_pending_events(project_id=project_id)
    proj_meta = worker.get_projection_status(project_id)
    return retrieval.get_resume_context(project_id, task_id, projection_metadata=proj_meta)


# =============================================================================
# Graph Administration
# =============================================================================


@router.post(
    "/rebuild",
    response_model=GraphRebuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Rebuild project graph from authoritative SQLite version-control state",
)
def rebuild_project_graph(
    project_id: str,
    storage: StorageProvider = Depends(get_storage),
    worker: GraphProjectionWorker = Depends(get_projection_worker),
) -> GraphRebuildResponse:
    _verify_project(project_id, storage)
    updated_meta = worker.rebuild_project_graph(project_id)
    return GraphRebuildResponse(
        project_id=project_id,
        rebuilt_nodes_count=updated_meta.node_count,
        rebuilt_relationships_count=updated_meta.relationship_count,
        applied_commit_id=updated_meta.applied_commit_id,
        status=updated_meta.status,
        message="Project graph successfully rebuilt from authoritative main branch state.",
    )
