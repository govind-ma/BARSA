"""Three-way merge engine for structured BMS project memory states."""

from typing import Any

from barsa.bms.base import generate_uuid_str
from barsa.models.versioning import (
    ChangeOperation,
    ConflictRecord,
    ConflictType,
    MemoryChange,
)


class MergeResult:
    """Outcome of a three-way merge operation."""

    def __init__(
        self,
        can_merge_cleanly: bool,
        merged_state: dict[str, dict[str, Any]],
        conflicts: list[ConflictRecord],
        changes: list[MemoryChange],
    ) -> None:
        self.can_merge_cleanly = can_merge_cleanly
        self.merged_state = merged_state
        self.conflicts = conflicts
        self.changes = changes


def three_way_merge_states(
    project_id: str,
    base_state: dict[str, dict[str, Any]],
    source_state: dict[str, dict[str, Any]],
    target_state: dict[str, dict[str, Any]],
    source_branch: str,
    target_branch: str,
    proposal_id: str | None = None,
) -> MergeResult:
    """Perform deterministic three-way merge on dictionary record maps.

    Logic:
    - If a record is unmodified in one branch and modified in the other, adopt the modification.
    - If a record is modified identically in both branches, adopt the modification cleanly.
    - If a record has independent field edits without conflict, merge fields cleanly.
    - If same field is edited with different values -> SAME_FIELD_UPDATE conflict.
    - If one branch deleted a record and the other edited it -> DELETE_VS_UPDATE conflict.
    - If both created a new record with same ID but different contents -> RECORD_COLLISION conflict.
    """
    merged: dict[str, dict[str, Any]] = {}
    conflicts: list[ConflictRecord] = []
    all_record_ids = sorted(set(base_state.keys()) | set(source_state.keys()) | set(target_state.keys()))

    for rid in all_record_ids:
        in_base = rid in base_state
        in_src = rid in source_state
        in_tgt = rid in target_state

        rec_base = base_state.get(rid)
        rec_src = source_state.get(rid)
        rec_tgt = target_state.get(rid)

        # Case 1: Unchanged in both branches relative to base
        if in_base and in_src and in_tgt and rec_src == rec_base and rec_tgt == rec_base:
            merged[rid] = rec_base
            continue

        # Case 2: Changed in source only (target matches base)
        if in_base and in_tgt and rec_tgt == rec_base:
            if in_src:
                merged[rid] = rec_src
            # if deleted in source (not in_src), don't include in merged
            continue

        # Case 3: Changed in target only (source matches base)
        if in_base and in_src and rec_src == rec_base:
            if in_tgt:
                merged[rid] = rec_tgt
            # if deleted in target, don't include in merged
            continue

        # Case 4: Added in one branch only
        if not in_base:
            if in_src and not in_tgt:
                merged[rid] = rec_src
                continue
            if in_tgt and not in_src:
                merged[rid] = rec_tgt
                continue
            if in_src and in_tgt:
                # Added in both branches
                if rec_src == rec_tgt:
                    merged[rid] = rec_src
                    continue
                # Both added differently -> collision
                conflicts.append(
                    ConflictRecord(
                        conflict_id=generate_uuid_str(),
                        project_id=project_id,
                        proposal_id=proposal_id,
                        source_branch=source_branch,
                        target_branch=target_branch,
                        affected_record_id=rid,
                        conflict_type=ConflictType.RECORD_COLLISION,
                        base_value=None,
                        source_value=rec_src,
                        target_value=rec_tgt,
                    )
                )
                continue

        # Case 5: Deleted in both branches
        if in_base and not in_src and not in_tgt:
            # Clean concurrent deletion
            continue

        # Case 6: Delete vs Update
        if in_base and (not in_src or not in_tgt):
            conflicts.append(
                ConflictRecord(
                    conflict_id=generate_uuid_str(),
                    project_id=project_id,
                    proposal_id=proposal_id,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    affected_record_id=rid,
                    conflict_type=ConflictType.DELETE_VS_UPDATE,
                    base_value=rec_base,
                    source_value=rec_src,
                    target_value=rec_tgt,
                )
            )
            continue

        # Case 7: Both modified in both branches
        assert in_src and in_tgt and in_base
        assert rec_src is not None and rec_tgt is not None and rec_base is not None

        if rec_src == rec_tgt:
            # Both made identical modifications
            merged[rid] = rec_src
            continue

        # Attempt granular field-level merge
        merged_rec = dict(rec_base)
        field_conflict = False
        all_keys = sorted(set(rec_base.keys()) | set(rec_src.keys()) | set(rec_tgt.keys()))

        for key in all_keys:
            val_base = rec_base.get(key)
            val_src = rec_src.get(key)
            val_tgt = rec_tgt.get(key)

            if val_src == val_tgt:
                merged_rec[key] = val_src
            elif val_src == val_base:
                # Only target changed key
                merged_rec[key] = val_tgt
            elif val_tgt == val_base:
                # Only source changed key
                merged_rec[key] = val_src
            else:
                # Both changed key with different values -> Same-field update conflict
                field_conflict = True
                conflicts.append(
                    ConflictRecord(
                        conflict_id=generate_uuid_str(),
                        project_id=project_id,
                        proposal_id=proposal_id,
                        source_branch=source_branch,
                        target_branch=target_branch,
                        affected_record_id=rid,
                        conflict_type=ConflictType.SAME_FIELD_UPDATE,
                        base_value={key: val_base},
                        source_value={key: val_src},
                        target_value={key: val_tgt},
                    )
                )

        if not field_conflict:
            merged[rid] = merged_rec

    # Compute changes from target to merged state
    changes: list[MemoryChange] = []
    for rid, m_rec in merged.items():
        if rid not in target_state:
            changes.append(
                MemoryChange(
                    operation=ChangeOperation.CREATE,
                    record_id=rid,
                    record_type=m_rec.get("record_type", "unknown"),
                    before_state=None,
                    after_state=m_rec,
                )
            )
        elif target_state[rid] != m_rec:
            changes.append(
                MemoryChange(
                    operation=ChangeOperation.UPDATE,
                    record_id=rid,
                    record_type=m_rec.get("record_type", "unknown"),
                    before_state=target_state[rid],
                    after_state=m_rec,
                )
            )

    for rid, t_rec in target_state.items():
        if rid not in merged and not any(c.affected_record_id == rid for c in conflicts):
            changes.append(
                MemoryChange(
                    operation=ChangeOperation.DELETE,
                    record_id=rid,
                    record_type=t_rec.get("record_type", "unknown"),
                    before_state=t_rec,
                    after_state=None,
                )
            )

    return MergeResult(
        can_merge_cleanly=(len(conflicts) == 0),
        merged_state=merged,
        conflicts=conflicts,
        changes=changes,
    )
