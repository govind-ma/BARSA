# BARSA Remote Repository Format Specification

## 1. Specification Version

- **Format Version**: `1.0`
- **Engine**: `barsa-sync`
- **Standard**: BMS (Barsa Memory Standard v0.1)

---

## 2. Directory & Key Hierarchy

Every remote BARSA repository adheres strictly to this layout:

```
<root>/
├── metadata/
│   └── format-version.json
├── repository.json
├── manifests/
│   └── <manifest_sha256>.json
├── refs/
│   └── <branch_name>.json
└── objects/
    └── sha256/
        └── <hash[:2]>/
            └── <hash>
```

---

## 3. File Schema Definitions

### 3.1 `metadata/format-version.json`
Ensures engine compatibility across different versions:
```json
{
  "format_version": "1.0",
  "engine": "barsa-sync",
  "initialized_at": "2026-10-15T00:00:00Z"
}
```

### 3.2 `repository.json`
Root repository manifest providing high-level project metadata:
```json
{
  "format_version": "1.0",
  "repository_id": "repo-proj-mars-rover",
  "project_id": "proj-mars-rover",
  "encryption_enabled": true,
  "encryption_algorithm": "AES-256-GCM",
  "branches": {
    "main": "d0f0ad0a466737c487158d87441cb8c0c91c366fb300582c411299120df93a2e",
    "feature-sampling": "a85bf7fe0a652024de69484fb465808e9b3e3c932252675298c29abcb360d92c"
  },
  "objects_count": 48,
  "total_bytes": 142850,
  "created_at": "2026-10-15T00:00:00Z",
  "updated_at": "2026-10-15T00:05:00Z"
}
```

### 3.3 `refs/<branch_name>.json`
Mutable pointer referencing the branch's tip commit:
```json
{
  "branch_name": "main",
  "commit_id": "d0f0ad0a466737c487158d87441cb8c0c91c366fb300582c411299120df93a2e",
  "updated_at": "2026-10-15T00:05:00Z"
}
```

### 3.4 `objects/sha256/<hash[:2]>/<hash>`
Immutable Content-Addressed objects. Objects are stored under a two-character prefix directory to optimize filesystem inode performance and prevent directory traversal limits.

#### Commit Object Payload
```json
{
  "author_id": "agent-curiosity",
  "author_type": "agent",
  "bms_version": "0.1",
  "changes": [
    {
      "after_hash": "3153be2f0f68423ab160fe1a623b0212266efb9d215ab00a1f9740f59824fb54",
      "after_state": {
        "content": "Gale Crater has high basalt concentration and loose sand dunes.",
        "created_at": "2026-10-15T00:00:00Z",
        "created_by": "agent-curiosity",
        "id": "fact-terrain-01",
        "knowledge_type": "fact",
        "project_id": "proj-mars-rover",
        "record_type": "knowledge",
        "schema_version": "0.1",
        "verification_status": "unverified"
      },
      "before_hash": null,
      "before_state": null,
      "operation": "create",
      "record_id": "fact-terrain-01",
      "record_type": "knowledge"
    }
  ],
  "created_at": "2026-10-15T00:00:00Z",
  "message": "Sol 142 traverse complete",
  "metadata": {},
  "parent_commit_ids": [],
  "project_id": "proj-mars-rover",
  "resulting_state_hash": "7d1ed45152d72f953c1958c0b8d2cca18165a9fa7fc82ab19ace03c90d86faf4"
}
```
