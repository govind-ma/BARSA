# Barsa Authorization & RBAC Architecture

This document describes the role-based and attribute-based access control engine implemented in **BARSA**, governed by the `CentralAuthorizer`.

---

## 1. Role-Based Access Control (RBAC) Matrix

Barsa provides five hierarchical workspace roles:

| Action / Permission | Viewer | Reviewer | Editor | Admin | Owner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `memory:read` / `project:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `artifact:read` / `graph:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `review:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `review:create` / `review:comment` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `memory:write` / `memory:commit` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `artifact:write` / `coordination:claim` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `branch:create` / `branch:merge` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `project:create` / `project:delete` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `member:manage` / `agent:create` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `policy:manage` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `workspace:*` (Ownership Transfer / Delete) | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 2. Sensitivity Classification & Clearance Levels

All project memories, commits, and artifacts can be tagged with an optional `sensitivity` classification level:

```mermaid
graph LR
    P["1. Public"] --> I["2. Internal"]
    I --> C["3. Confidential"]
    C --> R["4. Restricted"]
```

### Clearance Rules:
- An authenticated principal has a maximum sensitivity clearance (e.g., `internal`, `confidential`, `restricted`).
- Superusers default to `restricted` clearance.
- Regular principals with clearance `X` may only read or write records with sensitivity level `Y <= X`.
- Access to records with sensitivity `Y > X` is rejected with `403 Forbidden` (`INSUFFICIENT_CLEARANCE`).

---

## 3. Central Authorization Decision Flow

```mermaid
flowchart TD
    Start(["Client Action Request"]) --> SuperUser{"Is Superuser?"}
    SuperUser -- Yes --> ClearSens{"Sensitivity Check Passes?"}
    ClearSens -- Yes --> Allow(["Allow Action"])
    ClearSens -- No --> DenySens(["Deny: Insufficient Clearance"])

    SuperUser -- No --> CheckScope{"Has Required Agent Scope?\n(memory:read, memory:commit, etc.)"}
    CheckScope -- No --> DenyScope(["Deny: Missing Agent Scope"])
    CheckScope -- Yes --> CheckProjLimit{"Is Project in Agent\nAllowed Projects List?"}
    CheckProjLimit -- No --> DenyProj(["Deny: Project Not in Agent Allowlist"])
    CheckProjLimit -- Yes --> CheckGrant{"Has Specific Project Grant?"}

    CheckGrant -- Yes --> EvalGrantRole{"Does Project Role\nPermit Action?"}
    CheckGrant -- No --> CheckWorkspace{"Has Workspace Membership?"}

    CheckWorkspace -- No --> DenyMember(["Deny: No Workspace Access"])
    CheckWorkspace -- Yes --> EvalWsRole{"Does Workspace Role\nPermit Action?"}

    EvalGrantRole -- Yes --> ClearSens
    EvalGrantRole -- No --> DenyRole(["Deny: Role Does Not Permit Action"])

    EvalWsRole -- Yes --> ClearSens
    EvalWsRole -- No --> DenyRole
```

---

## 4. Project-Level Grants

While a workspace provides default role memberships across all contained projects, specific projects can have explicit overrides via `project_grants`:
- **Read-Only Narrowing:** A workspace `editor` can be restricted to `viewer` on a critical audit project.
- **Selective Escalation:** A workspace `reviewer` can be granted `editor` privileges on a designated sandbox project without granting broader workspace edit permissions.

---

## 5. Scope Bounds for AI Agents

For AI agents, authorization enforces a strict **two-key validation**:
1. The agent must possess a workspace role (or project grant) permitting the action.
2. The agent's issued credential must explicitly include the capability scope (e.g., `Scope.MEMORY_COMMIT`).

Even if an agent is granted `editor` in a workspace, if its issued API key only holds `Scope.MEMORY_READ`, any attempt to commit memory is denied.
