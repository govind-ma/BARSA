"""Incremental revision-aware context synchronization engine (Phase 8)."""

from typing import Any

from barsa.context.models import IncrementalSyncMetadata
from barsa.core.exceptions import StorageError
from barsa.versioning.engine import VersionControlEngine


class IncrementalSyncService:
    """Computes revision-aware delta context updates across Git-style memory commits."""

    def __init__(self, vc_engine: VersionControlEngine) -> None:
        self.vc = vc_engine

    def compute_incremental_sync(
        self,
        project_id: str,
        known_revision: str,
        authoritative_commit: str,
    ) -> tuple[IncrementalSyncMetadata, dict[str, Any]]:
        """Validate ancestry and compute incremental delta changes.

        Returns (IncrementalSyncMetadata, delta_payload).
        If known_revision is identical to authoritative_commit, returns empty delta.
        If known_revision is an ancestor, returns the delta changes.
        If known_revision is not an ancestor or not found, flags rebase_required=True.
        """
        # Case 1: Identical revision (client already has HEAD)
        if known_revision == authoritative_commit:
            meta = IncrementalSyncMetadata(
                is_incremental=True,
                known_revision=known_revision,
                authoritative_revision=authoritative_commit,
                rebase_required=False,
                added_records=[],
                modified_records=[],
                deleted_records=[],
                details="Client is already at authoritative HEAD revision. Zero delta required.",
            )
            return meta, {"changes": []}

        # Case 2: Validate known_revision exists in project
        known_c = self.vc.get_commit(project_id, known_revision)
        if not known_c:
            meta = IncrementalSyncMetadata(
                is_incremental=False,
                known_revision=known_revision,
                authoritative_revision=authoritative_commit,
                rebase_required=True,
                details=f"Known revision '{known_revision}' does not exist in project '{project_id}'. Full context required.",
            )
            return meta, {}

        # Case 3: Check DAG ancestry using Lowest Common Ancestor (LCA)
        try:
            lca = self.vc.find_lowest_common_ancestor(project_id, known_revision, authoritative_commit)
            if lca != known_revision:
                # Diverged branch or rebased history!
                meta = IncrementalSyncMetadata(
                    is_incremental=False,
                    known_revision=known_revision,
                    authoritative_revision=authoritative_commit,
                    rebase_required=True,
                    details=f"Known revision '{known_revision[:8]}' has diverged from current HEAD '{authoritative_commit[:8]}'. Full context required.",
                )
                return meta, {}
        except (StorageError, Exception) as exc:
            meta = IncrementalSyncMetadata(
                is_incremental=False,
                known_revision=known_revision,
                authoritative_revision=authoritative_commit,
                rebase_required=True,
                details=f"DAG ancestry check failed: {exc}. Full context required.",
            )
            return meta, {}

        # Case 4: True ancestor! Compute diff between known_revision and authoritative_commit
        diff = self.vc.diff_commits(project_id, known_revision, authoritative_commit)

        meta = IncrementalSyncMetadata(
            is_incremental=True,
            known_revision=known_revision,
            authoritative_revision=authoritative_commit,
            rebase_required=False,
            added_records=diff.added_records,
            modified_records=diff.modified_records,
            deleted_records=diff.removed_records,
            details=f"Computed incremental update from commit {known_revision[:8]} to {authoritative_commit[:8]}.",
        )

        # Extract latest states of added/modified records
        latest_states = self.vc.reconstruct_project_state(project_id, authoritative_commit)
        delta_records = {
            r_id: latest_states[r_id] for r_id in (diff.added_records + diff.modified_records) if r_id in latest_states
        }

        return meta, {"delta_records": delta_records, "diff": diff.model_dump(mode="json")}
