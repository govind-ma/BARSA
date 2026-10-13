# Barsa Memory Standard (BMS v0.1) Overview

## 1. What is BMS?

The **Barsa Memory Standard (BMS)** is an open, provider-independent data specification that allows human developers and heterogeneous AI systems (Claude, ChatGPT, Gemini, local open-source LLMs, coding agents) to persist, retrieve, exchange, and resume work without vendor lock-in.

Think of BMS as the **JVM bytecode or SQL standard for AI memory**: regardless of which model created the state or where it is executed, any compliant AI runtime can inspect and continue the work.

```
┌─────────────────┐        ┌──────────────────┐        ┌─────────────────┐
│     Claude      │        │      ChatGPT     │        │     Gemini      │
│  (Architecture) │        │ (Implementation) │        │ (Bio-Informatics│
└────────┬────────┘        └────────▲─────────┘        └────────▲────────┘
         │                          │                           │
         │ Exports                  │ Imports                   │ Extends
         ▼                          │                           │
┌───────────────────────────────────┴───────────────────────────┴────────┐
│                   Barsa Memory Package (BMS v0.1)                      │
│                                                                        │
│  • Workspace & Project Definitions                                     │
│  • Knowledge Records (Facts, Observations, Hypotheses)                 │
│  • Architectural & Technical Decisions                                 │
│  • Task State & Dependency Graph                                       │
│  • Resume Checkpoints (Next Actions, Completed Actions, Blockers)      │
│  • Artifact References & Graph Relationships                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. BMS vs. Raw Conversation History

A common anti-pattern in AI tooling is serializing the raw message transcript (`"user": "...", "assistant": "..."`). BMS explicitly departs from this approach:

| Dimension | Raw Conversation History | Barsa Memory Standard (BMS) |
|---|---|---|
| **Structure** | Unstructured conversational dialogue | Typed, validated semantic entities |
| **Noise** | High token bloat, pleasantries, dead-end tangents | Distilled, verified facts, tasks, and architectural decisions |
| **Model Independence** | Tied to provider formatting, system prompts, role names | Strictly model-agnostic JSON entities |
| **Resumability** | Next model must re-read full transcript and guess state | `ResumeCheckpoint` defines explicit `next_action`, blockers, and refs |
| **Graph Queries** | Impossible without ad-hoc parsing | Native `RelationshipRecord` graph edges |
| **Privacy / Safety** | May leak internal chain-of-thought or provider prompts | Preserves only durable project decisions and artifacts |

---

## 3. Storage & Provider Independence

BMS entities:
- Are pure JSON schemas governed by Pydantic v2.
- Contain zero dependencies on cloud vendors (AWS, GCP, Azure), database drivers (PostgreSQL, Redis), or graph backends (FalkorDB).
- Can be saved as local `.json` files, stored in Git repositories, synced to S3, or transmitted over REST APIs and MCP tools.
