# Essential Cypher Queries in BARSA's Continuation Engine

All task selection, blocker filtering, skill matching, and context compilation in `barsa_graph_resume(project_id, agent_id)` are executed directly in **FalkorDB** using OpenCypher.

Below are the five parameterized Cypher queries executed during continuation.

---

## Query 1: Unfinished Tasks & Multi-Hop Prerequisite Evaluation

Identifies all tasks in the project backlog that are not yet marked `done`, and collects their direct prerequisite dependencies and statuses.

### Cypher Query
```cypher
MATCH (p:Project {id: $project_id})-[:HAS_TASK]->(t:Task)
WHERE t.status IN ['todo', 'in_progress', 'pending', 'open']
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
RETURN t.id AS task_id, 
       t.title AS title, 
       t.priority AS priority, 
       t.status AS status,
       collect(dep.id) AS dep_ids, 
       collect(dep.status) AS dep_statuses
```

### Parameters
```json
{
  "project_id": "proj-hackathon-1"
}
```

### Live Output Example
| task_id | title | priority | status | dep_ids | dep_statuses |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-004` | JWT Token Generation & Validation | high | todo | `["TASK-002"]` | `["done"]` |
| `TASK-005` | Low Stock Alert Service | medium | todo | `["TASK-003"]` | `["done"]` |
| `TASK-006` | Sales Reporting & CSV Export API | medium | todo | `["TASK-003"]` | `["done"]` |
| `TASK-007` | React Inventory Dashboard UI | high | todo | `["TASK-004", "TASK-003"]` | `["todo", "done"]` |

**Graph Reasoning Insight**: FalkorDB automatically reveals that while `TASK-007` has high priority, its dependency `TASK-004` is still `todo`. Thus, `TASK-007` is disqualified from immediate execution.

---

## Query 2: Active Blocker & Incident Traversal

Detects active impediments blocking tasks. A task connected via `[:BLOCKED_BY]` to an unresolved `Issue` or incomplete `Task` cannot be assigned.

### Cypher Query
```cypher
MATCH (t:Task)-[:BLOCKED_BY]->(b)
WHERE b.status IS NULL OR b.status IN ['open', 'in_progress', 'blocked', 'active']
RETURN t.id AS task_id, 
       b.id AS blocker_id, 
       labels(b)[0] AS blocker_type,
       coalesce(b.title, b.id) AS blocker_title
```

### Parameters
None (evaluates all active blocker relationships in the graph partition).

### Live Output Example
| task_id | blocker_id | blocker_type | blocker_title |
| :--- | :--- | :--- | :--- |
| `TASK-005` | `ISSUE-101` | `Issue` | Deadlock under concurrent stock checkout test |

**Graph Reasoning Insight**: Even though `TASK-005` had all its `DEPENDS_ON` prerequisites fulfilled, FalkorDB instantly identifies that `TASK-005` is blocked by `ISSUE-101`.

---

## Query 3: Task Required Capabilities Extraction

Queries the specific technical competencies mandated to complete each task.

### Cypher Query
```cypher
MATCH (t:Task)-[:REQUIRES]->(c:Capability)
RETURN t.id AS task_id, 
       c.id AS cap_id, 
       c.name AS cap_name
```

### Parameters
None.

### Live Output Example
| task_id | cap_id | cap_name |
| :--- | :--- | :--- |
| `TASK-004` | `cap-java-spring` | java-spring-boot |
| `TASK-004` | `cap-sec-jwt` | security-jwt |
| `TASK-007` | `cap-react-ts` | react-typescript |

---

## Query 4: Agent Competency Matching

Queries verified capabilities of the agent requesting work to compute skill match bonuses or detect missing competencies.

### Cypher Query
```cypher
MATCH (a:Agent {id: $agent_id})-[:HAS_CAPABILITY]->(c:Capability)
RETURN c.id AS cap_id, 
       c.name AS cap_name
```

### Parameters
```json
{
  "agent_id": "agent-backend-claude"
}
```

### Live Output Example
| cap_id | cap_name |
| :--- | :--- |
| `cap-java-spring` | java-spring-boot |
| `cap-sec-jwt` | security-jwt |
| `cap-mysql-dba` | mysql-dba |

**Graph Reasoning Insight**: Matching agent capabilities against `TASK-004` requirements produces a 100% skill match bonus (+50 points). Conversely, querying for `agent-frontend-gpt4o` yields missing capabilities (`java-spring-boot`, `security-jwt`), safely routing the agent to wait or select a frontend-aligned task.

---

## Query 5: Architectural Decision Records (ADR) & Domain Lineage

Traverses `[:AFFECTS]` and `[:REFERENCES]` relationships to enrich the continuation payload with exact architectural decisions and domain documentation without requiring manual search.

### Cypher Query
```cypher
MATCH (t:Task)
OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
OPTIONAL MATCH (t)-[:REFERENCES]->(k:Knowledge)
RETURN t.id AS task_id,
       collect(DISTINCT {id: d.id, title: d.title, rationale: d.rationale}) AS decisions,
       collect(DISTINCT {id: k.id, title: k.title, snippet: k.content_snippet}) AS knowledge
```

### Parameters
None.

### Live Output Example for `TASK-004`
```json
{
  "task_id": "TASK-004",
  "decisions": [
    {
      "id": "ADR-001",
      "title": "Stateless JWT Authentication with HMAC-SHA256",
      "rationale": "Use stateless JWTs with 15-minute access tokens and Redis-backed refresh rotation."
    }
  ],
  "knowledge": [
    {
      "id": "DOC-001",
      "title": "JWT Secret & Expiry Rules",
      "snippet": "Token format: Bearer <jwt>; expiration claim is exp; subject claim is sub:user_id."
    }
  ]
}
```

---

## 6. Composite Path Traceability

FalkorDB generates verified graph traversal paths for the final recommendation:

- `Task: TASK-004 -(DEPENDS_ON)-> Task: TASK-002 [status=done]`
- `Task: TASK-004 -(REQUIRES)-> Capability: security-jwt <-(HAS_CAPABILITY)- Agent: agent-backend-claude`
- `Decision: ADR-001 -(AFFECTS)-> Task: TASK-004`
- `Task: TASK-004 -(REFERENCES)-> Knowledge: DOC-001`

This complete audit trail ensures that every agent continuation decision is fully deterministic and explainable.
