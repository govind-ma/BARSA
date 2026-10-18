# Project ATLAS — FalkorDB Cypher Queries Reference

This guide documents the OpenCypher queries executed by BARSA against the Project ATLAS knowledge graph partition (`barsa_atlas_proj_atlas`).

---

## 1. Top Unfinished Tasks with Upstream Prerequisite Analysis

Queries all incomplete tasks in the ATLAS project, traverses their `DEPENDS_ON` relationships, and collects prerequisite statuses.

```cypher
MATCH (p:Project {id: $project_id})-[:HAS_TASK]->(t:Task)
WHERE t.status IN ['todo', 'in_progress', 'blocked']
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
RETURN t.id AS comp_id, 
       t.raw_id AS raw_id, 
       t.title AS title, 
       t.status AS status,
       coalesce(t.priority, 'medium') AS priority,
       collect(DISTINCT {id: dep.raw_id, title: dep.title, status: dep.status}) AS dependencies
```

---

## 2. Active Blocker & Impediment Traversal

Traverses direct `BLOCKED_BY` and inverted `BLOCKS` relationships between tasks and unresolved issues.

```cypher
MATCH (t:Task {project_id: $project_id})
OPTIONAL MATCH (t)-[:BLOCKED_BY]->(b)
OPTIONAL MATCH (b2)-[:BLOCKS]->(t)
RETURN t.raw_id AS task_id,
       collect(DISTINCT coalesce(b.raw_id, b.id, b2.raw_id, b2.id)) AS blockers
```

---

## 3. Task Required Capabilities & Agent Skill Matching

Matches technical competency requirements (`REQUIRES`) with agent capabilities (`HAS_CAPABILITY`).

```cypher
// Query Task Capabilities
MATCH (t:Task {project_id: $project_id})-[:REQUIRES]->(c:Capability)
RETURN t.raw_id AS task_id, 
       collect(DISTINCT coalesce(c.name, c.raw_id, c.id)) AS capabilities

// Query Agent Competencies
MATCH (a:Agent {project_id: $project_id})
OPTIONAL MATCH (a)-[:HAS_CAPABILITY]->(c:Capability)
RETURN a.raw_id AS agent_id, 
       coalesce(a.name, a.raw_id) AS agent_name,
       coalesce(a.provider, 'AI') AS provider,
       collect(DISTINCT coalesce(c.name, c.raw_id, c.id)) AS capabilities
```

---

## 4. Architectural Decision Lineage (ADRs Affecting Tasks)

Traverses `AFFECTS`, `REFERENCES`, and `SUPPORTS` relationships up to 2 hops to discover relevant ADRs.

```cypher
MATCH (t:Task {project_id: $project_id})-[r:REFERENCES|AFFECTS|SUPPORTS*1..2]-(d:Decision)
RETURN t.raw_id AS task_id,
       collect(DISTINCT {id: d.raw_id, title: d.title, decision: d.decision, status: d.status}) AS decisions
```

---

## 5. Emergency Supply Impact Query (Medical Pre-emption)

Discovers all tasks and modules impacted by an emergency hospital allocation demand.

```cypher
MATCH (req:Requirement {category: 'emergency'})<-[:REFERENCES|RESOLVES]-(t:Task)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
RETURN req.title AS emergency_req,
       t.raw_id AS task_id,
       t.title AS task_title,
       t.status AS task_status,
       dep.raw_id AS prereq_task,
       d.title AS guiding_adr
```
