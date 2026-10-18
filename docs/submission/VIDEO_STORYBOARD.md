# BARSA — Video Demo Storyboard & Visual Cue Guide

| Time | Scene | Visual Layout | UI Action / Terminal Command | Key Talking Point |
| :---: | :--- | :--- | :--- | :--- |
| **00:00 - 00:30** | The Problem | Split screen: VS Code, terminal with Claude, ChatGPT window | Highlight switching windows and losing context | Context amnesia across AI sessions is broken. |
| **00:30 - 01:00** | Architecture | Browser: `README.md` architecture diagram | Scroll and highlight FalkorDB and BMS layers | BARSA standardizes memory and uses FalkorDB for reasoning. |
| **01:00 - 01:45** | Project ATLAS | Browser: `http://localhost:5173/projects/proj-atlas` | Show Overview and Knowledge Graph with 124 nodes | 124 nodes, 369 edges, tasks linked to ADRs and skills. |
| **01:45 - 02:30** | Dynamic Continuation | Terminal (split with UI): query `barsa_graph_resume` | Execute: `powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/projects/proj-atlas/graph/resume?agent_id=agent-backend'"` | Recommends `TASK-017` (Atomic Stock Reservation). Advancing on completion. |
| **02:30 - 03:10** | Blocker Pruning | Terminal: Inject `BLOCKED_BY` relationship | Show Cypher execution and re-querying resume endpoint | `TASK-023` pruned; dynamically routes to `TASK-027`. |
| **03:10 - 03:45** | DevOps Alignment | Terminal: query `barsa_graph_resume?agent_id=agent-devops` | Execute resume with `agent-devops` | Matches `TASK-060` (Kubernetes Helm Chart) based on capabilities. |
| **03:45 - 04:15** | Rule 3 Failure & Recovery | Terminal: simulate offline port `59999` | Show HTTP 503 error, then restore connection | Proof: Zero fake fallbacks. FalkorDB is strictly indispensable. |
| **04:15 - 04:35** | Wrap-Up | Browser: GitHub repository root | Scroll to README footer and documentation links | Switch AI, Not Your Progress. |
