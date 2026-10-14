# Barsa Conflict Handling Protocol

In distributed and multi-agent systems, concurrent updates to memory records can collide. Barsa prevents data loss by detecting conflicts and enforcing review procedures.

---

## 1. Conflict Types in Memory

| Conflict Type | Description | Example |
| :--- | :--- | :--- |
| **`SAME_FIELD_UPDATE`** | Two agents modified the same record property differently. | Agent A sets task priority to `critical`; Agent B sets it to `low`. |
| **`DELETE_VS_UPDATE`** | One agent deleted a record that another agent concurrently modified. | Agent A deletes obsolete requirement; Agent B updates its acceptance criteria. |
| **`RECORD_COLLISION`** | Two independent agents created different records with identical IDs. | Agent A and B both create `task-01` with different schemas. |
| **`INCOMPATIBLE_RELATIONSHIP`** | A relationship links to a record that was deleted or invalidated. | Dependency edge points to deleted prerequisite task. |

---

## 2. Detection & Inspection Flow

When `barsa_commit` fails with `[STALE_REVISION]` or `[MERGE_CONFLICT]`:

```
┌────────────────────────────────────────┐
│ barsa_commit() returns STALE_REVISION  │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│ 1. Call barsa_get_project()            │
│    Obtain new actual main HEAD         │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│ 2. Call barsa_get_diff()               │
│    From expected_head -> actual HEAD   │
│    Identify what the other agent changed│
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│ 3. Call barsa_list_conflicts()         │
│    List divergent branches & diffs     │
└───────────────────┬────────────────────┘
                    │
                    ▼
       ┌─────────────────────────┐
       │ Do the changes collide? │
       └────┬───────────────┬────┘
         No │               │ Yes
            ▼               ▼
┌───────────────────────┐ ┌──────────────────────────────────────┐
│ Clean Rebase:         │ │ Escalate to User:                    │
│ Update local expected │ │ Present both versions clearly        │
│ to actual HEAD & retry│ │ Request human decision on resolution │
└───────────────────────┘ └──────────────────────────────────────┘
```

---

## 3. Golden Rules of Conflict Resolution

1. **Never Silently Overwrite:** Do not retry with a newer `expected_head` without verifying that your changes do not erase the other agent's work.
2. **Preserve Both Contributions:** When in doubt, preserve the other agent's contribution as a `decision` or `knowledge` record and request human arbitration.
3. **Transparent Reporting:** Report conflicting record IDs and differing field values explicitly to the user.
