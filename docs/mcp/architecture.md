# Barsa MCP Server — Architecture & Design

BARSA exposes structured, provider-independent AI working memory to AI clients (Claude Desktop, ChatGPT, Cursor, Windsurf, coding agents) through the standard **Model Context Protocol (MCP)**.

---

## 1. Core Architecture Principles

1. **Adapter Pattern, Not Second Memory Engine:**
   The MCP server is strictly a stateless protocol adapter over existing, authoritative Barsa backend engines:
   - **StorageProvider (`SQLiteStorageProvider`)**: Local-first record and artifact persistence.
   - **VersionControlEngine**: DAG history, content hashes, branching, diffs, conflicts, and merge control.
   - **GraphProjectionWorker & GraphRetrievalService**: Contextual multi-hop retrieval over FalkorDB / In-Memory graph projections.
   - **BMS Serialization (`validate_record`)**: Strict schema enforcement on every record mutation.

2. **Single Source of Truth:**
   The MCP server never holds separate in-memory record stores or bypasses version control. Any mutation committed through MCP goes through the standard BMS validation and Git-style commit lifecycle.

3. **Protocol Isolation & Stdio Hygiene:**
   - In standard `stdio` transport mode, standard output (`stdout`) is strictly reserved for valid JSON-RPC 2.0 frames.
   - All diagnostic, error, and lifecycle logs are routed exclusively to `stderr` or rotating file handlers to prevent client stream corruption.

---

## 2. Component Diagram

```mermaid
flowchart TD
    subgraph AI_Clients["AI Agent Clients"]
        Claude["Claude Desktop"]
        ChatGPT["ChatGPT / OpenAI Client"]
        Agent["Autonomous Coding Agent"]
    end

    subgraph MCP_Boundary["Barsa MCP Protocol Server (src/barsa/mcp/)"]
        Transport["Transport Layer (stdio / SSE / Streamable-HTTP)"]
        Server["MCPServer (FastMCP v2)"]
        Security["Security & Local Identity (ContextVar, Input Sanitizers)"]
        Tools["12 Standard Tools (tools.py)"]
        Resources["5 Read-Only Resources (resources.py)"]
        Prompts["3 Guided Prompts (prompts.py)"]
    end

    subgraph Barsa_Core["Authoritative Barsa Backend"]
        BMS["BMS v0.1 Validator"]
        VC["VersionControlEngine (Phase 4)"]
        GraphWorker["GraphProjectionWorker (Phase 5)"]
        Retrieval["GraphRetrievalService"]
        Storage["SQLiteStorageProvider (Phase 3)"]
    end

    subgraph Persistence["Local-First Persistence"]
        DB[("SQLite Database\n(commits, records, outbox)")]
        FalkorDB[("FalkorDB / Graph Engine")]
        Artifacts[("Artifact Storage")]
    end

    Claude -->|JSON-RPC via stdio| Transport
    ChatGPT -->|JSON-RPC via stdio/HTTP| Transport
    Agent -->|JSON-RPC via stdio| Transport

    Transport --> Server
    Server --> Security
    Security --> Tools
    Security --> Resources
    Security --> Prompts

    Tools --> BMS
    Tools --> VC
    Tools --> Storage
    Tools --> GraphWorker
    Tools --> Retrieval

    Resources --> Storage
    Resources --> VC
    Prompts --> Storage

    VC --> DB
    Storage --> DB
    Storage --> Artifacts
    GraphWorker --> DB
    GraphWorker --> FalkorDB
    Retrieval --> FalkorDB
```

---

## 3. Communication Sequence: Cross-Session Continuity

```mermaid
sequenceDiagram
    autonumber
    actor SessionA as Claude (Session A)
    participant MCP as Barsa MCP Server
    participant VC as VersionControlEngine
    participant Graph as Graph Projection
    actor SessionB as ChatGPT (Session B)

    Note over SessionA, MCP: Session A: Architect designs and checkpoints
    SessionA->>MCP: barsa_list_projects()
    MCP-->>SessionA: [proj-auth-engine]
    SessionA->>MCP: barsa_propose_changes(branch="feature/pkce", changes=[Task, Decision, Checkpoint])
    MCP->>VC: Create branch & commit to feature/pkce
    MCP-->>SessionA: PROPOSED (Commit: e8a64d)
    SessionA->>MCP: barsa_commit(branch="main", changes=[...])
    MCP->>VC: Commit to main & trigger Outbox
    VC->>Graph: Asynchronously project graph
    MCP-->>SessionA: COMMITTED (Commit: 354133)
    Note over SessionA: Session A finishes turn

    Note over SessionB, MCP: Session B: Implementation agent continues
    SessionB->>MCP: barsa_get_checkpoint(project_id="proj-auth-engine")
    MCP-->>SessionB: Active Checkpoint (Task: implement-pkce, Next Action: S256 verifier)
    SessionB->>MCP: barsa_resume(project_id="proj-auth-engine", task_id="task-implement-pkce")
    MCP-->>SessionB: Structured Context Package (Task, Decision refs, HEAD revision)
    SessionB->>MCP: barsa_get_diff(from=e7a852, to=354133)
    MCP-->>SessionB: MemoryDiffResult (3 added records)
    Note over SessionB: Agent executes code implementation
    SessionB->>MCP: barsa_commit(branch="main", changes=[TaskStatus.COMPLETED, CheckpointStatus.ACTIVE])
    MCP->>VC: Commit progress to main (Commit: 39caf5)
    MCP-->>SessionB: COMMITTED
```

---

## 4. Key Architectural Decisions

1. **Idempotent Outbox Triggering:**
   When committing directly to `main` via `barsa_commit`, the tool calls `worker.process_pending_events(project_id)` to proactively update graph projections, guaranteeing retrieval freshness for subsequent queries.
2. **Rejection of Unvalidated State:**
   No record can be saved without passing `validate_record()`. Raw JSON blobs that violate BMS schemas are rejected with `INVALID_BMS_RECORD` error before touching disk.
3. **Protected Main Branch:**
   `barsa_propose_changes` strictly rejects targeting the `main` branch directly, requiring agents to specify a feature branch name. Direct mutations to `main` must use `barsa_commit` with explicit commit messages and expected HEAD verification.
