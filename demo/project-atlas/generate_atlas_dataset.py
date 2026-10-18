"""PROJECT ATLAS — Synthetic Dataset Generator.

Generates a realistic, deterministic, enterprise dataset for:
PROJECT ATLAS — Autonomous Supply Chain & Emergency Logistics Platform.

Dataset Contents:
- 1 Project: proj-atlas (Workspace: ws-atlas)
- 12 Modules
- 60 Development Tasks (with realistic dependency topology)
- 20 Requirements
- 12 Architecture Decision Records (ADRs)
- 8 Agent Profiles (with distinct capability sets)
- 15 Knowledge Records
- 10 Issues & Blockers
- 10 Artifact References
- 8 Resume Checkpoints
- 260+ Meaningful Graph Relationships (DEPENDS_ON, BLOCKED_BY, REQUIRES,
  HAS_CAPABILITY, AFFECTS, REFERENCES, RESOLVES, ASSIGNED_TO, CREATED_BY)
"""

import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def get_atlas_dataset() -> dict[str, Any]:
    project_id = "proj-atlas"
    workspace_id = "ws-atlas"

    # =========================================================================
    # 1. Workspace & Project
    # =========================================================================
    workspace = {
        "id": workspace_id,
        "name": "ATLAS Global Logistics Workspace",
        "owner_id": "org-atlas-ops",
        "description": "Enterprise workspace for Autonomous Supply Chain & Emergency Logistics",
    }

    project = {
        "id": project_id,
        "workspace_id": workspace_id,
        "name": "Project ATLAS — Autonomous Supply Chain & Emergency Logistics Platform",
        "status": "active",
        "description": "Mission-critical, distributed supply chain platform with real-time emergency medical prioritization",
        "goals": [
            "Real-time warehouse inventory synchronization across 50 regional distribution hubs",
            "Autonomous multi-modal route optimization and GPS shipment tracking",
            "Sub-minute emergency supply reallocation for disaster response hospitals",
            "Zero-trust auditability and cryptographic traceability for medical and hazardous cargo",
        ],
    }

    # =========================================================================
    # 2. 12 Modules
    # =========================================================================
    modules = [
        {"id": "MOD-AUTH", "name": "Identity & Authentication", "description": "OAuth2/OIDC, JWT tokens, RBAC, and zero-trust service mTLS"},
        {"id": "MOD-WAREHOUSE", "name": "Warehouse Management", "description": "Zone/aisle slotting, automated bin tracking, and dock scheduling"},
        {"id": "MOD-CATALOG", "name": "Product Catalog", "description": "SKU definitions, cold-chain temperature thresholds, and hazardous cargo classifications"},
        {"id": "MOD-INVENTORY", "name": "Inventory Management", "description": "Real-time stock reservation, batch expiration, and optimistic concurrency locks"},
        {"id": "MOD-SUPPLIER", "name": "Supplier Management", "description": "Vendor reliability scoring, purchase order intake, and SLA contracts"},
        {"id": "MOD-ORDER", "name": "Order Management", "description": "Multi-item order lifecycle, validation, approval workflows, and back-orders"},
        {"id": "MOD-SHIPMENT", "name": "Shipment Tracking", "description": "IoT GPS telemetry, sensor cold-chain alerts, and carrier status webhooks"},
        {"id": "MOD-ROUTE", "name": "Route Planning", "description": "Multi-modal routing algorithms, fuel efficiency, and traffic impedance bypass"},
        {"id": "MOD-EMERGENCY", "name": "Emergency Prioritization", "description": "Disaster triage protocol, military/hospital pre-emption, and emergency re-allocation"},
        {"id": "MOD-ALERT", "name": "Alerts & Notifications", "description": "Low-latency WebSocket streaming, SMS fallback, and urgent broadcast dispatcher"},
        {"id": "MOD-ANALYTICS", "name": "Analytics Dashboard", "description": "Supply chain velocity metrics, stockout risk predictions, and delivery heatmaps"},
        {"id": "MOD-AUDIT", "name": "Audit & Reporting", "description": "Tamper-evident regulatory compliance reports, chain-of-custody logging"},
    ]

    # =========================================================================
    # 3. 8 Agent Profiles & Capabilities
    # =========================================================================
    capabilities = [
        {"id": "cap-arch-design", "name": "arch-design", "category": "architecture"},
        {"id": "cap-domain-modeling", "name": "domain-modeling", "category": "architecture"},
        {"id": "cap-java-spring", "name": "java-spring-boot", "category": "backend"},
        {"id": "cap-rest-api", "name": "rest-api", "category": "backend"},
        {"id": "cap-jpa-hibernate", "name": "jpa-hibernate", "category": "backend"},
        {"id": "cap-react-ts", "name": "react-typescript", "category": "frontend"},
        {"id": "cap-tailwind-ui", "name": "tailwind-ui", "category": "frontend"},
        {"id": "cap-mysql-dba", "name": "mysql-dba", "category": "database"},
        {"id": "cap-liquibase", "name": "liquibase-flyway", "category": "database"},
        {"id": "cap-sec-jwt", "name": "security-jwt", "category": "security"},
        {"id": "cap-rbac-audit", "name": "rbac-audit", "category": "security"},
        {"id": "cap-automated-qa", "name": "automated-testing", "category": "qa"},
        {"id": "cap-playwright", "name": "e2e-playwright", "category": "qa"},
        {"id": "cap-docker", "name": "docker-containers", "category": "devops"},
        {"id": "cap-k8s", "name": "kubernetes", "category": "devops"},
        {"id": "cap-supply-chain", "name": "supply-chain-analytics", "category": "domain"},
        {"id": "cap-emergency-routing", "name": "emergency-routing", "category": "domain"},
        {"id": "cap-emergency-allocation", "name": "emergency-allocation", "category": "domain"},
    ]

    agents = [
        {
            "id": "agent-architect",
            "name": "Sarah Chen (Chief Architect)",
            "provider": "anthropic",
            "model": "claude-3-7-sonnet",
            "capabilities": ["cap-arch-design", "cap-domain-modeling", "cap-sec-jwt"],
            "role": "Lead System Architect",
        },
        {
            "id": "agent-backend",
            "name": "David Miller (Senior Backend Lead)",
            "provider": "anthropic",
            "model": "claude-3-7-sonnet",
            "capabilities": ["cap-java-spring", "cap-rest-api", "cap-jpa-hibernate"],
            "role": "Java / Spring Boot Backend Lead",
        },
        {
            "id": "agent-frontend",
            "name": "Elena Rostova (Frontend Architect)",
            "provider": "openai",
            "model": "gpt-4o",
            "capabilities": ["cap-react-ts", "cap-tailwind-ui"],
            "role": "React & TypeScript UI Architect",
        },
        {
            "id": "agent-database",
            "name": "Marcus Vance (Principal Data Engineer)",
            "provider": "anthropic",
            "model": "claude-3-7-sonnet",
            "capabilities": ["cap-mysql-dba", "cap-liquibase", "cap-domain-modeling"],
            "role": "MySQL Database & Migration Specialist",
        },
        {
            "id": "agent-security",
            "name": "Amina Al-Mansoor (SecOps Architect)",
            "provider": "openai",
            "model": "gpt-4o",
            "capabilities": ["cap-sec-jwt", "cap-rbac-audit"],
            "role": "Security Engineer & Compliance Auditor",
        },
        {
            "id": "agent-qa",
            "name": "Liam O'Connor (Lead Automation QA)",
            "provider": "google",
            "model": "gemini-1.5-pro",
            "capabilities": ["cap-automated-qa", "cap-playwright"],
            "role": "Quality Assurance & Performance Tester",
        },
        {
            "id": "agent-devops",
            "name": "Kavita Patel (Staff Site Reliability)",
            "provider": "google",
            "model": "gemini-1.5-pro",
            "capabilities": ["cap-docker", "cap-k8s"],
            "role": "DevOps & Cloud Infrastructure Engineer",
        },
        {
            "id": "agent-logistics",
            "name": "Dr. Hans Meyer (Logistics Domain Expert)",
            "provider": "anthropic",
            "model": "claude-3-7-sonnet",
            "capabilities": ["cap-supply-chain", "cap-emergency-routing", "cap-emergency-allocation"],
            "role": "Logistics & Disaster Response Domain Analyst",
        },
    ]

    # =========================================================================
    # 4. 20 Requirements
    # =========================================================================
    requirements = [
        {"id": "REQ-001", "module_id": "MOD-AUTH", "title": "Stateless OAuth2/JWT Authentication with Refresh Rotation", "category": "security"},
        {"id": "REQ-002", "module_id": "MOD-AUTH", "title": "Role-Based Access Control for Warehouse, Carrier, and Ops Personas", "category": "security"},
        {"id": "REQ-003", "module_id": "MOD-WAREHOUSE", "title": "Multi-Hub Warehouse Topology with Bin Slot Hierarchy", "category": "warehouse"},
        {"id": "REQ-004", "module_id": "MOD-WAREHOUSE", "title": "Inbound Dock Scheduling & Cross-Dock Staging Rules", "category": "warehouse"},
        {"id": "REQ-005", "module_id": "MOD-CATALOG", "title": "Global SKU Registry with Cold-Chain Storage Classifications", "category": "catalog"},
        {"id": "REQ-006", "module_id": "MOD-CATALOG", "title": "Hazardous Materials Classification & Packaging Protocols", "category": "catalog"},
        {"id": "REQ-007", "module_id": "MOD-INVENTORY", "title": "Real-Time Stock Reservation with Optimistic Concurrency Control", "category": "inventory"},
        {"id": "REQ-008", "module_id": "MOD-INVENTORY", "title": "FEFO (First Expired, First Out) Batch Allocation Engine", "category": "inventory"},
        {"id": "REQ-009", "module_id": "MOD-SUPPLIER", "title": "Supplier Purchase Order Intake & ASN (Advanced Shipping Notice) API", "category": "supplier"},
        {"id": "REQ-010", "module_id": "MOD-SUPPLIER", "title": "Automated Vendor Lead Time & Performance Scorecard Engine", "category": "supplier"},
        {"id": "REQ-011", "module_id": "MOD-ORDER", "title": "Transactional Order Validation & Split-Fulfillment Coordinator", "category": "order"},
        {"id": "REQ-012", "module_id": "MOD-ORDER", "title": "Order Priority Queuing with Automatic SLA Escalation", "category": "order"},
        {"id": "REQ-013", "module_id": "MOD-SHIPMENT", "title": "Carrier Waybill Generation & Multi-Carrier Dispatch Webhooks", "category": "shipment"},
        {"id": "REQ-014", "module_id": "MOD-SHIPMENT", "title": "Real-Time GPS Telemetry & Temperature Sensor Ingestion", "category": "shipment"},
        {"id": "REQ-015", "module_id": "MOD-ROUTE", "title": "Multi-Stop Vehicle Routing Problem (VRP) Solver with Traffic Feeds", "category": "route"},
        {"id": "REQ-016", "module_id": "MOD-EMERGENCY", "title": "Hospital Emergency Supply Pre-emption & Disaster Allocation Protocol", "category": "emergency"},
        {"id": "REQ-017", "module_id": "MOD-EMERGENCY", "title": "Inter-Warehouse Emergency Stock Rebalancing Trigger", "category": "emergency"},
        {"id": "REQ-018", "module_id": "MOD-ALERT", "title": "High-Priority Notification Dispatch (WebSocket + SMS Gateway)", "category": "alert"},
        {"id": "REQ-019", "module_id": "MOD-ANALYTICS", "title": "Stockout Risk Predictive Model & Hub Congestion Heatmap", "category": "analytics"},
        {"id": "REQ-020", "module_id": "MOD-AUDIT", "title": "Immutable Cryptographic Audit Trail for DEA/FDA Regulated Deliveries", "category": "audit"},
    ]

    # =========================================================================
    # 5. 12 Architecture Decisions (ADRs)
    # =========================================================================
    decisions = [
        {"id": "ADR-001", "module_id": "MOD-AUTH", "title": "Stateless JWT Auth with HMAC-SHA256 & Redis Revocation List", "decision": "Adopt stateless signed JWT access tokens with 15-minute expiration coupled with Redis bloom filter for immediate revocation.", "rationale": "Enables horizontal scaling of backend pods while supporting instant security invalidation."},
        {"id": "ADR-002", "module_id": "MOD-WAREHOUSE", "title": "Hierarchical Bin Addressing Scheme (Hub:Zone:Aisle:Shelf:Bin)", "decision": "Standardize all warehouse coordinate storage on a canonical 5-tier hierarchical string token.", "rationale": "Simplifies prefix-based range queries and physical warehouse forklift routing."},
        {"id": "ADR-003", "module_id": "MOD-CATALOG", "title": "Polyglot Schema: Relational SKU Core with JSONB Attribute Bag", "decision": "Store fixed SKU dimensions in standard MySQL columns and dynamic certification tags in indexed JSON columns.", "rationale": "Accommodates diverse supplier specs without requiring DDL alterations for new cargo types."},
        {"id": "ADR-004", "module_id": "MOD-INVENTORY", "title": "Optimistic Concurrency Control with Versioned Stock Pools", "decision": "Implement row-level versioning on stock pool records; reject reservations on version mismatch with exponential backoff.", "rationale": "Prevents catastrophic overselling during flash-order peaks while avoiding deadlock-prone SELECT FOR UPDATE."},
        {"id": "ADR-005", "module_id": "MOD-SUPPLIER", "title": "Asynchronous EDI/X12 and JSON Ingestion via Kafka/RabbitMQ", "decision": "Decouple supplier order submission from backend processing using an ingestion queue.", "rationale": "Shields core database from vendor retry storms during EDI batch uploads."},
        {"id": "ADR-006", "module_id": "MOD-ORDER", "title": "Saga Pattern for Multi-Warehouse Split Order Orchestration", "decision": "Coordinate split order fulfillment using an orchestrated Saga coordinator with compensating rollbacks.", "rationale": "Guarantees eventual consistency across regional hub databases without distributed 2PC transactions."},
        {"id": "ADR-007", "module_id": "MOD-SHIPMENT", "title": "Time-Series Telemetry Ingestion via Partitioned MySQL Tables", "decision": "Partition IoT waypoint records by month and vehicle_id hash.", "rationale": "Maintains high write throughput and enables rolling archival of historical tracking data."},
        {"id": "ADR-008", "module_id": "MOD-ROUTE", "title": "Hybrid Dijkstra/Genetic Algorithm for Dynamic Rerouting", "decision": "Use pre-computed highway graphs with local genetic algorithm optimizations for urban last-mile delivery.", "rationale": "Satisfies the sub-500ms route calculation requirement for dispatchers."},
        {"id": "ADR-009", "module_id": "MOD-EMERGENCY", "title": "Two-Tier Priority Pre-emption Protocol for Medical Disasters", "decision": "Hospital emergency requests automatically pre-empt commercial orders and reserve stock at the closest reachable hub.", "rationale": "Ensures FEMA/WHO compliance for disaster relief response."},
        {"id": "ADR-010", "module_id": "MOD-ALERT", "title": "Server-Sent Events (SSE) for Ops Web UI with SMS Twilio Fallback", "decision": "Stream operational alerts over SSE; trigger SMS webhook when alert severity is CRITICAL and unacknowledged within 60s.", "rationale": "Minimizes connection overhead while guaranteeing delivery to on-call warehouse managers."},
        {"id": "ADR-011", "module_id": "MOD-ANALYTICS", "title": "Read-Replicated Analytics Views with Materialized 15-Minute Rollups", "decision": "Route analytical queries to read-replicas querying materialized summary tables.", "rationale": "Protects OLTP write performance on core order/inventory tables."},
        {"id": "ADR-012", "module_id": "MOD-AUDIT", "title": "SHA-256 Merkle Audit Log for Chain-of-Custody Signoffs", "decision": "Every custody transfer event is hashed with the previous event hash, forming an append-only chain.", "rationale": "Provides non-repudiation and meets regulatory inspection mandates."},
    ]

    # =========================================================================
    # 6. 15 Knowledge Records
    # =========================================================================
    knowledge = [
        {"id": "DOC-001", "title": "Security Architecture & Key Management Guide", "content": "Defines rotation cycle for RSA-256 JWT keypairs and Vault secret integration."},
        {"id": "DOC-002", "title": "Warehouse Slotting Best Practices & Safety Standards", "content": "OSHA physical layout constraints, heavy item ground-level requirements."},
        {"id": "DOC-003", "title": "Cold Chain Storage & Transportation Guidelines", "content": "Thresholds: Category A (Ultra-cold -80C), Category B (-20C), Category C (2C to 8C)."},
        {"id": "DOC-004", "title": "Concurrency Locking & High-Volume Inventory Guide", "content": "Explains optimistic locking retry strategy, avoiding phantom reservations."},
        {"id": "DOC-005", "title": "Vendor EDI Integration Specification", "content": "EDIFACT and X12 mapping rules for purchase orders and ASNs."},
        {"id": "DOC-006", "title": "Order State Machine & Transition Rules", "content": "States: CREATED, VALIDATED, ALLOCATED, PICKING, PACKED, DISPATCHED, DELIVERED, CANCELLED."},
        {"id": "DOC-007", "title": "Carrier API Integration Protocol", "content": "REST specifications for FedEx, DHL, and local regional courier dispatches."},
        {"id": "DOC-008", "title": "Emergency Dispatch & Priority Escalation Standard", "content": "Triage priority levels: NORMAL (0), EXPEDITED (10), CRITICAL_HOSPITAL (100)."},
        {"id": "DOC-009", "title": "WebSocket/SSE Alert Channel Formatting", "content": "Event structure: {event_id, channel, severity, timestamp, payload, ack_url}."},
        {"id": "DOC-010", "title": "Database Indexing & Partitioning Strategy", "content": "Composite indexes for (hub_id, sku_id, status) on inventory records."},
        {"id": "DOC-011", "title": "Docker Compose & Kubernetes Staging Topology", "content": "Cluster deployment manifests, replica sets, resource limits."},
        {"id": "DOC-012", "title": "Spring Boot Security Filter Chain Implementation", "content": "SecurityFilterChain configuration, JwtAuthenticationConverter bean setup."},
        {"id": "DOC-013", "title": "React Dashboard Component Architecture", "content": "Folder structure, Zustand state stores, and Tailwind CSS design tokens."},
        {"id": "DOC-014", "title": "End-to-End Automated Testing Strategy", "content": "Unit (JUnit 5), integration (Testcontainers MySQL), and E2E (Playwright)."},
        {"id": "DOC-015", "title": "Regulatory Chain-of-Custody Compliance Handbook", "content": "FDA 21 CFR Part 11 electronic signature and audit compliance criteria."},
    ]

    # =========================================================================
    # 7. 10 Issues & Blockers
    # =========================================================================
    issues = [
        {"id": "ISSUE-001", "title": "JWT Expiration Drift across Distributed Hub Clocks", "severity": "high", "status": "resolved", "module_id": "MOD-AUTH"},
        {"id": "ISSUE-002", "title": "MySQL Deadlock during Bulk Inventory Reservation", "severity": "critical", "status": "resolved", "module_id": "MOD-INVENTORY"},
        {"id": "ISSUE-003", "title": "Carrier Waybill Webhook Timeout on DHL Sandbox", "severity": "medium", "status": "resolved", "module_id": "MOD-SHIPMENT"},
        {"id": "ISSUE-004", "title": "Cold-Chain Sensor Out-of-Range False Alarm Trigger", "severity": "medium", "status": "open", "module_id": "MOD-SHIPMENT"},
        {"id": "ISSUE-005", "title": "Cross-Dock Allocation Lag Under Peak Traffic", "severity": "high", "status": "open", "module_id": "MOD-WAREHOUSE"},
        {"id": "ISSUE-006", "title": "Emergency Priority Pre-emption Fails on Multi-Item Split", "severity": "critical", "status": "open", "module_id": "MOD-EMERGENCY"},
        {"id": "ISSUE-007", "title": "SSE Connection Drop on Mobile Warehouse Scanners", "severity": "medium", "status": "open", "module_id": "MOD-ALERT"},
        {"id": "ISSUE-008", "title": "VRP Route Optimizer Memory Leak with 500+ Waypoints", "severity": "high", "status": "open", "module_id": "MOD-ROUTE"},
        {"id": "ISSUE-009", "title": "Analytics Read-Replica Replication Delay exceeding 30s", "severity": "low", "status": "open", "module_id": "MOD-ANALYTICS"},
        {"id": "ISSUE-010", "title": "Emergency Allocation Capability Missing in Core Hub Service", "severity": "critical", "status": "open", "module_id": "MOD-EMERGENCY"},
    ]

    # =========================================================================
    # 8. 10 Artifacts
    # =========================================================================
    artifacts = [
        {"id": "ART-001", "name": "SecurityConfig.java", "type": "source_code", "uri": "backend/src/main/java/com/atlas/config/SecurityConfig.java"},
        {"id": "ART-002", "name": "WarehouseService.java", "type": "source_code", "uri": "backend/src/main/java/com/atlas/warehouse/WarehouseService.java"},
        {"id": "ART-003", "name": "InventoryPool.java", "type": "source_code", "uri": "backend/src/main/java/com/atlas/inventory/InventoryPool.java"},
        {"id": "ART-004", "name": "EmergencyAllocationService.java", "type": "source_code", "uri": "backend/src/main/java/com/atlas/emergency/EmergencyAllocationService.java"},
        {"id": "ART-005", "name": "OrderController.java", "type": "source_code", "uri": "backend/src/main/java/com/atlas/order/OrderController.java"},
        {"id": "ART-006", "name": "ShipmentTracker.tsx", "type": "source_code", "uri": "frontend/src/features/shipments/ShipmentTracker.tsx"},
        {"id": "ART-007", "name": "EmergencyTriageDashboard.tsx", "type": "source_code", "uri": "frontend/src/features/emergency/EmergencyTriageDashboard.tsx"},
        {"id": "ART-008", "name": "V001__init_atlas_schema.sql", "type": "config", "uri": "backend/src/main/resources/db/migration/V001__init_atlas_schema.sql"},
        {"id": "ART-009", "name": "docker-compose.atlas.yml", "type": "config", "uri": "deploy/docker-compose.atlas.yml"},
        {"id": "ART-010", "name": "AtlasOpenApiSpec.yaml", "type": "specification", "uri": "docs/api/AtlasOpenApiSpec.yaml"},
    ]

    # =========================================================================
    # 9. 8 Checkpoints
    # =========================================================================
    checkpoints = [
        {
            "id": "CP-001",
            "task_id": "TASK-003",
            "status": "completed",
            "agent_id": "agent-database",
            "next_action": "Proceed to TASK-004 (JWT Token Generation)",
            "completed_actions": ["Executed Liquibase baseline migration", "Verified foreign key cascade on hub_zones"],
            "pending_actions": [],
            "base_revision": "commit-atlas-001",
        },
        {
            "id": "CP-002",
            "task_id": "TASK-004",
            "status": "completed",
            "agent_id": "agent-backend",
            "next_action": "Proceed to TASK-005 (RBAC Controller)",
            "completed_actions": ["Created JwtTokenProvider", "Added unit tests with mock tokens"],
            "pending_actions": [],
            "base_revision": "commit-atlas-002",
        },
        {
            "id": "CP-003",
            "task_id": "TASK-009",
            "status": "completed",
            "agent_id": "agent-backend",
            "next_action": "Proceed to TASK-010 (Inventory Reservation)",
            "completed_actions": ["Created WarehouseRepository and ProductEntity", "Added CRUD REST endpoints"],
            "pending_actions": [],
            "base_revision": "commit-atlas-003",
        },
        {
            "id": "CP-004",
            "task_id": "TASK-010",
            "status": "in_progress",
            "agent_id": "agent-backend",
            "next_action": "Implement optimistic locking check in InventoryService.reserve()",
            "completed_actions": ["Added @Version column to inventory_pools", "Created test scenario for concurrency"],
            "pending_actions": ["Add retry loop with exponential jitter", "Expose reservation REST endpoint"],
            "base_revision": "commit-atlas-004",
        },
        {
            "id": "CP-005",
            "task_id": "TASK-035",
            "status": "active",
            "agent_id": "agent-logistics",
            "next_action": "Review multi-hub stock rebalancing heuristic for emergency supplies",
            "completed_actions": ["Documented triage criteria in DOC-008"],
            "pending_actions": ["Formulate mathematical solver constraints"],
            "base_revision": "commit-atlas-005",
        },
        {
            "id": "CP-006",
            "task_id": "TASK-041",
            "status": "blocked",
            "agent_id": "agent-backend",
            "next_action": "Resolve ISSUE-010 before continuing emergency allocation implementation",
            "completed_actions": ["Outlined EmergencyAllocationService skeleton"],
            "pending_actions": ["Implement multi-warehouse stock diversion algorithm"],
            "base_revision": "commit-atlas-006",
        },
        {
            "id": "CP-007",
            "task_id": "TASK-051",
            "status": "active",
            "agent_id": "agent-frontend",
            "next_action": "Integrate React Query hooks with emergency triage REST endpoint",
            "completed_actions": ["Created EmergencyTriageDashboard layout and Tailwind badges"],
            "pending_actions": ["Connect SSE live alert listener"],
            "base_revision": "commit-atlas-007",
        },
        {
            "id": "CP-008",
            "task_id": "TASK-058",
            "status": "active",
            "agent_id": "agent-qa",
            "next_action": "Execute concurrency stress test on 500 simultaneous checkout requests",
            "completed_actions": ["Configured Gatling load test script"],
            "pending_actions": ["Execute test run against staging pod", "Record latency percentiles"],
            "base_revision": "commit-atlas-008",
        },
    ]

    # =========================================================================
    # 10. 60 Development Tasks (Realistic Enterprise Graph)
    # =========================================================================
    # Structure: (task_id, module_id, title, status, priority, [deps], [req_caps], adr_id, [assigned_agent])
    tasks_data = [
        # --- Module 1: Auth (5 tasks) ---
        ("TASK-001", "MOD-AUTH", "Security Baseline & JWT Architecture Design", "completed", "critical", [], ["cap-arch-design", "cap-sec-jwt"], "ADR-001", "agent-architect"),
        ("TASK-002", "MOD-AUTH", "Database Migration: Users, Roles, and Permission Grants", "completed", "critical", ["TASK-001"], ["cap-mysql-dba", "cap-liquibase"], None, "agent-database"),
        ("TASK-003", "MOD-AUTH", "Spring Security Configuration & JWT Filter Chain", "completed", "critical", ["TASK-002"], ["cap-java-spring", "cap-sec-jwt"], "ADR-001", "agent-backend"),
        ("TASK-004", "MOD-AUTH", "JWT Token Generation, Validation & Refresh Rotation Endpoint", "completed", "high", ["TASK-003"], ["cap-java-spring", "cap-sec-jwt"], "ADR-001", "agent-backend"),
        ("TASK-005", "MOD-AUTH", "Role-Based Access Control Middleware & Controller Annotations", "completed", "high", ["TASK-004"], ["cap-java-spring", "cap-rbac-audit"], None, "agent-security"),

        # --- Module 2: Warehouse (5 tasks) ---
        ("TASK-006", "MOD-WAREHOUSE", "Warehouse Hub & Coordinate Bin Data Model Design", "completed", "high", ["TASK-002"], ["cap-domain-modeling", "cap-mysql-dba"], "ADR-002", "agent-database"),
        ("TASK-007", "MOD-WAREHOUSE", "Warehouse Hub CRUD & Capacity Allocation API", "completed", "high", ["TASK-006", "TASK-005"], ["cap-java-spring", "cap-rest-api"], None, "agent-backend"),
        ("TASK-008", "MOD-WAREHOUSE", "Dock Door Scheduling & Inbound Staging Area Manager", "completed", "medium", ["TASK-007"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-009", "MOD-WAREHOUSE", "Bin Slot Hierarchy Validation & Capacity Utilization Calculator", "completed", "medium", ["TASK-007"], ["cap-java-spring"], "ADR-002", "agent-backend"),
        ("TASK-010", "MOD-WAREHOUSE", "Warehouse Cross-Dock Reallocation Trigger", "todo", "high", ["TASK-008", "TASK-009"], ["cap-java-spring"], None, "agent-backend"),

        # --- Module 3: Catalog (5 tasks) ---
        ("TASK-011", "MOD-CATALOG", "Product SKU Schema Design & Category Taxonomy", "completed", "high", ["TASK-002"], ["cap-domain-modeling", "cap-mysql-dba"], "ADR-003", "agent-database"),
        ("TASK-012", "MOD-CATALOG", "Product Catalog REST API with Cold-Chain Classification Attributes", "completed", "high", ["TASK-011", "TASK-005"], ["cap-java-spring", "cap-rest-api"], "ADR-003", "agent-backend"),
        ("TASK-013", "MOD-CATALOG", "Hazardous Material Labeling & Special Handling Validation Service", "completed", "medium", ["TASK-012"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-014", "MOD-CATALOG", "Product SKU Search API with Dynamic JSONB Specification Filters", "todo", "medium", ["TASK-012"], ["cap-java-spring", "cap-mysql-dba"], "ADR-003", "agent-backend"),
        ("TASK-015", "MOD-CATALOG", "Cold-Chain Temperature Threshold Verifier Service", "todo", "medium", ["TASK-013"], ["cap-java-spring"], None, "agent-backend"),

        # --- Module 4: Inventory (6 tasks) ---
        ("TASK-016", "MOD-INVENTORY", "Inventory Pool Schema with Optimistic Locking Columns", "completed", "critical", ["TASK-006", "TASK-011"], ["cap-mysql-dba", "cap-liquibase"], "ADR-004", "agent-database"),
        ("TASK-017", "MOD-INVENTORY", "Atomic Stock Reservation Service with Exponential Backoff Retry", "todo", "critical", ["TASK-016", "TASK-005"], ["cap-java-spring", "cap-jpa-hibernate"], "ADR-004", "agent-backend"),
        ("TASK-018", "MOD-INVENTORY", "First-Expired First-Out (FEFO) Batch Allocation Engine", "todo", "high", ["TASK-017"], ["cap-java-spring", "cap-supply-chain"], None, "agent-backend"),
        ("TASK-019", "MOD-INVENTORY", "Low Stock Event Notification Trigger & Threshold Calculator", "todo", "medium", ["TASK-017"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-020", "MOD-INVENTORY", "Warehouse Stock Quarantine & Expiration Disposal Workflow", "todo", "medium", ["TASK-018"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-021", "MOD-INVENTORY", "Multi-Hub Global Stock Aggregate View API", "todo", "medium", ["TASK-017", "TASK-007"], ["cap-java-spring", "cap-mysql-dba"], None, "agent-backend"),

        # --- Module 5: Supplier (4 tasks) ---
        ("TASK-022", "MOD-SUPPLIER", "Supplier Registry & Contract Agreement Data Model", "completed", "medium", ["TASK-002"], ["cap-domain-modeling", "cap-mysql-dba"], None, "agent-database"),
        ("TASK-023", "MOD-SUPPLIER", "Supplier Purchase Order Intake REST & EDI Ingestion API", "todo", "high", ["TASK-022", "TASK-005"], ["cap-java-spring", "cap-rest-api"], "ADR-005", "agent-backend"),
        ("TASK-024", "MOD-SUPPLIER", "Advanced Shipping Notice (ASN) Intake & Inbound Verification", "todo", "medium", ["TASK-023", "TASK-008"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-025", "MOD-SUPPLIER", "Supplier On-Time In-Full (OTIF) Performance Scoring Service", "todo", "low", ["TASK-024"], ["cap-supply-chain"], None, "agent-logistics"),

        # --- Module 6: Order (5 tasks) ---
        ("TASK-026", "MOD-ORDER", "Order Aggregate Data Model with State Machine Definition", "completed", "critical", ["TASK-011", "TASK-002"], ["cap-domain-modeling"], "ADR-006", "agent-architect"),
        ("TASK-027", "MOD-ORDER", "Customer Order Placement & Line-Item Validation REST API", "todo", "high", ["TASK-026", "TASK-005"], ["cap-java-spring", "cap-rest-api"], None, "agent-backend"),
        ("TASK-028", "MOD-ORDER", "Order Fulfillment Saga Coordinator with Stock Reservation Calls", "todo", "critical", ["TASK-027", "TASK-017"], ["cap-java-spring"], "ADR-006", "agent-backend"),
        ("TASK-029", "MOD-ORDER", "Multi-Hub Split Fulfillment Order Routing Logic", "todo", "high", ["TASK-028", "TASK-021"], ["cap-java-spring", "cap-supply-chain"], "ADR-006", "agent-backend"),
        ("TASK-030", "MOD-ORDER", "Order Cancellation & Compensating Inventory Rollback Workflow", "todo", "high", ["TASK-028"], ["cap-java-spring"], "ADR-006", "agent-backend"),

        # --- Module 7: Shipment (5 tasks) ---
        ("TASK-031", "MOD-SHIPMENT", "Shipment Entity & Waybill Tracking Schema", "completed", "high", ["TASK-026"], ["cap-mysql-dba", "cap-domain-modeling"], "ADR-007", "agent-database"),
        ("TASK-032", "MOD-SHIPMENT", "Carrier Dispatch API with Rate Shopping & Waybill Generation", "todo", "high", ["TASK-031", "TASK-028"], ["cap-java-spring", "cap-rest-api"], None, "agent-backend"),
        ("TASK-033", "MOD-SHIPMENT", "IoT Waypoint Telemetry Streaming & GPS Ingestion Pipeline", "todo", "high", ["TASK-031"], ["cap-java-spring"], "ADR-007", "agent-backend"),
        ("TASK-034", "MOD-SHIPMENT", "Cold-Chain Continuous Temperature Telemetry Monitor", "todo", "medium", ["TASK-033", "TASK-015"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-035", "MOD-SHIPMENT", "Carrier Proof-of-Delivery Signature & Geofence Webhook", "todo", "medium", ["TASK-032"], ["cap-java-spring"], None, "agent-backend"),

        # --- Module 8: Route (4 tasks) ---
        ("TASK-036", "MOD-ROUTE", "Route Planning Graph Network & Highway Distance Topology", "completed", "high", ["TASK-006"], ["cap-domain-modeling"], "ADR-008", "agent-architect"),
        ("TASK-037", "MOD-ROUTE", "Multi-Stop Vehicle Routing Problem (VRP) Solver Engine", "todo", "high", ["TASK-036", "TASK-032"], ["cap-java-spring", "cap-emergency-routing"], "ADR-008", "agent-backend"),
        ("TASK-038", "MOD-ROUTE", "Real-Time Traffic Congestion Rerouting Calculator", "todo", "medium", ["TASK-037", "TASK-033"], ["cap-emergency-routing"], "ADR-008", "agent-logistics"),
        ("TASK-039", "MOD-ROUTE", "Fleet Fuel Consumption & Electric Vehicle Charging Optimizer", "todo", "low", ["TASK-037"], ["cap-supply-chain"], None, "agent-logistics"),

        # --- Module 9: Emergency Prioritization (5 tasks) ---
        ("TASK-040", "MOD-EMERGENCY", "Disaster Response Priority Pre-emption Protocol Specification", "completed", "critical", ["TASK-026"], ["cap-arch-design", "cap-emergency-allocation"], "ADR-009", "agent-architect"),
        ("TASK-041", "MOD-EMERGENCY", "Hospital Emergency Supply Order Intake with Instant Pre-emption", "todo", "critical", ["TASK-040", "TASK-028"], ["cap-java-spring", "cap-emergency-allocation"], "ADR-009", "agent-backend"),
        ("TASK-042", "MOD-EMERGENCY", "Multi-Hub Emergency Stock Rebalancing & Urgent Diversion Solver", "todo", "critical", ["TASK-041", "TASK-021", "TASK-037"], ["cap-java-spring", "cap-emergency-allocation", "cap-emergency-routing"], "ADR-009", "agent-backend"),
        ("TASK-043", "MOD-EMERGENCY", "Commercial Order Deferral & Customer Notification Service", "todo", "high", ["TASK-041"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-044", "MOD-EMERGENCY", "FEMA/Emergency Agency Live Telemetry Broadcast Dispatcher", "todo", "high", ["TASK-042", "TASK-033"], ["cap-java-spring", "cap-emergency-routing"], None, "agent-backend"),

        # --- Module 10: Alerts & Notifications (4 tasks) ---
        ("TASK-045", "MOD-ALERT", "Server-Sent Events (SSE) & WebSocket Operational Stream Gateway", "todo", "high", ["TASK-005"], ["cap-java-spring"], "ADR-010", "agent-backend"),
        ("TASK-046", "MOD-ALERT", "Twilio SMS & PagerDuty Critical Escalation Fallback Channel", "todo", "high", ["TASK-045"], ["cap-java-spring"], "ADR-010", "agent-backend"),
        ("TASK-047", "MOD-ALERT", "Warehouse Terminal Audio/Visual Flashing Alert Dispatcher", "todo", "medium", ["TASK-045"], ["cap-java-spring"], None, "agent-backend"),
        ("TASK-048", "MOD-ALERT", "Alert Acknowledgment & On-Call SLA Tracker", "todo", "medium", ["TASK-046"], ["cap-java-spring"], None, "agent-backend"),

        # --- Module 11: Frontend UI (6 tasks) ---
        ("TASK-049", "MOD-ANALYTICS", "React Project Scaffolding, Tailwind Design System & Auth Context", "completed", "high", ["TASK-004"], ["cap-react-ts", "cap-tailwind-ui"], "ADR-013", "agent-frontend"),
        ("TASK-050", "MOD-WAREHOUSE", "Interactive Warehouse Bin Slotting & Floor Plan Visualizer UI", "todo", "high", ["TASK-049", "TASK-007"], ["cap-react-ts", "cap-tailwind-ui"], None, "agent-frontend"),
        ("TASK-051", "MOD-EMERGENCY", "Emergency Triage & Hospital Reallocation Control Room Dashboard", "todo", "critical", ["TASK-049", "TASK-041", "TASK-045"], ["cap-react-ts", "cap-tailwind-ui"], None, "agent-frontend"),
        ("TASK-052", "MOD-SHIPMENT", "Live Leaflet/Mapbox GPS Fleet Tracking Map with Cold-Chain Status", "todo", "high", ["TASK-049", "TASK-033"], ["cap-react-ts", "cap-tailwind-ui"], None, "agent-frontend"),
        ("TASK-053", "MOD-INVENTORY", "Stock Inventory Health, Reorder Levels & Batch Lifespan Table", "todo", "medium", ["TASK-049", "TASK-021"], ["cap-react-ts", "cap-tailwind-ui"], None, "agent-frontend"),
        ("TASK-054", "MOD-ANALYTICS", "Executive Supply Chain KPI Dashboard with Real-Time Charting", "todo", "medium", ["TASK-049"], ["cap-react-ts", "cap-tailwind-ui"], "ADR-011", "agent-frontend"),

        # --- Module 12: QA, DevOps & Audit (6 tasks) ---
        ("TASK-055", "MOD-AUDIT", "SHA-256 Merkle Chain Immutable Custody Logging Engine", "todo", "high", ["TASK-035", "TASK-005"], ["cap-java-spring", "cap-sec-jwt"], "ADR-012", "agent-security"),
        ("TASK-056", "MOD-AUDIT", "FDA/DEA Electronic Signature Regulatory Report Exporter", "todo", "medium", ["TASK-055"], ["cap-java-spring", "cap-rbac-audit"], "ADR-012", "agent-security"),
        ("TASK-057", "MOD-AUTH", "Security Penetration & OAuth Token Tampering Automated Test Suite", "todo", "high", ["TASK-004", "TASK-005"], ["cap-automated-qa", "cap-sec-jwt"], None, "agent-qa"),
        ("TASK-058", "MOD-INVENTORY", "Concurrent Inventory Allocation Stress Test (500 Threads)", "todo", "high", ["TASK-017"], ["cap-automated-qa"], None, "agent-qa"),
        ("TASK-059", "MOD-AUTH", "Docker Compose Multi-Container Staging Environment Setup", "completed", "high", ["TASK-003", "TASK-002"], ["cap-docker"], "ADR-011", "agent-devops"),
        ("TASK-060", "MOD-EMERGENCY", "Kubernetes Production Helm Chart with HPA & Zero-Downtime Rolling Update", "todo", "medium", ["TASK-059"], ["cap-docker", "cap-k8s"], None, "agent-devops"),
    ]

    tasks = []
    for tid, mid, title, status, prio, deps, req_caps, adr, agent_id in tasks_data:
        tasks.append({
            "id": tid,
            "module_id": mid,
            "title": title,
            "status": status,
            "priority": prio,
            "dependencies": deps,
            "required_capabilities": req_caps,
            "adr_id": adr,
            "assigned_agent_id": agent_id,
            "project_id": project_id,
        })

    # =========================================================================
    # 11. Compile Complete Graph Relationships (260+ edges)
    # =========================================================================
    relationships = []

    # A. HAS_TASK (60)
    for t in tasks:
        relationships.append({
            "source_id": f"{project_id}:project",
            "target_id": f"{project_id}:{t['id']}",
            "rel_type": "HAS_TASK",
            "properties": {"module_id": t["module_id"]},
        })

    # B. DEPENDS_ON (65+)
    for t in tasks:
        for dep in t["dependencies"]:
            relationships.append({
                "source_id": f"{project_id}:{t['id']}",
                "target_id": f"{project_id}:{dep}",
                "rel_type": "DEPENDS_ON",
                "properties": {},
            })

    # C. REQUIRES (Task -> Capability) (90+)
    for t in tasks:
        for cap in t["required_capabilities"]:
            relationships.append({
                "source_id": f"{project_id}:{t['id']}",
                "target_id": f"{project_id}:{cap}",
                "rel_type": "REQUIRES",
                "properties": {},
            })

    # D. HAS_CAPABILITY (Agent -> Capability) (24)
    for ag in agents:
        for cap in ag["capabilities"]:
            relationships.append({
                "source_id": f"{project_id}:{ag['id']}",
                "target_id": f"{project_id}:{cap}",
                "rel_type": "HAS_CAPABILITY",
                "properties": {},
            })

    # E. AFFECTS (Decision -> Task) (22)
    for t in tasks:
        if t["adr_id"]:
            relationships.append({
                "source_id": f"{project_id}:{t['adr_id']}",
                "target_id": f"{project_id}:{t['id']}",
                "rel_type": "AFFECTS",
                "properties": {},
            })

    # F. ASSIGNED_TO (Task -> Agent) (60)
    for t in tasks:
        if t["assigned_agent_id"]:
            relationships.append({
                "source_id": f"{project_id}:{t['id']}",
                "target_id": f"{project_id}:{t['assigned_agent_id']}",
                "rel_type": "ASSIGNED_TO",
                "properties": {},
            })

    # G. REFERENCES (Task -> Knowledge) (15)
    for i, doc in enumerate(knowledge):
        t_id = f"TASK-0{i+1:02d}" if (i + 1) <= 60 else "TASK-001"
        relationships.append({
            "source_id": f"{project_id}:{t_id}",
            "target_id": f"{project_id}:{doc['id']}",
            "rel_type": "REFERENCES",
            "properties": {},
        })

    # H. BLOCKED_BY (Task -> Issue) (selected active issues)
    # ISSUE-006 blocks TASK-041 (Emergency Allocation)
    relationships.append({
        "source_id": f"{project_id}:TASK-041",
        "target_id": f"{project_id}:ISSUE-006",
        "rel_type": "BLOCKED_BY",
        "properties": {"reason": "Multi-item split bug prevents hospital emergency fulfillment"},
    })
    # ISSUE-008 blocks TASK-037 (VRP Routing)
    relationships.append({
        "source_id": f"{project_id}:TASK-037",
        "target_id": f"{project_id}:ISSUE-008",
        "rel_type": "BLOCKED_BY",
        "properties": {"reason": "Memory leak under 500+ waypoints"},
    })

    # I. CREATED_BY (Artifact/Checkpoint -> Agent) (18)
    for art in artifacts:
        relationships.append({
            "source_id": f"{project_id}:{art['id']}",
            "target_id": f"{project_id}:agent-backend",
            "rel_type": "CREATED_BY",
            "properties": {},
        })
    for cp in checkpoints:
        relationships.append({
            "source_id": f"{project_id}:{cp['id']}",
            "target_id": f"{project_id}:{cp['agent_id']}",
            "rel_type": "CREATED_BY",
            "properties": {},
        })

    return {
        "workspace": workspace,
        "project": project,
        "modules": modules,
        "capabilities": capabilities,
        "agents": agents,
        "requirements": requirements,
        "decisions": decisions,
        "knowledge": knowledge,
        "issues": issues,
        "artifacts": artifacts,
        "checkpoints": checkpoints,
        "tasks": tasks,
        "relationships": relationships,
    }


def main():
    data = get_atlas_dataset()
    out_file = Path(__file__).parent / "atlas_synthetic_dataset.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Generated Project ATLAS synthetic dataset at: {out_file}")
    print(f"Summary:")
    print(f" - Modules: {len(data['modules'])}")
    print(f" - Tasks: {len(data['tasks'])}")
    print(f" - Requirements: {len(data['requirements'])}")
    print(f" - Architecture Decisions (ADRs): {len(data['decisions'])}")
    print(f" - Agent Profiles: {len(data['agents'])}")
    print(f" - Capabilities: {len(data['capabilities'])}")
    print(f" - Knowledge Records: {len(data['knowledge'])}")
    print(f" - Issues & Blockers: {len(data['issues'])}")
    print(f" - Artifacts: {len(data['artifacts'])}")
    print(f" - Checkpoints: {len(data['checkpoints'])}")
    print(f" - Total Graph Relationships: {len(data['relationships'])}")


if __name__ == "__main__":
    main()
