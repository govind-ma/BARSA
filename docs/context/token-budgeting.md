# Token Budgeting & Counting Engine

The **TokenBudgetAllocator** ([`src/barsa/context/budget.py`](file:///d:/projects/BARSA/src/barsa/context/budget.py)) and **TokenCounter** ([`src/barsa/context/token_counter.py`](file:///d:/projects/BARSA/src/barsa/context/token_counter.py)) enforce strict token upper bounds while reserving adequate room for response generation and JSON framing overhead.

---

## 1. Token Budget Allocation Algorithm

```mermaid
flowchart TD
    Start["Inputs: max_context_tokens, reserved_overhead, mandatory_records, ranked_candidates"] --> DeductOverhead["Calculate Available Budget:\navailable = max_context_tokens - reserved_overhead"]
    
    DeductOverhead --> MeasureMandatory["Measure Mandatory Level 1 Context\n(Project Info, Task, Latest Checkpoint, Approved Decisions, Blockers)"]
    
    MeasureMandatory --> CheckBudget{"Does Mandatory Context\nFit in Available Budget?"}
    
    CheckBudget -->|No (Exceeds Available)| MarkInsufficient["Set completeness = INSUFFICIENT\nReport exact mandatory token count\nOmit all optional candidates"]
    
    CheckBudget -->|Yes| PackMandatory["Pack all Level 1 Mandatory Records\nTrack remaining available tokens"]
    
    PackMandatory --> LoopCandidates["Iterate Candidates by\nRelevance Score Descending"]
    
    LoopCandidates --> CheckFit{"Does candidate record\nfit in remaining space?"}
    
    CheckFit -->|Yes| AddRecord["Append record to Context Package\nDecrement remaining budget"]
    CheckFit -->|No| OmitRecord["Append record ID to omitted_record_refs\nFlag completeness = PARTIAL"]
    
    AddRecord --> MoreCandidates{"More candidate\nrecords?"}
    OmitRecord --> MoreCandidates
    
    MoreCandidates -->|Yes| LoopCandidates
    MoreCandidates -->|No| Finalize["Emit Final BarsaContextPackage"]
    MarkInsufficient --> Finalize
```

---

## 2. Tokenizer Implementations

Barsa supports pluggable tokenizer implementations conforming to the `TokenCounter` protocol:

| Tokenizer | Type | When Used | Details |
|---|---|---|---|
| **`TiktokenTokenCounter`** | Exact | When `tiktoken` is installed and an OpenAI / compatible model is requested | Provides 100% exact BPE token counts for `cl100k_base`, `o200k_base`, etc. |
| **`HeuristicTokenCounter`** | Estimated | Default fallback (zero external dependencies) | Multi-factor character and word boundary calculation with CJK/Unicode compensation. Accurate within $\pm 6\%$ of BPE tokenizers on JSON and code. |
| **`ExactMockTokenCounter`** | Exact | Test suites and deterministic unit tests | Guarantees exact, reproducible mock counts without external library variability. |

---

## 3. Insufficient Budget Behavior

When an agent or user requests a budget too small to accommodate even Level 1 essential context:
- Barsa returns `completeness: "insufficient"`.
- Explains the exact token deficit in `completeness_reasons`.
- Never silently drops an active blocker, approved decision, or checkpoint to force-fit an impossible budget.

Example response:

```json
{
  "completeness": "insufficient",
  "completeness_reasons": [
    "Mandatory Level 1 essential context (840 tokens) exceeds available budget (500 tokens). Budget is insufficient."
  ],
  "token_usage": {
    "count": 840,
    "budget": 500,
    "method": "heuristic_char_word_ratio_v1",
    "tokenizer": "heuristic-cl100k-approx",
    "reserved_margin": 100,
    "utilization_percent": 168.0
  }
}
```
