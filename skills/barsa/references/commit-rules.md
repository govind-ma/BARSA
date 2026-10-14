# Barsa Commit & Branching Rules

Barsa memory versioning follows Git principles. Every commit is content-addressed with SHA-256 and represents reproducible changes to structured project memory.

---

## 1. Branching Strategy

- **`main` Branch (Protected):**
  - Represents the authoritative, accepted project memory.
  - Changes directly committed to `main` via `barsa_commit` are automatically projected into the FalkorDB knowledge graph.
  - Cannot be proposed directly using `barsa_propose_changes`.
- **Feature Branches (`feature/<slug>` or `proposal/<slug>`):**
  - Created when proposing non-trivial or multi-agent changes for review.
  - Use `barsa_propose_changes(project_id, branch, base_commit, changes, message)`.
  - Feature branch commits do NOT contaminate the primary graph projection until merged into `main`.

---

## 2. Commit Rules & Concurrency Control

When calling `barsa_commit`:

1. **Verify HEAD:** Always pass `expected_head`. Set it to the commit ID retrieved from `barsa_get_project` or `barsa_resume`.
2. **Handle Stale Revisions:** If `barsa_commit` returns `[STALE_REVISION]`, another session has committed changes to `main`.
   - Retrieve the new HEAD via `barsa_get_project`.
   - Call `barsa_get_diff` between your old base and new HEAD.
   - Rebase or adjust your changes to avoid overwriting recent updates.
   - Retry with updated `expected_head`.
3. **Commit Messages:** Follow conventional commit guidelines:
   - `feat(<component>): <action summary>`
   - `fix(<component>): <bug description>`
   - `docs(<component>): <decision documentation>`
   - `chore(<component>): <checkpoint save>`
4. **Author Identification:** Identity is resolved automatically by the server based on the local OS identity context.

---

## 3. Atomic Change Construction

When supplying the `changes` list:
```json
[
  {
    "operation": "create",
    "record_id": "dec-use-postgresql",
    "record_type": "decision",
    "after_state": { ... }
  },
  {
    "operation": "update",
    "record_id": "task-auth-01",
    "record_type": "task",
    "before_state": { ... },
    "after_state": { ... }
  },
  {
    "operation": "delete",
    "record_id": "kn-obsolete-fact",
    "record_type": "knowledge"
  }
]
```
- For `"create"`: `after_state` is required.
- For `"update"`: `after_state` is required; `before_state` is recommended for field-level diff calculation.
- For `"delete"`: `record_id` and `record_type` are required.
