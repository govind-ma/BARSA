# Security & Authorization Testing Evaluation

This document details the security guarantees and verification testing performed for multi-account and cross-agent integrations.

## Security Architecture in Cross-AI Scenarios

When multiple AI agents connect to BARSA from distinct platforms, authorization is enforced via the `CentralAuthorizer` and `SecurityService`:

```
AI Client Request
      │
      ▼
Bearer API Key Authentication -> Resolves Agent Credential
      │
      ▼
Workspace Membership Check -> Verifies Contributor/Editor Role
      │
      ▼
Resource & Action Scopes -> e.g. memory:read, memory:write
      │
      ▼
Audit Event Emission -> Logs Principal ID, Resource, Timestamp
```

## Tested Invariants in `test_cross_account_access.py`

1. **Unauthorized Project Isolation:**
   Agents belonging to Workspace 1 cannot view, query, or mutate projects in Workspace 2. Attempts raise an immediate `AuthorizationError` (HTTP 403 equivalent).
2. **Dynamic Credential Revocation:**
   Revoking an agent's API key immediately invalidates subsequent tool calls. Re-authentication attempts fail cleanly with `AuthenticationError`.
3. **Audit Trail Completeness:**
   All cross-account queries, read accesses, commits, and handoffs generate structured audit events stored in the SQLite audit log with cryptographic principal identifiers.
4. **Role-Based Permission Bounds:**
   Agents assigned `VIEWER` or `REVIEWER` roles cannot invoke mutating tools (`barsa_commit`, `barsa_propose_changes`), guaranteeing that read-only testing agents cannot corrupt project state.
