# Dashboard Authentication & Session Security

This document explains how the Barsa Web Dashboard interfaces with the Phase 10 security and identity engine.

---

## 1. Authentication Modalities

```mermaid
sequenceDiagram
    autonumber
    actor User as Dashboard User
    participant Browser as Browser Client
    participant ApiClient as Typed ApiClient
    participant FastAPI as Barsa Backend Engine

    alt Local Desktop Single-User Workflow (Default)
        Browser->>ApiClient: Load Dashboard
        ApiClient->>FastAPI: GET /api/v1/security/auth/me (No header)
        FastAPI->>FastAPI: Loopback origin check (127.0.0.1)
        FastAPI-->>ApiClient: AuthenticatedPrincipal (id="local-owner", is_superuser=True)
        ApiClient-->>Browser: Render Dashboard with full root privileges
    else Explicit Bearer Token Workflow
        User->>Browser: Submit credentials (Login Form)
        Browser->>ApiClient: api.login(username, password)
        ApiClient->>FastAPI: POST /api/v1/security/auth/login
        FastAPI-->>ApiClient: { access_token: "jwt...", token_type: "bearer" }
        ApiClient->>ApiClient: Store in sessionStorage (ephemeral)
        ApiClient->>FastAPI: Subsequent requests with Authorization: Bearer <jwt>
    end
```

---

## 2. Key Security Invariants in the Frontend

1. **No Sensitive Access Tokens in Persistent LocalStorage:**
   - JWT tokens are stored solely in `sessionStorage` (which is scoped to the current browser tab and purged upon tab closure).
2. **One-Time Secret Key Display:**
   - Newly generated agent API keys (`barsa_ak_...`) are returned in the response payload of `POST /api/v1/security/agents/credentials` exactly once.
   - The UI displays a modal with a copy button and a prominent warning:
     > *"Store this secret securely now. It will NEVER be displayed again!"*
   - Once dismissed, the raw key cannot be retrieved from either the backend or frontend state.
3. **No Hash Exposure:**
   - Stored Argon2id and SHA-256 hashes are omitted from all dashboard API payloads.
4. **Local Origin Protection:**
   - The backend checks `Origin` headers on mutating requests, preventing malicious external web pages from forging requests to the local dashboard API.
