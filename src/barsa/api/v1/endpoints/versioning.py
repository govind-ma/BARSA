"""Version Control API endpoints for Git-style Memory operations (Phase 4)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from barsa.api.deps import get_storage, get_version_control
from barsa.core.exceptions import ResourceNotFoundError
from barsa.models.versioning import (
    Branch,
    BranchCreateRequest,
    Commit,
    CommitCreateRequest,
    CommitDiff,
    ConflictRecord,
    ConflictResolveRequest,
    MergeExecuteRequest,
    MergeProposal,
    MergeProposalCreateRequest,
    ProposalStatus,
    RestoreRequest,
    ReviewComment,
    ReviewCommentCreateRequest,
    ReviewSubmitRequest,
)
from barsa.storage.protocol import StorageProvider
from barsa.versioning.engine import VersionControlEngine

logger = logging.getLogger("barsa.api.versioning")

router = APIRouter(prefix="/projects/{project_id}/versioning", tags=["Memory Version Control"])


def _verify_project(project_id: str, storage: StorageProvider) -> None:
    if not storage.get_project(project_id):
        raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)


# =============================================================================
# Commits & History
# =============================================================================


@router.post(
    "/commits",
    response_model=Commit,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new atomic memory commit",
)
def create_commit(
    project_id: str,
    payload: CommitCreateRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> Commit:
    _verify_project(project_id, storage)
    return vc.create_commit(
        project_id=project_id,
        branch_name=payload.branch,
        changes=payload.changes,
        message=payload.message,
        author_id=payload.author_id,
        author_type=payload.author_type,
        expected_head_commit_id=payload.expected_head_commit_id,
        parent_commit_ids=payload.parent_commit_ids,
        metadata=payload.metadata,
    )


@router.get(
    "/commits/{commit_id}",
    response_model=Commit,
    summary="Get details of a specific commit by ID",
)
def get_commit(
    project_id: str,
    commit_id: str,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> Commit:
    _verify_project(project_id, storage)
    commit = vc.get_commit(project_id, commit_id)
    if not commit:
        raise ResourceNotFoundError(f"Commit '{commit_id}' not found.", "Commit", commit_id)
    return commit


@router.get(
    "/history",
    response_model=list[Commit],
    summary="List commit history for project or specific branch",
)
def get_history(
    project_id: str,
    branch: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> list[Commit]:
    _verify_project(project_id, storage)
    return vc.get_history(project_id, branch_name=branch, limit=limit)


@router.get(
    "/records/{record_id}/history",
    response_model=list[Commit],
    summary="Get commit history specifically affecting a record",
)
def get_record_history(
    project_id: str,
    record_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> list[Commit]:
    _verify_project(project_id, storage)
    return vc.get_record_history(project_id, record_id=record_id, limit=limit)


# =============================================================================
# Branches
# =============================================================================


@router.get(
    "/branches",
    response_model=list[Branch],
    summary="List all branches in project",
)
def list_branches(
    project_id: str,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> list[Branch]:
    _verify_project(project_id, storage)
    # Ensure main branch is initialized if none exists
    vc.initialize_project_main_branch(project_id)
    return vc.list_branches(project_id)


@router.post(
    "/branches",
    response_model=Branch,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new branch pointing to HEAD or a specific commit",
)
def create_branch(
    project_id: str,
    payload: BranchCreateRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> Branch:
    _verify_project(project_id, storage)
    return vc.create_branch(project_id, payload.name, payload.start_commit_id)


@router.get(
    "/branches/{branch_name:path}",
    response_model=Branch,
    summary="Get details of a branch by name",
)
def get_branch(
    project_id: str,
    branch_name: str,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> Branch:
    _verify_project(project_id, storage)
    branch = vc.get_branch(project_id, branch_name)
    if not branch:
        raise ResourceNotFoundError(f"Branch '{branch_name}' not found.", "Branch", branch_name)
    return branch


@router.delete(
    "/branches/{branch_name:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a branch (main branch is protected)",
)
def delete_branch(
    project_id: str,
    branch_name: str,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> None:
    _verify_project(project_id, storage)
    deleted = vc.delete_branch(project_id, branch_name)
    if not deleted:
        raise ResourceNotFoundError(f"Branch '{branch_name}' not found.", "Branch", branch_name)


# =============================================================================
# Diff
# =============================================================================


@router.get(
    "/diff",
    response_model=CommitDiff,
    summary="Compute structured record and field diff between two commits",
)
def diff_commits(
    project_id: str,
    to_commit: str = Query(...),
    from_commit: str | None = Query(default=None),
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> CommitDiff:
    _verify_project(project_id, storage)
    return vc.diff_commits(project_id, from_commit_id=from_commit, to_commit_id=to_commit)


# =============================================================================
# Merge Proposals & Reviews
# =============================================================================


@router.post(
    "/merge-proposals",
    response_model=MergeProposal,
    status_code=status.HTTP_201_CREATED,
    summary="Create a merge proposal between branches",
)
def create_merge_proposal(
    project_id: str,
    payload: MergeProposalCreateRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> MergeProposal:
    _verify_project(project_id, storage)
    return vc.create_merge_proposal(
        project_id=project_id,
        title=payload.title,
        source_branch=payload.source_branch,
        target_branch=payload.target_branch,
        author_id=payload.author_id,
        description=payload.description,
    )


@router.get(
    "/merge-proposals",
    response_model=list[MergeProposal],
    summary="List merge proposals in project",
)
def list_merge_proposals(
    project_id: str,
    status_filter: ProposalStatus | None = Query(default=None, alias="status"),
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> list[MergeProposal]:
    _verify_project(project_id, storage)
    return vc.list_merge_proposals(project_id, status=status_filter)


@router.get(
    "/merge-proposals/{proposal_id}",
    response_model=MergeProposal,
    summary="Get details of a merge proposal",
)
def get_merge_proposal(
    project_id: str,
    proposal_id: str,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> MergeProposal:
    _verify_project(project_id, storage)
    prop = vc.get_merge_proposal(project_id, proposal_id)
    if not prop:
        raise ResourceNotFoundError(f"Proposal '{proposal_id}' not found.", "MergeProposal", proposal_id)
    return prop


@router.post(
    "/merge-proposals/{proposal_id}/comments",
    response_model=ReviewComment,
    status_code=status.HTTP_201_CREATED,
    summary="Add a review comment to a merge proposal",
)
def add_review_comment(
    project_id: str,
    proposal_id: str,
    payload: ReviewCommentCreateRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> ReviewComment:
    _verify_project(project_id, storage)
    return vc.add_review_comment(
        project_id=project_id,
        proposal_id=proposal_id,
        author_id=payload.author_id,
        content=payload.content,
        author_type=payload.author_type,
        record_id=payload.record_id,
    )


@router.post(
    "/merge-proposals/{proposal_id}/reviews",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a formal review (approved, changes_requested, rejected)",
)
def submit_review(
    project_id: str,
    proposal_id: str,
    payload: ReviewSubmitRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> dict[str, Any]:
    _verify_project(project_id, storage)
    return vc.submit_review(
        project_id=project_id,
        proposal_id=proposal_id,
        reviewer_id=payload.reviewer_id,
        status=payload.status,
        summary=payload.summary,
        reviewer_type=payload.reviewer_type,
    )


@router.post(
    "/merge-proposals/{proposal_id}/merge",
    response_model=Commit,
    summary="Execute a three-way merge commit for an approved proposal",
)
def execute_merge(
    project_id: str,
    proposal_id: str,
    payload: MergeExecuteRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> Commit:
    _verify_project(project_id, storage)
    return vc.execute_merge(
        project_id=project_id,
        proposal_id=proposal_id,
        author_id=payload.author_id,
    )


# =============================================================================
# Conflicts
# =============================================================================


@router.get(
    "/conflicts",
    response_model=list[ConflictRecord],
    summary="List conflicts for project or specific proposal",
)
def list_conflicts(
    project_id: str,
    proposal_id: str | None = Query(default=None),
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> list[ConflictRecord]:
    _verify_project(project_id, storage)
    return vc.list_conflicts(project_id, proposal_id=proposal_id)


@router.post(
    "/conflicts/{conflict_id}/resolve",
    response_model=ConflictRecord,
    summary="Explicitly resolve a conflict with an approved record state",
)
def resolve_conflict(
    project_id: str,
    conflict_id: str,
    payload: ConflictResolveRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> ConflictRecord:
    _verify_project(project_id, storage)
    return vc.resolve_conflict(
        project_id=project_id,
        conflict_id=conflict_id,
        resolved_by=payload.resolved_by,
        resolved_value=payload.resolved_value,
    )


# =============================================================================
# Historical Restoration
# =============================================================================


@router.post(
    "/restore",
    response_model=Commit,
    status_code=status.HTTP_201_CREATED,
    summary="Restore memory state to an earlier historical commit without deleting history",
)
def restore_commit(
    project_id: str,
    payload: RestoreRequest,
    storage: StorageProvider = Depends(get_storage),
    vc: VersionControlEngine = Depends(get_version_control),
) -> Commit:
    _verify_project(project_id, storage)
    return vc.restore_commit_state(
        project_id=project_id,
        target_branch=payload.target_branch,
        restore_from_commit_id=payload.restore_from_commit_id,
        author_id=payload.author_id,
        message=payload.message,
    )
