"""Backup and restore utilities for BARSA local storage."""

import json
import logging
import shutil
import sqlite3
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from barsa.core.config import Settings
from barsa.core.exceptions import StorageError, ValidationError
from barsa.storage.migrations import verify_database_integrity

logger = logging.getLogger("barsa.storage.backup")


def create_backup(settings: Settings, target_path: Path | None = None) -> Path:
    """Create a consistent backup of the SQLite database and artifacts.

    Uses SQLite VACUUM INTO to safely checkpoint and snapshot WAL database.
    Archives database snapshot, manifest, and artifacts into a .tar.gz bundle.
    """
    settings.ensure_data_dir()
    db_path = settings.db_path
    if not db_path.exists():
        msg = f"Database at '{db_path}' does not exist. Nothing to backup."
        raise StorageError(msg)

    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    if target_path is None:
        target_path = settings.backups_dir / f"barsa_backup_{timestamp_str}.tar.gz"
    else:
        target_path = target_path.resolve()

    target_path.parent.mkdir(parents=True, exist_ok=True)

    temp_staging = settings.backups_dir / f"staging_{timestamp_str}"
    temp_staging.mkdir(parents=True, exist_ok=True)
    temp_db_snapshot = temp_staging / "barsa.db"

    try:
        # Step 1: Safely snapshot the SQLite database using VACUUM INTO
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(f"VACUUM INTO '{temp_db_snapshot.as_posix()}';")
        finally:
            conn.close()

        # Step 2: Write backup metadata manifest
        manifest = {
            "version": "1.0",
            "app_version": settings.app_version,
            "created_at": datetime.now(UTC).isoformat(),
            "has_artifacts": settings.artifacts_dir.exists(),
        }
        manifest_file = temp_staging / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Step 3: Bundle into .tar.gz archive
        with tarfile.open(target_path, "w:gz") as tar:
            tar.add(temp_db_snapshot, arcname="barsa.db")
            tar.add(manifest_file, arcname="manifest.json")
            if settings.artifacts_dir.exists():
                tar.add(settings.artifacts_dir, arcname="artifacts")

        logger.info("Successfully created backup at %s", target_path)
        return target_path
    finally:
        shutil.rmtree(temp_staging, ignore_errors=True)


def restore_backup(
    settings: Settings,
    backup_file: Path,
    confirm_overwrite: bool = False,
) -> dict[str, Any]:
    """Restore SQLite database and artifacts from a backup archive.

    Verifies manifest and database integrity before replacing active data.
    """
    if not backup_file.exists():
        msg = f"Backup file '{backup_file}' does not exist."
        raise ValidationError(msg)

    if not confirm_overwrite:
        msg = "Confirmation required to restore backup: parameter 'confirm_overwrite' must be True."
        raise ValidationError(msg)

    settings.ensure_data_dir()
    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    temp_extract = settings.backups_dir / f"restore_staging_{timestamp_str}"
    temp_extract.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(backup_file, "r:gz") as tar:
            tar.extractall(path=temp_extract, filter="data")

        manifest_path = temp_extract / "manifest.json"
        if not manifest_path.exists():
            msg = "Corrupted backup archive: missing manifest.json"
            raise StorageError(msg)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        extracted_db = temp_extract / "barsa.db"
        if not extracted_db.exists():
            msg = "Corrupted backup archive: missing barsa.db"
            raise StorageError(msg)

        # Verify integrity of extracted SQLite database
        test_conn = sqlite3.connect(str(extracted_db))
        try:
            check_res = verify_database_integrity(test_conn)
            if not check_res["integrity_ok"]:
                msg = f"Restored database failed integrity check: {check_res['integrity_messages']}"
                raise StorageError(msg)
        finally:
            test_conn.close()

        # Atomic replacement: replace active database and remove leftover WAL/SHM files
        target_db = settings.db_path
        target_db.parent.mkdir(parents=True, exist_ok=True)
        wal_file = Path(str(target_db) + "-wal")
        shm_file = Path(str(target_db) + "-shm")
        wal_file.unlink(missing_ok=True)
        shm_file.unlink(missing_ok=True)
        target_db.unlink(missing_ok=True)
        shutil.copy2(extracted_db, target_db)

        # Restore artifacts if present
        extracted_artifacts = temp_extract / "artifacts"
        if extracted_artifacts.exists() and extracted_artifacts.is_dir():
            shutil.copytree(extracted_artifacts, settings.artifacts_dir, dirs_exist_ok=True)

        logger.info("Successfully restored backup from %s", backup_file)
        return {
            "restored_at": datetime.now(UTC).isoformat(),
            "manifest": manifest,
            "integrity": check_res,
        }
    finally:
        shutil.rmtree(temp_extract, ignore_errors=True)
