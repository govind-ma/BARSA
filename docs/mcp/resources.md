# Barsa MCP Resources & Prompts Reference

The Barsa MCP server registers **5 read-only resources** and **3 guided prompts** for standard AI client introspection.

---

## 1. Read-Only Resources Catalog

All resources are accessible via the `read_resource` protocol method and provide standardized JSON output.

### 1. `barsa://system/info`
- **MIME Type:** `application/json`
- **Purpose:** Exposes current server engine details, active backend storage type, and graph database status.
- **Example Content:**
  ```json
  {
    "application": "BARSA",
    "version": "0.1.0",
    "environment": "development",
    "storage_provider": "local",
    "graph_enabled": true,
    "graph_provider": "falkordb",
    "graph_available": true
  }
  ```

---

### 2. `barsa://bms/schema/version`
- **MIME Type:** `text/plain`
- **Purpose:** Returns the current supported Barsa Memory Standard semantic version.
- **Example Content:**
  ```text
  0.1.0
  ```

---

### 3. `barsa://bms/schema/records`
- **MIME Type:** `application/json`
- **Purpose:** Full in-memory JSON Schema definitions generated directly from Pydantic models for all BMS record types (`project`, `task`, `decision`, `knowledge`, `artifact`, `relationship`, `checkpoint`, and `package`).
- **Use Case:** AI models can inspect exact field definitions, enumerations, and validation requirements before constructing change payloads.

---

### 4. `barsa://projects/{project_id}/overview`
- **MIME Type:** `application/json`
- **Purpose:** Dynamic resource providing project identity, workspace ID, current lifecycle status, and current main commit hash.
- **Example Content:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "project_name": "OAuth2 Auth Engine",
    "workspace_id": "ws-demo-1",
    "status": "active",
    "description": "High-security OAuth2 microservice with PKCE support",
    "head_commit": "3541330462f338fdc4e8879f1a2788c876b776d85159e58002800953dd2494dd"
  }
  ```

---

### 5. `barsa://projects/{project_id}/checkpoints/latest`
- **MIME Type:** `application/json`
- **Purpose:** Returns the most recently updated checkpoint record for the specified project.
- **Example Content:**
  ```json
  {
    "project_id": "proj-auth-engine",
    "latest_checkpoint": {
      "id": "cp-pkce-init",
      "task_id": "task-implement-pkce",
      "status": "active",
      "completed_actions": ["Requirement and security RFC review completed"],
      "pending_actions": ["Implement S256 verifier computation module"],
      "next_action": "Implement S256 verifier computation module in auth/pkce.py",
      "created_by": "claude-architect",
      "created_at": "2026-10-14T14:05:00Z"
    }
  }
  ```

---

## 2. Standard Guided Prompts

MCP prompts give AI clients structured starting prompts to guide users through standard memory workflows.

### 1. `barsa_resume_project`
- **Arguments:** `project_id` (string, required), `task_id` (string, optional)
- **Role:** `user`
- **Prompt Text:**
  > "You are resuming work on Barsa project '{project_id}'. First, inspect the latest checkpoint and active task using `barsa_get_checkpoint` or `barsa_resume`. Review the completed actions, blockers, and next action. Then proceed with the task and commit your progress when finished."

---

### 2. `barsa_save_checkpoint`
- **Arguments:** `project_id` (string, required), `task_id` (string, required), `summary` (string, required)
- **Role:** `user`
- **Prompt Text:**
  > "Create a new Barsa resume checkpoint for project '{project_id}' and task '{task_id}'. Summary: '{summary}'. Ensure all completed actions, remaining pending actions, and the single immediate next action are clearly documented according to BMS v0.1 format, and commit it to the main branch."

---

### 3. `barsa_review_changes`
- **Arguments:** `project_id` (string, required), `branch` (string, required), `base_commit` (string, optional)
- **Role:** `user`
- **Prompt Text:**
  > "Review the proposed changes on branch '{branch}' against base commit '{base_commit}' for project '{project_id}'. Call `barsa_get_diff` and `barsa_list_conflicts` to inspect record-level modifications and detect potential collisions."
