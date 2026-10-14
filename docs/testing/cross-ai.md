# Cross-AI Integration Testing Guide

This document describes the structure, execution, and interpretation of the cross-AI test suite located under `tests/integration/cross_ai/`.

## Test Suite Structure

```
tests/integration/cross_ai/
├── test_mcp_sessions.py        # Independent, isolated MCP client sessions
├── test_project_resume.py      # Real-world Spring Boot handoff & rubric scoring
├── test_cross_account_access.py # Workspace authorization & cross-account access
├── test_bms_portability.py     # Lossless package export/import across storages
├── test_conflict_handling.py   # Multi-agent concurrency & DAG branch conflict handling
├── test_token_comparison.py    # Quantitative token benchmarks (3 conditions)
└── test_reliability.py         # 15 edge-case failure & resilience scenarios
```

## Running the Tests

To run the entire cross-AI suite:

```bash
pytest tests/integration/cross_ai/ -v
```

To run a specific test file:

```bash
pytest tests/integration/cross_ai/test_project_resume.py -v
```

## Adding New Test Scenarios

1. Create a client configuration using `ClientSessionConfig`:
   ```python
   config = ClientSessionConfig(client_id="new-agent", provider=AIProvider.GOOGLE, model="gemini-1.5-pro")
   ```
2. Wrap with `MCPClientAdapter` and `AgentSession`.
3. Assert state mutations using the 7-dimension `ContextContinuityEvaluator.evaluate(...)` rubric.
