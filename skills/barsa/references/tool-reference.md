# Barsa MCP Tool Reference

All Barsa operations MUST use these 12 registered MCP tools. Do not invent non-existent tool names.

---

## Tool Quick Lookup

| Tool | Category | When to Call |
| :--- | :--- | :--- |
| `barsa_list_projects` | Read | Session start when project is unspecified or to discover IDs |
| `barsa_get_project` | Read | Fetch current project overview, status, record count, and main HEAD |
| `barsa_search_memory` | Read | Keyword & attribute query across project records |
| `barsa_get_memory` | Read | Retrieve exact record or historical snapshot at a commit |
| `barsa_get_checkpoint` | Read | Fetch latest or task-specific resume checkpoint |
| `barsa_resume` | Read | Core entry point to retrieve full context package to continue work |
| `barsa_get_history` | Read | Inspect commit DAG history on a branch |
| `barsa_get_diff` | Read | Compare record modifications between two commits |
| `barsa_propose_changes` | Write | Propose changes on a feature branch (never `main`) |
| `barsa_commit` | Write | Commit validated changes directly to a branch (with `expected_head`) |
| `barsa_list_conflicts` | Read | Inspect divergent branches and potential merge collisions |
| `barsa_get_graph_context` | Read | Multi-hop task dependency and blocker analysis |
| `barsa_build_context` | Read | Build token-optimized, 3-level context package with incremental delta sync |

---

## Standard Error Handling

When a tool returns an error code (formatted as `[ERROR_CODE] message`), handle it according to the protocol below:

| Error Code | Meaning | Agent Action |
| :--- | :--- | :--- |
| `[PROJECT_NOT_FOUND]` | Project ID does not exist | Call `barsa_list_projects` to confirm valid project IDs. Ask user if ambiguity remains. |
| `[RECORD_NOT_FOUND]` | Requested record missing | Inform user; search alternative records using `barsa_search_memory`. |
| `[CHECKPOINT_NOT_FOUND]` | No checkpoint saved | Check if tasks exist; create an initial checkpoint via `barsa_commit`. |
| `[COMMIT_NOT_FOUND]` | Invalid commit SHA | Call `barsa_get_history` to verify commit hashes on branch. |
| `[BRANCH_NOT_FOUND]` | Branch does not exist | Check branch names or propose branch via `barsa_propose_changes`. |
| `[INVALID_BMS_RECORD]` | Schema validation failed | Fix missing required fields, naive timestamp, or invalid enum. Do NOT re-submit without correction. |
| `[STALE_REVISION]` | Branch HEAD moved concurrently | Do NOT blindly retry. Retrieve current HEAD via `barsa_get_project`, inspect new diff, and rebase changes. |
| `[MERGE_CONFLICT]` | Colliding changes detected | Call `barsa_list_conflicts` and `barsa_get_diff`. Report conflicts to user. |
| `[UNSUPPORTED_OPERATION]` | E.g. proposing to `main` | Use a feature branch name (e.g. `feature/my-task`) for proposals. |
| `[INTERNAL_ERROR]` | Server runtime failure | Report error to user; verify MCP server health and stderr logs. |
