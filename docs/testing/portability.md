# Memory Portability & Storage Independence Testing

BARSA memory packages adhere to the Barsa Memory Standard (BMS v0.1) specification, ensuring that project state can be exported, transported, and restored across completely isolated storage systems without loss of data integrity or version provenance.

## Portability Verification Workflow

```
┌─────────────────────────────────┐
│     Source Storage (A)          │
│ SQLite Instance / Remote DB     │
└────────────────┬────────────────┘
                 │
                 ▼ export_package(project_id)
┌─────────────────────────────────┐
│      BMS Memory Package         │
│  - schema_version: "0.1"        │
│  - manifest: records, DAG, art  │
│  - checksums / cryptographic    │
└────────────────┬────────────────┘
                 │
                 ▼ import_package(package)
┌─────────────────────────────────┐
│     Target Storage (B)          │
│ Completely Isolated Storage     │
└─────────────────────────────────┘
```

## Tested Invariants in `test_bms_portability.py`

1. **Lossless Record Roundtrip:**
   All tasks, decisions, knowledge entries, artifact references, and checkpoints retain identical primary keys, field data, and timestamps after import.
2. **DAG Structure Preservation:**
   Commits, parents, and resulting state hashes match exactly between Source Storage A and Target Storage B.
3. **Collision Detection:**
   Importing the same package into an existing project raises a descriptive `ConflictError` to prevent accidental overwrites.
4. **Corrupt Package Rejection:**
   Packages with tampered JSON payloads, missing mandatory BMS headers, or malformed schema versions fail validation cleanly before altering any database records.
