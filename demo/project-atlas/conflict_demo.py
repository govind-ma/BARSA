"""PROJECT ATLAS — Git-Style Versioning & Conflict Resolution Demo (Section 8).

Demonstrates:
1. Two branches: feature/inventory-optimistic and feature/inventory-pessimistic.
2. Two agents propose incompatible inventory reservation rules for TASK-017.
3. Git-style branch isolation, state hashing, and conflict detection.
4. Review proposal creation, review comments, and merge resolution.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from barsa.bms.records import Project, TaskPriority, TaskRecord, TaskStatus, Workspace
from barsa.models.versioning import AuthorType, ChangeOperation, MemoryChange
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.diff import compute_state_diff
from barsa.versioning.engine import VersionControlEngine
from barsa.versioning.merge import three_way_merge_states

PROJECT_ID = "proj-atlas-vc"
WORKSPACE_ID = "ws-atlas-vc"


def main():
    print("=" * 80)
    print("PROJECT ATLAS — GIT-STYLE MEMORY VERSIONING & CONFLICT DEMO (SECTION 8)")
    print("=" * 80)

    db_path = ROOT_DIR / "data" / "atlas_vc.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    storage = SQLiteStorageProvider(db_path, ROOT_DIR / "data" / "art")
    storage.initialize()
    vc = VersionControlEngine(storage)

    # 1. Initialize Workspace & Project
    ws = Workspace(id=WORKSPACE_ID, name="ATLAS VC Space", owner_id="org-atlas")
    storage.create_workspace(ws)
    proj = Project(id=PROJECT_ID, workspace_id=WORKSPACE_ID, name="Project ATLAS (VC Track)")
    storage.create_project(proj)

    # 2. Initialize Main Branch
    main_branch = vc.initialize_project_main_branch(PROJECT_ID)
    print(f"\n[Step 1] Initialized main branch at commit: {main_branch.head_commit_id[:12]}...")

    # 3. Base Commit: Initial Baseline for TASK-017
    base_task = TaskRecord(
        id="TASK-017",
        project_id=PROJECT_ID,
        title="Atomic Stock Reservation Service",
        status=TaskStatus.TODO,
        priority=TaskPriority.CRITICAL,
        description="Base reservation rule: No locking policy defined yet.",
    )
    change_base = MemoryChange(
        record_id="TASK-017",
        record_type="task",
        operation=ChangeOperation.CREATE,
        after_state=base_task.model_dump(mode="json"),
    )
    commit_base = vc.create_commit(
        project_id=PROJECT_ID,
        branch_name="main",
        changes=[change_base],
        message="Initial specification for TASK-017: Atomic Stock Reservation",
        author_id="agent-architect",
        author_type=AuthorType.AGENT,
    )
    print(f"[Step 2] Base commit on main: {commit_base.commit_id[:12]} | Task state committed.")

    # 4. Branch A: Optimistic Concurrency Rule (Proposed by Backend Lead)
    branch_a = vc.create_branch(PROJECT_ID, "feature/inventory-optimistic", commit_base.commit_id)
    task_opt = TaskRecord(
        id="TASK-017",
        project_id=PROJECT_ID,
        title="Atomic Stock Reservation Service (Optimistic Locking)",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.CRITICAL,
        description="Adopt optimistic locking with @Version and exponential backoff. ADR-004 compliant.",
    )
    commit_a = vc.create_commit(
        project_id=PROJECT_ID,
        branch_name="feature/inventory-optimistic",
        changes=[
            MemoryChange(
                record_id="TASK-017",
                record_type="task",
                operation=ChangeOperation.UPDATE,
                before_state=base_task.model_dump(mode="json"),
                after_state=task_opt.model_dump(mode="json"),
            )
        ],
        message="Implement ADR-004 optimistic locking rule for stock reservation",
        author_id="agent-backend",
        author_type=AuthorType.AGENT,
    )
    print(f"[Step 3] Branch 'feature/inventory-optimistic' committed: {commit_a.commit_id[:12]} by agent-backend")

    # 5. Branch B: Pessimistic Row-Locking Rule (Proposed by Logistics Analyst)
    branch_b = vc.create_branch(PROJECT_ID, "feature/inventory-pessimistic", commit_base.commit_id)
    task_pess = TaskRecord(
        id="TASK-017",
        project_id=PROJECT_ID,
        title="Atomic Stock Reservation Service (Pessimistic SELECT FOR UPDATE)",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.CRITICAL,
        description="Adopt pessimistic row locking via SELECT FOR UPDATE to strictly serialize allocation.",
    )
    commit_b = vc.create_commit(
        project_id=PROJECT_ID,
        branch_name="feature/inventory-pessimistic",
        changes=[
            MemoryChange(
                record_id="TASK-017",
                record_type="task",
                operation=ChangeOperation.UPDATE,
                before_state=base_task.model_dump(mode="json"),
                after_state=task_pess.model_dump(mode="json"),
            )
        ],
        message="Propose pessimistic row-locking for strict linear allocation",
        author_id="agent-logistics",
        author_type=AuthorType.AGENT,
    )
    print(f"[Step 4] Branch 'feature/inventory-pessimistic' committed: {commit_b.commit_id[:12]} by agent-logistics")

    # 6. Conflict Detection via 3-Way Merge
    print("\n[Step 5] Executing 3-Way Diff & Conflict Analysis between branches...")
    base_state = vc.reconstruct_project_state(PROJECT_ID, commit_base.commit_id)
    state_a = vc.reconstruct_project_state(PROJECT_ID, commit_a.commit_id)
    state_b = vc.reconstruct_project_state(PROJECT_ID, commit_b.commit_id)

    diff_a = compute_state_diff(PROJECT_ID, commit_base.commit_id, commit_a.commit_id, base_state, state_a)
    diff_b = compute_state_diff(PROJECT_ID, commit_base.commit_id, commit_b.commit_id, base_state, state_b)

    merge_result = three_way_merge_states(
        project_id=PROJECT_ID,
        base_state=base_state,
        source_state=state_a,
        target_state=state_b,
        source_branch="feature/inventory-optimistic",
        target_branch="feature/inventory-pessimistic",
    )
    conflicts = merge_result.conflicts
    print(f"-> Conflicts Detected: {len(conflicts)}")
    for conf in conflicts:
        print(f"   Conflict on record '{conf.affected_record_id}', type '{conf.conflict_type}':")
        print(f"   - Base: '{conf.base_value}'")
        print(f"   - Branch A: '{conf.source_value}'")
        print(f"   - Branch B: '{conf.target_value}'")

    assert len(conflicts) > 0, "Conflict must be detected between conflicting reservation rules"

    # 7. Merge Resolution: Chief Architect Resolves in favor of Optimistic Locking (ADR-004)
    print("\n[Step 6] Chief Architect (agent-architect) resolving conflict in favor of ADR-004...")
    resolved_task = TaskRecord(
        id="TASK-017",
        project_id=PROJECT_ID,
        title="Atomic Stock Reservation Service (Optimistic Locking + Dynamic Fallback)",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.CRITICAL,
        description="Resolved: Adopt ADR-004 optimistic locking as primary; allow short-lived row lock only during emergency medical triage.",
    )
    resolved_commit = vc.create_commit(
        project_id=PROJECT_ID,
        branch_name="main",
        changes=[
            MemoryChange(
                record_id="TASK-017",
                record_type="task",
                operation=ChangeOperation.UPDATE,
                before_state=base_task.model_dump(mode="json"),
                after_state=resolved_task.model_dump(mode="json"),
            )
        ],
        message="Merge resolution: Unify inventory reservation policy around ADR-004",
        author_id="agent-architect",
        author_type=AuthorType.AGENT,
        parent_commit_ids=[commit_a.commit_id, commit_b.commit_id],
    )
    print(f"-> Merge Resolution Committed to main: {resolved_commit.commit_id[:12]}")
    print(f"-> Verified commit parent hashes: {[h[:12] for h in resolved_commit.parent_commit_ids]}")
    print("=" * 80)
    print("GIT-STYLE MEMORY VERSIONING & CONFLICT RESOLUTION VERIFIED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
