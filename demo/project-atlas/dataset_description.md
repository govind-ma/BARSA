# Project ATLAS — Synthetic Dataset Description

## Overview

- **Project**: `proj-atlas` ("Project ATLAS — Autonomous Supply Chain & Emergency Logistics Platform")
- **Workspace**: `ws-atlas` ("ATLAS Global Logistics Workspace")
- **Target Architecture**: Java 21 + Spring Boot 3.3 Backend, React 18 + Tailwind Frontend, MySQL 8.0, FalkorDB LPG

---

## Dataset Inventory

| Category | Count | Scope / Details |
| :--- | :---: | :--- |
| **Modules** | **12** | Auth, Warehouse, Catalog, Inventory, Supplier, Order, Shipment, Route, Emergency, Alert, Analytics, Audit |
| **Tasks** | **60** | Complete backlog (`TASK-001` through `TASK-060`) with priority, status, module tag, and dependencies |
| **Requirements** | **20** | Functional and non-functional requirements (`REQ-001` through `REQ-020`) |
| **Architecture Decisions** | **12** | ADRs (`ADR-001` through `ADR-012`) with rationale and alternatives |
| **Agent Roles** | **8** | Architect, Backend Lead, Frontend Architect, DBA, SecOps, QA Lead, DevOps, Logistics Analyst |
| **Capabilities** | **18** | Specialized skill tags (`cap-java-spring`, `cap-react-ts`, `cap-sec-jwt`, `cap-emergency-routing`, etc.) |
| **Knowledge Records** | **15** | Domain specifications (`DOC-001` through `DOC-015`) |
| **Issues & Blockers** | **10** | Bugs and operational incidents (`ISSUE-001` through `ISSUE-010`) |
| **Artifacts** | **10** | Source code, Liquibase SQL migrations, Docker compose, OpenAPI spec |
| **Checkpoints** | **8** | Resumable state snapshots (`CP-001` through `CP-008`) |
| **Graph Relationships** | **388** | `HAS_TASK` (60), `DEPENDS_ON` (65), `REQUIRES` (90), `HAS_CAPABILITY` (24), `AFFECTS` (22), `ASSIGNED_TO` (60), `REFERENCES` (20), `BLOCKED_BY` (2), `CREATED_BY` (18) |
| **Total Graph Entities** | **124** | Seeded directly into FalkorDB |

---

## Generator Script
The dataset is generated deterministically via:
```powershell
python demo/project-atlas/generate_atlas_dataset.py
```
Output artifact: `demo/project-atlas/atlas_synthetic_dataset.json` (119 KB JSON).
