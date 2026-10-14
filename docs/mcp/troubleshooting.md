# Barsa MCP Server — Troubleshooting & Diagnostics

Common issues, diagnostic procedures, error code explanations, and solutions for the Barsa MCP server.

---

## 1. Error Codes Reference

All Barsa tool failures return structured errors with standardized error codes:

| Error Code | HTTP / RPC Semantic | Cause & Resolution |
| :--- | :--- | :--- |
| `PROJECT_NOT_FOUND` | 404 Not Found | Project ID does not exist in local storage. Call `barsa_list_projects` to verify IDs. |
| `RECORD_NOT_FOUND` | 404 Not Found | Record ID does not exist in project or was not present at requested historical commit. |
| `CHECKPOINT_NOT_FOUND`| 404 Not Found | No checkpoint exists matching criteria. Call `barsa_commit` to save an initial checkpoint. |
| `COMMIT_NOT_FOUND` | 404 Not Found | Commit SHA-256 does not exist in DAG. Inspect branch using `barsa_get_history`. |
| `BRANCH_NOT_FOUND` | 404 Not Found | Specified branch name does not exist. Call `barsa_propose_changes` or create branch. |
| `INVALID_BMS_RECORD` | 422 Unprocessable | Change payload violates BMS schema (e.g., missing required fields, naive timestamp). |
| `INVALID_PARAMETER` | 400 Bad Request | Identifier contains illegal characters, exceeds length limits, or pagination bounds exceeded. |
| `UNSUPPORTED_OPERATION` | 403 Forbidden | Attempted forbidden operation (e.g., calling `barsa_propose_changes` directly against `main`). |
| `STALE_REVISION` | 409 Conflict | Concurrency conflict: `expected_head` diverges from actual branch HEAD. Fetch latest commit and rebase. |
| `MERGE_CONFLICT` | 409 Conflict | Committing or merging changes collides with competing modifications. Inspect via `barsa_list_conflicts`. |
| `UNAUTHORIZED` | 403 Forbidden | Current identity is not authorized for the requested project. |
| `INTERNAL_ERROR` | 500 Server Error | Unexpected internal server exception. Check stderr logs for stack trace. |

---

## 2. Common Scenarios & Diagnostics

### Stdio Communication Broken / Protocol Parse Errors
- **Symptom:** Claude Desktop or MCP Inspector reports `Failed to parse message` or hangs on startup.
- **Root Cause:** Standard output (`stdout`) was polluted with application logs or `print()` statements.
- **Solution:** In `stdio` mode, Barsa redirects all loggers to `sys.stderr`. If writing custom scripts or extensions, ensure nothing writes to `sys.stdout` except JSON-RPC protocol frames.

### Stale Revision on Commit
- **Symptom:** `[STALE_REVISION] Branch 'main' HEAD has moved from 'e7a8...' to '3541...'`.
- **Root Cause:** Another agent or human committed to `main` while your agent was thinking.
- **Solution:** Call `barsa_resume` or `barsa_get_project` to obtain the new HEAD commit hash, verify changes, and retry with the updated `expected_head`.

### Graph Shows Unavailable / Stale Projection
- **Symptom:** `barsa_get_graph_context` returns `GRAPH_UNAVAILABLE`.
- **Root Cause:** FalkorDB daemon is offline or connection failed.
- **Solution:** Barsa automatically operates in resilient fallback mode using SQLite. When FalkorDB resumes, the transactional outbox (`graph_outbox`) catches up automatically via `worker.process_pending_events()`.
