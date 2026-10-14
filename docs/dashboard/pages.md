# Barsa Web Dashboard Pages Specification

This document provides a breakdown of each routed page implemented in the Barsa Web Dashboard.

---

## 1. Overview Dashboard (`/`)
- **Component:** `features/dashboard/DashboardHome.tsx`
- **Purpose:** System-wide operational summary.
- **Key Metrics:**
  - Active workspace name and ID
  - Connected AI agents and active status
  - Version commits recorded in active project
  - FalkorDB knowledge graph node and relationship counts
  - Running and blocked multi-agent tasks
  - Unresolved merge conflicts warning banner
  - Storage provider and BMS version info
- **Primary Actions:** One-click "Resume Context" button to launch context generation for the active project.

---

## 2. Workspaces (`/workspaces`)
- **Component:** `features/workspaces/WorkspacesPage.tsx`
- **Purpose:** Manage organizational memory boundaries.
- **Capabilities:**
  - List all accessible workspaces
  - Create new workspace modal with validation
  - Switch active workspace
  - Delete workspace with permanent deletion confirmation warning

---

## 3. Projects & Project Detail (`/projects` & `/projects/:projectId`)
- **Components:** `features/projects/ProjectsPage.tsx`, `ProjectDetailPage.tsx`
- **Capabilities:**
  - Create project within active workspace
  - Detailed project status: goals, description, creation date, status badges
  - Latest approved commit and checkpoint summary
  - Pending tasks and blockers
  - Important architectural decision log
  - **Resume Context Engine Integration:** Calls `POST /api/v1/context/{id}/resume` with configurable token budget (e.g. 8000 tokens), displays token counts and compression ratios, and provides a 1-click "Copy Prompt" action for AI agent handoff.
  - Export BMS project memory container (.json).

---

## 4. Structured Memory Explorer (`/memory`)
- **Component:** `features/memory/MemoryExplorerPage.tsx`
- **Capabilities:**
  - Full-text search by title, summary, or record ID
  - Filter by record type: `task`, `requirement`, `decision`, `context`, `constraint`, `knowledge`, `checkpoint`, `agent`
  - Filter by verification status: `verified`, `unverified`, `inconclusive`, `refuted`
  - Detail pane displaying JSON content, tags, attributes, and revision count
  - Create new record with **real-time BMS schema validation** (`POST /api/v1/bms/validate`) before persisting to SQLite.

---

## 5. Git-Style Version Control (`/version-control`)
- **Component:** `features/versioning/VersionControlPage.tsx`
- **Capabilities:**
  - **Commit History:** Inspect immutable commit DAG, author metadata, and commit timestamps
  - **Structured Diffs:** Field-level before/after changes against parent commits
  - **Branches:** List existing branches, create new feature branches, view default branch
  - **Reviews & Pull Proposals:** Review source/target branch proposals, comments, and approvals
  - **Conflict Inspector:** Three-way merge conflict visualizer displaying base value, source value, target value, and resolution state.

---

## 6. Knowledge Graph Explorer (`/graph`)
- **Component:** `features/graph/GraphExplorerPage.tsx`
- **Capabilities:**
  - Interactive SVG canvas with zoom, pan, and node dragging
  - Color-coded node entities: Project, Task, Requirement, Decision, Knowledge, Checkpoint, Agent, Artifact
  - Edge relations: `DEPENDS_ON`, `IMPLEMENTS`, `REFERENCES`, `SUPPORTS`, `BLOCKS`, `SUPERSEDES`, `CREATED_BY`
  - Node Inspector Panel: Entity properties, metadata, and connected incoming/outgoing relationships
  - Search and filter by entity type
  - **Accessible Table Alternative View:** Full HTML table for screen readers and tabular data review
  - FalkorDB status banner and "Rebuild Projection" trigger.

---

## 7. Agent Registry (`/agents`)
- **Component:** `features/agents/AgentsPage.tsx`
- **Capabilities:**
  - Grid of registered AI agents (Claude, GPT-4, Local Copilot)
  - Distinguishes claimed capabilities from verified capabilities
  - Supported tools and assigned task workloads
  - Live heartbeat timestamps and connection indicators
  - Register new agent modal.

---

## 8. Multi-Agent Coordination Board (`/tasks`)
- **Component:** `features/coordination/TasksPage.tsx`
- **Capabilities:**
  - 6-column Kanban task board matching Phase 9 lifecycle:
    `Pending` | `Ready` | `Running` | `Blocked` | `Under Review` | `Completed`
  - Task cards displaying priority, required capabilities, and assigned agent
  - Inspect task details modal with dependencies and blockers
  - Manual claim task action binding an agent to a pending task.

---

## 9. Security & Access Control (`/security`)
- **Component:** `features/security/SecurityPage.tsx`
- **Capabilities:**
  - Display authenticated principal profile, clearance level, and superuser status
  - **Issue Agent API Key:** Generates cryptographically random `barsa_ak_...` key. Displays raw secret key **only once** with security warning.
  - Immutable Security Audit Log: Displays append-only audit events from SQLite with timestamps, actors, event types, and sanitized details.

---

## 10. Storage & Portable Packages (`/storage`)
- **Component:** `features/storage/StoragePage.tsx`
- **Capabilities:**
  - Local-first SQLite database health and WAL mode status
  - Export project memory container as portable BMS JSON
  - Import BMS package with file upload or JSON paste, validation check, and workspace insertion.

---

## 11. Settings & Diagnostics (`/settings`)
- **Component:** `features/settings/SettingsPage.tsx`
- **Capabilities:**
  - Toggle light/dark interface theme
  - Local daemon configuration, loopback bindings, and BMS specification version.
