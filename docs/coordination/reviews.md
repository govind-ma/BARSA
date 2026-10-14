# Review Workflows & Self-Approval Prevention

The **Barsa Review Workflow** integrates task completion with Git-style memory version control (`VersionControlEngine`), ensuring all architectural and critical code changes undergo formal peer review before merging.

---

## 1. Review & Verification Workflow

```mermaid
flowchart TD
    Worker["Worker Agent\n(author)"] --> Submit["Submit Task Result\n(requires_review=true)"]
    Submit --> Branch["Create Feature Branch & Commit Changes\n(via VersionControlEngine)"]
    Branch --> Prop["Open MergeProposal\n(title, author_id, changes)"]
    Prop --> StatusReview["Task Transitions to UNDER_REVIEW"]
    StatusReview --> AttemptSelf{"Author Attempts\nReview?"}
    AttemptSelf -- Yes --> Block["400 VALIDATION ERROR\nSelf-approval prohibited!"]
    AttemptSelf -- No --> PeerReview["Independent Reviewer\n(Human or Peer Agent)"]
    PeerReview --> Decision{"Review Decision"}
    Decision -- changes_requested --> ReWork["Task Remains Incomplete\nFeedback returned to Author"]
    Decision -- rejected --> Close["Proposal Rejected\nTask Fails / Needs Redo"]
    Decision -- approved --> Merge["Merge Proposal to Main Branch"]
    Merge --> Complete["Task Transitions to COMPLETED\nDependent Tasks Promoted to READY"]
```

---

## 2. Self-Approval Prohibition Enforcement

In `CoordinatorEngine.submit_review_decision`:

```python
proposal = self.vc.get_merge_proposal(project_id, proposal_id)
if proposal.author_id == reviewer_agent_id:
    raise ValidationError(
        f"Self-approval prohibited: reviewer '{reviewer_agent_id}' cannot review their own proposal '{proposal_id}'"
    )
```

This invariant ensures that no agent can unilaterally approve its own architectural decisions or code contributions, preventing hallucinated or faulty updates from silently entering shared memory.

---

## 3. Review Status Values

- `approved`: Formal approval signoff. When associated with an `UNDER_REVIEW` task, transitions the task to `completed` and unlocks downstream dependent tasks.
- `changes_requested`: Reviewer requests revisions. The task remains uncompleted until another submission and review cycle occurs.
- `rejected`: The proposal is formally declined.
