# PROJECT ATLAS — Architecture & System Specification

## Platform Overview

**Project ATLAS** is an enterprise-scale **Autonomous Supply Chain & Emergency Logistics Platform** engineered to orchestrate real-time inventory allocation, multi-modal vehicle routing, and disaster relief triage across 50 regional distribution hubs.

Project ATLAS serves as the benchmark challenge for verifying **BARSA**'s cross-agent memory persistence, Git-style version control, and **FalkorDB-powered knowledge graph reasoning**.

---

## 1. Domain Modules (12 Subsystems)

| Module ID | Subsystem Name | Business Scope & Architectural Responsibility | Sample Stack Target |
| :--- | :--- | :--- | :--- |
| **`MOD-AUTH`** | **Identity & Authentication** | Stateless OAuth2/OIDC, HMAC-SHA256 JWT tokens, refresh token rotation, RBAC enforcement across Carrier, Hub Manager, and SecOps personas. | Spring Security 6, Redis token revocation bloom filter |
| **`MOD-WAREHOUSE`** | **Warehouse Management** | Multi-hub physical topology, 5-tier bin slot hierarchy (`Hub:Zone:Aisle:Shelf:Bin`), automated dock door scheduling, and cross-docking staging rules. | Spring Data JPA, MySQL 8.0 spatial indexing |
| **`MOD-CATALOG`** | **Product Catalog** | Global SKU registry with polyglot schema (relational attributes + JSONB custom specs), temperature thresholds (Category A/B/C), and hazardous materials classifications. | MySQL JSONB attributes, Hibernate Validator |
| **`MOD-INVENTORY`** | **Inventory Management** | Atomic stock reservation with optimistic concurrency control (`@Version`), FEFO (First-Expired, First-Out) batch rotation, and low-stock threshold alerts. | Spring Data JPA Optimistic Locking, Redisson |
| **`MOD-SUPPLIER`** | **Supplier Management** | Supplier registry, EDIFACT/X12 and REST purchase order intake, Advanced Shipping Notice (ASN) reconciliation, and vendor OTIF scorecard engine. | Spring Integration, Jackson XML/JSON |
| **`MOD-ORDER`** | **Order Management** | Transactional multi-item order placement, split-fulfillment coordination across regional hubs, and Saga orchestrator with compensating rollbacks. | Spring StateMachine, Outbox Pattern |
| **`MOD-SHIPMENT`** | **Shipment Tracking** | Carrier waybill generation, real-time IoT GPS waypoint ingestion, cold-chain temperature telemetry monitoring, and webhook event dispatchers. | Kafka/RabbitMQ consumer, MySQL Partitioned Tables |
| **`MOD-ROUTE`** | **Route Planning** | Multi-stop Vehicle Routing Problem (VRP) solver with live traffic feeds, fuel optimization, and emergency bypass routing. | Java OptaPlanner / GraphHopper algorithms |
| **`MOD-EMERGENCY`** | **Emergency Prioritization** | Real-time disaster triage protocol, hospital emergency pre-emption, and inter-hub stock diversion algorithms. | FalkorDB Cypher traversal, Spring Service |
| **`MOD-ALERT`** | **Alerts & Notifications** | Low-latency Server-Sent Events (SSE) streaming for web dashboards, critical SMS gateway fallbacks, and audible warehouse terminal alarms. | Spring WebFlux SSE, Twilio REST API |
| **`MOD-ANALYTICS`** | **Analytics Dashboard** | Read-replicated analytical queries, stockout risk predictive models, and distribution heatmaps with 15-minute rollups. | MySQL Read Replicas, React + Tailwind + Chart.js |
| **`MOD-AUDIT`** | **Audit & Reporting** | SHA-256 Merkle chain tamper-evident audit logging, regulatory FDA 21 CFR Part 11 electronic signatures, and chain-of-custody export. | Cryptographic hashing, Spring AspectJ Interceptors |

---

## 2. Technical Stack Reference Architecture

The fictional ATLAS platform is designed around:
- **Backend**: Java 21, Spring Boot 3.3, Spring Data JPA, Spring Security, Flyway/Liquibase.
- **Frontend**: React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite.
- **Relational Data**: MySQL 8.0 (InnoDB) with partitioned event tables.
- **AI Memory & Graph Reasoning Engine**: **BARSA** with **FalkorDB** as primary LPG reasoning database.

---

## 3. Key Architectural Decisions (ADRs)

- **`ADR-001`**: Stateless JWT Authentication with HMAC-SHA256 & Redis Revocation List.
- **`ADR-002`**: Canonical 5-Tier Hierarchical Bin Addressing Scheme (`Hub:Zone:Aisle:Shelf:Bin`).
- **`ADR-003`**: Polyglot Schema: Relational SKU Core with JSONB Attribute Bag.
- **`ADR-004`**: Optimistic Concurrency Control with Versioned Stock Pools to prevent deadlocks.
- **`ADR-005`**: Asynchronous Supplier Order Ingestion via Message Queues.
- **`ADR-006`**: Saga Pattern for Multi-Warehouse Split Order Orchestration.
- **`ADR-007`**: Time-Series Telemetry Ingestion via Partitioned MySQL Tables.
- **`ADR-008`**: Hybrid Dijkstra / Genetic Algorithm for Dynamic Multi-Stop Delivery Rerouting.
- **`ADR-009`**: Two-Tier Priority Pre-emption Protocol for Medical Disasters.
- **`ADR-010`**: Server-Sent Events (SSE) for Ops Web UI with SMS Twilio Fallback.
- **`ADR-011`**: Read-Replicated Analytics Views with Materialized 15-Minute Rollups.
- **`ADR-012`**: SHA-256 Merkle Audit Log for Chain-of-Custody Signoffs.

---

## 4. Verification Objective for BARSA

Project ATLAS does not require completing every Java and React screen of a commercial logistics system. Rather, it serves as the ultimate stress-test proving that **BARSA + FalkorDB**:
1. Accurately coordinates 8 distinct AI agent personas across 60 interdependent tasks.
2. Traverses multi-hop dependency chains to determine real task readiness.
3. Dynamically reacts to prerequisite completion, blocker injection, and emergency requirement changes.
4. Preserves collaborative multi-agent memory through Git-style versioning and checkpoints.
