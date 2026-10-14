# Barsa Memory Standard (BMS v0.1) Reference

Barsa working memory is structured into strictly validated, typed records defined in JSON Schema and Pydantic models. Agents must never invent fields or unsupported record types.

---

## 1. Supported Record Types

Every record must include:
- `id` (string): Unique identifier (e.g., `task-auth-01`, `dec-pkce-oauth`).
- `project_id` (string): Authoritative project ID to which the record belongs.
- `record_type` (string): Discriminator name matching the schemas below.
- `created_at` (string, ISO-8601 with timezone): e.g. `2026-10-14T14:30:00Z`. Naive timestamps are rejected.

### A. `task` (TaskRecord)
Tracks work units, execution state, priorities, and dependency linkages.
```json
{
  "id": "task-impl-oauth",
  "project_id": "proj-auth-engine",
  "record_type": "task",
  "title": "Implement S256 PKCE Code Verifier Validation",
  "description": "Cryptographic checks verifying code_challenge with code_verifier according to RFC 7636.",
  "status": "in_progress",
  "priority": "critical",
  "assigned_agent_id": "coding-agent",
  "dependencies": ["task-setup-db"],
  "created_at": "2026-10-14T14:00:00Z"
}
```
- **Allowed `status`:** `"todo"`, `"in_progress"`, `"blocked"`, `"completed"`, `"cancelled"`.
- **Allowed `priority`:** `"low"`, `"medium"`, `"high"`, `"critical"`.

---

### B. `decision` (DecisionRecord)
Records architectural, design, and technical decisions made during the project.
```json
{
  "id": "dec-pkce-oauth",
  "project_id": "proj-auth-engine",
  "record_type": "decision",
  "title": "Adopt PKCE for OAuth2 Authorization Code Flow",
  "decision": "Enforce S256 code challenge for all public and confidential clients.",
  "rationale": "Prevents code interception and code injection attacks per RFC 7636.",
  "status": "approved",
  "created_by": "claude-architect",
  "created_at": "2026-10-14T14:05:00Z"
}
```
- **Allowed `status`:** `"proposed"`, `"approved"`, `"rejected"`, `"superseded"`.

---

### C. `checkpoint` (ResumeCheckpoint)
Provides the primary bridge across sessions. Captures exactly where the last agent stopped.
```json
{
  "id": "cp-pkce-init",
  "project_id": "proj-auth-engine",
  "record_type": "checkpoint",
  "task_id": "task-impl-oauth",
  "status": "active",
  "completed_actions": [
    "Requirement review completed",
    "Decision dec-pkce-oauth approved"
  ],
  "pending_actions": [
    "Implement S256 verifier computation module",
    "Add RFC 7636 test vectors"
  ],
  "next_action": "Implement S256 verifier computation module in auth/pkce.py",
  "blockers": [],
  "decision_refs": ["dec-pkce-oauth"],
  "artifact_refs": [],
  "base_revision": "e7a852a323fc75f969876a8bed1f6cf97e163bfa8b8a86c19bebb9a523433bf8",
  "created_by": "claude-architect",
  "created_at": "2026-10-14T14:10:00Z"
}
```
- **Allowed `status`:** `"active"`, `"superseded"`, `"archived"`.

---

### D. `knowledge` (KnowledgeRecord)
Persistent project knowledge, external constraints, environment standards, or facts.
```json
{
  "id": "kn-token-ttl",
  "project_id": "proj-auth-engine",
  "record_type": "knowledge",
  "content": "Access tokens expire after 15 minutes; refresh tokens expire after 7 days.",
  "knowledge_type": "fact",
  "verification_status": "verified",
  "created_by": "security-reviewer",
  "created_at": "2026-10-14T14:15:00Z"
}
```
- **Allowed `knowledge_type`:** `"fact"`, `"constraint"`, `"observation"`, `"hypothesis"`, `"requirement"`.
- **Allowed `verification_status`:** `"unverified"`, `"verified"`, `"disputed"`, `"superseded"`.

---

### E. `artifact` (ArtifactReference)
Pointers to concrete files, source repositories, documentation, or binary hashes.
```json
{
  "id": "art-pkce-spec",
  "project_id": "proj-auth-engine",
  "record_type": "artifact",
  "name": "pkce_verifier.py",
  "artifact_type": "source_code",
  "path_or_uri": "src/auth/pkce.py",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "created_by": "coding-agent",
  "created_at": "2026-10-14T14:20:00Z"
}
```
- **Allowed `artifact_type`:** `"source_code"`, `"document"`, `"test_result"`, `"log"`, `"config"`, `"other"`.

---

## 2. Memory Classification Rules

Before committing memory:
1. **Never conflate facts with hypotheses:** Speculative model ideas must use `knowledge_type: "hypothesis"` and `verification_status: "unverified"`.
2. **User confirmation required for facts:** Only mark knowledge as `"verified"` if grounded in verified test execution or explicit user instruction.
3. **Decisions require rationale:** Every `decision` record must explain both the *decision* and the *rationale*.
