"""Tests for S3StorageAdapter with mocked S3 client."""

import io

import pytest
from botocore.exceptions import ClientError

from barsa.core.exceptions import ConflictError
from barsa.sync.adapters.s3 import S3StorageAdapter
from barsa.sync.crypto import compute_sha256


class MockS3Client:
    """In-memory dictionary-backed mock for boto3 S3 client."""

    def __init__(self):
        self.storage: dict[str, bytes] = {}
        self.etags: dict[str, str] = {}

    def head_bucket(self, Bucket: str):  # noqa: ARG002
        return {}

    def head_object(self, Bucket: str, Key: str):  # noqa: ARG002
        if Key not in self.storage:
            error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
            raise ClientError(error_response, "HeadObject")
        return {"ETag": self.etags.get(Key, "mock-etag")}

    def get_object(self, Bucket: str, Key: str):  # noqa: ARG002
        if Key not in self.storage:
            error_response = {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}
            raise ClientError(error_response, "GetObject")
        data = self.storage[Key]
        etag = self.etags.get(Key, "mock-etag")
        return {"Body": io.BytesIO(data), "ETag": etag}

    def put_object(self, Bucket: str, Key: str, Body: io.BytesIO, ContentLength: int, **kwargs):  # noqa: ARG002
        data = Body.read()
        etag = f"etag-{compute_sha256(data)[:16]}"
        self.storage[Key] = data
        self.etags[Key] = etag
        return {"ETag": etag}

    def list_objects_v2(self, Bucket: str, Prefix: str = ""):  # noqa: ARG002
        contents = []
        for key in self.storage:
            if key.startswith(Prefix):
                contents.append({"Key": key})
        return {"Contents": contents}

    def get_paginator(self, operation_name: str):  # noqa: ARG002
        class MockPaginator:
            def __init__(self, client):
                self.client = client

            def paginate(self, Bucket: str, Prefix: str = ""):
                yield self.client.list_objects_v2(Bucket=Bucket, Prefix=Prefix)

        return MockPaginator(self)


@pytest.fixture
def mock_s3() -> MockS3Client:
    return MockS3Client()


@pytest.fixture
def adapter(mock_s3: MockS3Client) -> S3StorageAdapter:
    return S3StorageAdapter(
        bucket_name="barsa-test-bucket",
        region_name="us-east-1",
        prefix="projects/alpha",
        s3_client=mock_s3,
    )


@pytest.mark.asyncio
async def test_s3_connectivity_and_init(adapter: S3StorageAdapter, mock_s3: MockS3Client):
    """Verify S3 bucket connectivity check and repository initialization."""
    assert await adapter.check_connectivity() is True

    manifest = await adapter.initialize(
        repository_id="repo-001",
        project_id="proj-123",
        encryption_enabled=False,
    )
    assert manifest.repository_id == "repo-001"
    assert manifest.project_id == "proj-123"

    # Verify keys are stored with prefix
    assert "projects/alpha/metadata/format-version.json" in mock_s3.storage
    assert "projects/alpha/repository.json" in mock_s3.storage


@pytest.mark.asyncio
async def test_s3_cas_put_and_get(adapter: S3StorageAdapter):
    """Verify CAS put and get against S3."""
    await adapter.initialize("repo-001", "proj-123")

    payload = b'{"record_type": "checkpoint", "title": "Check A"}'
    expected_hash = compute_sha256(payload)

    written_hash = await adapter.put_object(expected_hash, payload)
    assert written_hash == expected_hash

    # Duplicate upload deduplication
    assert await adapter.put_object(expected_hash, payload) == expected_hash

    # Retrieve object
    retrieved = await adapter.get_object(expected_hash)
    assert retrieved == payload

    assert await adapter.object_exists(expected_hash) is True
    assert await adapter.object_exists("f" * 64) is False


@pytest.mark.asyncio
async def test_s3_branch_ref_updates(adapter: S3StorageAdapter):
    """Verify S3 branch reference updates and list branches."""
    await adapter.initialize("repo-001", "proj-123")

    ref = await adapter.update_branch_ref("master", "commit-alpha", expected_etag=None)
    assert ref.branch_name == "master"
    assert ref.commit_id == "commit-alpha"

    # List branch refs
    refs = await adapter.list_branch_refs()
    assert len(refs) == 1
    assert refs[0].branch_name == "master"
    assert refs[0].commit_id == "commit-alpha"

    # Concurrent update with mismatching expected etag raises ConflictError
    with pytest.raises(ConflictError):
        await adapter.update_branch_ref("master", "commit-beta", expected_etag="wrong-etag")
