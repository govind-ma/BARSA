# PROJECT ATLAS — FalkorDB Graph Data Model

## Graph Topology Summary

The Project ATLAS knowledge graph represents the end-to-end engineering, requirement, architectural, and operational topology of the autonomous logistics platform.

- **Total Graph Nodes**: 124
- **Total Directed Relationships**: 388
- **Primary Database**: FalkorDB (OpenCypher)
- **Partition Key**: `barsa_atlas_proj_atlas`

---

## 1. Node Types & Property Schema

| Node Label | Count | Purpose | Properties |
| :--- | :---: | :--- | :--- |
| **`Project`** | 1 | Root repository and workspace container. | `id`, `name`, `description`, `status` |
| **`Task`** | 60 | Actionable units of engineering work across 12 modules. | `id`, `raw_id`, `title`, `status` (`completed`, `todo`), `priority` (`critical`, `high`, `medium`, `low`), `module_id` |
| **`Capability`** | 18 | Discrete technical competencies required or possessed. | `id`, `name`, `category` (`backend`, `frontend`, `database`, `security`, `qa`, `devops`, `domain`) |
| **`Agent`** | 8 | AI agent configurations and operational roles. | `id`, `name`, `provider` (`anthropic`, `openai`, `google`), `model`, `role` |
| **`Decision`** | 12 | Architecture Decision Records (ADRs). | `id`, `title`, `decision`, `rationale`, `status` (`approved`) |
| **`Knowledge`** | 15 | Architectural guides, standards, and domain specifications. | `id`, `title`, `content` |
| **`Issue`** | 10 | Incidents, active blockers, and environmental impediments. | `id`, `title`, `severity`, `status` (`open`, `resolved`), `module_id` |
| **`Artifact`** | 10 | Source code files, migrations, docker-compose, and specifications. | `id`, `name`, `type`, `uri` |
| **`Checkpoint`**| 8 | Resumable state snapshots capturing in-flight work. | `id`, `task_id`, `agent_id`, `status`, `next_action`, `base_revision` |

---

## 2. Directed Relationships (388 Edges)

| Edge Type | Count | Semantics | Example Cypher Pattern |
| :--- | :---: | :--- | :--- |
| **`HAS_TASK`** | 60 | Project containment of development tasks. | `(p:Project)-[:HAS_TASK]->(t:Task)` |
| **`DEPENDS_ON`** | 65 | Prerequisite dependency between tasks. | `(t2:Task)-[:DEPENDS_ON]->(t1:Task)` |
| **`REQUIRES`** | 90 | Skills strictly required to execute a task. | `(t:Task)-[:REQUIRES]->(c:Capability)` |
| **`HAS_CAPABILITY`**| 24 | Verified technical capabilities of an AI agent. | `(a:Agent)-[:HAS_CAPABILITY]->(c:Capability)` |
| **`AFFECTS`** | 22 | Architectural constraints imposed on tasks by ADRs. | `(d:Decision)-[:AFFECTS]->(t:Task)` |
| **`ASSIGNED_TO`** | 60 | Task assignment to suitable agent personas. | `(t:Task)-[:ASSIGNED_TO]->(a:Agent)` |
| **`REFERENCES`** | 20 | Contextual links between tasks and knowledge documents. | `(t:Task)-[:REFERENCES]->(k:Knowledge)` |
| **`BLOCKED_BY`** | 2+ | Active issues or incidents blocking execution. | `(t:Task)-[:BLOCKED_BY]->(i:Issue)` |
| **`CREATED_BY`** | 18 | Authorship attribution for artifacts and checkpoints. | `(art:Artifact)-[:CREATED_BY]->(a:Agent)` |

---

## 3. Core Task Dependency Subgraph (Representative Slice)

```mermaid
graph TD
    classDef done fill:#10b981,stroke:#059669,color:#fff;
    classDef ready fill:#f59e0b,stroke:#d97706,color:#fff;
    classDef todo fill:#6b7280,stroke:#4b5563,color:#fff;
    classDef blocked fill:#ef4444,stroke:#dc2626,color:#fff;

    %% Authentication Pre-requisites
    T1["TASK-001: Security Baseline<br/>(completed)"]:::done
    T2["TASK-002: User/Role Migration<br/>(completed)"]:::done
    T3["TASK-003: Spring Security Filter<br/>(completed)"]:::done
    T4["TASK-004: JWT Token Endpoint<br/>(completed)"]:::done
    T5["TASK-005: RBAC Middleware<br/>(completed)"]:::done

    %% Core Data & Domain
    T6["TASK-006: Warehouse Data Model<br/>(completed)"]:::done
    T7["TASK-007: Warehouse Hub CRUD<br/>(completed)"]:::done
    T11["TASK-011: SKU Schema Design<br/>(completed)"]:::done
    T16["TASK-016: Inventory Pool Schema<br/>(completed)"]:::done

    %% Inventory & Orders
    T17["TASK-017: Atomic Stock Reservation<br/>(INITIAL READY - CRITICAL)"]:::ready
    T18["TASK-018: FEFO Batch Allocation<br/>(todo)"]:::todo
    T27["TASK-027: Customer Order Placement<br/>(todo)"]:::todo
    T28["TASK-028: Order Saga Coordinator<br/>(todo)"]:::todo

    %% Emergency Prioritization
    T40["TASK-040: Emergency Triage Spec<br/>(completed)"]:::done
    T41["TASK-041: Hospital Urgent Order Intake<br/>(BLOCKED by ISSUE-006)"]:::blocked

    %% Edges
    T2 -->|DEPENDS_ON| T1
    T3 -->|DEPENDS_ON| T2
    T4 -->|DEPENDS_ON| T3
    T5 -->|DEPENDS_ON| T4

    T6 -->|DEPENDS_ON| T2
    T7 -->|DEPENDS_ON| T6
    T7 -->|DEPENDS_ON| T5

    T11 -->|DEPENDS_ON| T2
    T16 -->|DEPENDS_ON| T6
    T16 -->|DEPENDS_ON| T11

    T17 -->|DEPENDS_ON| T16
    T17 -->|DEPENDS_ON| T5

    T18 -->|DEPENDS_ON| T17
    T27 -->|DEPENDS_ON| T5
    T28 -->|DEPENDS_ON| T27
    T28 -->|DEPENDS_ON| T17

    T41 -->|DEPENDS_ON| T40
    T41 -->|DEPENDS_ON| T28
```
