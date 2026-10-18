# PROJECT ATLAS — Test Scenarios & Multi-Agent Verification Matrix

This document defines the 15 end-to-end verification scenarios executed against the Project ATLAS dataset.

---

## Scenario Overview & Verification Matrix

| Scenario | Objective | Target Agent / Subsystem | Verification Criterion |
| :--- | :--- | :--- | :--- |
| **Scenario 1: Identity & Security** | Verify authentication prerequisite enforcement | `agent-security`, `MOD-AUTH` | Protected endpoints reject unauthenticated access; `TASK-001` through `TASK-005` form an unbroken prerequisite chain. |
| **Scenario 2: Data Model Setup** | Verify multi-hub warehouse and catalog schemas | `agent-database`, `MOD-WAREHOUSE` | Liquibase baseline applies cleanly; 5-tier bin hierarchy validated. |
| **Scenario 3: Initial Continuation** | Evaluate initial unblocked task for backend agent | `agent-backend` | `barsa_graph_resume` selects `TASK-017` (Atomic Stock Reservation) based on critical priority, met prerequisites (`TASK-016`, `TASK-005`), and zero active blockers. |
| **Scenario 4: Task State Mutation** | Complete `TASK-017` and verify graph-driven transition | `agent-backend`, FalkorDB | `barsa_graph_resume` dynamically recalculates readiness and transitions recommendation to `TASK-010` / `TASK-018`. |
| **Scenario 5: Blocker Injection** | Inject active incident `BLOCKED_BY` relationship | `agent-backend`, FalkorDB | Blocked task is immediately disqualified; next unblocked candidate (`TASK-023`) is recommended. |
| **Scenario 6: Emergency Requirement** | Hospital needs 500 units; hub has only 120 units | `agent-logistics`, `agent-architect` | Graph identifies affected modules (`MOD-EMERGENCY`, `MOD-INVENTORY`, `MOD-ORDER`), unblocks emergency allocation capability, and flags conflicting ADRs. |
| **Scenario 7: Multi-Agent Collaboration** | Propose, review, and commit emergency design | Architect -> Backend -> QA -> Security | Real BMS records created for proposed decisions, issues, reviews, and approved commit attribution. |
| **Scenario 8: Memory Versioning & Merge** | Two agents propose incompatible reservation rules | `agent-backend` vs `agent-logistics` | Both branches preserved in SQLite VCS DAG; conflict detected; merge review created and cleanly resolved. |
| **Scenario 9: Agent Continuation** | Agent B resumes in clean session with no prior history | `agent-backend` (Session A) -> `agent-qa` (Session B) | Session B reads checkpoint `CP-004`, loads graph decisions, identifies authorized task, and continues without context loss. |
| **Scenario 10: Context Optimization** | Compare full-history vs SCE optimized context package | `src/barsa/context/engine.py` | Token count reduced by 60%+ while retaining 100% of required decision and dependency references. |
| **Scenario 11: Security & Permissions** | Verify viewer cannot commit; check credential isolation | `agent-security` | Unauthorized write operations return HTTP 403; project isolation strictly enforced. |
| **Scenario 12: Storage & Sync** | Test local SQLite persistence and export/import | `SQLiteStorageProvider` | Local memory persists across server restarts; JSON BMS bundle can be exported and imported losslessly. |
| **Scenario 13: FalkorDB Indispensability** | Stop FalkorDB during live execution (Rule 3) | FalkorDB Engine on port 6389 | Non-graph storage returns HTTP 200; graph continuation strictly returns HTTP 503 (`FALKORDB_UNAVAILABLE`). |
| **Scenario 14: Dashboard Inspection** | Verify interactive web dashboard controls | React Dashboard | Graph canvas, continuation engine panel, node inspector, and accessible table render properly. |
| **Scenario 15: Demonstrator Walkthrough** | Execute complete video/live demo script | Hackathon Demo Director | All flows execute within 5 minutes with deterministic output and zero crashes. |
