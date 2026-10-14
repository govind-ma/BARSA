# Dashboard API Integration Guide

This document maps all frontend dashboard interactions to their corresponding FastAPI backend endpoints.

---

## 1. Endpoint Mapping Matrix

| Dashboard Feature | HTTP Method | Backend URL | Description |
| :--- | :--- | :--- | :--- |
| **System Info** | `GET` | `/api/v1/info` | Retrieves version, environment, and FalkorDB status |
| **Health Check** | `GET` | `/health` | Loopback daemon availability |
| **List Workspaces** | `GET` | `/api/v1/workspaces` | Lists all accessible workspaces |
| **Create Workspace** | `POST` | `/api/v1/workspaces` | Creates a new workspace boundary |
| **Delete Workspace** | `DELETE` | `/api/v1/workspaces/{id}` | Permanently removes a workspace |
| **List Projects** | `GET` | `/api/v1/workspaces/{id}/projects` | Lists projects within a workspace |
| **Create Project** | `POST` | `/api/v1/workspaces/{id}/projects` | Adds a project to a workspace |
| **Get Project** | `GET` | `/api/v1/projects/{id}` | Retrieves project metadata |
| **Delete Project** | `DELETE` | `/api/v1/projects/{id}` | Deletes a project and its memory |
| **List Records** | `GET` | `/api/v1/projects/{id}/records` | Fetches BMS records (supports type filter) |
| **Validate Record** | `POST` | `/api/v1/bms/validate` | Validates candidate memory record against BMS schema |
| **Create Record** | `POST` | `/api/v1/projects/{id}/records` | Persists a validated BMS record |
| **List Commits** | `GET` | `/api/v1/projects/{id}/commits` | Retrieves immutable commit DAG history |
| **List Branches** | `GET` | `/api/v1/projects/{id}/branches` | Retrieves project branches |
| **Create Branch** | `POST` | `/api/v1/projects/{id}/branches` | Forks memory state into a new branch |
| **Diff Revisions** | `GET` | `/api/v1/projects/{id}/diff` | Field-level before/after diffs |
| **List Conflicts** | `GET` | `/api/v1/projects/{id}/conflicts` | Detects three-way merge divergence |
| **Merge Branches** | `POST` | `/api/v1/projects/{id}/merge` | Merges changes into target branch |
| **List Reviews** | `GET` | `/api/v1/projects/{id}/reviews` | Pull proposal reviews and comments |
| **Graph Overview** | `GET` | `/api/v1/graph/{id}/overview` | Node and edge counts from FalkorDB |
| **Get Subgraph** | `GET` | `/api/v1/graph/{id}/subgraph` | Local entity neighborhood with relations |
| **Rebuild Graph** | `POST` | `/api/v1/graph/{id}/rebuild` | Projects authoritative state into FalkorDB |
| **Resume Context** | `POST` | `/api/v1/context/{id}/resume` | Smart Context Engine optimized prompt generation |
| **List Agents** | `GET` | `/api/v1/coordination/agents` | Registered AI agent profiles and heartbeats |
| **Register Agent** | `POST` | `/api/v1/coordination/agents/register`| Adds an AI agent to the registry |
| **List Tasks** | `GET` | `/api/v1/coordination/tasks` | Coordination tasks across lifecycle states |
| **Create Task** | `POST` | `/api/v1/coordination/tasks` | Submits a new coordination task |
| **Claim Task** | `POST` | `/api/v1/coordination/tasks/{id}/claim` | Binds an agent to a task |
| **Current User** | `GET` | `/api/v1/security/auth/me` | Principal identity and clearance level |
| **Generate API Key**| `POST` | `/api/v1/security/agents/credentials` | Issues `barsa_ak_...` agent key |
| **List Audit Events**| `GET` | `/api/v1/security/audit` | Forensics log from `audit_events` |
| **Export Package** | `GET` | `/api/v1/projects/{id}/export` | Downloads portable BMS JSON package |
| **Import Package** | `POST` | `/api/v1/workspaces/{id}/import` | Validates and imports BMS JSON package |

---

## 2. Vite Proxy Configuration

In `frontend/vite.config.ts`, all `/api` and `/health` requests are proxied directly to the backend daemon:

```typescript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      secure: false,
    },
    '/health': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      secure: false,
    },
  },
}
```

---

## 3. Error Normalization

The typed `ApiClient` catches non-2xx HTTP responses, extracts the structured `{"detail": "..."}` payload emitted by FastAPI, and presents clean user-friendly alerts without crashing the UI.
