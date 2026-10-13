# ADR 0001: Local-First and Storage-Independent Architecture

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Software Architect & Core Engineering Team

---

## Context

BARSA is designed to store cross-agent memories, decisions, and task history across heterogeneous AI systems. Traditional cloud architectures enforce vendor lock-in by hosting user data on centralized servers, creating ongoing hosting costs for the project maintainers and raising privacy concerns for users who operate on proprietary codebases.

## Decision

1. **Storage Independence via Protocols:**
   We decouple the domain model (Barsa Memory Standard / BMS) from physical persistence by introducing a Python `typing.Protocol` named `StorageProvider`. The core application engine never makes direct assumptions about filesystem paths, S3 buckets, or database sockets.

2. **Local-First Default:**
   The default storage backend operates locally on the user's machine using a configurable data directory (`BARSA_DATA_DIR`, default `.barsa/`). Users do not need an internet connection or external cloud accounts to run BARSA.

3. **Pluggable Future Adapters:**
   Future adapters (User-owned S3 buckets, GitHub Git synchronization, MinIO) will implement the identical `StorageProvider` interface without requiring alterations to core memory logic.

## Consequences

- **Positive:**
  - Zero cloud hosting bills for user data storage.
  - Complete data privacy and sovereignty for users.
  - Clean testability using mock or in-memory implementations.
- **Negative:**
  - Multi-device synchronization requires explicit storage adapters (e.g. Git or S3) to be implemented in subsequent phases.
