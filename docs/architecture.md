# BARSA System Architecture

## 1. Architectural Philosophy: Local-First & Storage-Independent

BARSA (**Universal AI Memory and Collaboration Infrastructure**) is architected to allow human engineers and autonomous AI agents to switch frictionlessly across diverse models (Claude, ChatGPT, Gemini, local LLMs) without loss of project memory, architectural decisions, task graphs, or conversational context.

A foundational architectural requirement of BARSA is **data sovereignty and cost neutrality**:
- **Zero mandatory cloud lock-in:** The project does not require users or organizations to pay a central SaaS vendor to store their context or knowledge graphs.
- **Local-first default:** All memories, commits, and graphs can exist locally on the developer's workstation inside the configured data directory (e.g. `.barsa`).
- **Storage-independent abstractions:** The runtime layer never interacts directly with low-level disk I/O, S3 APIs, or Git plumbing. All persistence interacts through strictly typed protocol boundaries.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AI Systems & Agents                             │
│       Claude 3.7 / OpenAI GPT-4o / Gemini 2.5 / Roo / Cline / Cursor   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST / WebSocket / MCP Server
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Barsa Runtime Engine (FastAPI)                      │
│                                                                        │
│   ┌────────────────────┐   ┌───────────────────┐  ┌────────────────┐   │
│   │ Smart Context      │   │ Agent Coordinator │  │ Security &     │   │
│   │ Engine (Retrieval) │   │ (Model Handoff)   │  │ Isolation Auth │   │
│   └────────────────────┘   └───────────────────┘  └────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │             Barsa Memory Standard (BMS) Entities               │   │
│   │         MemoryItem · MemoryCommit · AgentIdentity              │   │
│   └────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ StorageProvider Protocol
┌───────────────────────────────────▼────────────────────────────────────┐
│                   Storage Provider Adapter Layer                       │
│                                                                        │
│   ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐   │
│   │ Local Filesystem  │  │ User-owned S3 /   │  │ GitHub Git-Repo  │   │
│   │ Storage (Default) │  │ MinIO ObjectStore │  │ Remote Adapter   │   │
│   └───────────────────┘  └───────────────────┘  └──────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Separation of Concerns

### A. Barsa Memory Standard (BMS)
- **Role:** Pure domain entity definitions and serialization contracts.
- **Independence:** Contains zero references to filesystem operations, cloud SDKs, database drivers, or API frameworks.
- **Entities:**
  - `MemoryItem`: Atomic unit representing a task, decision, context snippet, artifact reference, or conversation milestone.
  - `MemoryCommit`: Directed acyclic graph (DAG) snapshot pointing to parent commits, tracking author attribution, and recording incremental diffs.
  - `AgentIdentity`: Provider-independent identity tuple tracking the authoring agent (`provider`, `model`, `role`, `agent_id`).

### B. Barsa Runtime
- **Role:** Coordinates ingestion, query parsing, token-budget context packing, authentication, and HTTP/MCP communication.
- **Framework:** Asynchronous ASGI backend built on FastAPI and Pydantic v2.
- **Configuration & Lifespan:** Environment-driven settings with strict type-safety, automatic path expansion, secret sanitization, and graceful startup/shutdown hooks.

### C. Storage Adapters
- **Role:** Satisfies the `StorageProvider` protocol.
- **Implementations:**
  - `LocalFileStorage` (Phase 2): Persists structured JSON/Markdown trees within the local workspace `.barsa/` directory.
  - `S3StorageAdapter` (Future): User-provided S3/MinIO buckets.
  - `GitHubStorageAdapter` (Future): Commits directly into user-specified Git repositories.
  - `MemoryStorageAdapter` (Testing/Mocking): In-memory volatile store for zero-I/O test execution.

### D. AI Integrations & Tool Protocol
- **Role:** Exposes memory actions to external agents.
- **Channels:**
  - REST endpoints for programmatic scripting and web integrations.
  - MCP (Model Context Protocol) tool servers allowing tools like Claude Desktop, Cursor, and Gemini CLI to call memory tools natively.
  - Barsa Skill instructions guiding LLMs on optimal memory commit etiquette.

---

## 3. Directory Layout & Module Boundaries

| Module | Purpose |
|---|---|
| `barsa.models` | Pydantic domain models for BMS and API schemas |
| `barsa.core` | Configuration, secrets masking, structured logging, base exceptions |
| `barsa.storage` | `StorageProvider` protocols and factory registry |
| `barsa.api` | FastAPI routers, health checks, versioned endpoints, error mappers |
| `barsa.versioning` | Future Git-style commit DAG, branching, and merge conflict engine |
| `barsa.graph` | Future FalkorDB knowledge graph integration |
| `barsa.context` | Future token compaction and semantic context retrieval engine |
| `barsa.agents` | Future capability-based task routing and agent-to-agent handoffs |
| `barsa.security` | Future multi-project isolation, tenant ACLs, and approval rules |
| `barsa.integrations` | Future AI client adapters and MCP server implementation |
