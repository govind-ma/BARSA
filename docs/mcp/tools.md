# Barsa MCP Tools Reference

The Barsa MCP server registers **12 standard tools** providing safe, version-controlled, and validated access to project memory.

---

## Tool Catalog Summary

| Tool Name | Operation Type | Purpose |
| :--- | :--- | :--- |
| `barsa_list_projects` | Read | List accessible projects with main branch commit status |
| `barsa_get_project` | Read | Retrieve project metadata, summary counts, and HEAD commit |
| `barsa_search_memory` | Read | Substring & attribute search across records with graph status |
| `barsa_get_memory` | Read | Fetch exact record or historical snapshot at a commit |
| `barsa_get_checkpoint` | Read | Retrieve latest or specific task resume checkpoint |
| `barsa_resume` | Read | Acquire complete structured context package to continue work |
| `barsa_get_history` | Read | Inspect commit DAG history on a branch |
| `barsa_get_diff` | Read | Compare record-level differences between two commits |
| `barsa_propose_changes` | Write (Branch) | Validate BMS records & commit to an isolated feature branch |
| `barsa_commit` | Write (Main/Branch) | Commit validated changes with optimistic concurrency |
| `barsa_list_conflicts` | Read | Identify divergent branches and potential merge conflicts |
| `barsa_get_graph_context` | Read | Explore task dependencies and graph projection freshness |

---

## Detailed Tool Specifications

### 1. `barsa_list_projects`
- **Description:** Lists projects accessible to the current local identity.
- **Parameters:**
  - `workspace_id` (string, optional): Filter by workspace.
  - `limit` (integer, default: 50, max: 100): Pagination limit.
  - `offset` (integer, default: 0): Pagination offset.
- **Response:**
  ```json
  {
    "projects": [
      {
        "project_id": "proj-auth-engine",
        "project_name": "OAuth2 Auth Engine",
        "workspace_id": "ws-demo-1",
        "status": "active",
        "description": "...",
        "latest_main_commit": "35413304...",
        "created_at": "2026-10-14T14:00:00Z"
      }
    ],
    "total_count": 1,
    "limit": 50,
    "offset": 0
  }
  ```

---

### 2. `barsa_get_project`
- **Description:** Retrieve comprehensive overview of a project including total record count and HEAD commit.
- **Parameters:**
  - `project_id` (string, required): Target project ID.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "project_name": "OAuth2 Auth Engine",
    "workspace_id": "ws-demo-1",
    "status": "active",
    "description": "...",
    "current_main_commit": "35413304...",
    "total_records_count": 8,
    "created_at": "2026-10-14T14:00:00Z",
    "metadata": {}
  }
  ```

---

### 3. `barsa_search_memory`
- **Description:** Search structured records and graph entities by keyword and attribute matching.
- **Parameters:**
  - `project_id` (string, required): Project identifier.
  - `query` (string, required): Search query (minimum 1 non-whitespace char).
  - `record_types` (list of strings, optional): Filter by BMS record types (`task`, `decision`, `knowledge`, `artifact`, `checkpoint`).
  - `limit` (integer, default: 20, max: 50): Number of matches to return.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "query": "pkce",
    "matches": [
      {
        "record_id": "dec-pkce-oauth",
        "record_type": "decision",
        "excerpt": "Adopt PKCE for OAuth2 Authorization Code Flow...",
        "properties": {"title": "Adopt PKCE", "status": "approved"},
        "created_at": "2026-10-14T14:05:00Z"
      }
    ],
    "total_matches": 1,
    "applied_graph_commit": "35413304...",
    "applied_graph_revision": 3,
    "retrieval_limitations": "Substring/attribute matching across record storage and graph index."
  }
  ```

---

### 4. `barsa_get_memory`
- **Description:** Retrieve an exact memory record by ID, or time-travel to inspect its historical state at a specific commit.
- **Parameters:**
  - `project_id` (string, required): Project identifier.
  - `record_id` (string, required): Unique record ID.
  - `commit_id` (string, optional): Specific commit SHA-256 for historical state.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "record_id": "task-implement-pkce",
    "commit_id": "35413304...",
    "record": {
      "id": "task-implement-pkce",
      "project_id": "proj-auth-engine",
      "record_type": "task",
      "title": "Implement S256 PKCE Code Verifier Validation",
      "status": "in_progress",
      "priority": "critical"
    }
  }
  ```

---

### 5. `barsa_get_checkpoint`
- **Description:** Retrieve the latest relevant resume checkpoint for a project or specific task.
- **Parameters:**
  - `project_id` (string, required): Project ID.
  - `task_id` (string, optional): Specific task ID.
  - `checkpoint_id` (string, optional): Specific checkpoint ID.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "checkpoint_id": "cp-pkce-init",
    "task_id": "task-implement-pkce",
    "status": "active",
    "completed_actions": ["RFC review completed", "Decision dec-pkce-oauth approved"],
    "pending_actions": ["Implement S256 verifier computation module"],
    "next_action": "Implement S256 verifier computation module in auth/pkce.py",
    "blockers": [],
    "decision_refs": ["dec-pkce-oauth"],
    "artifact_refs": [],
    "base_revision": "e7a852...",
    "created_by": "claude-architect",
    "created_at": "2026-10-14T14:05:00Z"
  }
  ```

---

### 6. `barsa_resume`
- **Description:** Constructs the full structured context package needed for an AI agent to continue work.
- **Parameters:**
  - `project_id` (string, required): Project identifier.
  - `task_id` (string, optional): Target task to resume (defaults to first active task).
  - `max_context_tokens` (integer, optional): Token budget guidance.
  - `expected_revision` (string, optional): Verifies client's cached revision matches authoritative HEAD.
- **Response:**
  ```json
  {
    "project_identity": {"project_id": "proj-auth-engine", "status": "active"},
    "authoritative_revision": "35413304...",
    "revision_warning": null,
    "current_task": {"id": "task-implement-pkce", "status": "in_progress"},
    "latest_checkpoint": {"checkpoint_id": "cp-pkce-init", "next_action": "..."},
    "relevant_decisions": [...],
    "requirements": [...],
    "dependencies": [...],
    "artifacts": [...],
    "blockers": [],
    "instructions": "Review next_action in latest_checkpoint and relevant_decisions before proceeding."
  }
  ```

---

### 7. `barsa_get_history`
- **Description:** Retrieve Git-style commit DAG history for a branch.
- **Parameters:**
  - `project_id` (string, required): Project identifier.
  - `branch` (string, default: "main"): Branch name.
  - `limit` (integer, default: 50): Number of commits to return.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "branch": "main",
    "commits": [
      {
        "commit_id": "35413304...",
        "author_id": "claude-architect",
        "message": "feat(auth): specify PKCE architecture and initial task checkpoint",
        "parent_commit_ids": ["e7a852a3..."],
        "resulting_state_hash": "a1b2...",
        "created_at": "2026-10-14T14:10:00Z",
        "change_count": 3
      }
    ],
    "total_returned": 1
  }
  ```

---

### 8. `barsa_get_diff`
- **Description:** Compute deterministic, record-level differences between two commits.
- **Parameters:**
  - `project_id` (string, required): Project identifier.
  - `from_commit` (string, required): Base commit SHA-256.
  - `to_commit` (string, required): Target commit SHA-256.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "from_commit": "e7a852a3...",
    "to_commit": "35413304...",
    "diff": {
      "from_commit_id": "e7a852a3...",
      "to_commit_id": "35413304...",
      "project_id": "proj-auth-engine",
      "added_records": ["cp-pkce-init", "dec-pkce-oauth", "task-implement-pkce"],
      "removed_records": [],
      "modified_records": [],
      "changes": [...]
    }
  }
  ```

---

### 9. `barsa_propose_changes`
- **Description:** Validates BMS records against schemas and commits to an isolated feature branch without modifying `main`.
- **Parameters:**
  - `project_id` (string, required): Project ID.
  - `branch` (string, required): Feature branch name (e.g., `feature/pkce`). Must NOT be `main`.
  - `base_commit` (string, required): Commit from which the branch begins.
  - `changes` (list of change dicts, required): Array of mutations `{operation, record_id, record_type, after_state}`.
  - `message` (string, required): Proposal summary message.
- **Response:**
  ```json
  {
    "proposal_id": "feature/pkce-spec",
    "project_id": "proj-auth-engine",
    "branch": "feature/pkce-spec",
    "base_commit": "e7a852a3...",
    "commit_id": "e8a64d7e...",
    "status": "PROPOSED",
    "validation_results": [{"index": 0, "record_id": "dec-pkce-oauth", "valid": true}],
    "change_count": 3
  }
  ```

---

### 10. `barsa_commit`
- **Description:** Atomically commit validated changes directly to a branch (such as `main`). Includes optimistic concurrency control (`expected_head`). Proactively projects changes to knowledge graph outbox.
- **Parameters:**
  - `project_id` (string, required): Project ID.
  - `branch` (string, default: "main"): Target branch.
  - `expected_head` (string, optional): HEAD commit SHA-256 expected by caller.
  - `changes` (list of change dicts, required): Validated BMS changes.
  - `message` (string, required): Commit explanation.
  - `operation_id` (string, optional): Client operation identifier for idempotency.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "branch": "main",
    "commit_id": "35413304...",
    "resulting_state_hash": "a1b2c3...",
    "author_id": "govin",
    "change_count": 3,
    "status": "COMMITTED"
  }
  ```

---

### 11. `barsa_list_conflicts`
- **Description:** Check for unmerged branches and divergence against the current `main` branch.
- **Parameters:**
  - `project_id` (string, required): Project ID.
  - `status` (string, optional): Unused / reserved for future conflict lifecycle states.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "main_head": "35413304...",
    "divergent_branches": [
      {
        "branch": "feature/pkce-spec",
        "branch_head": "e8a64d7e...",
        "main_head": "35413304...",
        "potential_conflict": false,
        "divergent_changes_count": 3
      }
    ],
    "total_conflicts": 1
  }
  ```

---

### 12. `barsa_get_graph_context`
- **Description:** Retrieve multi-hop graph neighbors, dependency chains, blockers, and projection freshness.
- **Parameters:**
  - `project_id` (string, required): Project ID.
  - `task_id` (string, optional): Target task for dependency traversal.
  - `depth` (integer, default: 2, max: 5): Maximum traversal depth.
  - `limit` (integer, default: 50, max: 100): Result count.
- **Response:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "task_id": "task-implement-pkce",
    "dependencies": [],
    "blockers": [],
    "connected_neighbors": [...],
    "freshness": {
      "is_available": true,
      "provider": "in_memory",
      "is_fresh": true,
      "applied_commit_id": "35413304...",
      "lag_commits_count": 0,
      "node_count": 6,
      "relationship_count": 7
    }
  }
  ```
