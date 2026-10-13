# Barsa Memory Package Format

## 1. Package Structure

The `BarsaMemoryPackage` is the canonical JSON exchange unit for BMS v0.1.

```json
{
  "format": "barsa-memory-package",
  "bms_version": "0.1",
  "schema_version": "0.1",
  "exported_at": "2026-10-13T16:20:00Z",
  "workspace": { ... },
  "project": { ... },
  "records": {
    "knowledge": [ ... ],
    "decisions": [ ... ],
    "tasks": [ ... ],
    "agents": [ ... ],
    "artifacts": [ ... ],
    "checkpoints": [ ... ]
  },
  "relationships": [ ... ],
  "latest_checkpoint_id": "chk-resume-idempotency",
  "commits": [ ... ]
}
```

---

## 2. Referential Integrity Rules

A compliant `BarsaMemoryPackage` must satisfy the following validation rules:

1. **Workspace and Project Alignment:** `package.project.workspace_id` must match `package.workspace.id`.
2. **Project ID Scoping:** All records inside `records` and `relationships` must have a `project_id` matching `package.project.id`.
3. **Globally Unique IDs:** No two records within the entire package may share the same `id`.
4. **Task Dependencies:** Every task in `dependencies` must exist within `records.tasks`, and no task may depend on itself.
5. **Relationship Targets:** Both `source_id` and `target_id` must reference valid records within the package, and cannot be identical.
6. **Latest Checkpoint Reference:** If `latest_checkpoint_id` is supplied, it must match an existing checkpoint in `records.checkpoints`.
7. **Decision and Artifact References:** Checkpoint `decision_refs` and `artifact_refs` must reference existing record IDs.
