# Synchronization Testing & Benchmark Guide

## 1. Test Suite Structure

The Phase 13 BYOS and Cloud Synchronization test suites are located in `tests/sync/`:

| Test Suite | Purpose | Execution Time |
|:---|:---|:---|
| `test_cas_and_crypto.py` | Validates canonical JSON, SHA-256 CAS, and AES-256-GCM encryption / tamper detection | ~0.6s |
| `test_local_adapter.py` | Tests LocalFilesystemStorageAdapter atomic writes, ETag concurrency, and path traversal guards | ~0.5s |
| `test_s3_adapter.py` | Tests S3StorageAdapter CAS uploads, branch refs, and pagination using a deterministic client stub | ~0.5s |
| `test_sync_coordinator.py` | Tests push, pull (fast-forward & divergence), and sync history recording in SQLite | ~0.5s |
| `test_cross_device_continuity.py` | Multi-device integration test: Device A (push) -> Device B (fresh pull & update) -> Device A (pull) | ~1.1s |
| `test_sync_security.py` | Tests all 18 security requirements (RBAC, tamper rejection, SSRF, ETag mismatch, etc.) | ~1.1s |
| `test_sync_benchmarks.py` | Performance benchmarks for Small (20), Medium (200), and Large (2000) record scales | ~11.0s |

---

## 2. Running the Test Suites

To execute the synchronization test suites:

```powershell
# Run all sync tests
.\.venv\Scripts\pytest -q tests/sync

# Run only the security suite
.\.venv\Scripts\pytest -q tests/sync/test_sync_security.py

# Run only the cross-device continuity test
.\.venv\Scripts\pytest -q tests/sync/test_cross_device_continuity.py

# Run the performance benchmarks
.\.venv\Scripts\pytest -q tests/sync/test_sync_benchmarks.py
```

---

## 3. Local MinIO Test Setup (Optional)

To test live S3 integration against a local MinIO server:

```powershell
# 1. Start MinIO via Docker or standalone binary
docker run -p 9000:9000 -p 9001:9001 -e "MINIO_ROOT_USER=minioadmin" -e "MINIO_ROOT_PASSWORD=minioadmin" minio/minio server /data --console-address ":9001"

# 2. Configure a local MinIO remote in BARSA
$headers = @{ "Content-Type" = "application/json" }
$body = @{
    name = "minio-local"
    provider_type = "s3"
    s3_bucket_name = "barsa-test"
    s3_endpoint_url = "http://127.0.0.1:9000"
    s3_region = "us-east-1"
    s3_access_key = "minioadmin"
    s3_secret_key = "minioadmin"
    encryption_enabled = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/sync/projects/proj-123/remotes" -Method Post -Headers $headers -Body $body
```
