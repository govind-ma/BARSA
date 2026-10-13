# Storage Security Boundaries

## 1. Threat Model & Scope

BARSA Phase 3 is designed for **single-user, local-first operation** on personal workstations or trusted developer environments.

It does **not** yet claim multi-tenant enterprise isolation or remote public hosting capabilities.

---

## 2. Implemented Protections

1. **Localhost Binding:**
   - The server binds strictly to `127.0.0.1` by default.
   - It is never exposed publicly to external network interfaces (`0.0.0.0`) by default.

2. **Strict CORS Policy:**
   - Permissive wildcard CORS (`allow_origins=["*"]`) is strictly disabled.
   - Cross-origin browser requests from external internet websites are blocked.

3. **Path Traversal Protection:**
   - Artifacts use hex SHA-256 addresses for blob filenames.
   - All directory operations expand and resolve paths within `{data_dir}`.

4. **Project Scoping:**
   - Database queries scope all record queries by `(project_id, record_id)` composite keys.

5. **Secrets Sanitation:**
   - Application logging redacts bearer tokens, API keys, and passwords.
