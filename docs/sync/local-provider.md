# Local Filesystem BYOS Provider Guide

## 1. Overview

The `LocalFilesystemStorageAdapter` allows users to configure any locally accessible filesystem directory, USB external drive, Network Attached Storage (NAS), or mounted SMB/NFS share as a BYOS remote destination.

---

## 2. Configuration & Registration

### Via REST API
```bash
POST /api/v1/sync/projects/proj-123/remotes
Content-Type: application/json

{
  "name": "backup-drive",
  "provider_type": "local",
  "local_path": "E:/BarsaBackups/ProjectAlpha",
  "encryption_enabled": true
}
```

### Via Python SDK
```python
from barsa.sync.models import RemoteCreate, RemoteProviderType
from barsa.sync.service import SyncService

sync_service.create_remote(
    project_id="proj-123",
    req=RemoteCreate(
        name="nas-backup",
        provider_type=RemoteProviderType.LOCAL,
        local_path="//nas01/shared/barsa_repos/proj-123",
        encryption_enabled=False,
    ),
    principal_id="user-owner",
)
```

---

## 3. Directory Layout on Disk

When initialized, the local provider establishes the following standardized tree:

```
E:/BarsaBackups/ProjectAlpha/
├── metadata/
│   └── format-version.json          # Format version (e.g. {"format_version": "1.0"})
├── repository.json                  # Root repository manifest
├── manifests/                       # Historical manifests indexed by SHA-256
│   └── 3f8a4...json
├── refs/                            # Branch references containing commit hash & ETag
│   ├── main.json
│   └── feature-auth.json
└── objects/
    └── sha256/                      # 2-character fan-out directory structure
        ├── 0a/
        │   └── 0a1b2c3d4e5f...
        └── ff/
            └── ff98a7b6c5d4...
```

---

## 4. Atomic File Operations

To prevent data corruption during write interruptions or system power loss:
- All writes use an atomic two-stage write pattern:
  1. Data is written to a temporary sibling file `.tmp_<uuid>`.
  2. The file is atomically renamed (`os.replace` / `Path.replace`) to the target filename.
- If a write fails before completion, the temporary file is unlinked.

---

## 5. Security & Path Traversal Guards

The local adapter enforces strict path isolation:
- All hashes are verified against `^[0-9a-fA-F]{64}$`.
- Any relative component (`..`, `/`, `\`) in an object identifier triggers an immediate `ValueError`.
- Resolved paths are verified to remain strictly within `base_dir`.
