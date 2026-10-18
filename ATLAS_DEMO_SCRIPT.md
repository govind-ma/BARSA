# PROJECT ATLAS — Live Hackathon Demonstration Script

## Technical Demonstration Overview

- **Audience**: Graph Hacks Evaluators & Technical Judges
- **Platform**: BARSA (Barsa Agentic Memory Standard Architecture) + FalkorDB
- **Duration**: ~4.5 minutes
- **Focus**: Proving FalkorDB is **essential and indispensable (Rule 2 & Rule 3)** for multi-agent reasoning, dependency resolution, and continuation.

---

## Act 1: The Multi-Agent Memory Problem (0:00 - 0:45)

### Voiceover / Spoken Narrative
> "Welcome to BARSA. In complex software projects, different AI agents—from Claude to GPT-4o—frequently lose context when switching tasks or picking up where another agent left off. 
> 
> Vector databases and flat SQL tables fail here because they lack **structural topology**: an LLM querying 'what should I work on next?' doesn't know whether prerequisite architecture decisions or upstream dependencies have been completed.
> 
> To demonstrate BARSA's graph-powered memory architecture, we created **Project ATLAS**—an enterprise autonomous supply chain and emergency logistics platform with 12 modules, 60 interdependent development tasks, 12 architecture decisions, and 8 specialized AI agents."

### Screen Action
- Show BARSA Dashboard on `http://localhost:5173`.
- Navigate to **Knowledge Graph Explorer** for `proj-atlas`.
- Highlight graph metrics: **124 Nodes**, **388 Interconnected Edges**, **FalkorDB Connected**.

---

## Act 2: Multi-Hop Cypher Traversal & Initial Continuation (0:45 - 1:45)

### Voiceover / Spoken Narrative
> "Let's ask BARSA what our Senior Backend Developer should work on. We trigger `barsa_graph_resume`. 
> 
> Instead of a heuristic guess, FalkorDB executes five real Cypher multi-hop queries. It traverses the dependency graph, inspects prerequisite completion states, evaluates active blockers, and matches agent capabilities.
> 
> Instantly, FalkorDB recommends **TASK-017: Atomic Stock Reservation Service**. Notice the explanation: both prerequisite tasks (Database Schema and RBAC Middleware) are satisfied, zero blockers exist, priority is rated critical, and our agent's Spring Boot and JPA capabilities match perfectly."

### Screen Action
- In the **Graph-Powered Continuation Engine** panel, select `agent-backend` (David Miller).
- Click **"Compute Next Task"**.
- Point to the Recommended Task badge (`TASK-017`), Readiness Score (270.0), and the verified Cypher path list.

---

## Act 3: Dynamic Graph State Shift (1:45 - 2:45)

### Voiceover / Spoken Narrative
> "Now, watch how the graph dynamically adapts as work progresses. Our backend agent completes `TASK-017`. 
> 
> We synchronize this update to FalkorDB via Cypher. When we re-run `barsa_graph_resume`, the recommendation dynamically shifts to **TASK-010: Warehouse Cross-Dock Reallocation Trigger**.
> 
> Next, let's inject a real-world impediment. Suppose a critical issue is discovered. We add a `BLOCKED_BY` relationship in FalkorDB linking `TASK-010` to an open deadlock issue. 
> 
> Recomputing continuation immediately prunes `TASK-010` and reroutes our agent to **TASK-023: Supplier Purchase Order Intake API**. The graph reasoning actively prevents our AI from working on blocked or invalid tasks."

### Screen Action
- Show command or API updating `TASK-017` to `completed`.
- Refresh continuation panel: observe recommendation change to `TASK-010`.
- Inject `BLOCKED_BY` relationship to `ISSUE-002`.
- Refresh continuation panel: observe `TASK-010` pruned and `TASK-023` recommended.

---

## Act 4: Rule 3 Failure & Recovery Proof (2:45 - 4:00)

### Voiceover / Spoken Narrative
> "Now for the ultimate test: **Graph Hacks Rule 3 Compliance**. Is FalkorDB genuinely indispensable, or is this just a visualization over relational tables?
> 
> Watch as we kill the FalkorDB server process live. 
> 
> First, notice that non-graph operations continue to work normally: SQLite returns our project metadata with HTTP 200 OK. 
> 
> But when we call `barsa_graph_resume`, it strictly returns **HTTP 503: FalkorDB Unavailable**. BARSA refuses to fake an answer or fall back to an in-memory heuristic. 
> 
> Now, we restart FalkorDB. Immediately, the connection recovers, Cypher queries resume, and our continuation recommendation is fully restored. FalkorDB is genuinely essential."

### Screen Action
- Run `server_proc.terminate()`.
- Send request to `/api/v1/projects/proj-atlas`: returns `200 OK`.
- Send request to `/api/v1/projects/proj-atlas/graph/resume`: shows red error banner **HTTP 503 FALKORDB_UNAVAILABLE**.
- Restart FalkorDB server: click **"Compute Next Task"** -> immediate recovery with green status and task recommendation.

---

## Act 5: Conclusion & Wrap-up (4:00 - 4:30)

### Voiceover / Spoken Narrative
> "With BARSA and FalkorDB, AI development memory is no longer a fragile text log. It is a live, version-controlled knowledge graph that empowers autonomous multi-agent engineering teams to build complex software with zero lost context."

### Screen Action
- Show the 8 agent roles, 60 tasks, and full knowledge graph topology.
- Conclude demo.
