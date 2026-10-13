# SQLite Database Schema Specification

BARSA utilizes a schema-managed SQLite database with Write-Ahead Logging (`WAL`), foreign key enforcement (`PRAGMA foreign_keys = ON`), and an internal `schema_migrations` tracking table.

---

## 1. Relational Tables

### `schema_migrations`
Tracks database schema migration versions.
```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
```

### `workspaces`
Stores high-level workspace definitions.
```sql
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    description TEXT,
    data_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### `projects`
Stores projects belonging to workspaces.
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT,
    data_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX idx_projects_workspace ON projects(workspace_id);
```

### `bms_records`
Polymorphic storage for core BMS records (`knowledge`, `decision`, `task`, `agent`, `commit`).
```sql
CREATE TABLE bms_records (
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX idx_bms_records_type ON bms_records(project_id, record_type);
CREATE INDEX idx_bms_records_created ON bms_records(project_id, created_at);
```

### `checkpoints`
Dedicated storage for `ResumeCheckpoint` records with task-indexed queries.
```sql
CREATE TABLE checkpoints (
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    data_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX idx_checkpoints_task ON checkpoints(project_id, task_id);
CREATE INDEX idx_checkpoints_status ON checkpoints(project_id, status);
```

### `relationships`
Stores directed graph connections between records.
```sql
CREATE TABLE relationships (
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX idx_rel_source ON relationships(project_id, source_id);
CREATE INDEX idx_rel_target ON relationships(project_id, target_id);
CREATE INDEX idx_rel_type ON relationships(project_id, relationship_type);
```

### `artifact_metadata`
Stores metadata and content hashes for external or local files.
```sql
CREATE TABLE artifact_metadata (
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    uri TEXT NOT NULL,
    content_hash TEXT,
    size_bytes INTEGER,
    media_type TEXT,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX idx_artifact_hash ON artifact_metadata(content_hash);
```
