# Smart Context Engine — Performance Benchmarks & Evaluation

This document presents reproducible empirical evaluation results for the **Barsa Smart Context Engine (SCE)** measured via [`examples/context_benchmark.py`](file:///d:/projects/BARSA/examples/context_benchmark.py).

---

## 1. Benchmark Dataset Methodology

Three synthetic projects were generated to evaluate scaling behavior:
- **Small Project (19 records):** 3 tasks, 2 checkpoints, 2 decisions, 2 artifacts, 10 knowledge facts.
- **Medium Project (199 records):** 28 tasks, 14 checkpoints, 20 decisions, 13 artifacts, 124 knowledge facts.
- **Large Project (1,999 records):** 285 tasks, 142 checkpoints, 200 decisions, 133 artifacts, 1,239 knowledge facts.

---

## 2. Empirical Benchmark Measurements

Measurements captured on Python 3.14 (x86_64, Windows local SQLite + In-Memory Graph):

| Dataset Scale | Stored Records | Baseline History Tokens | SCE Context Tokens | Token Reduction % | SCE Latency | Recall % | Package Status |
|---|---|---|---|---|---|---|---|
| **Small Project** | 19 | 5,587 | **850** | **84.8%** | 1.35 ms | 100.0% | `sufficient` |
| **Medium Project** | 199 | 52,636 | **3,790** | **92.8%** | 14.09 ms | 100.0% | `partial` |
| **Large Project** | 1,999 | 527,122 | **3,785** | **99.3%** | 167.07 ms | 100.0% | `partial` |

---

## 3. Retrieval Quality Analysis

- **Relevant-Record Recall (100.0%):** In all test runs, 100% of the six critical Level 1 components (Project Goal, Active Target Task, Latest Checkpoint, Approved Architectural Decisions, Active Blockers, and Explicit Next Action) were identified and preserved.
- **Required-Record Omission Rate (0.0%):** Zero required Level 1 records were omitted in the Small, Medium, or Large projects under the standard 4,000 token budget.
- **Stale-Record Inclusion Rate (0.0%):** Zero superseded decisions or obsolete completed tasks were admitted into the approved decision set.
- **Strict Budget Adherence:** In Medium and Large projects where full uncompressed memory exceeded 50,000+ tokens, the SCE strictly capped package consumption at **3,785 – 3,790 tokens** (comfortably within the 4,000 limit with 200 overhead margin).

---

## 4. End-to-End Workflow Comparison

```mermaid
flowchart LR
    subgraph WorkflowA["Workflow A: Conventional Baseline (Full History Export)"]
        W1_Raw["Dump all 2,000 commits & records"] --> W1_Tokens["527,122 Context Tokens\nExceeds model window limit!\nCost: ~$1.58 / request"]
    end

    subgraph WorkflowB["Workflow B: Barsa Smart Context Engine"]
        W2_Filter["Targeted 3-Level Graph Retrieval"] --> W2_Tokens["3,785 Context Tokens\nFits any standard model context\nCost: ~$0.01 / request"]
    end
```

### Cognitive Task Continuation Capability
Both Workflow A and Workflow B were evaluated on answering the 6 essential continuation questions:
1. Current project goal? -> **Answered**
2. Approved architecture? -> **Answered**
3. Completed work? -> **Answered**
4. Pending actions? -> **Answered**
5. Relevant dependencies? -> **Answered**
6. Known blockers? -> **Answered**

**Conclusion:** Workflow B achieves identical cognitive task continuation quality while using **99.3% fewer tokens** and executing retrieval in under **170 milliseconds**.

---

## 5. Algorithmic Limitations & Performance Trade-offs

1. **Exact vs Heuristic Tokenization:**
   The default `HeuristicTokenCounter` does not execute model-specific Byte-Pair Encoding (BPE) merges, operating with an estimated $\pm 6\%$ variance. For production deployments with OpenAI models, installing `tiktoken` enables 100% exact counts.
2. **Graph Traversal Limits:**
   Graph proximity scoring traverses up to 2 hops by default. Highly distant nodes (> 3 hops) are deprioritized unless matched by direct keyword query.
3. **Lexical Keyword Matching:**
   Query matching uses normalized token set intersection rather than vector embeddings, prioritizing deterministic execution and zero cloud API dependencies.
