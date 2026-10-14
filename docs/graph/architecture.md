# BARSA Knowledge Graph Architecture

## 1. Dual-Store Model

BARSA implements an event-driven **dual-store architecture** designed for data integrity, multi-agent collaboration, and zero vendor lock-in.

```mermaid
flowchart TD
    subgraph Client["AI Clients & API Users"]
        Agent["Autonomous Agent / User"]
    end

    subgraph Core["BARSA Core Application"]
        VC["Version Control Engine\n(Phase 4)"]
        OutboxWriter["Transactional Outbox Writer"]
        Worker["Graph Projection Worker"]
        Retrieval["Graph Retrieval Service"]
    end

    subgraph Primary["Primary Storage (Authoritative)"]
        SQLite[("SQLite Database\n(WAL Mode)")]
        Records["bms_records"]
        Commits["commits & branches"]
        OutboxTable["graph_outbox"]
    end

    subgraph Projection["Derived Graph Store (Index)"]
        FalkorDB[("FalkorDB / InMemory Fallback\nKnowledge Graph")]
    end

    Agent -->|"1. create_commit()"| VC
    VC -->|"2. Atomic Transaction"| SQLite
    VC -->|"3. Insert Outbox Event"| OutboxTable
    Worker -->|"4. Poll / Batch Events"| OutboxTable
    Worker -->|"5. Cypher / Memory Sync"| FalkorDB
    Agent -->|"6. Query Graph / Resume Context"| Retrieval
    Retrieval -->|"7. Read Graph & Verify Freshness"| FalkorDB
    Retrieval -.->|"Check Commit Head"| SQLite
```

### Roles and Boundaries:
1. **Authoritative Source of Truth:**
   - SQLite (Phase 3 & 4) holds the entire canonical history: raw BMS records, content-addressed commits, branch refs, artifacts, and reviews.
   - If FalkorDB fails, crashes, or is completely wiped, **zero project data is lost**.
2. **Derived Knowledge Index:**
   - FalkorDB (or the `InMemoryGraphProvider` fallback) holds an indexed projection of current entity relationships.
   - It is purely a query index optimized for multi-hop graph traversals (task dependencies, decision impact, agent contributions, and resume context).
   - Writes to the graph are strictly performed via projection of committed outbox events.

---

## 2. Transactional Outbox Pattern & Event Sync

To guarantee atomic persistence without dual-write inconsistencies or distributed 2PC transactions:

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Agent / User
    participant VC as VersionControlEngine
    participant DB as SQLite (Authoritative)
    participant Worker as GraphProjectionWorker
    participant Graph as FalkorDB (Graph Index)

    Agent->>VC: create_commit(branch="main", changes=[...])
    rect rgb(240, 248, 255)
        Note over VC,DB: Single Atomic SQLite Transaction
        VC->>DB: INSERT INTO commits (SHA-256 hash)
        VC->>DB: UPDATE branch_heads SET commit_id = new_commit
        VC->>DB: INSERT INTO graph_outbox (event_id, project_id, commit_id, payload, status='pending')
    end
    VC-->>Agent: CommitResponse(commit_id, ...)

    Worker->>DB: Fetch pending outbox events (ordered by created_at)
    Worker->>Graph: Execute idempotent Cypher statements (MERGE / SET / DELETE)
    Worker->>DB: UPDATE graph_outbox SET status='processed', processed_at=UTC
    Worker->>DB: UPDATE graph_projections SET applied_commit_id=new_commit, status='up_to_date'
```

### Sync Guarantees:
- **At-Least-Once Delivery & Idempotency:** Every graph projection query uses Cypher `MERGE` semantics keyed by `node_id = {project_id}:{record_id}`. Replaying events produces identical graph state.
- **Ordered Consumption:** Events are processed monotonically by commit timestamp and sequence.
- **Main Branch Isolation:** Outbox events are only created for commits on `main` (or explicitly merged branches). Feature branch commits never pollute the primary graph index.

---

## 3. Consistency Boundaries and Freshness

Graph queries return metadata with:
- `is_fresh`: Boolean indicating whether `applied_commit_id` matches current `head_commit_id` on the `main` branch.
- `applied_commit_id`: The commit hash up to which the graph has processed.
- `pending_events_count`: Number of outbox events awaiting projection.
- `last_sync_timestamp`: UTC timestamp of the last processed outbox event.
