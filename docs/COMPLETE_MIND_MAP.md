# AEGIS — Complete Mind Map & Relational Architecture

The AEGIS system is modeled as an interconnected knowledge and operational graph stored directly in **FalkorDB Cloud** and indexed in **BARSA**.

---

## 1. Complete Mind Map Diagram

```mermaid
graph TD
    classDef projectClass fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef agentClass fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#f8fafc;
    classDef taskClass fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef facilityClass fill:#701a75,stroke:#f472b6,stroke-width:2px,color:#f8fafc;
    classDef roadClass fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#f8fafc;
    classDef resourceClass fill:#831843,stroke:#fb7185,stroke-width:2px,color:#f8fafc;
    classDef vehicleClass fill:#134e4a,stroke:#2dd4bf,stroke-width:2px,color:#f8fafc;

    Proj["AEGIS: Emergency Response"]:::projectClass

    subgraph Agents ["AI Agent Roster"]
        AgA["Agent A: Situation Analyst\n(Claude 3.7)"]:::agentClass
        AgB["Agent B: Logistics Planner\n(GPT-4o)"]:::agentClass
        AgC["Agent C: Coordinator\n(Gemini 2.5)"]:::agentClass
    end

    subgraph WorkflowTasks ["Task DAG & Dependencies"]
        T1["Task 1: Incident & Facility Triage"]:::taskClass
        T2["Task 2: Route & Capacity Matching"]:::taskClass
        T3["Task 3: Final Execution Approval"]:::taskClass
    end

    subgraph CheckpointsDAG ["BARSA Checkpoint DAG"]
        CP1["Checkpoint 1: Situation Assessed"]
        CP2["Checkpoint 2: Logistics Planned"]
        CP3["Checkpoint 3: Response Authorized"]
    end

    subgraph CityInfrastructure ["FalkorDB City Infrastructure"]
        CH["Central Hospital\n(ICU: Critical)"]:::facilityClass
        SA["Shelter Alpha\n(Occupancy: 86%)"]:::facilityClass
        ND["North Supply Depot\n(Stocks: 60 O2)"]:::facilityClass
        HD["Harbor Logistics Base\n(Stocks: 250 Food)"]:::facilityClass
        
        MB["Main City Bridge\n(Status: CLOSED)"]:::roadClass
        EA["East Commercial Arterial\n(Status: OPEN, 9.1 km)"]:::roadClass
        NA["North Avenue\n(Status: OPEN, 3.5 km)"]:::roadClass
        HE["Harbor Expressway\n(Status: OPEN, 6.5 km)"]:::roadClass
        
        T01["Truck 01\n(Cap: 50 O2)"]:::vehicleClass
        T02["Truck 02\n(Cap: 120 Food)"]:::vehicleClass
        
        O2["Medical Oxygen Cylinders"]:::resourceClass
        Food["Emergency Food Rations"]:::resourceClass
    end

    Proj -->|HAS_TASK| T1
    Proj -->|HAS_TASK| T2
    Proj -->|HAS_TASK| T3

    T1 -->|ASSIGNED_TO| AgA
    T2 -->|ASSIGNED_TO| AgB
    T3 -->|ASSIGNED_TO| AgC

    T2 -->|DEPENDS_ON| T1
    T3 -->|DEPENDS_ON| T2

    CP1 -->|PRESERVES| T1
    CP2 -->|PRESERVES| T2
    CP3 -->|PRESERVES| T3
    CP2 -->|CONTINUES_FROM| CP1
    CP3 -->|CONTINUES_FROM| CP2

    CH -->|REQUIRES {qty: 40}| O2
    SA -->|REQUIRES {qty: 100}| Food

    ND -->|STOCKS {qty: 60}| O2
    HD -->|STOCKS {qty: 250}| Food

    ND -->|CONNECTED_VIA| NA
    NA -->|LEADS_TO| EA
    EA -->|LEADS_TO| CH
    ND -.->|BLOCKED_BY| MB

    T01 -->|STATIONED_AT| ND
    T02 -->|STATIONED_AT| HD
```

---

## 2. Key Graph Relationships Explained

1. **`[:REQUIRES]`**: Connects affected facilities (e.g. `Central Hospital`) to resources (`Medical Oxygen Cylinders`) with quantity, required-by timeframe, and priority.
2. **`[:STOCKS]`**: Connects supply depots to available resources.
3. **`[:CONNECTED_VIA]` & `[:LEADS_TO]`**: Directs topological reachability between zones, roads, and facilities. Road closure (`status: 'closed'`) immediately prunes paths.
4. **`[:ASSIGNED_TO]` & `[:DEPENDS_ON]`**: Enforces task execution order across independent agent sessions.
5. **`[:PRESERVES]` & `[:CONTINUES_FROM]`**: Represents the BARSA Checkpoint DAG that allows cold-start session recovery.
