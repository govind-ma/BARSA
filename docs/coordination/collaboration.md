# Collaboration, Structured Communication & Issue Routing

The **Barsa Collaboration Engine** enables asynchronous communication between independent agents, issue tracking, and capability-targeted help requests.

---

## 1. Asynchronous Collaboration Flow

```mermaid
sequenceDiagram
    autonumber
    participant Coder as Coding Agent (Agent B)
    participant Coord as Coordinator
    participant QA as Security QA (Agent C)

    Coder->>Coord: report_issue("RSA Key Mismatch in JwtDecoder", evidence={...})
    Coord-->>Coder: Issue logged (issue-123, status: open)
    Coder->>Coord: request_help(issue_id="issue-123", req_caps=["security-testing"])
    Coord-->>Coder: Help request published (help-456)
    Note over Coord: Matcher identifies Agent C as best helper
    QA->>Coord: list_help_requests() -> finds help-456
    QA->>Coord: claim_help_request(help-456)
    QA->>Coord: add_comment("Inspected JWK Set format; auth server provides X.509 JWK at /.well-known/jwks.json")
    QA->>Coord: resolve_issue(issue-123, proposal={solution: "configure jwk-set-uri"})
    Coord-->>QA: Issue marked RESOLVED
    Note over Coder: Coder verifies issue resolution, applies fix, resumes work
```

---

## 2. Structured Collaboration Messages

Messages are stored in the `collaboration_messages` table and support rich message types:

| Type | Purpose |
|---|---|
| `comment` | Standard asynchronous collaboration remark. |
| `observation` | Technical discovery or environmental fact. |
| `issue` | Problem blocker requiring investigation. |
| `help_request` | Call for a peer agent with specific skills to assist. |
| `suggestion` | Proposed alternative architecture or refactoring tip. |
| `progress_update` | Milestone update during long running executions. |
| `resolution` | Confirmed solution fixing an open impediment. |

---

## 3. Help Request Matching

When an agent calls `request_help`:
1. The requester specifies required capabilities (e.g. `["security-testing", "api-testing"]`).
2. The coordinator matches candidate agents who are currently `available`, have valid heartbeats, and possess the required capabilities.
3. The requester is explicitly excluded from being matched to their own help request.
4. The helper claims the request, posts advice or patches, and resolves the issue.
