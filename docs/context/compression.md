# Deterministic Context Compression & Deduplication

The **Compression & Deduplication** subsystem ([`src/barsa/context/compression.py`](file:///d:/projects/BARSA/src/barsa/context/compression.py) and [`src/barsa/context/deduplication.py`](file:///d:/projects/BARSA/src/barsa/context/deduplication.py)) strips redundant transport overhead while maintaining 100% semantic fidelity.

---

## 1. Why Deterministic Compression?

Many AI memory architectures attempt to compress memory by invoking a secondary LLM to "summarize" past notes. In production infrastructure, this approach has severe failure modes:
1. **Hallucination & Drift:** LLMs frequently omit critical negative constraints (e.g. changing *"Do NOT use MongoDB"* to *"Evaluated MongoDB"*).
2. **Latency & Cost Overhead:** Making external LLM calls on every context retrieval adds 1–3 seconds of latency and doubles API costs.
3. **Loss of Provenance:** A summarized paragraph destroys direct record identifiers and commit linkages.

**The Barsa Approach:** Purely deterministic, structural compression:
- Strips internal database bookkeeping fields (`_sqlite_id`, duplicate timestamps, vector blobs).
- Preserves exact technical rationales and decision statements verbatim.
- Replaces repeated inline object definitions with clean canonical references.

---

## 2. Compression Rules by Record Type

| Record Type | Uncompressed Raw Form | Compressed Form in Context Package |
|---|---|---|
| **`TaskRecord`** | Full JSON with DB auto-increments, changelogs, and redundant timestamps | `{id, title, status, priority, assignee_id, tags}` |
| **`DecisionRecord`**| Full RFC payload with voting metadata and audit logs | `{id, title, status, summary, rationale, selected_option}` |
| **`ResumeCheckpoint`**| Raw serialized state with internal revision hashes | `{id, task_id, status, completed_actions, pending_actions, next_action, blockers}` |
| **`KnowledgeRecord`**| Extended ingest headers and vector embeddings | `{id, title, content, is_verified, source}` |

---

## 3. Contradiction Preservation (The Golden Rule)

> **Contradictions are NOT duplicates. They are active engineering trade-offs.**

If two records make opposing claims:
- Record A: *"Adopt PostgreSQL for financial transaction consistency."*
- Record B: *"Adopt MySQL for existing DBA team operational familiarity."*

The `RecordDeduplicator` computes semantic fingerprints of normalized content. Because the statements differ, both records are preserved in the candidate pool. The `RelevanceRanker` then scores both records according to their respective review statuses (`approved` vs `proposed`), allowing the receiving agent to see the trade-off clearly.
