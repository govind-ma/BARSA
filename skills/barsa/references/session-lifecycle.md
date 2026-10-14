# Session Lifecycle Protocol

Guidelines for managing session start, active task establishment, execution, and graceful session exit.

---

## 1. Session Initialization Checklist

When an agent begins a Barsa-enabled session:

1. **Verify Tool Availability:** Confirm `barsa_*` tools exist. If missing, explain to the user that Barsa MCP server is offline.
2. **Resolve Target Project:**
   - If the user explicitly stated the project name or ID (e.g., "Resume my auth engine project"), search or verify with `barsa_get_project` or `barsa_list_projects`.
   - If unspecified and only one project exists, use it.
   - If multiple projects exist, list them to the user and request selection. **Never guess the active project when multiple candidates exist.**
3. **Establish Authoritative Revision:** Call `barsa_get_project` to fetch the authoritative HEAD commit ID on `main`.
4. **Acquire Context Package:** Call `barsa_resume(project_id=...)` or `barsa_get_checkpoint(project_id=...)` to retrieve the latest checkpoint, active task, decisions, and blockers.
5. **Verify Artifact Accessibility:** Check that files referenced in `artifact_refs` actually exist on disk in the local workspace. If missing, mark them as unverified and notify the user.
6. **Formulate Continuation Plan:** Summarize what previous sessions completed and state the immediate next action.

```
       ┌─────────────────────────────┐
       │ Session Starts              │
       └──────────────┬──────────────┘
                      │
                      ▼
       ┌─────────────────────────────┐
       │ Check Tool Availability     │
       └──────────────┬──────────────┘
                      │
                      ▼
       ┌─────────────────────────────┐
       │ Project Explicitly Named?   │
       └───┬─────────────────────┬───┘
       Yes │                  No │
           ▼                     ▼
┌──────────────────┐  ┌───────────────────────────────────┐
│ Verify Project ID│  │ Call barsa_list_projects()           │
└──────────┬───────┘  │ If 1 project -> Select it            │
           │          │ If >1 project -> Ask user to choose  │
           │          └──────────────────┬──────────────────┘
           └──────────────┬──────────────┘
                          │
                          ▼
       ┌─────────────────────────────────────┐
       │ Call barsa_resume(project_id=...)   │
       │ Retrieve Checkpoint, Task, Decisions│
       └──────────────────┬──────────────────┘
                          │
                          ▼
       ┌─────────────────────────────────────┐
       │ Verify Local Artifacts & Blockers   │
       └──────────────────┬──────────────────┘
                          │
                          ▼
       ┌─────────────────────────────────────┐
       │ Present Plan & Begin Execution      │
       └─────────────────────────────────────┘
```

---

## 2. Active Session Work Execution

During task execution:
- Respect approved architectural decisions (`status: "approved"`). Do not reverse them without asking the user.
- If a task dependency is unfinished or a blocker is recorded, resolve the dependency first before proceeding.
- Record key intermediate findings as `knowledge` records if they will affect future sessions.

---

## 3. Session End & Handoff Preparation

When an agent completes a milestone, is interrupted, or prepares for a handoff:
1. Ensure all modified files are syntactically sound or documented as broken in `blockers`.
2. Construct an updated `checkpoint` record:
   - Add completed work items to `completed_actions`.
   - Update `pending_actions` to reflect remaining steps.
   - Formulate a clear, unambiguous, atomic `next_action`.
3. Commit the checkpoint to `main` using `barsa_commit` with `expected_head`.
4. Inform the user of the committed commit hash and provide a 2-line summary of what the next agent will do upon resuming.
