# Project ATLAS — Task Dependency Map (60 Tasks)

## Key Topological Invariants

1. **Authentication Must Precede Protected APIs**:
   - `TASK-001` (Security Baseline) -> `TASK-002` (User/Role Migration) -> `TASK-003` (Security Filter Chain) -> `TASK-004` (JWT Token Endpoint) -> `TASK-005` (RBAC Middleware).
   - All secure REST controllers (`TASK-007`, `TASK-012`, `TASK-017`, `TASK-023`, `TASK-027`, `TASK-045`) depend on `TASK-005`.

2. **Warehouse & Product Models Precede Inventory**:
   - `TASK-006` (Warehouse Data Model) and `TASK-011` (SKU Schema Design) must be completed before `TASK-016` (Inventory Pool Schema).

3. **Inventory Precedes Order Fulfillment**:
   - `TASK-017` (Atomic Stock Reservation) must be completed before `TASK-028` (Order Fulfillment Saga).

4. **Orders Precede Shipment Processing**:
   - `TASK-028` (Order Saga) must be completed before `TASK-032` (Carrier Dispatch API) and `TASK-037` (VRP Route Optimizer).

5. **Inventory & Shipment Status Influence Emergency Planning**:
   - `TASK-041` (Hospital Emergency Intake) depends on `TASK-028` (Order Saga) and `TASK-040` (Emergency Triage Protocol).
   - `TASK-042` (Emergency Stock Rebalancing) depends on `TASK-021` (Global Stock View) and `TASK-037` (VRP Route Optimizer).

---

## Complete Task Catalog & Prerequisite Chains

| Task ID | Module | Title | Status | Priority | Prerequisite Dependencies | Required Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-001` | `MOD-AUTH` | Security Baseline & JWT Architecture Design | completed | critical | None | `cap-arch-design`, `cap-sec-jwt` |
| `TASK-002` | `MOD-AUTH` | Database Migration: Users, Roles, Grants | completed | critical | `TASK-001` | `cap-mysql-dba`, `cap-liquibase` |
| `TASK-003` | `MOD-AUTH` | Spring Security Configuration & JWT Filter | completed | critical | `TASK-002` | `cap-java-spring`, `cap-sec-jwt` |
| `TASK-004` | `MOD-AUTH` | JWT Token Generation, Validation & Rotation | completed | high | `TASK-003` | `cap-java-spring`, `cap-sec-jwt` |
| `TASK-005` | `MOD-AUTH` | Role-Based Access Control Middleware | completed | high | `TASK-004` | `cap-java-spring`, `cap-rbac-audit` |
| `TASK-006` | `MOD-WAREHOUSE` | Warehouse Hub & Bin Data Model Design | completed | high | `TASK-002` | `cap-domain-modeling`, `cap-mysql-dba` |
| `TASK-007` | `MOD-WAREHOUSE` | Warehouse Hub CRUD & Capacity API | completed | high | `TASK-006`, `TASK-005` | `cap-java-spring`, `cap-rest-api` |
| `TASK-008` | `MOD-WAREHOUSE` | Dock Door Scheduling & Inbound Staging | completed | medium | `TASK-007` | `cap-java-spring` |
| `TASK-009` | `MOD-WAREHOUSE` | Bin Slot Hierarchy Validation Calculator | completed | medium | `TASK-007` | `cap-java-spring` |
| `TASK-010` | `MOD-WAREHOUSE` | Warehouse Cross-Dock Reallocation Trigger | todo | high | `TASK-008`, `TASK-009` | `cap-java-spring` |
| `TASK-011` | `MOD-CATALOG` | Product SKU Schema Design & Category Taxonomy | completed | high | `TASK-002` | `cap-domain-modeling`, `cap-mysql-dba` |
| `TASK-012` | `MOD-CATALOG` | Product Catalog REST API with Cold-Chain | completed | high | `TASK-011`, `TASK-005` | `cap-java-spring`, `cap-rest-api` |
| `TASK-013` | `MOD-CATALOG` | Hazardous Material Labeling & Validation | completed | medium | `TASK-012` | `cap-java-spring` |
| `TASK-014` | `MOD-CATALOG` | Product SKU Search API with JSONB Filters | todo | medium | `TASK-012` | `cap-java-spring`, `cap-mysql-dba` |
| `TASK-015` | `MOD-CATALOG` | Cold-Chain Temperature Threshold Verifier | todo | medium | `TASK-013` | `cap-java-spring` |
| `TASK-016` | `MOD-INVENTORY` | Inventory Pool Schema with Optimistic Lock | completed | critical | `TASK-006`, `TASK-011` | `cap-mysql-dba`, `cap-liquibase` |
| `TASK-017` | `MOD-INVENTORY` | Atomic Stock Reservation Service | todo | critical | `TASK-016`, `TASK-005` | `cap-java-spring`, `cap-jpa-hibernate` |
| `TASK-018` | `MOD-INVENTORY` | FEFO Batch Allocation Engine | todo | high | `TASK-017` | `cap-java-spring`, `cap-supply-chain` |
| `TASK-019` | `MOD-INVENTORY` | Low Stock Event Notification Trigger | todo | medium | `TASK-017` | `cap-java-spring` |
| `TASK-020` | `MOD-INVENTORY` | Stock Quarantine & Expiration Disposal | todo | medium | `TASK-018` | `cap-java-spring` |
| `TASK-021` | `MOD-INVENTORY` | Multi-Hub Global Stock Aggregate View API | todo | medium | `TASK-017`, `TASK-007` | `cap-java-spring`, `cap-mysql-dba` |
| `TASK-022` | `MOD-SUPPLIER` | Supplier Registry & Contract Data Model | completed | medium | `TASK-002` | `cap-domain-modeling`, `cap-mysql-dba` |
| `TASK-023` | `MOD-SUPPLIER` | Supplier PO Intake REST & EDI Ingestion API | todo | high | `TASK-022`, `TASK-005` | `cap-java-spring`, `cap-rest-api` |
| `TASK-024` | `MOD-SUPPLIER` | Advanced Shipping Notice (ASN) Intake | todo | medium | `TASK-023`, `TASK-008` | `cap-java-spring` |
| `TASK-025` | `MOD-SUPPLIER` | Supplier OTIF Performance Scoring Service | todo | low | `TASK-024` | `cap-supply-chain` |
| `TASK-026` | `MOD-ORDER` | Order Aggregate Model with State Machine | completed | critical | `TASK-011`, `TASK-002` | `cap-domain-modeling` |
| `TASK-027` | `MOD-ORDER` | Customer Order Placement REST API | todo | high | `TASK-026`, `TASK-005` | `cap-java-spring`, `cap-rest-api` |
| `TASK-028` | `MOD-ORDER` | Order Fulfillment Saga Coordinator | todo | critical | `TASK-027`, `TASK-017` | `cap-java-spring` |
| `TASK-029` | `MOD-ORDER` | Multi-Hub Split Fulfillment Routing | todo | high | `TASK-028`, `TASK-021` | `cap-java-spring`, `cap-supply-chain` |
| `TASK-030` | `MOD-ORDER` | Order Cancellation & Compensating Rollback | todo | high | `TASK-028` | `cap-java-spring` |
| `TASK-031` | `MOD-SHIPMENT` | Shipment Entity & Waybill Tracking Schema | completed | high | `TASK-026` | `cap-mysql-dba`, `cap-domain-modeling` |
| `TASK-032` | `MOD-SHIPMENT` | Carrier Dispatch API & Waybill Generation | todo | high | `TASK-031`, `TASK-028` | `cap-java-spring`, `cap-rest-api` |
| `TASK-033` | `MOD-SHIPMENT` | IoT Waypoint Telemetry Streaming Pipeline | todo | high | `TASK-031` | `cap-java-spring` |
| `TASK-034` | `MOD-SHIPMENT` | Cold-Chain Continuous Telemetry Monitor | todo | medium | `TASK-033`, `TASK-015` | `cap-java-spring` |
| `TASK-035` | `MOD-SHIPMENT` | Carrier Proof-of-Delivery Signature Webhook | todo | medium | `TASK-032` | `cap-java-spring` |
| `TASK-036` | `MOD-ROUTE` | Route Planning Graph Network Topology | completed | high | `TASK-006` | `cap-domain-modeling` |
| `TASK-037` | `MOD-ROUTE` | Multi-Stop VRP Solver Engine | todo | high | `TASK-036`, `TASK-032` | `cap-java-spring`, `cap-emergency-routing` |
| `TASK-038` | `MOD-ROUTE` | Real-Time Traffic Congestion Rerouting | todo | medium | `TASK-037`, `TASK-033` | `cap-emergency-routing` |
| `TASK-039` | `MOD-ROUTE` | Fleet Fuel Consumption & EV Charging Optimizer | todo | low | `TASK-037` | `cap-supply-chain` |
| `TASK-040` | `MOD-EMERGENCY` | Disaster Priority Pre-emption Specification | completed | critical | `TASK-026` | `cap-arch-design`, `cap-emergency-allocation` |
| `TASK-041` | `MOD-EMERGENCY` | Hospital Emergency Supply Order Intake | todo | critical | `TASK-040`, `TASK-028` | `cap-java-spring`, `cap-emergency-allocation` |
| `TASK-042` | `MOD-EMERGENCY` | Multi-Hub Emergency Stock Rebalancing Solver | todo | critical | `TASK-041`, `TASK-021`, `TASK-037` | `cap-java-spring`, `cap-emergency-allocation`, `cap-emergency-routing` |
| `TASK-043` | `MOD-EMERGENCY` | Commercial Order Deferral & Notification | todo | high | `TASK-041` | `cap-java-spring` |
| `TASK-044` | `MOD-EMERGENCY` | FEMA/Emergency Broadcast Dispatcher | todo | high | `TASK-042`, `TASK-033` | `cap-java-spring`, `cap-emergency-routing` |
| `TASK-045` | `MOD-ALERT` | SSE & WebSocket Operational Stream Gateway | todo | high | `TASK-005` | `cap-java-spring` |
| `TASK-046` | `MOD-ALERT` | Twilio SMS & PagerDuty Critical Escalation | todo | high | `TASK-045` | `cap-java-spring` |
| `TASK-047` | `MOD-ALERT` | Warehouse Audio/Visual Flashing Alert | todo | medium | `TASK-045` | `cap-java-spring` |
| `TASK-048` | `MOD-ALERT` | Alert Acknowledgment & On-Call SLA Tracker | todo | medium | `TASK-046` | `cap-java-spring` |
| `TASK-049` | `MOD-ANALYTICS` | React Project Scaffolding & Tailwind Setup | completed | high | `TASK-004` | `cap-react-ts`, `cap-tailwind-ui` |
| `TASK-050` | `MOD-WAREHOUSE` | Interactive Warehouse Bin Floor Plan UI | todo | high | `TASK-049`, `TASK-007` | `cap-react-ts`, `cap-tailwind-ui` |
| `TASK-051` | `MOD-EMERGENCY` | Emergency Triage Control Room Dashboard UI | todo | critical | `TASK-049`, `TASK-041`, `TASK-045` | `cap-react-ts`, `cap-tailwind-ui` |
| `TASK-052` | `MOD-SHIPMENT` | Live GPS Fleet Tracking Map UI | todo | high | `TASK-049`, `TASK-033` | `cap-react-ts`, `cap-tailwind-ui` |
| `TASK-053` | `MOD-INVENTORY` | Stock Inventory Health & Lifespan Table UI | todo | medium | `TASK-049`, `TASK-021` | `cap-react-ts`, `cap-tailwind-ui` |
| `TASK-054` | `MOD-ANALYTICS` | Executive Supply Chain KPI Dashboard UI | todo | medium | `TASK-049` | `cap-react-ts`, `cap-tailwind-ui` |
| `TASK-055` | `MOD-AUDIT` | SHA-256 Merkle Chain Custody Logging | todo | high | `TASK-035`, `TASK-005` | `cap-java-spring`, `cap-sec-jwt` |
| `TASK-056` | `MOD-AUDIT` | FDA/DEA Regulatory Electronic Signatures | todo | medium | `TASK-055` | `cap-java-spring`, `cap-rbac-audit` |
| `TASK-057` | `MOD-AUTH` | Security Penetration & Token Tampering Tests | todo | high | `TASK-004`, `TASK-005` | `cap-automated-qa`, `cap-sec-jwt` |
| `TASK-058` | `MOD-INVENTORY` | Concurrent Inventory Stress Test (500 Threads)| todo | high | `TASK-017` | `cap-automated-qa` |
| `TASK-059` | `MOD-AUTH` | Docker Compose Multi-Container Staging | completed | high | `TASK-003`, `TASK-002` | `cap-docker` |
| `TASK-060` | `MOD-EMERGENCY` | Kubernetes Production Helm Chart with HPA | todo | medium | `TASK-059` | `cap-docker`, `cap-k8s` |
