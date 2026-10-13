# BARSA Project Roadmap

This roadmap outlines the phased development plan for **BARSA — Universal AI Memory and Collaboration Infrastructure**.

---

## ✅ Phase 1: Project Foundation (Completed)
- Clean Python 3.12+ package setup with `pyproject.toml` and Hatchling.
- FastAPI application entry point with asynchronous lifespan management.
- Health check endpoint (`GET /health`) returning service status, application name, and version.
- Platform info endpoint (`GET /api/v1/info`) returning platform metadata and feature capabilities.
- Type-safe configuration via Pydantic Settings (`BARSA_DATA_DIR`, `BARSA_STORAGE_PROVIDER`, `BARSA_LOG_LEVEL`).
- Centralized API error handling with standard `ErrorResponse` envelope.
- Structured application logging with automatic credential and bearer token redaction.
- Decoupled `StorageProvider` protocol separating the memory standard from storage backends.
- Ruff linter/formatter integration and Pytest test suite with async HTTP client fixtures.

---

## 📅 Phase 2: Local Storage Provider & Barsa Memory Standard (BMS)
- Implement `LocalFileStorage` adapter persisting memories inside `.barsa/`.
- File layout specification: atomic JSON documents, markdown exports, and index files.
- Project workspace isolation and multi-project directory resolution.
- Memory item CRUD REST API (`POST/GET/PUT/DELETE /api/v1/projects/{id}/memories`).

---

## 📅 Phase 3: Git-Inspired Memory Versioning
- Implementation of DAG-based commit tracking (`MemoryCommit`).
- Branching and merging logic for concurrent agent workstreams.
- Diff generation between commits.
- Conflict detection and resolution strategies for parallel agent contributions.

---

## 📅 Phase 4: FalkorDB Knowledge Graph
- Graph database integration for relationship modeling.
- Automatic node creation for tasks, decisions, agents, artifacts, and concepts.
- Cypher query endpoint for deep relational and causal querying.

---

## 📅 Phase 5: Smart Context Engine
- Token-budget-constrained context packing algorithms.
- Relevance ranking combining recency, graph distance, and semantic similarity.
- Context injection payloads for AI prompts.

---

## 📅 Phase 6: Agent Coordinator
- Model capability registry (reasoning, coding, speed, vision, cost).
- Automatic task routing based on required capabilities.
- Standardized handoff payloads for seamless agent-to-agent task transfers.

---

## 📅 Phase 7: Security & Project Isolation
- Role-based access control (RBAC) and workspace API tokens.
- Sandboxing and privacy boundaries.
- Approval rules for critical state changes and commits.

---

## 📅 Phase 8: MCP Server & Integrations
- Model Context Protocol (MCP) server implementation for Claude Desktop, Cursor, and CLI tools.
- Barsa Skill guidelines instructing AI agents on automated memory recording.
- External cloud storage adapters (User S3 buckets, GitHub repository sync).
