# BARSA Graph Security and Multi-Project Isolation

## 1. Cypher Injection Prevention

Cypher injection occurs when untrusted user or agent inputs (e.g. record content, titles, IDs) are concatenated directly into Cypher query strings.

### BARSA Security Invariants:
1. **Zero Raw String Concatenation for Values:**
   All user-supplied values, identifiers, timestamps, titles, descriptions, and payloads **MUST** be passed through Cypher query parameters:
   ```python
   # STRICTLY FORBIDDEN:
   # query = f"MATCH (n {{id: '{user_id}'}}) RETURN n"
   
   # MANDATORY BARSA PATTERN:
   query = "MATCH (n {id: $id, project_id: $project_id}) RETURN n"
   params = {"id": node_id, "project_id": project_id}
   graph.query(query, params)
   ```

2. **Allowlisted Labels and Relationship Types:**
   Cypher syntax does not allow labels or relationship types to be parameterized via `$param`. Therefore, any dynamic interpolation of labels or relationship types is strictly guarded by an immutable allowlist enum:
   ```python
   ALLOWED_LABELS = {l.value for l in GraphNodeType}
   ALLOWED_RELS = {r.value for r in GraphRelationshipType}

   if label not in ALLOWED_LABELS:
       raise SecurityError(f"Disallowed graph label: {label}")
   ```

---

## 2. Multi-Project Isolation

BARSA is designed to host multiple concurrent projects within a single database instance without cross-project data leakage:

1. **Composite Identifiers:**
   Every node ID in the graph store is prefixed with the project ID:
   $$\text{node\_id} = \text{project\_id} + \text{":"} + \text{raw\_id}$$
2. **Mandatory Query Filtering:**
   Every Cypher query and memory graph traversal enforces:
   $$\text{node.project\_id} = \$project\_id$$
3. **Partition Isolation:**
   Deleting or rebuilding one project's graph namespace using `clear_project_graph(project_id)` only executes:
   ```cypher
   MATCH (n {project_id: $project_id}) DETACH DELETE n
   ```
   Other projects in the database remain completely unaffected.

---

## 3. Least-Privilege & Connection Credentials

- Connection strings are configured via environment variables:
  - `BARSA_GRAPH_ENABLED`
  - `BARSA_FALKORDB_HOST`
  - `BARSA_FALKORDB_PORT`
  - `BARSA_FALKORDB_PASSWORD`
  - `BARSA_FALKORDB_GRAPH_PREFIX`
- Passwords and secrets are redacted from logs, representations, and debug endpoints via Pydantic `SecretStr`.
