# Barsa Security, Authentication & Authorization Architecture

The **Barsa Security Subsystem** provides a zero-cloud-dependency, local-first identity, authentication, and authorization architecture protecting multi-tenant AI working memory, artifacts, knowledge graphs, and agent tasks.

---

## 1. Security Architecture Topology

```mermaid
flowchart TD
    subgraph Clients ["Authenticated Actors"]
        Human["Human User\n(Desktop UI / CLI / Browser)"]
        AIAgent["AI Agent\n(Claude / GPT-4o / Local Copilot)"]
        Service["Service Principal\n(CI/CD Pipeline / Projection Worker)"]
    end

    subgraph SecurityGate ["Barsa Security Perimeter"]
        AuthnFilter["1. Authentication Filter\n(Bearer JWT / Salted API Key / Local Context)"]
        OriginGuard["2. Origin & CORS Guard\n(Strict Localhost Origin Validation)"]
        Authorizer["3. Central Authorization Service\n(CentralAuthorizer)"]
        SecretScan["4. Defense-in-Depth Secret Scanner\n(SecretScanner)"]
    end

    subgraph AccessControl ["RBAC & Fine-Grained Policy Engine"]
        Workspaces["Workspace Memberships\n(Owner, Admin, Editor, Reviewer, Viewer)"]
        Grants["Project-Level Grants\n(Project Overrides)"]
        AgentScopes["Agent Scope Bounds\n(memory:read, memory:commit, etc.)"]
        Sensitivity["Sensitivity Clearance\n(public, internal, confidential, restricted)"]
    end

    subgraph Persistence ["Authoritative SQLite & Audit Log"]
        SecurityDB["Security Tables\n(principals, identities, credentials, memberships, grants)"]
        AuditLog["Immutable Audit Log\n(audit_events table)"]
        VC["VersionControlEngine\n(Protected Commits & Branches)"]
        Storage["BMS Working Memory & Artifacts"]
    end

    Clients --> AuthnFilter
    AuthnFilter --> OriginGuard
    OriginGuard --> Authorizer
    Authorizer --> AccessControl
    AccessControl --> SecurityDB
    Authorizer --> SecretScan
    Authorizer --> AuditLog
    Authorizer --> VC
    VC --> Storage
```

---

## 2. Core Security Invariants

1. **Model-Generated Agent IDs are Untrusted:** An agent claiming to be `admin-bot` or `alice` in request arguments is never trusted. Identity is derived strictly from validated cryptographic API keys, signed JWT bearer tokens, or trusted local OS process context.
2. **Local-First Threat Model Protection:** Network APIs bind to `127.0.0.1` by default. Cross-origin requests from external web pages are blocked at the HTTP middleware layer.
3. **No Unencrypted Stored Passwords:** Human user passwords are hashed using Argon2id with unique per-user salts following OWASP guidelines.
4. **Hashed Agent Credentials:** Raw API keys are shown exactly once at generation time. Only salted SHA-256 hashes are stored in SQLite.
5. **No Blind Privilege Escalation:** An agent cannot escalate its permissions simply by declaring high capabilities in coordination tasks. All actions require explicit workspace membership or credential-scoped project grants.
6. **Defense-in-Depth Secret Prevention:** All memory updates undergo regex-based scanning to prevent accidental committing of AWS keys, private keys, OpenAI keys, or JWT tokens.
