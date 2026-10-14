# Barsa Resume Rules

This reference outlines the exact steps and behavioral guarantees when a user asks an agent to resume or continue work.

---

## 1. Resume Triggers

The agent must activate the resume protocol whenever the user expresses continuation intent:
- *"Continue my project."*
- *"Resume from Barsa."*
- *"What were we working on last?"*
- *"Pick up where we left off."*
- *"Pull the latest Barsa checkpoint."*
- *"Open my saved work on project X."*

---

## 2. Step-by-Step Resume Procedure

### Step 1: Identify and Verify the Project
- If the project ID is stated by the user, verify it via `barsa_get_project(project_id)`.
- If the project is ambiguous, call `barsa_list_projects()` and present options to the user.

### Step 2: Acquire Authoritative Context Package
Call `barsa_resume(project_id=..., task_id=...)`.
The response contains:
- `project_identity`: Current project metadata and lifecycle status.
- `authoritative_revision`: The latest commit hash on `main`.
- `revision_warning`: Any warning if client cache diverged.
- `current_task`: The active task record (or first pending/in_progress task).
- `latest_checkpoint`: The most recent checkpoint detailing completed actions, pending actions, and `next_action`.
- `relevant_decisions`: Approved architectural decisions constraining this task.
- `dependencies`: Prerequisite tasks.
- `blockers`: Active blockers.

### Step 3: Inspect Checkpoint and Active Task
Check the `latest_checkpoint`:
- If `status == "active"`: Review `completed_actions` and locate `next_action`.
- If `blockers` is non-empty: Focus on diagnosing and clearing the blocker first.
- If `next_action` is present: Use it as the immediate focal point of your continuation plan.

### Step 4: Verify Local Artifact Integrity
Check whether files listed in `artifact_refs` exist in the workspace and match expected content. If files are missing, alert the user before proceeding with edits.

### Step 5: Formulate and Present Continuation Plan
Present a concise (3 to 5 bullet points) continuation briefing:
1. **Current Project & Revision:** Name, ID, HEAD commit hash.
2. **Current Goal / Task:** Title and status.
3. **Completed in Prior Sessions:** Brief summary from `completed_actions`.
4. **Immediate Next Action:** Exact step about to be executed.
5. **Known Blockers / Constraints:** (if any).

---

## 3. What Resume Guarantees (and Does Not Guarantee)

| What Barsa Guarantees | What Cannot Be Guaranteed |
| :--- | :--- |
| Exact knowledge preservation across sessions | Identical model token generation or exact execution phrasing |
| Deterministic commit history and versioned diffs | Unverified third-party external files not checked in |
| Approved decisions and architectural boundaries | Model hallucination immunity without grounding |
| Immediate visibility of what the previous agent completed | Transfer of proprietary provider hidden reasoning traces |
