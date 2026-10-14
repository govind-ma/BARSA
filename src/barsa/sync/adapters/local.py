"""Local Filesystem BYOS Storage Adapter for Barsa Cloud Sync."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from barsa.core.exceptions import ConflictError
from barsa.sync.adapters.base import RemoteStorageAdapter
from barsa.sync.crypto import (
    SyncEncryptor,
    canonical_json_bytes,
    compute_sha256,
    verify_sha256,
)
from barsa.sync.models import RemoteBranchRef, RepositoryManifest

logger = logging.getLogger("barsa.sync.adapters.local")

HASH_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")


class LocalFilesystemStorageAdapter(RemoteStorageAdapter):
    """Production local filesystem adapter implementing the CAS repository layout."""

    def __init__(
        self,
        base_dir: Path | str,
        encryptor: SyncEncryptor | None = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.encryptor = encryptor
        self._refs_dir = self.base_dir / "refs"
        self._objects_dir = self.base_dir / "objects" / "sha256"
        self._manifests_dir = self.base_dir / "manifests"
        self._metadata_dir = self.base_dir / "metadata"

    def _ensure_dirs(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._refs_dir.mkdir(parents=True, exist_ok=True)
        self._objects_dir.mkdir(parents=True, exist_ok=True)
        self._manifests_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write(self, target_path: Path, data: bytes) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.parent / f".tmp_{uuid4().hex}"
        try:
            tmp_path.write_bytes(data)
            tmp_path.replace(target_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def _validate_hash(self, content_hash: str) -> None:
        if not HASH_REGEX.match(content_hash):
            raise ValueError(f"Malicious or invalid content hash format: {content_hash}")

    async def initialize(
        self,
        repository_id: str,
        project_id: str,
        encryption_enabled: bool = False,
    ) -> RepositoryManifest:
        self._ensure_dirs()
        # metadata/format-version.json
        format_meta = {"format_version": "1.0", "engine": "barsa-sync", "initialized_at": datetime.now(UTC).isoformat()}
        self._atomic_write(self._metadata_dir / "format-version.json", canonical_json_bytes(format_meta))

        manifest = RepositoryManifest(
            format_version="1.0",
            repository_id=repository_id,
            project_id=project_id,
            encryption_enabled=encryption_enabled,
            encryption_algorithm="AES-256-GCM" if encryption_enabled else None,
            branches={},
            objects_count=0,
            total_bytes=0,
        )
        await self.write_manifest(manifest)
        return manifest

    async def check_connectivity(self) -> bool:
        try:
            self._ensure_dirs()
            test_file = self.base_dir / f".connectivity_check_{uuid4().hex}"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return True
        except Exception as exc:
            logger.warning(f"Local storage connectivity check failed: {exc}")
            return False

    async def read_manifest(self) -> RepositoryManifest | None:
        manifest_path = self.base_dir / "repository.json"
        if not manifest_path.exists():
            return None
        data = manifest_path.read_bytes()
        if self.encryptor:
            data = self.encryptor.decrypt(data)
        parsed = json.loads(data.decode("utf-8"))
        return RepositoryManifest.model_validate(parsed)

    async def write_manifest(self, manifest: RepositoryManifest) -> None:
        self._ensure_dirs()
        raw = canonical_json_bytes(manifest.model_dump())
        # Store in manifests history
        manifest_hash = compute_sha256(raw)
        self._atomic_write(self._manifests_dir / f"{manifest_hash}.json", raw)

        # Store as active repository.json
        payload = raw
        if self.encryptor:
            payload = self.encryptor.encrypt(raw)
        self._atomic_write(self.base_dir / "repository.json", payload)

    async def get_branch_ref(self, branch_name: str) -> RemoteBranchRef | None:
        ref_path = self._refs_dir / f"{branch_name}.json"
        if not ref_path.exists():
            return None
        content = ref_path.read_bytes()
        etag = compute_sha256(content)
        parsed = json.loads(content.decode("utf-8"))
        return RemoteBranchRef(
            branch_name=branch_name,
            commit_id=parsed["commit_id"],
            etag=etag,
            updated_at=parsed.get("updated_at", datetime.now(UTC).isoformat()),
        )

    async def update_branch_ref(
        self,
        branch_name: str,
        commit_id: str,
        expected_etag: str | None = None,
    ) -> RemoteBranchRef:
        self._ensure_dirs()
        ref_path = self._refs_dir / f"{branch_name}.json"
        if ref_path.exists():
            current_bytes = ref_path.read_bytes()
            current_etag = compute_sha256(current_bytes)
            if expected_etag and expected_etag != current_etag:
                raise ConflictError(
                    f"Remote branch '{branch_name}' has changed unexpectedly. "
                    f"Expected etag '{expected_etag}', but observed '{current_etag}'."
                )
        elif expected_etag is not None:
            raise ConflictError(f"Remote branch '{branch_name}' does not exist, but expected etag was provided.")

        ref_data: dict[str, Any] = {
            "branch_name": branch_name,
            "commit_id": commit_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        raw_bytes = canonical_json_bytes(ref_data)
        new_etag = compute_sha256(raw_bytes)
        self._atomic_write(ref_path, raw_bytes)

        # Also update root repository manifest branch list if manifest exists
        manifest = await self.read_manifest()
        if manifest:
            manifest.branches[branch_name] = commit_id
            await self.write_manifest(manifest)

        return RemoteBranchRef(
            branch_name=branch_name, commit_id=commit_id, etag=new_etag, updated_at=ref_data["updated_at"]
        )

    async def list_branch_refs(self) -> list[RemoteBranchRef]:
        if not self._refs_dir.exists():
            return []
        results = []
        for p in self._refs_dir.glob("*.json"):
            branch_name = p.stem
            ref = await self.get_branch_ref(branch_name)
            if ref:
                results.append(ref)
        return results

    async def object_exists(self, content_hash: str) -> bool:
        self._validate_hash(content_hash)
        prefix = content_hash[:2]
        obj_path = self._objects_dir / prefix / content_hash
        return obj_path.exists()

    async def put_object(self, content_hash: str, data: bytes, object_type: str = "object") -> str:
        _ = object_type
        self._validate_hash(content_hash)
        # Verify content hash before storing (integrity guarantee)
        if not verify_sha256(data, content_hash):
            actual = compute_sha256(data)
            raise ValueError(f"Content-address mismatch: expected '{content_hash}', calculated '{actual}'")

        prefix = content_hash[:2]
        obj_path = self._objects_dir / prefix / content_hash
        if obj_path.exists():
            return content_hash  # Deduplicated

        payload = data
        if self.encryptor:
            payload = self.encryptor.encrypt(data)

        self._atomic_write(obj_path, payload)
        return content_hash

    async def get_object(self, content_hash: str) -> bytes:
        self._validate_hash(content_hash)
        prefix = content_hash[:2]
        obj_path = self._objects_dir / prefix / content_hash
        if not obj_path.exists():
            raise FileNotFoundError(f"Content-addressed object not found: {content_hash}")

        data = obj_path.read_bytes()
        if self.encryptor:
            data = self.encryptor.decrypt(data)

        # Verify integrity on retrieval
        if not verify_sha256(data, content_hash):
            raise ValueError(f"Object corrupted in storage: hash verification failed for {content_hash}")

        return data

    async def list_objects(self, prefix: str = "") -> list[str]:
        if not self._objects_dir.exists():
            return []
        hashes = []
        for p in self._objects_dir.glob("*/*"):
            if p.is_file() and not p.name.startswith(".") and (not prefix or p.name.startswith(prefix)):
                hashes.append(p.name)
        return sorted(hashes)

    async def delete_object(self, content_hash: str) -> bool:
        self._validate_hash(content_hash)
        prefix = content_hash[:2]
        obj_path = self._objects_dir / prefix / content_hash
        if obj_path.exists():
            obj_path.unlink()
            return True
        return False
