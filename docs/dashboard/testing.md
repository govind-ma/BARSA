# Dashboard Testing & Verification Guide

This document describes the automated test suite and verification procedures for the Barsa Web Dashboard.

---

## 1. Test Architecture

The dashboard test suite uses:
- **Test Runner:** [Vitest](https://vitest.dev/) (fast ESM-native test runner)
- **DOM Simulation:** [jsdom](https://github.com/jsdom/jsdom)
- **Component Testing:** [React Testing Library](https://testing-library.com/react)
- **Assertion Helpers:** `@testing-library/jest-dom`

---

## 2. Test Coverage Matrix (24 Verification Scenarios)

The test file `frontend/src/test/dashboard.test.tsx` implements 21 test blocks covering all 24 required scenarios:

1. **Dashboard Rendering:** Renders system overview, stat cards, and metrics.
2. **Workspace List:** Lists workspaces with names, IDs, and descriptions.
3. **Project Creation:** Opens modal, accepts input, and calls `api.createProject`.
4. **Project Details:** Shows project status, goals, commits, and decisions.
5. **Memory Search:** Real-time search query filtering over titles and summaries.
6. **Memory Record Inspection:** Clicking a record renders full BMS details and content.
7. **Commit History:** Lists commit hashes, authors, and timestamps.
8. **Diff Visualization:** Structured before/after field changes against parent commit.
9. **Conflict Display:** Three-way merge conflicts with base, source, and target values.
10. **Review Actions:** Review list, branch comparisons, and approval states.
11. **Graph Navigation:** Renders entity nodes and inspects property details.
12. **Graph Unavailable State:** Gracefully displays inactive FalkorDB status banner.
13. **Agent Registry:** Shows agent providers, models, tools, and heartbeats.
14. **Task Board:** 6-column coordination Kanban lifecycle columns.
15. **Checkpoint Retrieval:** Retrieves checkpoint history for active projects.
16. **Context Package Generation:** Invokes Smart Context Engine and renders copyable prompt.
17. **Permission-Aware UI:** Displays authenticated principal identity and superuser clearance.
18. **Credential Revocation & Generation:** Issues new key and displays secret once with warning.
19. **Package Import:** Validates and imports BMS JSON memory containers.
20. **Package Export:** Triggers download of serialized project memory.
21. **API Error Handling:** Displays clean user-friendly alerts on server failure.
22. **Unauthorized Responses:** Handles 401/403 status codes without crashing.
23. **Responsive Navigation:** Renders sidebar navigation links.
24. **Keyboard Accessibility:** Dismisses modal dialogs via the `Escape` key.

---

## 3. Running the Test Suite

### Running Frontend Tests:
```powershell
cd frontend
npm test
```

### Running TypeScript Check & Production Build:
```powershell
cd frontend
npm run build
```

### Running Full Backend Tests:
```powershell
.\.venv\Scripts\pytest -q
```
