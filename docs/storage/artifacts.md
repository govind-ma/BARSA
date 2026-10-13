# Safe File and Artifact Storage

## 1. Principles of Artifact Storage

BARSA never embeds large binary payloads directly into SQLite database rows or JSON memory packages.

Instead, the `ArtifactStore`:
1. Computes the cryptographic **SHA-256** hash of streamed file bytes.
2. Deduplicates identical files automatically.
3. Shards file paths using the first 2 hex characters (`artifacts/{shard}/{sha256}`) to prevent directory listing bottlenecks.
4. Performs atomic writes via temporary files to prevent partially written blobs.
5. Emits a `ArtifactReference` record (`record_type: "artifact"`) containing metadata, URI, content hash, and byte length.

---

## 2. Security Safeguards

- **Path Traversal Prevention:** Blob filenames are derived strictly from hex characters (`0-9a-f`). Raw user filenames are never used as filesystem paths.
- **Maximum Size Limits:** Configured via `BARSA_MAX_ARTIFACT_SIZE_BYTES` (default: 50 MB). Streaming aborts immediately if exceeded.
- **Project Isolation:** Artifact metadata records are scoped by `project_id`. Access across project boundaries is strictly rejected.
