"""Git-style Memory Version Control Engine for BARSA (Phase 4)."""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from typing import Any

from barsa.bms.base import BMS_VERSION, generate_uuid_str, utc_now
from barsa.bms.serialization import deserialize_record
from barsa.core.exceptions import ConflictError, ResourceNotFoundError, StorageError, ValidationError
from barsa.models.versioning import (
    AuthorType,
    Branch,
    ChangeOperation,
    Commit,
    CommitDiff,
    ConflictRecord,
    ConflictStatus,
    ConflictType,
    MemoryChange,
    MergeProposal,
    ProposalStatus,
    ReviewComment,
    ReviewStatus,
    compute_commit_id,
)
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.diff import compute_state_diff
from barsa.versioning.merge import three_way_merge_states

logger = logging.getLogger("barsa.versioning.engine")


class VersionControlEngine:
    """Core version control engine managing commits, branches, DAG history, diffs, and merges."""

    def __init__(self, storage: SQLiteStorageProvider) -> None:
        self.storage = storage

    def _get_conn(self) -> sqlite3.Connection:
        return self.storage._get_connection()

    # =========================================================================
    # Branching
    # =========================================================================

    def initialize_project_main_branch(self, project_id: str, author_id: str = "system") -> Branch:
        """Ensure a project has an initial commit and a 'main' branch."""
        conn = self._get_conn()
        cur = conn.execute("SELECT head_commit_id FROM branches WHERE project_id = ? AND name = 'main';", (project_id,))
        row = cur.fetchone()
        if row:
            return Branch(
                name="main",
                project_id=project_id,
                head_commit_id=row["head_commit_id"],
            )

        # Create root commit with empty changes
        now = utc_now()
        empty_hash = hashlib.sha256(b"{}").hexdigest()
        root_commit_id = compute_commit_id(
            project_id=project_id,
            parent_commit_ids=[],
            author_id=author_id,
            author_type=AuthorType.AGENT,
            message="Initial project memory root commit",
            created_at=now,
            changes=[],
            resulting_state_hash=empty_hash,
            metadata={"initial": True},
        )

        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO commits (
                    commit_id, project_id, parent_commit_ids_json, author_id, author_type,
                    message, created_at, changes_json, resulting_state_hash, metadata_json, bms_version
                ) VALUES (?, ?, '[]', ?, ?, ?, ?, '[]', ?, ?, ?);
                """,
                (
                    root_commit_id,
                    project_id,
                    author_id,
                    AuthorType.AGENT.value,
                    "Initial project memory root commit",
                    now.isoformat(),
                    empty_hash,
                    json.dumps({"initial": True}),
                    BMS_VERSION,
                ),
            )

            iso_now = now.isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO branches (project_id, name, head_commit_id, created_at, updated_at)
                VALUES (?, 'main', ?, ?, ?);
                """,
                (project_id, root_commit_id, iso_now, iso_now),
            )

            # Emit initial root commit outbox event
            event_id = generate_uuid_str()
            outbox_payload = {
                "project_id": project_id,
                "commit_id": root_commit_id,
                "branch_name": "main",
                "resulting_state_hash": empty_hash,
            }
            conn.execute(
                """
                INSERT INTO graph_outbox (
                    event_id, project_id, commit_id, event_type, payload_json, status, created_at
                ) VALUES (?, ?, ?, 'COMMIT_APPROVED', ?, 'PENDING', ?);
                """,
                (event_id, project_id, root_commit_id, json.dumps(outbox_payload), iso_now),
            )

            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise

        return Branch(
            name="main",
            project_id=project_id,
            head_commit_id=root_commit_id,
            created_at=now,
            updated_at=now,
        )

    def create_branch(self, project_id: str, branch_name: str, start_commit_id: str | None = None) -> Branch:
        """Create a new branch from a commit or the main branch HEAD."""
        clean_name = branch_name.strip()
        if not clean_name:
            raise ValidationError("Branch name cannot be empty")

        conn = self._get_conn()
        # Verify branch doesn't already exist
        cur = conn.execute("SELECT name FROM branches WHERE project_id = ? AND name = ?;", (project_id, clean_name))
        if cur.fetchone():
            raise ConflictError(f"Branch '{clean_name}' already exists in project '{project_id}'")

        if start_commit_id is None:
            # Default to main branch HEAD
            main_branch = self.get_branch(project_id, "main")
            if not main_branch:
                main_branch = self.initialize_project_main_branch(project_id)
            start_commit_id = main_branch.head_commit_id
        else:
            # Verify start_commit_id exists
            if not self.get_commit(project_id, start_commit_id):
                raise ResourceNotFoundError(f"Commit '{start_commit_id}' not found.", "Commit", start_commit_id)

        now = utc_now()
        conn.execute(
            """
            INSERT INTO branches (project_id, name, head_commit_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (project_id, clean_name, start_commit_id, now.isoformat(), now.isoformat()),
        )

        return Branch(
            name=clean_name,
            project_id=project_id,
            head_commit_id=start_commit_id,
            created_at=now,
            updated_at=now,
        )

    def get_branch(self, project_id: str, branch_name: str) -> Branch | None:
        """Retrieve branch reference by name."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT name, project_id, head_commit_id, created_at, updated_at FROM branches WHERE project_id = ? AND name = ?;",
            (project_id, branch_name),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Branch(
            name=row["name"],
            project_id=row["project_id"],
            head_commit_id=row["head_commit_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_branches(self, project_id: str) -> list[Branch]:
        """List all branches for a project."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT name, project_id, head_commit_id, created_at, updated_at FROM branches WHERE project_id = ? ORDER BY name ASC;",
            (project_id,),
        )
        return [
            Branch(
                name=r["name"],
                project_id=r["project_id"],
                head_commit_id=r["head_commit_id"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in cur.fetchall()
        ]

    def delete_branch(self, project_id: str, branch_name: str) -> bool:
        """Delete a branch. Protects the main branch from deletion."""
        if branch_name == "main":
            raise ConflictError("The 'main' branch is protected and cannot be deleted.")

        conn = self._get_conn()
        cur = conn.execute("DELETE FROM branches WHERE project_id = ? AND name = ?;", (project_id, branch_name))
        return cur.rowcount > 0

    # =========================================================================
    # Historical State Reconstruction
    # =========================================================================

    def reconstruct_project_state(self, project_id: str, commit_id: str) -> dict[str, dict[str, Any]]:
        """Reconstruct the entire active record dictionary map at a historical commit."""
        conn = self._get_conn()
        # Verify commit exists
        if not self.get_commit(project_id, commit_id):
            raise ResourceNotFoundError(f"Commit '{commit_id}' not found.", "Commit", commit_id)

        cur = conn.execute(
            """
            SELECT record_id, record_data_json
            FROM commit_record_states
            WHERE project_id = ? AND commit_id = ? AND record_data_json IS NOT NULL;
            """,
            (project_id, commit_id),
        )
        state: dict[str, dict[str, Any]] = {}
        for r in cur.fetchall():
            state[r["record_id"]] = json.loads(r["record_data_json"])
        return state

    def get_record_at_commit(self, project_id: str, record_id: str, commit_id: str) -> dict[str, Any] | None:
        """Retrieve a specific record's state as of a historical commit."""
        conn = self._get_conn()
        if not self.get_commit(project_id, commit_id):
            raise ResourceNotFoundError(f"Commit '{commit_id}' not found.", "Commit", commit_id)

        cur = conn.execute(
            """
            SELECT record_data_json
            FROM commit_record_states
            WHERE project_id = ? AND commit_id = ? AND record_id = ? AND record_data_json IS NOT NULL;
            """,
            (project_id, commit_id, record_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row["record_data_json"])

    # =========================================================================
    # Commits
    # =========================================================================

    def create_commit(
        self,
        project_id: str,
        branch_name: str,
        changes: list[MemoryChange],
        message: str,
        author_id: str,
        author_type: AuthorType = AuthorType.AGENT,
        expected_head_commit_id: str | None = None,
        parent_commit_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Commit:
        """Atomically create a commit, compute deterministic hash, update DAG, and advance branch."""
        conn = self._get_conn()

        # Step 1: Read and verify branch
        branch = self.get_branch(project_id, branch_name)
        if not branch:
            if branch_name == "main":
                branch = self.initialize_project_main_branch(project_id, author_id=author_id)
            else:
                raise ResourceNotFoundError(f"Branch '{branch_name}' not found.", "Branch", branch_name)

        # Step 2: Compare-and-swap check against expected HEAD
        if expected_head_commit_id is not None and branch.head_commit_id != expected_head_commit_id:
            msg = (
                f"Stale HEAD on branch '{branch_name}'. Current HEAD is '{branch.head_commit_id}', "
                f"expected '{expected_head_commit_id}'."
            )
            raise ConflictError(
                msg,
                details={"current_head": branch.head_commit_id, "expected_head": expected_head_commit_id},
            )

        raw_parents = parent_commit_ids if parent_commit_ids is not None else [branch.head_commit_id]
        parents = list(dict.fromkeys([p for p in raw_parents if p]))

        # Step 3: Reconstruct base state at primary parent
        current_state = (
            self.reconstruct_project_state(project_id, branch.head_commit_id) if branch.head_commit_id else {}
        )

        # Security: Defense-in-depth secret scanner check
        from barsa.security.crypto import SecretScanner

        for chg in changes:
            if chg.after_state:
                detected_secrets = SecretScanner.scan_text(json.dumps(chg.after_state))
                if detected_secrets:
                    raise ValidationError(
                        f"Security policy violation: Change contains sensitive secrets or credentials ({', '.join(detected_secrets)})"
                    )

        # Step 4: Validate and apply changes to construct new state
        new_state = dict(current_state)
        for chg in changes:
            if chg.operation == ChangeOperation.CREATE:
                if not chg.after_state:
                    raise ValidationError(f"CREATE operation for record '{chg.record_id}' requires after_state")
                if "record_type" not in chg.after_state:
                    chg.after_state["record_type"] = chg.record_type
                if "schema_version" not in chg.after_state:
                    chg.after_state["schema_version"] = BMS_VERSION
                # Validate BMS data model
                deserialize_record(chg.after_state)
                new_state[chg.record_id] = chg.after_state
            elif chg.operation == ChangeOperation.UPDATE:
                if not chg.after_state:
                    raise ValidationError(f"UPDATE operation for record '{chg.record_id}' requires after_state")
                if "record_type" not in chg.after_state:
                    chg.after_state["record_type"] = chg.record_type
                if "schema_version" not in chg.after_state:
                    chg.after_state["schema_version"] = BMS_VERSION
                deserialize_record(chg.after_state)
                new_state[chg.record_id] = chg.after_state
            elif chg.operation == ChangeOperation.DELETE:
                if chg.record_id in new_state:
                    del new_state[chg.record_id]

        # Step 5: Compute state hash and canonical commit ID
        canonical_state_json = json.dumps(new_state, sort_keys=True, separators=(",", ":"))
        resulting_state_hash = hashlib.sha256(canonical_state_json.encode("utf-8")).hexdigest()
        now = utc_now()
        meta = metadata or {}

        commit_id = compute_commit_id(
            project_id=project_id,
            parent_commit_ids=parents,
            author_id=author_id,
            author_type=author_type,
            message=message,
            created_at=now,
            changes=changes,
            resulting_state_hash=resulting_state_hash,
            metadata=meta,
        )

        commit_entity = Commit(
            commit_id=commit_id,
            project_id=project_id,
            parent_commit_ids=parents,
            author_id=author_id,
            author_type=author_type,
            message=message,
            created_at=now,
            changes=changes,
            resulting_state_hash=resulting_state_hash,
            metadata=meta,
            bms_version=BMS_VERSION,
        )

        # Step 6: Atomic transaction persistence
        conn.execute("BEGIN IMMEDIATE;")
        try:
            # 6a: Insert commit
            conn.execute(
                """
                INSERT INTO commits (
                    commit_id, project_id, parent_commit_ids_json, author_id, author_type,
                    message, created_at, changes_json, resulting_state_hash, metadata_json, bms_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    commit_id,
                    project_id,
                    json.dumps(parents),
                    author_id,
                    author_type.value,
                    message,
                    now.isoformat(),
                    json.dumps([c.model_dump(mode="json") for c in changes]),
                    resulting_state_hash,
                    json.dumps(meta),
                    BMS_VERSION,
                ),
            )

            # 6b: Insert commit parents DAG edges
            for pid in parents:
                conn.execute(
                    """
                    INSERT INTO commit_parents (project_id, commit_id, parent_id)
                    VALUES (?, ?, ?);
                    """,
                    (project_id, commit_id, pid),
                )

            # 6c: Store snapshot states for O(1) time-travel lookups
            for rid, rdata in new_state.items():
                conn.execute(
                    """
                    INSERT INTO commit_record_states (project_id, commit_id, record_id, record_type, record_data_json)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (project_id, commit_id, rid, rdata.get("record_type", "unknown"), json.dumps(rdata)),
                )

            # 6d: Advance branch HEAD
            cur_up = conn.execute(
                """
                UPDATE branches
                SET head_commit_id = ?, updated_at = ?
                WHERE project_id = ? AND name = ? AND head_commit_id = ?;
                """,
                (commit_id, now.isoformat(), project_id, branch_name, branch.head_commit_id),
            )
            if cur_up.rowcount == 0:
                raise ConflictError(f"Concurrent update conflict advancing branch '{branch_name}'.")

            # 6e: Synchronize active Phase 3 storage for branch == 'main'
            if branch_name == "main":
                self._synchronize_active_storage(project_id, changes)
                # 6f: Emit transactional outbox event for Knowledge Graph projection
                event_id = generate_uuid_str()
                outbox_payload = {
                    "project_id": project_id,
                    "commit_id": commit_id,
                    "branch_name": branch_name,
                    "resulting_state_hash": resulting_state_hash,
                }
                conn.execute(
                    """
                    INSERT INTO graph_outbox (
                        event_id, project_id, commit_id, event_type, payload_json, status, created_at
                    ) VALUES (?, ?, ?, 'COMMIT_APPROVED', ?, 'PENDING', ?);
                    """,
                    (event_id, project_id, commit_id, json.dumps(outbox_payload), now.isoformat()),
                )

            conn.execute("COMMIT;")
            logger.info("Created commit %s on branch '%s'", commit_id[:8], branch_name)
        except Exception:
            conn.execute("ROLLBACK;")
            raise

        return commit_entity

    def _synchronize_active_storage(self, project_id: str, changes: list[MemoryChange]) -> None:
        """Keep the active SQLite tables synchronized with main branch updates."""
        for chg in changes:
            if chg.operation in (ChangeOperation.CREATE, ChangeOperation.UPDATE) and chg.after_state:
                rec = deserialize_record(chg.after_state)
                # Check if exists
                existing = self.storage.get_record(project_id, chg.record_id)
                if existing:
                    _, current_rev = existing
                    self.storage.update_record(rec, expected_revision=current_rev)
                else:
                    self.storage.create_record(rec)
            elif chg.operation == ChangeOperation.DELETE:
                existing = self.storage.get_record(project_id, chg.record_id)
                if existing:
                    _, current_rev = existing
                    self.storage.delete_record(project_id, chg.record_id, expected_revision=current_rev)

    def get_commit(self, project_id: str, commit_id: str) -> Commit | None:
        """Retrieve commit details by ID."""
        conn = self._get_conn()
        cur = conn.execute(
            """
            SELECT commit_id, project_id, parent_commit_ids_json, author_id, author_type,
                   message, created_at, changes_json, resulting_state_hash, metadata_json, bms_version
            FROM commits
            WHERE project_id = ? AND commit_id = ?;
            """,
            (project_id, commit_id),
        )
        row = cur.fetchone()
        if not row:
            return None

        raw_changes = json.loads(row["changes_json"])
        changes = [MemoryChange.model_validate(c) for c in raw_changes]

        return Commit(
            commit_id=row["commit_id"],
            project_id=row["project_id"],
            parent_commit_ids=json.loads(row["parent_commit_ids_json"]),
            author_id=row["author_id"],
            author_type=AuthorType(row["author_type"]),
            message=row["message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            changes=changes,
            resulting_state_hash=row["resulting_state_hash"],
            metadata=json.loads(row["metadata_json"]),
            bms_version=row["bms_version"],
        )

    def get_history(self, project_id: str, branch_name: str | None = None, limit: int = 50) -> list[Commit]:
        """List commit history in reverse-chronological order."""
        conn = self._get_conn()
        if branch_name:
            branch = self.get_branch(project_id, branch_name)
            if not branch:
                raise ResourceNotFoundError(f"Branch '{branch_name}' not found.", "Branch", branch_name)

            # Traverse DAG backwards from HEAD
            commits: list[Commit] = []
            visited: set[str] = set()
            queue = [branch.head_commit_id]

            while queue and len(commits) < limit:
                cid = queue.pop(0)
                if cid in visited or not cid:
                    continue
                visited.add(cid)

                commit = self.get_commit(project_id, cid)
                if commit:
                    commits.append(commit)
                    queue.extend(commit.parent_commit_ids)

            commits.sort(key=lambda c: c.created_at, reverse=True)
            return commits

        # All project commits
        cur = conn.execute(
            "SELECT commit_id FROM commits WHERE project_id = ? ORDER BY created_at DESC LIMIT ?;",
            (project_id, limit),
        )
        return [self.get_commit(project_id, r["commit_id"]) for r in cur.fetchall() if r["commit_id"]]  # type: ignore[misc]

    def get_record_history(self, project_id: str, record_id: str, limit: int = 50) -> list[Commit]:
        """Find commits that specifically created, modified, or deleted a given record ID."""
        conn = self._get_conn()
        cur = conn.execute(
            """
            SELECT c.commit_id
            FROM commits c
            WHERE c.project_id = ? AND c.changes_json LIKE ?
            ORDER BY c.created_at DESC LIMIT ?;
            """,
            (project_id, f'%"{record_id}"%', limit),
        )
        commits: list[Commit] = []
        for r in cur.fetchall():
            c = self.get_commit(project_id, r["commit_id"])
            if c and any(chg.record_id == record_id for chg in c.changes):
                commits.append(c)
        return commits

    # =========================================================================
    # Common Ancestor (LCA)
    # =========================================================================

    def find_lowest_common_ancestor(self, project_id: str, commit_a: str, commit_b: str) -> str:
        """Find the Lowest Common Ancestor (LCA) between two commits in the DAG."""
        if commit_a == commit_b:
            return commit_a

        # BFS ancestors of A
        ancestors_a: set[str] = set()
        queue = [commit_a]
        while queue:
            cid = queue.pop(0)
            if cid in ancestors_a or not cid:
                continue
            ancestors_a.add(cid)
            c = self.get_commit(project_id, cid)
            if c:
                queue.extend(c.parent_commit_ids)

        # BFS from B until first common node
        queue = [commit_b]
        visited_b: set[str] = set()
        while queue:
            cid = queue.pop(0)
            if cid in ancestors_a:
                return cid
            if cid in visited_b or not cid:
                continue
            visited_b.add(cid)
            c = self.get_commit(project_id, cid)
            if c:
                queue.extend(c.parent_commit_ids)

        raise StorageError(f"No common ancestor found between commits '{commit_a}' and '{commit_b}'")

    # =========================================================================
    # Diffs
    # =========================================================================

    def diff_commits(self, project_id: str, from_commit_id: str | None, to_commit_id: str) -> CommitDiff:
        """Compute structured record-level and field-level diff between two commits."""
        from_state = self.reconstruct_project_state(project_id, from_commit_id) if from_commit_id else {}
        to_state = self.reconstruct_project_state(project_id, to_commit_id)
        return compute_state_diff(project_id, from_commit_id, to_commit_id, from_state, to_state)

    # =========================================================================
    # Merge Proposals & Collaboration
    # =========================================================================

    def create_merge_proposal(
        self,
        project_id: str,
        title: str,
        source_branch: str,
        target_branch: str,
        author_id: str,
        description: str = "",
    ) -> MergeProposal:
        """Create a new merge proposal and pre-check for merge conflicts."""
        src = self.get_branch(project_id, source_branch)
        if not src:
            raise ResourceNotFoundError(f"Source branch '{source_branch}' not found.", "Branch", source_branch)
        tgt = self.get_branch(project_id, target_branch)
        if not tgt:
            raise ResourceNotFoundError(f"Target branch '{target_branch}' not found.", "Branch", target_branch)

        proposal_id = generate_uuid_str()
        now = utc_now()
        conn = self._get_conn()

        conn.execute(
            """
            INSERT INTO merge_proposals (
                proposal_id, project_id, title, description, source_branch, target_branch,
                source_head, target_head, author_id, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?);
            """,
            (
                proposal_id,
                project_id,
                title,
                description,
                source_branch,
                target_branch,
                src.head_commit_id,
                tgt.head_commit_id,
                author_id,
                now.isoformat(),
                now.isoformat(),
            ),
        )

        # Check for conflicts immediately and persist them
        base_commit = self.find_lowest_common_ancestor(project_id, src.head_commit_id, tgt.head_commit_id)
        base_state = self.reconstruct_project_state(project_id, base_commit)
        source_state = self.reconstruct_project_state(project_id, src.head_commit_id)
        target_state = self.reconstruct_project_state(project_id, tgt.head_commit_id)

        merge_eval = three_way_merge_states(
            project_id=project_id,
            base_state=base_state,
            source_state=source_state,
            target_state=target_state,
            source_branch=source_branch,
            target_branch=target_branch,
            proposal_id=proposal_id,
        )

        for conf in merge_eval.conflicts:
            conn.execute(
                """
                INSERT INTO conflicts (
                    conflict_id, project_id, proposal_id, source_branch, target_branch,
                    affected_record_id, conflict_type, base_value_json, source_value_json,
                    target_value_json, resolution_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unresolved');
                """,
                (
                    conf.conflict_id,
                    project_id,
                    proposal_id,
                    source_branch,
                    target_branch,
                    conf.affected_record_id,
                    conf.conflict_type.value,
                    json.dumps(conf.base_value),
                    json.dumps(conf.source_value),
                    json.dumps(conf.target_value),
                ),
            )

        return MergeProposal(
            proposal_id=proposal_id,
            project_id=project_id,
            title=title,
            description=description,
            source_branch=source_branch,
            target_branch=target_branch,
            source_head=src.head_commit_id,
            target_head=tgt.head_commit_id,
            author_id=author_id,
            status=ProposalStatus.OPEN,
            created_at=now,
            updated_at=now,
        )

    def get_merge_proposal(self, project_id: str, proposal_id: str) -> MergeProposal | None:
        """Retrieve merge proposal and attached review comments."""
        conn = self._get_conn()
        cur = conn.execute(
            """
            SELECT proposal_id, project_id, title, description, source_branch, target_branch,
                   source_head, target_head, author_id, status, created_at, updated_at
            FROM merge_proposals
            WHERE project_id = ? AND proposal_id = ?;
            """,
            (project_id, proposal_id),
        )
        row = cur.fetchone()
        if not row:
            return None

        # Fetch comments
        cur_c = conn.execute(
            "SELECT comment_id, author_id, author_type, content, record_id, created_at FROM review_comments WHERE proposal_id = ? ORDER BY created_at ASC;",
            (proposal_id,),
        )
        comments = [
            ReviewComment(
                comment_id=r["comment_id"],
                proposal_id=proposal_id,
                author_id=r["author_id"],
                author_type=AuthorType(r["author_type"]),
                content=r["content"],
                record_id=r["record_id"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in cur_c.fetchall()
        ]

        # Fetch reviews
        cur_r = conn.execute(
            "SELECT review_id, reviewer_id, reviewer_type, status, summary, created_at FROM reviews WHERE proposal_id = ? ORDER BY created_at ASC;",
            (proposal_id,),
        )
        reviews = [dict(r) for r in cur_r.fetchall()]

        return MergeProposal(
            proposal_id=row["proposal_id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"] or "",
            source_branch=row["source_branch"],
            target_branch=row["target_branch"],
            source_head=row["source_head"],
            target_head=row["target_head"],
            author_id=row["author_id"],
            status=ProposalStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            comments=comments,
            reviews=reviews,
        )

    def list_merge_proposals(self, project_id: str, status: ProposalStatus | None = None) -> list[MergeProposal]:
        """List merge proposals for a project, optionally filtered by status."""
        conn = self._get_conn()
        sql = "SELECT proposal_id FROM merge_proposals WHERE project_id = ?"
        params: list[Any] = [project_id]
        if status:
            sql += " AND status = ?"
            params.append(status.value)
        sql += " ORDER BY created_at DESC;"

        cur = conn.execute(sql, tuple(params))
        proposals: list[MergeProposal] = []
        for r in cur.fetchall():
            prop = self.get_merge_proposal(project_id, r["proposal_id"])
            if prop:
                proposals.append(prop)
        return proposals

    def add_review_comment(
        self,
        project_id: str,
        proposal_id: str,
        author_id: str,
        content: str,
        author_type: AuthorType = AuthorType.AGENT,
        record_id: str | None = None,
    ) -> ReviewComment:
        """Add a review comment to a merge proposal."""
        if not self.get_merge_proposal(project_id, proposal_id):
            raise ResourceNotFoundError(f"Proposal '{proposal_id}' not found.", "MergeProposal", proposal_id)

        comment_id = generate_uuid_str()
        now = utc_now()
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO review_comments (comment_id, project_id, proposal_id, author_id, author_type, content, record_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (comment_id, project_id, proposal_id, author_id, author_type.value, content, record_id, now.isoformat()),
        )
        return ReviewComment(
            comment_id=comment_id,
            proposal_id=proposal_id,
            author_id=author_id,
            author_type=author_type,
            content=content,
            record_id=record_id,
            created_at=now,
        )

    def submit_review(
        self,
        project_id: str,
        proposal_id: str,
        reviewer_id: str,
        status: ReviewStatus,
        summary: str | None = None,
        reviewer_type: AuthorType = AuthorType.HUMAN,
    ) -> dict[str, Any]:
        """Submit a formal review (approved, changes_requested, rejected)."""
        if not self.get_merge_proposal(project_id, proposal_id):
            raise ResourceNotFoundError(f"Proposal '{proposal_id}' not found.", "MergeProposal", proposal_id)

        review_id = generate_uuid_str()
        now = utc_now()
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO reviews (review_id, project_id, proposal_id, reviewer_id, reviewer_type, status, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                review_id,
                project_id,
                proposal_id,
                reviewer_id,
                reviewer_type.value,
                status.value,
                summary,
                now.isoformat(),
            ),
        )
        return {
            "review_id": review_id,
            "proposal_id": proposal_id,
            "reviewer_id": reviewer_id,
            "status": status.value,
            "summary": summary,
            "created_at": now.isoformat(),
        }

    # =========================================================================
    # Conflict Resolution & Merge Execution
    # =========================================================================

    def list_conflicts(self, project_id: str, proposal_id: str | None = None) -> list[ConflictRecord]:
        """List unresolved or all conflicts for a project or proposal."""
        conn = self._get_conn()
        sql = "SELECT * FROM conflicts WHERE project_id = ?"
        params: list[Any] = [project_id]
        if proposal_id:
            sql += " AND proposal_id = ?"
            params.append(proposal_id)
        sql += " ORDER BY conflict_id ASC;"

        cur = conn.execute(sql, tuple(params))
        conflicts: list[ConflictRecord] = []
        for r in cur.fetchall():
            conflicts.append(
                ConflictRecord(
                    conflict_id=r["conflict_id"],
                    project_id=r["project_id"],
                    proposal_id=r["proposal_id"],
                    source_branch=r["source_branch"],
                    target_branch=r["target_branch"],
                    affected_record_id=r["affected_record_id"],
                    conflict_type=ConflictType(r["conflict_type"]),
                    base_value=json.loads(r["base_value_json"]) if r["base_value_json"] else None,
                    source_value=json.loads(r["source_value_json"]) if r["source_value_json"] else None,
                    target_value=json.loads(r["target_value_json"]) if r["target_value_json"] else None,
                    resolution_status=ConflictStatus(r["resolution_status"]),
                    resolved_by=r["resolved_by"],
                    resolution_timestamp=datetime.fromisoformat(r["resolution_timestamp"])
                    if r["resolution_timestamp"]
                    else None,
                    resolved_value=json.loads(r["resolved_value_json"]) if r["resolved_value_json"] else None,
                )
            )
        return conflicts

    def resolve_conflict(
        self,
        project_id: str,
        conflict_id: str,
        resolved_by: str,
        resolved_value: dict[str, Any] | None,
    ) -> ConflictRecord:
        """Mark a conflict as resolved with an explicitly approved record state."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM conflicts WHERE project_id = ? AND conflict_id = ?;", (project_id, conflict_id)
        )
        row = cur.fetchone()
        if not row:
            raise ResourceNotFoundError(f"Conflict '{conflict_id}' not found.", "Conflict", conflict_id)

        now = utc_now()
        conn.execute(
            """
            UPDATE conflicts
            SET resolution_status = 'resolved', resolved_by = ?, resolution_timestamp = ?, resolved_value_json = ?
            WHERE project_id = ? AND conflict_id = ?;
            """,
            (resolved_by, now.isoformat(), json.dumps(resolved_value), project_id, conflict_id),
        )

        return ConflictRecord(
            conflict_id=conflict_id,
            project_id=project_id,
            proposal_id=row["proposal_id"],
            source_branch=row["source_branch"],
            target_branch=row["target_branch"],
            affected_record_id=row["affected_record_id"],
            conflict_type=ConflictType(row["conflict_type"]),
            base_value=json.loads(row["base_value_json"]) if row["base_value_json"] else None,
            source_value=json.loads(row["source_value_json"]) if row["source_value_json"] else None,
            target_value=json.loads(row["target_value_json"]) if row["target_value_json"] else None,
            resolution_status=ConflictStatus.RESOLVED,
            resolved_by=resolved_by,
            resolution_timestamp=now,
            resolved_value=resolved_value,
        )

    def execute_merge(
        self,
        project_id: str,
        proposal_id: str,
        author_id: str,
    ) -> Commit:
        """Execute a three-way merge commit for an approved proposal once all conflicts are resolved."""
        proposal = self.get_merge_proposal(project_id, proposal_id)
        if not proposal:
            raise ResourceNotFoundError(f"Proposal '{proposal_id}' not found.", "MergeProposal", proposal_id)

        if proposal.status != ProposalStatus.OPEN:
            raise ConflictError(f"Proposal '{proposal_id}' is already {proposal.status.value}")

        # Re-verify branch HEADs
        src_branch = self.get_branch(project_id, proposal.source_branch)
        tgt_branch = self.get_branch(project_id, proposal.target_branch)
        if not src_branch or not tgt_branch:
            raise ConflictError("Source or target branch missing during merge execution")

        if tgt_branch.head_commit_id != proposal.target_head:
            raise ConflictError(
                f"Target branch '{tgt_branch.name}' has advanced since proposal creation. "
                f"Expected '{proposal.target_head}', found '{tgt_branch.head_commit_id}'. Please rebase or recreate proposal."
            )

        # Check for unresolved conflicts
        conflicts = self.list_conflicts(project_id, proposal_id)
        unresolved = [c for c in conflicts if c.resolution_status == ConflictStatus.UNRESOLVED]
        if unresolved:
            raise ConflictError(
                f"Cannot execute merge: {len(unresolved)} unresolved conflict(s) remain.",
                details={"unresolved_conflict_ids": [c.conflict_id for c in unresolved]},
            )

        # Three-way merge evaluation
        base_commit = self.find_lowest_common_ancestor(project_id, src_branch.head_commit_id, tgt_branch.head_commit_id)
        base_state = self.reconstruct_project_state(project_id, base_commit)
        source_state = self.reconstruct_project_state(project_id, src_branch.head_commit_id)
        target_state = self.reconstruct_project_state(project_id, tgt_branch.head_commit_id)

        merge_eval = three_way_merge_states(
            project_id=project_id,
            base_state=base_state,
            source_state=source_state,
            target_state=target_state,
            source_branch=src_branch.name,
            target_branch=tgt_branch.name,
            proposal_id=proposal_id,
        )

        final_merged_state = dict(merge_eval.merged_state)
        # Apply explicit manual resolutions
        for c in conflicts:
            if c.resolution_status == ConflictStatus.RESOLVED:
                if c.resolved_value is not None:
                    final_merged_state[c.affected_record_id] = c.resolved_value
                elif c.affected_record_id in final_merged_state:
                    del final_merged_state[c.affected_record_id]

        # Calculate final diff changes from target_state to final_merged_state
        final_diff = compute_state_diff(
            project_id,
            from_commit_id=tgt_branch.head_commit_id,
            to_commit_id="merge-target",
            from_state=target_state,
            to_state=final_merged_state,
        )

        changes: list[MemoryChange] = []
        for rd in final_diff.changes:
            changes.append(
                MemoryChange(
                    operation=rd.operation,
                    record_id=rd.record_id,
                    record_type=rd.record_type,
                    before_state=rd.before_state,
                    after_state=rd.after_state,
                )
            )

        # Create multi-parent merge commit
        merge_commit = self.create_commit(
            project_id=project_id,
            branch_name=tgt_branch.name,
            changes=changes,
            message=f"Merge branch '{src_branch.name}' into '{tgt_branch.name}': {proposal.title}",
            author_id=author_id,
            author_type=AuthorType.AGENT,
            expected_head_commit_id=tgt_branch.head_commit_id,
            parent_commit_ids=[tgt_branch.head_commit_id, src_branch.head_commit_id],
            metadata={"merge_proposal_id": proposal_id},
        )

        # Mark proposal as merged
        now = utc_now()
        conn = self._get_conn()
        conn.execute(
            "UPDATE merge_proposals SET status = 'merged', updated_at = ? WHERE proposal_id = ?;",
            (now.isoformat(), proposal_id),
        )

        return merge_commit

    # =========================================================================
    # Historical Restore
    # =========================================================================

    def restore_commit_state(
        self,
        project_id: str,
        target_branch: str,
        restore_from_commit_id: str,
        author_id: str,
        message: str | None = None,
    ) -> Commit:
        """Create a new commit on target_branch that restores the historical state from restore_from_commit_id."""
        branch = self.get_branch(project_id, target_branch)
        if not branch:
            raise ResourceNotFoundError(f"Branch '{target_branch}' not found.", "Branch", target_branch)

        current_state = self.reconstruct_project_state(project_id, branch.head_commit_id)
        target_historical_state = self.reconstruct_project_state(project_id, restore_from_commit_id)

        diff = compute_state_diff(
            project_id,
            from_commit_id=branch.head_commit_id,
            to_commit_id=restore_from_commit_id,
            from_state=current_state,
            to_state=target_historical_state,
        )

        changes: list[MemoryChange] = []
        for rd in diff.changes:
            changes.append(
                MemoryChange(
                    operation=rd.operation,
                    record_id=rd.record_id,
                    record_type=rd.record_type,
                    before_state=rd.before_state,
                    after_state=rd.after_state,
                )
            )

        commit_message = message or f"Restore memory state to commit {restore_from_commit_id[:8]}"

        return self.create_commit(
            project_id=project_id,
            branch_name=target_branch,
            changes=changes,
            message=commit_message,
            author_id=author_id,
            author_type=AuthorType.AGENT,
            expected_head_commit_id=branch.head_commit_id,
            metadata={"restored_from": restore_from_commit_id},
        )
