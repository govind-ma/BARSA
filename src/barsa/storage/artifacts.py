"""Local artifact storage manager using content-addressed storage (SHA-256)."""

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

from barsa.bms.base import utc_now
from barsa.bms.records import ArtifactReference, ArtifactType
from barsa.core.exceptions import (
    ResourceNotFoundError,
    StorageError,
    ValidationError,
)


class ArtifactStore:
    """Manages secure, content-addressed artifact bytes in the local filesystem.

    Enforces:
    - Content-addressed deduplication by SHA-256
    - Configurable maximum file size limits
    - Path traversal prevention
    - Atomic writes via temporary files
    """

    def __init__(self, artifacts_dir: Path, max_size_bytes: int = 50 * 1024 * 1024) -> None:
        self.artifacts_dir = artifacts_dir.resolve()
        self.max_size_bytes = max_size_bytes
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _get_blob_path(self, sha256_hash: str) -> Path:
        """Resolve path for a content-addressed blob using two-character sharding."""
        if len(sha256_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in sha256_hash):
            msg = f"Invalid SHA-256 hash: '{sha256_hash}'"
            raise ValidationError(msg)

        clean_hash = sha256_hash.lower()
        shard = clean_hash[:2]
        shard_dir = self.artifacts_dir / shard
        shard_dir.mkdir(parents=True, exist_ok=True)
        return shard_dir / clean_hash

    def save_artifact_bytes(
        self,
        project_id: str,
        artifact_id: str,
        file_obj: BinaryIO,
        artifact_type: ArtifactType = ArtifactType.OTHER,
        media_type: str | None = None,
        filename_hint: str | None = None,
    ) -> ArtifactReference:
        """Stream bytes to a temp file, verify size and hash, and store atomically."""
        hasher = hashlib.sha256()
        total_bytes = 0
        # Safe temporary file in the artifacts directory to allow atomic rename
        # NamedTemporaryFile is explicitly closed before rename/unlink for Windows compatibility
        temp_file = tempfile.NamedTemporaryFile(dir=self.artifacts_dir, delete=False)  # noqa: SIM115
        temp_path = Path(temp_file.name)
        try:
            try:
                while True:
                    chunk = file_obj.read(65536)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > self.max_size_bytes:
                        msg = (
                            f"Artifact exceeds maximum allowed size of {self.max_size_bytes} bytes "
                            f"(read {total_bytes} bytes)"
                        )
                        raise ValidationError(msg)
                    hasher.update(chunk)
                    temp_file.write(chunk)

                temp_file.flush()
            finally:
                temp_file.close()

            content_hash = hasher.hexdigest()
            final_blob_path = self._get_blob_path(content_hash)

            # Atomic replace if blob doesn't exist yet, otherwise remove temp file
            if not final_blob_path.exists():
                shutil.move(str(temp_path), str(final_blob_path))
            else:
                temp_path.unlink(missing_ok=True)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

        uri = f"artifacts://{content_hash}"
        if filename_hint:
            safe_hint = Path(filename_hint).name
            uri = f"artifacts://{content_hash}?filename={safe_hint}"

        return ArtifactReference(
            id=artifact_id,
            project_id=project_id,
            artifact_type=artifact_type,
            uri=uri,
            content_hash=content_hash,
            size_bytes=total_bytes,
            media_type=media_type or "application/octet-stream",
            created_at=utc_now(),
        )

    def get_artifact_path(self, content_hash: str) -> Path:
        """Retrieve the filesystem path for an artifact by its content hash."""
        blob_path = self._get_blob_path(content_hash)
        if not blob_path.exists():
            msg = f"Artifact content blob for hash '{content_hash}' not found."
            raise ResourceNotFoundError(msg, resource_type="ArtifactBlob", identifier=content_hash)
        return blob_path

    def delete_artifact_blob(self, content_hash: str) -> bool:
        """Delete an artifact blob by hash if it exists."""
        try:
            blob_path = self._get_blob_path(content_hash)
            if blob_path.exists():
                blob_path.unlink()
                return True
            return False
        except Exception as err:
            msg = f"Failed to delete artifact blob '{content_hash}': {err}"
            raise StorageError(msg) from err
