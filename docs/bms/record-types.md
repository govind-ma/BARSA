# BMS v0.1 Record Types Specification

BMS v0.1 defines 10 core record types. Every record inherits from `BMSRecord`, which mandates:
- `id`: Stable non-empty string identifier.
- `schema_version`: String matching supported versions (e.g. `"0.1"`).
- UTC timezone-aware datetimes.

---

## 1. Workspace (`record_type: "workspace"`)
Represents a user-controlled or team-controlled knowledge domain.
- `id` (string, required): Unique workspace ID.
- `name` (string, required): Workspace name.
- `owner_id` (string, required): Owner user ID or organization ID.
- `created_at` (datetime UTC, required): Creation timestamp.
- `schema_version` (string, required): `"0.1"`.
- `description` (string, optional): Contextual description.
- `metadata` (dict, optional): Custom attributes.

---

## 2. Project (`record_type: "project"`)
Represents an individual project within a workspace.
- `id` (string, required): Unique project ID.
- `workspace_id` (string, required): Parent workspace reference.
- `name` (string, required): Project title.
- `status` (enum, required): `active`, `paused`, `archived`, `completed`.
- `created_at`, `updated_at` (datetime UTC, required).
- `description` (string, optional).
- `goals` (list[string], optional): List of goals.
- `metadata` (dict, optional).

---

## 3. Knowledge Record (`record_type: "knowledge"`)
Represents an individual claim, concept, verified observation, or reference.
- `id` (string, required).
- `project_id` (string, required).
- `content` (string, required): Textual knowledge claim or markdown snippet.
- `knowledge_type` (enum, required): `fact`, `observation`, `hypothesis`, `reference`.
- `verification_status` (enum, required): `unverified`, `verified`, `disputed`, `superseded`.
- `created_by` (string, required): Author agent ID or user ID.
- `created_at` (datetime UTC, required).

---

## 4. Decision Record (`record_type: "decision"`)
Represents an architectural, technical, or business decision (ADR style).
- `id` (string, required).
- `project_id` (string, required).
- `title` (string, required): Decision title.
- `decision` (string, required): Description of the agreed choice.
- `rationale` (string, required): Justification.
- `status` (enum, required): `proposed`, `approved`, `rejected`, `superseded`.
- `created_by` (string, required).
- `created_at` (datetime UTC, required).
- `alternatives` (list[string], optional): Considered options.
- `evidence_refs` (list[string], optional): Supporting knowledge or artifact IDs.

---

## 5. Task Record (`record_type: "task"`)
Represents an actionable task or unit of work.
- `id` (string, required).
- `project_id` (string, required).
- `title` (string, required).
- `description` (string, optional).
- `status` (enum, required): `todo`, `in_progress`, `blocked`, `completed`, `cancelled`.
- `priority` (enum, required): `low`, `medium`, `high`, `critical`.
- `dependencies` (list[string], required): IDs of predecessor tasks (direct self-dependency strictly prohibited).
- `assigned_agent_id` (string or null, optional): Null when unassigned.
- `created_at`, `updated_at` (datetime UTC, required).

---

## 6. Agent Record (`record_type: "agent"`)
Represents an AI assistant, model runtime configuration, or collaborator.
- `id` (string, required).
- `name` (string, required).
- `provider` (string, required): Metadata provider name (`anthropic`, `openai`, `google`, `local`).
- `capabilities` (list[string], required): e.g. `['coding', 'architecture', 'review']`.
- `model` (string, optional): Specific model identifier (`claude-3-7-sonnet`, `gpt-4o`).
- `description` (string, optional).
- `metadata` (dict, optional).

---

## 7. Artifact Reference (`record_type: "artifact"`)
Pointers to local or remote files, datasets, or repositories.
- `id` (string, required).
- `project_id` (string, required).
- `artifact_type` (enum, required): `source_code`, `documentation`, `config`, `specification`, `dataset`, `image`, `model`, `other`.
- `uri` (string, required): Local relative path or remote URL.
- `content_hash` (string, optional): SHA-256 hash of content.
- `size_bytes` (int, optional).
- `media_type` (string, optional): MIME type.
- `repository_revision` (string, optional): Git commit SHA.

---

## 8. Relationship Record (`record_type: "relationship"`)
Graph-compatible directed edge between two records.
- `id` (string, required).
- `project_id` (string, required).
- `source_id` (string, required).
- `target_id` (string, required): Self-referencing prohibited.
- `relationship_type` (enum, required): `depends_on`, `implements`, `references`, `supersedes`, `created_by`, `related_to`, `supports`, `blocks`.

---

## 9. Resume Checkpoint (`record_type: "checkpoint"`)
Detailed in [checkpoint-spec.md](checkpoint-spec.md).

---

## 10. Memory Commit (`record_type: "commit"`)
Point-in-time state capture.
- `id` (string, required).
- `project_id` (string, required).
- `parent_commit_ids` (list[string], required).
- `author_id` (string, required).
- `message` (string, required).
- `created_at` (datetime UTC, required).
- `changes` (list of `CommitChange`, required):
  - `operation`: `create`, `update`, `delete`.
  - `record_id`: Target record ID.
  - `record_type`: Target type name.
  - `before_revision`, `after_revision` (string or null).
