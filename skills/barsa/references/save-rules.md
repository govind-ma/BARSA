# Barsa Memory Save Rules

This document specifies *when* and *how* to commit working memory to Barsa, avoiding both micro-save clutter and cross-session data loss.

---

## 1. Meaningful Save Triggers

An agent should trigger a save operation (`barsa_commit` or `barsa_propose_changes`) upon any of the following events:

| Trigger | Description | Action Required |
| :--- | :--- | :--- |
| **Milestone / Task Completion** | An active task transitions from `in_progress` to `completed`. | Commit updated `task` record with `status: "completed"` and create new `checkpoint`. |
| **Work Paused / Handoff** | Agent finishes turn, reaches token limit, or user requests pause. | Create new `checkpoint` documenting exact completed items and single `next_action`. |
| **New Architecture Decision** | A non-trivial engineering choice is agreed upon (e.g., choice of library, auth flow, database schema). | Commit `decision` record with `status: "approved"`, `decision`, and `rationale`. |
| **Major Error / Blocker Encountered** | An unexpected failure prevents forward progress. | Update `checkpoint` with populated `blockers` array describing root cause and reproduction. |
| **Explicit User Command** | User says: "Save checkpoint", "Commit memory", "Save my work". | Immediately commit current state and confirm with commit ID. |
| **External Dependency Introduced** | Added major package, external API, or infrastructure dependency. | Add `knowledge` record (`knowledge_type: "requirement"`) and link in `checkpoint`. |

---

## 2. Anti-Patterns (When NOT to Save)

To keep commit DAGs clean and token consumption lean, DO NOT save:
- **Micro-interactions:** After every routine question, single-line edit, or explanatory prose message.
- **Speculative Thoughts:** While brainstorming alternatives before a decision has been agreed upon.
- **Raw Tool Outputs:** Do not dump megabytes of compiler logs or raw test outputs directly into memory records (save an artifact reference instead).
- **Ephemeral State:** Scratchpad calculations or temporary variable explorations.

---

## 3. Atomic Checkpoint Structure

Every checkpoint saved MUST follow this structure:

```json
{
  "id": "cp-<timestamp-or-slug>",
  "project_id": "<project-id>",
  "record_type": "checkpoint",
  "task_id": "<target-task-id>",
  "status": "active",
  "completed_actions": [
    "Specific completed action item 1",
    "Specific completed action item 2"
  ],
  "pending_actions": [
    "Remaining action item 1",
    "Remaining action item 2"
  ],
  "next_action": "The single atomic immediate step to perform next",
  "blockers": [],
  "decision_refs": ["<decision-id-1>"],
  "artifact_refs": ["<artifact-id-1>"],
  "base_revision": "<commit-id-at-checkpoint-creation>",
  "created_by": "<agent-or-user-id>",
  "created_at": "<ISO-8601-UTC-timestamp>"
}
```

> [!TIP]
> The `next_action` field is the most critical attribute of a checkpoint. It tells the next agent exactly what to do without needing to parse the full conversation history. Make it actionable, specific, and bounded.
