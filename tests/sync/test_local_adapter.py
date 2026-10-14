"""Tests for LocalFilesystemStorageAdapter."""

from pathlib import Path

import pytest

from barsa.core.exceptions import ConflictError
from barsa.sync.adapters.local import LocalFilesystemStorageAdapter
from barsa.sync.crypto import compute_sha256


@pytest.fixture
def local_repo_dir(tmp_path: Path) -> Path:
    repo_path = tmp_path / "barsa-remote-storage"
    repo_path.mkdir(parents=True, exist_ok=True)
    return repo_path


@pytest.fixture
def adapter(local_repo_dir: Path) -> LocalFilesystemStorageAdapter:
    return LocalFilesystemStorageAdapter(base_dir=local_repo_dir)


@pytest.mark.asyncio
async def test_initialize_repository(adapter: LocalFilesystemStorageAdapter, local_repo_dir: Path):
    """Verify repository initialization sets up directory structure and format version."""
    assert await adapter.read_manifest() is None
    manifest = await adapter.initialize(
        repository_id="repo-123",
        project_id="proj-123",
        encryption_enabled=False,
    )
    assert manifest.repository_id == "repo-123"
    assert manifest.project_id == "proj-123"

    read_back = await adapter.read_manifest()
    assert read_back is not None
    assert read_back.repository_id == "repo-123"

    # Verify physical files exist
    assert (local_repo_dir / "metadata" / "format-version.json").is_file()
    assert (local_repo_dir / "repository.json").is_file()
    assert (local_repo_dir / "refs").is_dir()
    assert (local_repo_dir / "objects" / "sha256").is_dir()


@pytest.mark.asyncio
async def test_cas_put_get_deduplication(adapter: LocalFilesystemStorageAdapter):
    """Verify CAS object storage, retrieval, and deduplication."""
    await adapter.initialize("repo-123", "proj-123")

    payload = b'{"record_type": "decision", "title": "Adopt SQLite"}'
    expected_hash = compute_sha256(payload)

    # First put
    written_hash = await adapter.put_object(expected_hash, payload)
    assert written_hash == expected_hash

    # Duplicate put deduplication
    second_hash = await adapter.put_object(expected_hash, payload)
    assert second_hash == expected_hash

    # Retrieve object
    retrieved = await adapter.get_object(expected_hash)
    assert retrieved == payload

    # Object existence
    assert await adapter.object_exists(expected_hash) is True
    assert await adapter.object_exists("0" * 64) is False


@pytest.mark.asyncio
async def test_branch_ref_optimistic_concurrency(adapter: LocalFilesystemStorageAdapter):
    """Verify optimistic concurrency and ETag checks when updating branch refs."""
    await adapter.initialize("repo-123", "proj-123")

    # Initial branch ref write (expected_etag is None)
    ref1 = await adapter.update_branch_ref("main", "commit-001", expected_etag=None)
    assert ref1.branch_name == "main"
    assert ref1.commit_id == "commit-001"
    etag1 = ref1.etag
    assert etag1 is not None

    # Update with correct etag succeeds
    ref2 = await adapter.update_branch_ref("main", "commit-002", expected_etag=etag1)
    assert ref2.commit_id == "commit-002"
    assert ref2.etag != etag1

    # Update with stale etag fails with ConflictError
    with pytest.raises(ConflictError):
        await adapter.update_branch_ref("main", "commit-003", expected_etag=etag1)


@pytest.mark.asyncio
async def test_path_traversal_prevention(adapter: LocalFilesystemStorageAdapter):
    """Verify malicious paths or invalid hashes are rejected."""
    await adapter.initialize("repo-123", "proj-123")

    # Malformed hash with directory traversal
    with pytest.raises(ValueError):
        await adapter.get_object("../../etc/passwd")

    with pytest.raises(ValueError):
        await adapter.get_object("abc; rm -rf /")
