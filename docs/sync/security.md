# Synchronization Security & Threat Model

## 1. Threat Model & Mitigations

BARSA's BYOS synchronization layer protects against the following threat vectors:

### 1.1 Path Traversal Attacks
- **Vector**: Malicious actor supplies `../../etc/passwd` as an object identifier or local path.
- **Defense**: All hashes are strictly validated against `^[0-9a-fA-F]{64}$`. Directory separators are rejected before any filesystem or S3 API call. All relative paths are resolved and checked against the root jail.

### 1.2 Server-Side Request Forgery (SSRF)
- **Vector**: Malicious actor points S3 endpoint URL to internal metadata services (`http://169.254.169.254/`) or localhost ports (`gopher://127.0.0.1:6379`).
- **Defense**: S3 endpoints are restricted to `http://` or `https://`. Cloud metadata IP ranges and non-HTTP protocols are blocked.

### 1.3 Plaintext Credential Leakage
- **Vector**: S3 access keys or encryption passphrases leak into REST response bodies, console logs, or versioned manifests.
- **Defense**:
  - `RemoteResponse` models strip `s3_secret_key` and passphrases entirely.
  - S3 configuration is encrypted at rest in SQLite.
  - Passphrases are passed ephemerally in execution requests and never written to remote manifests.

### 1.4 Unauthorized Remote Access
- **Vector**: An unauthorized agent triggers push, pull, or remote deletion.
- **Defense**: `CentralAuthorizer` enforces strict RBAC before any sync operation. Write operations (`create_remote`, `push`, `delete_remote`) require `memory:write` scope and `EDITOR` or `OWNER` workspace roles.

### 1.5 Man-in-the-Middle (MITM) & Cloud Provider Inspection
- **Vector**: Cloud storage provider or network intermediary inspects stored AI agent memories.
- **Defense**: Client-side AES-256-GCM authenticated encryption with PBKDF2 key derivation. The cloud holds only opaque ciphertext blobs.
