# Backup and Recovery Guide

## 1. Safe Backups with SQLite WAL Mode

Simply copying `barsa.db` while active processes are writing can result in a corrupted snapshot because modified pages reside in the `barsa.db-wal` journal file.

BARSA creates transactional, point-in-time backups using the SQLite `VACUUM INTO` command:
1. SQLite safely flushes pending WAL frames into an isolated checkpoint snapshot.
2. The snapshot database, metadata manifest (`manifest.json`), and content-addressed blobs are compressed into a `.tar.gz` archive.
3. The backup file is written to `{data_dir}/backups/barsa_backup_YYYYMMDD_HHMMSS.tar.gz`.

---

## 2. Recovery Process

To restore from a backup:
```python
from barsa.core.config import get_settings
from barsa.storage.backup import restore_backup

settings = get_settings()
restore_backup(settings, backup_file_path, confirm_overwrite=True)
```

### Safety Guarantees during Restore:
- **Manifest Verification:** Verifies the archive structure and format.
- **Database Integrity Check:** Runs `PRAGMA integrity_check` on the extracted database before replacing the active database.
- **WAL Journal Cleanup:** Unlinks leftover `.db-wal` and `.db-shm` files to prevent stale state overlay.
- **Explicit Confirmation:** Fails immediately unless `confirm_overwrite=True` is provided.

---

## 3. Failure Recovery Scope

| Failure Mode | Recoverable? | Explanation |
|---|---|---|
| Process crash / sudden power loss | Yes | SQLite WAL automatically recovers uncommitted transactions on next startup |
| Concurrent update race condition | Yes | Handled by optimistic locking; client retries with latest revision |
| Corrupted database file on disk | Yes | Restore from the latest `.tar.gz` backup archive |
| Physical hard drive catastrophic failure | Partial | Requires user to have copied the `.tar.gz` backups to an external disk or cloud backup |
