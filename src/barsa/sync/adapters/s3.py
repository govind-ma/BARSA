"""S3-Compatible Object Storage Adapter for Barsa Cloud Sync (AWS S3, MinIO, R2, Ceph)."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from barsa.core.exceptions import ConflictError, StorageError
from barsa.sync.adapters.base import RemoteStorageAdapter
from barsa.sync.crypto import (
    SyncEncryptor,
    canonical_json_bytes,
    compute_sha256,
    verify_sha256,
)
from barsa.sync.models import RemoteBranchRef, RepositoryManifest

logger = logging.getLogger("barsa.sync.adapters.s3")

HASH_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")


class S3StorageAdapter(RemoteStorageAdapter):
    """Production S3-compatible adapter implementing CAS and conditional ref updates."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        prefix: str = "",
        encryptor: SyncEncryptor | None = None,
        s3_client: Any | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name or "us-east-1"
        self.prefix = prefix.strip("/")
        self.encryptor = encryptor

        if s3_client is not None:
            self._client = s3_client
        else:
            config = Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=self.region_name,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                config=config,
            )

    def _get_key(self, relative_path: str) -> str:
        clean_rel = relative_path.lstrip("/")
        if self.prefix:
            return f"{self.prefix}/{clean_rel}"
        return clean_rel

    def _validate_hash(self, content_hash: str) -> None:
        if not HASH_REGEX.match(content_hash):
            raise ValueError(f"Malicious or invalid content hash format: {content_hash}")

    async def initialize(
        self,
        repository_id: str,
        project_id: str,
        encryption_enabled: bool = False,
    ) -> RepositoryManifest:
        # 1. Format metadata
        format_meta = {
            "format_version": "1.0",
            "engine": "barsa-sync",
            "initialized_at": datetime.now(UTC).isoformat(),
        }
        await self._put_raw(self._get_key("metadata/format-version.json"), canonical_json_bytes(format_meta))

        # 2. Root manifest
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
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self._client.head_bucket(Bucket=self.bucket_name))
            return True
        except Exception as exc:
            logger.warning(f"S3 connectivity check failed for bucket {self.bucket_name}: {exc}")
            return False

    async def _get_raw(self, key: str) -> tuple[bytes, str]:
        """Fetch raw bytes and clean ETag from S3."""
        loop = asyncio.get_running_loop()
        try:
            res = await loop.run_in_executor(None, lambda: self._client.get_object(Bucket=self.bucket_name, Key=key))
            body: bytes = res["Body"].read()
            etag: str = res.get("ETag", "").strip('"')
            return body, etag
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"S3 key not found: {key}") from e
            raise StorageError(f"S3 error reading key {key}: {e}") from e

    async def _put_raw(self, key: str, data: bytes, if_match: str | None = None) -> str:
        """Upload raw bytes to S3, optionally verifying If-Match condition."""
        loop = asyncio.get_running_loop()
        extra_args: dict[str, Any] = {}
        if if_match:
            extra_args["IfMatch"] = f'"{if_match}"'

        def _do_put() -> dict[str, Any]:
            return self._client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=io.BytesIO(data),
                ContentLength=len(data),
                **extra_args,
            )

        try:
            res = await loop.run_in_executor(None, _do_put)
            return res.get("ETag", "").strip('"')
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("PreconditionFailed", "412"):
                raise ConflictError(f"Conditional write failed for key {key} (etag mismatch)") from e
            raise StorageError(f"S3 error writing key {key}: {e}") from e

    async def read_manifest(self) -> RepositoryManifest | None:
        key = self._get_key("repository.json")
        try:
            raw_bytes, _ = await self._get_raw(key)
        except FileNotFoundError:
            return None

        if self.encryptor:
            raw_bytes = self.encryptor.decrypt(raw_bytes)
        parsed = json.loads(raw_bytes.decode("utf-8"))
        return RepositoryManifest.model_validate(parsed)

    async def write_manifest(self, manifest: RepositoryManifest) -> None:
        raw = canonical_json_bytes(manifest.model_dump())
        manifest_hash = compute_sha256(raw)
        # Store in manifests/
        await self._put_raw(self._get_key(f"manifests/{manifest_hash}.json"), raw)

        # Store as repository.json
        payload = raw
        if self.encryptor:
            payload = self.encryptor.encrypt(raw)
        await self._put_raw(self._get_key("repository.json"), payload)

    async def get_branch_ref(self, branch_name: str) -> RemoteBranchRef | None:
        key = self._get_key(f"refs/{branch_name}.json")
        try:
            raw_bytes, s3_etag = await self._get_raw(key)
        except FileNotFoundError:
            return None

        # Content-level etag: sha256 of the ref JSON
        content_etag = compute_sha256(raw_bytes)
        parsed = json.loads(raw_bytes.decode("utf-8"))
        return RemoteBranchRef(
            branch_name=branch_name,
            commit_id=parsed["commit_id"],
            etag=s3_etag or content_etag,
            updated_at=parsed.get("updated_at", datetime.now(UTC).isoformat()),
        )

    async def update_branch_ref(
        self,
        branch_name: str,
        commit_id: str,
        expected_etag: str | None = None,
    ) -> RemoteBranchRef:
        key = self._get_key(f"refs/{branch_name}.json")

        # Concurrency verification
        current_ref = await self.get_branch_ref(branch_name)
        if current_ref:
            if expected_etag and expected_etag not in (
                current_ref.etag,
                compute_sha256(canonical_json_bytes({"commit_id": current_ref.commit_id})),
            ):
                raise ConflictError(
                    f"Remote branch '{branch_name}' has changed concurrently on S3. "
                    f"Expected etag '{expected_etag}', but observed '{current_ref.etag}'."
                )
        elif expected_etag is not None:
            raise ConflictError(f"Remote branch '{branch_name}' does not exist on S3, but expected etag was provided.")

        ref_data: dict[str, Any] = {
            "branch_name": branch_name,
            "commit_id": commit_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        raw_bytes = canonical_json_bytes(ref_data)
        new_etag = await self._put_raw(key, raw_bytes)

        # Update root manifest branch list
        manifest = await self.read_manifest()
        if manifest:
            manifest.branches[branch_name] = commit_id
            await self.write_manifest(manifest)

        return RemoteBranchRef(
            branch_name=branch_name,
            commit_id=commit_id,
            etag=new_etag or compute_sha256(raw_bytes),
            updated_at=ref_data["updated_at"],
        )

    async def list_branch_refs(self) -> list[RemoteBranchRef]:
        loop = asyncio.get_running_loop()
        refs_prefix = self._get_key("refs/")
        try:
            res = await loop.run_in_executor(
                None, lambda: self._client.list_objects_v2(Bucket=self.bucket_name, Prefix=refs_prefix)
            )
            contents = res.get("Contents", [])
            results = []
            for item in contents:
                key = item["Key"]
                if key.endswith(".json"):
                    branch_name = key.split("/")[-1].replace(".json", "")
                    ref = await self.get_branch_ref(branch_name)
                    if ref:
                        results.append(ref)
            return results
        except Exception as exc:
            logger.warning(f"Failed to list S3 branch refs: {exc}")
            return []

    async def object_exists(self, content_hash: str) -> bool:
        self._validate_hash(content_hash)
        prefix = content_hash[:2]
        key = self._get_key(f"objects/sha256/{prefix}/{content_hash}")
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: self._client.head_object(Bucket=self.bucket_name, Key=key))
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return False
            raise StorageError(f"Error checking object {key}: {e}") from e

    async def put_object(self, content_hash: str, data: bytes, object_type: str = "object") -> str:
        _ = object_type
        self._validate_hash(content_hash)
        if not verify_sha256(data, content_hash):
            actual = compute_sha256(data)
            raise ValueError(f"Content-address mismatch: expected '{content_hash}', calculated '{actual}'")

        if await self.object_exists(content_hash):
            return content_hash  # Deduplicated

        prefix = content_hash[:2]
        key = self._get_key(f"objects/sha256/{prefix}/{content_hash}")
        payload = data
        if self.encryptor:
            payload = self.encryptor.encrypt(data)

        await self._put_raw(key, payload)
        return content_hash

    async def get_object(self, content_hash: str) -> bytes:
        self._validate_hash(content_hash)
        prefix = content_hash[:2]
        key = self._get_key(f"objects/sha256/{prefix}/{content_hash}")
        raw_bytes, _ = await self._get_raw(key)

        if self.encryptor:
            raw_bytes = self.encryptor.decrypt(raw_bytes)

        if not verify_sha256(raw_bytes, content_hash):
            raise ValueError(f"Object corrupted in S3 storage: hash verification failed for {content_hash}")

        return raw_bytes

    async def list_objects(self, prefix: str = "") -> list[str]:
        loop = asyncio.get_running_loop()
        objects_prefix = self._get_key("objects/sha256/")
        hashes = []
        paginator = self._client.get_paginator("list_objects_v2")
        try:
            pages = await loop.run_in_executor(
                None, lambda: list(paginator.paginate(Bucket=self.bucket_name, Prefix=objects_prefix))
            )
            for page in pages:
                for item in page.get("Contents", []):
                    key = item["Key"]
                    obj_hash = key.split("/")[-1]
                    if not prefix or obj_hash.startswith(prefix):
                        hashes.append(obj_hash)
            return sorted(hashes)
        except Exception as exc:
            logger.warning(f"Failed to list S3 objects: {exc}")
            return []

    async def delete_object(self, content_hash: str) -> bool:
        self._validate_hash(content_hash)
        prefix = content_hash[:2]
        key = self._get_key(f"objects/sha256/{prefix}/{content_hash}")
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: self._client.delete_object(Bucket=self.bucket_name, Key=key))
            return True
        except Exception:
            return False
