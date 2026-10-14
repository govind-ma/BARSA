"""Diff engine for computing deterministic record-level and field-level diffs."""

from typing import Any

from barsa.models.versioning import (
    ChangeOperation,
    CommitDiff,
    FieldDiff,
    RecordDiff,
)


def compute_field_diffs(before: dict[str, Any], after: dict[str, Any], prefix: str = "") -> list[FieldDiff]:
    """Recursively compute JSON Pointer field diffs between two dictionaries."""
    diffs: list[FieldDiff] = []
    all_keys = sorted(set(before.keys()) | set(after.keys()))

    for key in all_keys:
        path = f"{prefix}/{key}"
        if key not in before:
            diffs.append(FieldDiff(path=path, before=None, after=after[key]))
        elif key not in after:
            diffs.append(FieldDiff(path=path, before=before[key], after=None))
        else:
            val_b = before[key]
            val_a = after[key]
            if isinstance(val_b, dict) and isinstance(val_a, dict):
                diffs.extend(compute_field_diffs(val_b, val_a, prefix=path))
            elif val_b != val_a:
                diffs.append(FieldDiff(path=path, before=val_b, after=val_a))

    return diffs


def compute_state_diff(
    project_id: str,
    from_commit_id: str | None,
    to_commit_id: str,
    from_state: dict[str, dict[str, Any]],
    to_state: dict[str, dict[str, Any]],
) -> CommitDiff:
    """Compute structured record-level and field-level differences between two project states."""
    added: list[str] = []
    removed: list[str] = []
    modified: list[str] = []
    record_diffs: list[RecordDiff] = []

    all_ids = sorted(set(from_state.keys()) | set(to_state.keys()))

    for rid in all_ids:
        in_before = rid in from_state
        in_after = rid in to_state

        if not in_before and in_after:
            rec_after = to_state[rid]
            rec_type = rec_after.get("record_type", "unknown")
            added.append(rid)
            record_diffs.append(
                RecordDiff(
                    record_id=rid,
                    record_type=rec_type,
                    operation=ChangeOperation.CREATE,
                    fields=[],
                    before_state=None,
                    after_state=rec_after,
                )
            )
        elif in_before and not in_after:
            rec_before = from_state[rid]
            rec_type = rec_before.get("record_type", "unknown")
            removed.append(rid)
            record_diffs.append(
                RecordDiff(
                    record_id=rid,
                    record_type=rec_type,
                    operation=ChangeOperation.DELETE,
                    fields=[],
                    before_state=rec_before,
                    after_state=None,
                )
            )
        else:
            rec_before = from_state[rid]
            rec_after = to_state[rid]
            rec_type = rec_after.get("record_type", rec_before.get("record_type", "unknown"))

            if rec_before != rec_after:
                field_diffs = compute_field_diffs(rec_before, rec_after)
                modified.append(rid)
                record_diffs.append(
                    RecordDiff(
                        record_id=rid,
                        record_type=rec_type,
                        operation=ChangeOperation.UPDATE,
                        fields=field_diffs,
                        before_state=rec_before,
                        after_state=rec_after,
                    )
                )

    return CommitDiff(
        from_commit_id=from_commit_id,
        to_commit_id=to_commit_id,
        project_id=project_id,
        added_records=added,
        removed_records=removed,
        modified_records=modified,
        changes=record_diffs,
    )
