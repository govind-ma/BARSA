# Barsa MCP Server — Security & Permissions

Barsa's local-first MCP server incorporates rigorous security boundaries to prevent prompt injection attacks, arbitrary file system traversal, unauthorized multi-project data leaks, and race conditions.

---

## 1. Local Identity Context

- In local-first deployments, authentication uses the local operating system user identity (`getpass.getuser()`) via `LocalIdentity`.
- This identity is stored in an `asyncio` / Python `ContextVar` (`CURRENT_IDENTITY`), establishing clear authorship tracking for every commit and review comment.
- Subprocesses or client tokens can customize the context, but the default context automatically attributes actions to the local system operator without requiring third-party credentials.

---

## 2. Input Sanitization & Bounds

Every input parameter received across the MCP transport is validated before touching storage or business logic:

1. **Identifier Sanitization (`validate_identifier`):**
   - Applies to `project_id`, `record_id`, `task_id`, `checkpoint_id`, and `commit_id`.
   - Length is strictly bounded (1 to 128 characters).
   - Character set is strictly restricted to alphanumeric characters, dashes, and underscores (`^[a-zA-Z0-9_\-]+$`).
   - Rejects directory separators (`/`, `\`), null bytes (`\0`), and path traversal tokens (`..`), preventing file traversal attacks into the local SQLite or artifact directories.

2. **Branch Name Validation (`validate_branch_name`):**
   - Must match `^[a-zA-Z0-9_\-\.\/]+$`.
   - Cannot start or end with a slash (`/`), and cannot contain consecutive slashes (`//`) or `..`.

3. **Query String Sanitization (`validate_query_string`):**
   - Query strings are stripped of leading/trailing whitespace and capped at 500 characters.

4. **Limits & Pagination Bounds (`validate_limit`):**
   - Explicit upper bounds prevent memory exhaustion attacks. Default page limit is 50; hard ceiling is 100 records.

5. **Graph Traversal Depth Bounds (`validate_depth`):**
   - Traversal depth is clamped between 1 and 5 hops, preventing runaway Cypher traversals or denial-of-service in heavily interconnected graphs.

---

## 3. Project Isolation & Access Control

- Every tool invocation verifies project existence using `verify_project_access(project_id, storage)`.
- Reconstructive operations and diffs are strictly scoped by `project_id`. A client cannot query commits or records belonging to another project.
- Relationships between records cannot link across different projects.

---

## 4. Protected Branches & Optimistic Concurrency

1. **Main Branch Protection:**
   - `barsa_propose_changes` explicitly rejects modifications targeting the `main` branch. Agents must submit proposals to feature branches (e.g., `feature/task-name`).
   - Mutations directly to `main` require `barsa_commit`, which enforces optimistic concurrency via `expected_head`.
2. **Stale Revision Detection:**
   - If two agents attempt to commit to the same branch concurrently, the agent with an out-of-date `expected_head` is rejected with `STALE_REVISION`, returning the current HEAD commit hash to allow the client to rebase or merge.
