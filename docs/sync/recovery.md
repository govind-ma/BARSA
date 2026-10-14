# Disaster Recovery and Data Integrity

## 1. Threat Scenarios & Mitigations

| Threat | System Detection Mechanism | Recovery Procedure |
|:---|:---|:---|
| **Local Disk Corruption / Loss** | Local database unreadable or lost | Fresh install -> Register BYOS Remote -> Pull full project history |
| **Tampered Cloud Storage Object** | SHA-256 CAS hash mismatch on download | Adapter rejects corrupted payload; reverts to cached replica or local commit |
| **Interrupted Sync Transfer** | Partial file write or network timeout | Atomic `.tmp_<uuid>` writes discarded; branch ref unchanged until all objects uploaded |
| **Lost Remote Credentials** | S3 access key expired or rotated | Update remote config via `/api/v1/sync/projects/{id}/remotes/{id}` |

---

## 2. Reconstructing State from a Fresh Environment

When setting up a replacement device or moving to a new cloud VM:

```bash
# 1. Start clean BARSA instance
# 2. Register existing BYOS remote
POST /api/v1/sync/projects/proj-123/remotes
{
  "name": "origin",
  "provider_type": "s3",
  "s3_bucket_name": "company-barsa-storage",
  "s3_prefix": "proj-123",
  "encryption_enabled": true
}

# 3. Pull all branches and content-addressed objects
POST /api/v1/sync/projects/proj-123/remotes/rem-abc/pull
{
  "branch_name": "main",
  "passphrase": "YourDecryptionPassphrase"
}
```

The pull process:
1. Re-creates all historical commits in `commits` and `commit_parents`.
2. Populates `commit_record_states` for historical time-travel.
3. Synchronizes the active records in `bms_records` and `checkpoints`.
4. Rebuilds the FalkorDB knowledge graph projection.

---

## 3. Data Integrity Verification

At any time, run integrity checks on local and remote storage:
- **Local SQLite**: `PRAGMA integrity_check;` and `PRAGMA foreign_key_check;`.
- **CAS Objects**: Every object is verified against its SHA-256 identifier upon retrieval.
- **Commits**: Every commit's state hash (`resulting_state_hash`) is recomputed from the constituent record state dictionary.
