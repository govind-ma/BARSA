"""SQLite-backed persistent storage for the Barsa Multi-Agent Coordination Engine."""

import contextlib
import json
import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any

from barsa.coordination.models import (
    AgentProfile,
    AgentRegistration,
    AgentState,
    CollaborationMessage,
    CoordinationEvent,
    CoordinationIssue,
    CoordinationTask,
    CoordinationTaskStatus,
    HelpRequest,
    HelpRequestStatus,
    IssueStatus,
    MessageType,
    Priority,
    VerificationLevel,
)
from barsa.core.exceptions import ConflictError, ResourceNotFoundError, ValidationError
from barsa.storage.sqlite import SQLiteStorageProvider

logger = logging.getLogger("barsa.coordination.storage")


class CoordinationStorage:
    """Storage adapter managing coordination tables with ACID transactions."""

    def __init__(self, storage: SQLiteStorageProvider) -> None:
        self.storage = storage

    def _get_conn(self) -> sqlite3.Connection:
        return self.storage._get_connection()

    def _rollback(self, conn: sqlite3.Connection) -> None:
        with contextlib.suppress(Exception):
            conn.execute("ROLLBACK;")

    # =========================================================================
    # Agent Registry Operations
    # =========================================================================

    def register_agent(self, reg: AgentRegistration) -> AgentProfile:
        """Register or update an agent in the registry."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT * FROM agents WHERE agent_id = ?;", (reg.agent_id,))
            row = cur.fetchone()

            if row:
                conn.execute(
                    """
                    UPDATE agents
                    SET display_name = ?,
                        provider = ?,
                        model = ?,
                        claimed_capabilities_json = ?,
                        verified_capabilities_json = ?,
                        supported_tools_json = ?,
                        allowed_projects_json = ?,
                        maximum_concurrent_tasks = ?,
                        updated_at = ?,
                        metadata_json = ?
                    WHERE agent_id = ?;
                    """,
                    (
                        reg.display_name,
                        reg.provider,
                        reg.model,
                        json.dumps(reg.claimed_capabilities),
                        json.dumps(reg.verified_capabilities),
                        json.dumps(reg.supported_tools),
                        json.dumps(reg.allowed_projects),
                        reg.maximum_concurrent_tasks,
                        now,
                        json.dumps(reg.metadata),
                        reg.agent_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO agents (
                        agent_id, display_name, provider, model,
                        claimed_capabilities_json, verified_capabilities_json,
                        supported_tools_json, allowed_projects_json,
                        availability_status, last_heartbeat, current_workload,
                        maximum_concurrent_tasks, registered_at, updated_at,
                        metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?);
                    """,
                    (
                        reg.agent_id,
                        reg.display_name,
                        reg.provider,
                        reg.model,
                        json.dumps(reg.claimed_capabilities),
                        json.dumps(reg.verified_capabilities),
                        json.dumps(reg.supported_tools),
                        json.dumps(reg.allowed_projects),
                        AgentState.AVAILABLE.value,
                        now,
                        reg.maximum_concurrent_tasks,
                        now,
                        now,
                        json.dumps(reg.metadata),
                    ),
                )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        agent = self.get_agent(reg.agent_id)
        if not agent:
            raise ResourceNotFoundError(f"Agent {reg.agent_id} could not be retrieved after registration")
        return agent

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Fetch agent profile by ID."""
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM agents WHERE agent_id = ?;", (agent_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_agent(row)

    def list_agents(
        self,
        project_id: str | None = None,
        status: AgentState | None = None,
    ) -> list[AgentProfile]:
        """List registered agents, optionally filtered by project or availability."""
        conn = self._get_conn()
        query = "SELECT * FROM agents WHERE 1=1"
        params: list[Any] = []

        if status:
            query += " AND availability_status = ?"
            params.append(status.value)

        cur = conn.execute(query + " ORDER BY agent_id ASC;", params)
        agents = [self._row_to_agent(r) for r in cur.fetchall()]

        if project_id:
            filtered = []
            for a in agents:
                if "*" in a.allowed_projects or project_id in a.allowed_projects:
                    filtered.append(a)
            return filtered

        return agents

    def update_agent_status(self, agent_id: str, status: AgentState) -> AgentProfile:
        """Update agent availability status."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT agent_id FROM agents WHERE agent_id = ?;", (agent_id,))
            if not cur.fetchone():
                raise ResourceNotFoundError(f"Agent {agent_id} not found")

            conn.execute(
                """
                UPDATE agents
                SET availability_status = ?, updated_at = ?
                WHERE agent_id = ?;
                """,
                (status.value, now, agent_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        agent = self.get_agent(agent_id)
        if not agent:
            raise ResourceNotFoundError(f"Agent {agent_id} not found")
        return agent

    def heartbeat_agent(self, agent_id: str) -> AgentProfile:
        """Update last heartbeat timestamp for an agent."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT agent_id FROM agents WHERE agent_id = ?;", (agent_id,))
            if not cur.fetchone():
                raise ResourceNotFoundError(f"Agent {agent_id} not found")

            conn.execute(
                """
                UPDATE agents
                SET last_heartbeat = ?, updated_at = ?
                WHERE agent_id = ?;
                """,
                (now, now, agent_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        agent = self.get_agent(agent_id)
        if not agent:
            raise ResourceNotFoundError(f"Agent {agent_id} not found")
        return agent

    def _row_to_agent(self, row: sqlite3.Row) -> AgentProfile:
        return AgentProfile(
            agent_id=row["agent_id"],
            display_name=row["display_name"],
            provider=row["provider"],
            model=row["model"],
            claimed_capabilities=json.loads(row["claimed_capabilities_json"] or "[]"),
            verified_capabilities=json.loads(row["verified_capabilities_json"] or "[]"),
            supported_tools=json.loads(row["supported_tools_json"] or "[]"),
            allowed_projects=json.loads(row["allowed_projects_json"] or '["*"]'),
            availability_status=AgentState(row["availability_status"]),
            last_heartbeat=datetime.fromisoformat(row["last_heartbeat"]),
            current_workload=row["current_workload"],
            maximum_concurrent_tasks=row["maximum_concurrent_tasks"],
            registered_at=datetime.fromisoformat(row["registered_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    # =========================================================================
    # Task Lifecycle Operations
    # =========================================================================

    def create_task(self, task: CoordinationTask) -> CoordinationTask:
        """Persist a new coordination task."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT task_id FROM coordination_tasks WHERE task_id = ?;", (task.task_id,))
            if cur.fetchone():
                raise ConflictError(f"Task {task.task_id} already exists")

            conn.execute(
                """
                INSERT INTO coordination_tasks (
                    task_id, project_id, title, description,
                    required_capabilities_json, required_tools_json,
                    min_verified_level, priority, dependencies_json,
                    status, assigned_agent_id, lease_token, lease_expires_at,
                    heartbeat_timeout_seconds, max_attempts, attempt_count,
                    failure_reason, result_json, resource_usage_json,
                    created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    task.task_id,
                    task.project_id,
                    task.title,
                    task.description,
                    json.dumps(task.required_capabilities),
                    json.dumps(task.required_tools),
                    task.min_verified_level.value,
                    task.priority.value,
                    json.dumps(task.dependencies),
                    task.status.value,
                    task.assigned_agent_id,
                    task.lease_token,
                    task.lease_expires_at.isoformat() if task.lease_expires_at else None,
                    task.heartbeat_timeout_seconds,
                    task.max_attempts,
                    task.attempt_count,
                    task.failure_reason,
                    json.dumps(task.result) if task.result else None,
                    json.dumps(task.resource_usage),
                    task.created_at.isoformat() if task.created_at else now,
                    task.updated_at.isoformat() if task.updated_at else now,
                    json.dumps(task.metadata),
                ),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        created = self.get_task(task.task_id)
        if not created:
            raise ResourceNotFoundError(f"Task {task.task_id} could not be retrieved")
        return created

    def get_task(self, task_id: str) -> CoordinationTask | None:
        """Fetch task by ID."""
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM coordination_tasks WHERE task_id = ?;", (task_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_task(row)

    def list_tasks(
        self,
        project_id: str | None = None,
        status: CoordinationTaskStatus | None = None,
    ) -> list[CoordinationTask]:
        """List tasks optionally filtered by project and status."""
        conn = self._get_conn()
        query = "SELECT * FROM coordination_tasks WHERE 1=1"
        params: list[Any] = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if status:
            query += " AND status = ?"
            params.append(status.value)

        cur = conn.execute(query + " ORDER BY created_at ASC;", params)
        return [self._row_to_task(r) for r in cur.fetchall()]

    def update_task_status(
        self,
        task_id: str,
        new_status: CoordinationTaskStatus,
        failure_reason: str | None = None,
    ) -> CoordinationTask:
        """Update task status with optional failure reason."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT * FROM coordination_tasks WHERE task_id = ?;", (task_id,))
            row = cur.fetchone()
            if not row:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            conn.execute(
                """
                UPDATE coordination_tasks
                SET status = ?, failure_reason = COALESCE(?, failure_reason), updated_at = ?
                WHERE task_id = ?;
                """,
                (new_status.value, failure_reason, now, task_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        task = self.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def claim_task(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        lease_expires_at: datetime,
    ) -> CoordinationTask:
        """Atomically claim a task with compare-and-swap semantics."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            # 1. Verify agent
            cur_agent = conn.execute("SELECT * FROM agents WHERE agent_id = ?;", (agent_id,))
            agent_row = cur_agent.fetchone()
            if not agent_row:
                raise ResourceNotFoundError(f"Agent {agent_id} not registered")

            if agent_row["availability_status"] in (AgentState.OFFLINE.value, AgentState.DISABLED.value):
                raise ValidationError(f"Agent {agent_id} is {agent_row['availability_status']}")

            if agent_row["current_workload"] >= agent_row["maximum_concurrent_tasks"]:
                raise ConflictError(
                    f"Agent {agent_id} has reached maximum concurrent workload "
                    f"({agent_row['current_workload']}/{agent_row['maximum_concurrent_tasks']})"
                )

            # 2. Check task status
            cur_task = conn.execute("SELECT * FROM coordination_tasks WHERE task_id = ?;", (task_id,))
            task_row = cur_task.fetchone()
            if not task_row:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            current_status = task_row["status"]
            if current_status not in (CoordinationTaskStatus.READY.value, CoordinationTaskStatus.PENDING.value):
                raise ConflictError(f"Task {task_id} cannot be claimed; current status is '{current_status}'")

            # Check dependencies if pending
            deps = json.loads(task_row["dependencies_json"] or "[]")
            if deps:
                for dep_id in deps:
                    cur_dep = conn.execute("SELECT status FROM coordination_tasks WHERE task_id = ?;", (dep_id,))
                    dep_row = cur_dep.fetchone()
                    if not dep_row or dep_row["status"] != CoordinationTaskStatus.COMPLETED.value:
                        raise ConflictError(
                            f"Task {task_id} is blocked on dependency {dep_id} (status: {dep_row['status'] if dep_row else 'missing'})"
                        )

            # 3. Atomically update task to claimed
            new_attempts = task_row["attempt_count"] + 1
            cursor = conn.execute(
                """
                UPDATE coordination_tasks
                SET status = ?,
                    assigned_agent_id = ?,
                    lease_token = ?,
                    lease_expires_at = ?,
                    attempt_count = ?,
                    updated_at = ?
                WHERE task_id = ? AND status = ?;
                """,
                (
                    CoordinationTaskStatus.CLAIMED.value,
                    agent_id,
                    lease_token,
                    lease_expires_at.isoformat(),
                    new_attempts,
                    now,
                    task_id,
                    current_status,
                ),
            )
            if cursor.rowcount == 0:
                raise ConflictError(f"Task {task_id} was claimed concurrently by another agent")

            # 4. Increment agent workload and update status if full
            new_workload = agent_row["current_workload"] + 1
            new_agent_status = (
                AgentState.BUSY.value
                if new_workload >= agent_row["maximum_concurrent_tasks"]
                else AgentState.AVAILABLE.value
            )
            conn.execute(
                """
                UPDATE agents
                SET current_workload = ?, availability_status = ?, updated_at = ?
                WHERE agent_id = ?;
                """,
                (new_workload, new_agent_status, now, agent_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        task = self.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found after claiming")
        return task

    def start_task(self, task_id: str, agent_id: str, lease_token: str) -> CoordinationTask:
        """Transition task from CLAIMED to RUNNING verifying fencing token."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute(
                """
                SELECT status, assigned_agent_id, lease_token, lease_expires_at
                FROM coordination_tasks WHERE task_id = ?;
                """,
                (task_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            if row["assigned_agent_id"] != agent_id or row["lease_token"] != lease_token:
                raise ConflictError(f"Fencing token or agent mismatch for task {task_id}")

            if row["status"] != CoordinationTaskStatus.CLAIMED.value:
                if row["status"] == CoordinationTaskStatus.RUNNING.value:
                    conn.execute("COMMIT;")
                    task = self.get_task(task_id)
                    assert task is not None
                    return task
                raise ConflictError(f"Task {task_id} is in status '{row['status']}', expected 'claimed'")

            # Check expiration
            expires_at = datetime.fromisoformat(row["lease_expires_at"])
            if datetime.now(UTC) > expires_at:
                raise ConflictError(f"Task {task_id} lease has expired")

            conn.execute(
                """
                UPDATE coordination_tasks
                SET status = ?, updated_at = ?
                WHERE task_id = ? AND lease_token = ?;
                """,
                (CoordinationTaskStatus.RUNNING.value, now, task_id, lease_token),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        task = self.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def heartbeat_task(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        new_lease_expires_at: datetime,
    ) -> CoordinationTask:
        """Renew task lease and agent heartbeat."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute(
                """
                SELECT status, assigned_agent_id, lease_token, lease_expires_at
                FROM coordination_tasks WHERE task_id = ?;
                """,
                (task_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            if row["assigned_agent_id"] != agent_id or row["lease_token"] != lease_token:
                raise ConflictError(f"Fencing token or agent mismatch for task {task_id}")

            if row["status"] not in (CoordinationTaskStatus.CLAIMED.value, CoordinationTaskStatus.RUNNING.value):
                raise ConflictError(f"Task {task_id} is in '{row['status']}' state; heartbeat rejected")

            # Update lease expiration
            conn.execute(
                """
                UPDATE coordination_tasks
                SET lease_expires_at = ?, updated_at = ?
                WHERE task_id = ? AND lease_token = ?;
                """,
                (new_lease_expires_at.isoformat(), now, task_id, lease_token),
            )

            # Update agent heartbeat
            conn.execute(
                """
                UPDATE agents
                SET last_heartbeat = ?, updated_at = ?
                WHERE agent_id = ?;
                """,
                (now, now, agent_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        task = self.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def update_task_progress(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        message: str,
        progress_percent: float | None = None,
        resource_usage: dict[str, Any] | None = None,
    ) -> CoordinationTask:
        """Record progress update from the executing agent."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute(
                """
                SELECT project_id, status, assigned_agent_id, lease_token, lease_expires_at, resource_usage_json
                FROM coordination_tasks WHERE task_id = ?;
                """,
                (task_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            if row["assigned_agent_id"] != agent_id or row["lease_token"] != lease_token:
                raise ConflictError(f"Fencing token or agent mismatch for task {task_id}")

            if row["status"] != CoordinationTaskStatus.RUNNING.value:
                raise ConflictError(f"Task {task_id} is '{row['status']}', expected 'running'")

            # Check expiration
            expires_at = datetime.fromisoformat(row["lease_expires_at"])
            if datetime.now(UTC) > expires_at:
                raise ConflictError(f"Task {task_id} lease has expired; progress update rejected")

            # Merge resource usage if provided
            current_usage = json.loads(row["resource_usage_json"] or "{}")
            if resource_usage:
                current_usage.update(resource_usage)

            conn.execute(
                """
                UPDATE coordination_tasks
                SET resource_usage_json = ?, updated_at = ?
                WHERE task_id = ? AND lease_token = ?;
                """,
                (json.dumps(current_usage), now, task_id, lease_token),
            )

            # Insert collaboration message
            msg_id = f"msg-{now[:10]}-{task_id[:6]}"
            conn.execute(
                """
                INSERT INTO collaboration_messages (
                    message_id, project_id, task_id, author_agent_id,
                    message_type, content, related_record_refs_json,
                    created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg_id,
                    row["project_id"],
                    task_id,
                    agent_id,
                    MessageType.PROGRESS_UPDATE.value,
                    message,
                    "[]",
                    now,
                    json.dumps({"progress_percent": progress_percent} if progress_percent is not None else {}),
                ),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        task = self.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def release_task(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        reason: str | None = None,
    ) -> CoordinationTask:
        """Voluntary release of task lease back to ready status."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute(
                """
                SELECT status, assigned_agent_id, lease_token
                FROM coordination_tasks WHERE task_id = ?;
                """,
                (task_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            if row["assigned_agent_id"] != agent_id or row["lease_token"] != lease_token:
                raise ConflictError(f"Fencing token or agent mismatch for task {task_id}")

            # Reset task
            conn.execute(
                """
                UPDATE coordination_tasks
                SET status = ?,
                    assigned_agent_id = NULL,
                    lease_token = NULL,
                    lease_expires_at = NULL,
                    failure_reason = ?,
                    updated_at = ?
                WHERE task_id = ? AND lease_token = ?;
                """,
                (CoordinationTaskStatus.READY.value, reason, now, task_id, lease_token),
            )

            # Decrement agent workload
            cur_agent = conn.execute("SELECT current_workload FROM agents WHERE agent_id = ?;", (agent_id,))
            a_row = cur_agent.fetchone()
            if a_row and a_row["current_workload"] > 0:
                conn.execute(
                    """
                    UPDATE agents
                    SET current_workload = current_workload - 1,
                        availability_status = ?,
                        updated_at = ?
                    WHERE agent_id = ?;
                    """,
                    (AgentState.AVAILABLE.value, now, agent_id),
                )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        task = self.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def submit_task(
        self,
        task_id: str,
        agent_id: str,
        lease_token: str,
        result: dict[str, Any],
        new_status: CoordinationTaskStatus,
        resource_usage: dict[str, Any] | None = None,
    ) -> CoordinationTask:
        """Submit task results, verifying fencing token and expiration."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute(
                """
                SELECT status, assigned_agent_id, lease_token, lease_expires_at, resource_usage_json
                FROM coordination_tasks WHERE task_id = ?;
                """,
                (task_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            # FENCING TOKEN CHECK: Expired or superseded token must be rejected!
            if row["assigned_agent_id"] != agent_id or row["lease_token"] != lease_token:
                raise ConflictError(
                    f"Task {task_id} submission rejected: lease token {lease_token} is invalid or has been superseded"
                )

            if row["status"] != CoordinationTaskStatus.RUNNING.value:
                raise ConflictError(
                    f"Task {task_id} is in '{row['status']}' state; only 'running' tasks can be submitted"
                )

            # Check expiration
            expires_at = datetime.fromisoformat(row["lease_expires_at"])
            if datetime.now(UTC) > expires_at:
                raise ConflictError(f"Task {task_id} submission rejected: lease expired at {row['lease_expires_at']}")

            current_usage = json.loads(row["resource_usage_json"] or "{}")
            if resource_usage:
                current_usage.update(resource_usage)

            conn.execute(
                """
                UPDATE coordination_tasks
                SET status = ?,
                    result_json = ?,
                    resource_usage_json = ?,
                    updated_at = ?
                WHERE task_id = ? AND lease_token = ?;
                """,
                (new_status.value, json.dumps(result), json.dumps(current_usage), now, task_id, lease_token),
            )

            # Decrement agent workload if completed or under review
            cur_agent = conn.execute("SELECT current_workload FROM agents WHERE agent_id = ?;", (agent_id,))
            a_row = cur_agent.fetchone()
            if a_row and a_row["current_workload"] > 0:
                conn.execute(
                    """
                    UPDATE agents
                    SET current_workload = current_workload - 1,
                        availability_status = ?,
                        updated_at = ?
                    WHERE agent_id = ?;
                    """,
                    (AgentState.AVAILABLE.value, now, agent_id),
                )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        task = self.get_task(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def reap_expired_leases(self, now: datetime | None = None) -> list[tuple[CoordinationTask, str]]:
        """Reap tasks with expired leases and handle retry or terminal failure."""
        conn = self._get_conn()
        current_time = now or datetime.now(UTC)
        current_iso = current_time.isoformat()

        reaped: list[tuple[CoordinationTask, str]] = []

        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute(
                """
                SELECT * FROM coordination_tasks
                WHERE status IN ('claimed', 'running')
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at < ?;
                """,
                (current_iso,),
            )
            rows = cur.fetchall()

            for row in rows:
                task_id = row["task_id"]
                assigned_agent_id = row["assigned_agent_id"]
                attempt_count = row["attempt_count"]
                max_attempts = row["max_attempts"]

                # Decrement agent workload
                if assigned_agent_id:
                    cur_a = conn.execute(
                        "SELECT current_workload FROM agents WHERE agent_id = ?;", (assigned_agent_id,)
                    )
                    a_row = cur_a.fetchone()
                    if a_row and a_row["current_workload"] > 0:
                        conn.execute(
                            """
                            UPDATE agents
                            SET current_workload = current_workload - 1,
                                availability_status = ?,
                                updated_at = ?
                            WHERE agent_id = ?;
                            """,
                            (AgentState.AVAILABLE.value, current_iso, assigned_agent_id),
                        )

                if attempt_count < max_attempts:
                    conn.execute(
                        """
                        UPDATE coordination_tasks
                        SET status = ?,
                            assigned_agent_id = NULL,
                            lease_token = NULL,
                            lease_expires_at = NULL,
                            failure_reason = ?,
                            updated_at = ?
                        WHERE task_id = ?;
                        """,
                        (
                            CoordinationTaskStatus.READY.value,
                            f"Lease expired on attempt {attempt_count}/{max_attempts}; reassigned to ready pool",
                            current_iso,
                            task_id,
                        ),
                    )
                    action = "reassigned"
                else:
                    conn.execute(
                        """
                        UPDATE coordination_tasks
                        SET status = ?,
                            failure_reason = ?,
                            updated_at = ?
                        WHERE task_id = ?;
                        """,
                        (
                            CoordinationTaskStatus.FAILED.value,
                            f"Lease expired and maximum attempts ({max_attempts}) exceeded",
                            current_iso,
                            task_id,
                        ),
                    )
                    action = "failed"

                updated_task = self.get_task(task_id)
                if updated_task:
                    reaped.append((updated_task, action))

            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        return reaped

    def _row_to_task(self, row: sqlite3.Row) -> CoordinationTask:
        return CoordinationTask(
            task_id=row["task_id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            required_capabilities=json.loads(row["required_capabilities_json"] or "[]"),
            required_tools=json.loads(row["required_tools_json"] or "[]"),
            min_verified_level=VerificationLevel(row["min_verified_level"] or "claimed"),
            priority=Priority(row["priority"] or "medium"),
            dependencies=json.loads(row["dependencies_json"] or "[]"),
            status=CoordinationTaskStatus(row["status"]),
            assigned_agent_id=row["assigned_agent_id"],
            lease_token=row["lease_token"],
            lease_expires_at=datetime.fromisoformat(row["lease_expires_at"]) if row["lease_expires_at"] else None,
            heartbeat_timeout_seconds=row["heartbeat_timeout_seconds"],
            max_attempts=row["max_attempts"],
            attempt_count=row["attempt_count"],
            failure_reason=row["failure_reason"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            resource_usage=json.loads(row["resource_usage_json"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    # =========================================================================
    # Collaboration Messages
    # =========================================================================

    def add_collaboration_message(self, msg: CollaborationMessage) -> CollaborationMessage:
        """Store a structured collaboration message."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute(
                """
                INSERT INTO collaboration_messages (
                    message_id, project_id, task_id, author_agent_id,
                    message_type, content, related_record_refs_json,
                    created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg.message_id,
                    msg.project_id,
                    msg.task_id,
                    msg.author_agent_id,
                    msg.message_type.value,
                    msg.content,
                    json.dumps(msg.related_record_refs),
                    msg.created_at.isoformat() if msg.created_at else now,
                    json.dumps(msg.metadata),
                ),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise
        return msg

    def list_collaboration_messages(
        self,
        project_id: str,
        task_id: str | None = None,
    ) -> list[CollaborationMessage]:
        """Retrieve collaboration messages for a project or specific task."""
        conn = self._get_conn()
        query = "SELECT * FROM collaboration_messages WHERE project_id = ?"
        params: list[Any] = [project_id]

        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)

        query += " ORDER BY created_at ASC;"
        cur = conn.execute(query, params)
        return [
            CollaborationMessage(
                message_id=r["message_id"],
                project_id=r["project_id"],
                task_id=r["task_id"],
                author_agent_id=r["author_agent_id"],
                message_type=MessageType(r["message_type"]),
                content=r["content"],
                related_record_refs=json.loads(r["related_record_refs_json"] or "[]"),
                created_at=datetime.fromisoformat(r["created_at"]),
                metadata=json.loads(r["metadata_json"] or "{}"),
            )
            for r in cur.fetchall()
        ]

    # =========================================================================
    # Issues & Help Requests
    # =========================================================================

    def create_issue(self, issue: CoordinationIssue) -> CoordinationIssue:
        """Create a new coordination issue."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute(
                """
                INSERT INTO coordination_issues (
                    issue_id, project_id, task_id, author_agent_id,
                    title, description, evidence_json, required_capabilities_json,
                    status, resolver_agent_id, resolution_proposal_json,
                    created_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    issue.issue_id,
                    issue.project_id,
                    issue.task_id,
                    issue.author_agent_id,
                    issue.title,
                    issue.description,
                    json.dumps(issue.evidence),
                    json.dumps(issue.required_capabilities),
                    issue.status.value,
                    issue.resolver_agent_id,
                    json.dumps(issue.resolution_proposal) if issue.resolution_proposal else None,
                    issue.created_at.isoformat() if issue.created_at else now,
                    issue.resolved_at.isoformat() if issue.resolved_at else None,
                ),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise
        return issue

    def get_issue(self, issue_id: str) -> CoordinationIssue | None:
        """Fetch issue by ID."""
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM coordination_issues WHERE issue_id = ?;", (issue_id,))
        row = cur.fetchone()
        if not row:
            return None
        return CoordinationIssue(
            issue_id=row["issue_id"],
            project_id=row["project_id"],
            task_id=row["task_id"],
            author_agent_id=row["author_agent_id"],
            title=row["title"],
            description=row["description"],
            evidence=json.loads(row["evidence_json"] or "{}"),
            required_capabilities=json.loads(row["required_capabilities_json"] or "[]"),
            status=IssueStatus(row["status"]),
            resolver_agent_id=row["resolver_agent_id"],
            resolution_proposal=json.loads(row["resolution_proposal_json"])
            if row["resolution_proposal_json"]
            else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
        )

    def list_issues(
        self,
        project_id: str,
        task_id: str | None = None,
        status: IssueStatus | None = None,
    ) -> list[CoordinationIssue]:
        """List coordination issues."""
        conn = self._get_conn()
        query = "SELECT * FROM coordination_issues WHERE project_id = ?"
        params: list[Any] = [project_id]

        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at ASC;"
        cur = conn.execute(query, params)
        return [
            CoordinationIssue(
                issue_id=r["issue_id"],
                project_id=r["project_id"],
                task_id=r["task_id"],
                author_agent_id=r["author_agent_id"],
                title=r["title"],
                description=r["description"],
                evidence=json.loads(r["evidence_json"] or "{}"),
                required_capabilities=json.loads(r["required_capabilities_json"] or "[]"),
                status=IssueStatus(r["status"]),
                resolver_agent_id=r["resolver_agent_id"],
                resolution_proposal=json.loads(r["resolution_proposal_json"])
                if r["resolution_proposal_json"]
                else None,
                created_at=datetime.fromisoformat(r["created_at"]),
                resolved_at=datetime.fromisoformat(r["resolved_at"]) if r["resolved_at"] else None,
            )
            for r in cur.fetchall()
        ]

    def resolve_issue(
        self,
        issue_id: str,
        resolver_agent_id: str,
        proposal: dict[str, Any],
    ) -> CoordinationIssue:
        """Mark issue as resolved with proposal details."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT issue_id FROM coordination_issues WHERE issue_id = ?;", (issue_id,))
            if not cur.fetchone():
                raise ResourceNotFoundError(f"Issue {issue_id} not found")

            conn.execute(
                """
                UPDATE coordination_issues
                SET status = ?,
                    resolver_agent_id = ?,
                    resolution_proposal_json = ?,
                    resolved_at = ?
                WHERE issue_id = ?;
                """,
                (IssueStatus.RESOLVED.value, resolver_agent_id, json.dumps(proposal), now, issue_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        issue = self.get_issue(issue_id)
        if not issue:
            raise ResourceNotFoundError(f"Issue {issue_id} not found")
        return issue

    def create_help_request(self, req: HelpRequest) -> HelpRequest:
        """Persist a new help request."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute(
                """
                INSERT INTO help_requests (
                    request_id, project_id, task_id, issue_id,
                    requester_agent_id, target_agent_id,
                    required_capabilities_json, status, assigned_helper_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    req.request_id,
                    req.project_id,
                    req.task_id,
                    req.issue_id,
                    req.requester_agent_id,
                    req.target_agent_id,
                    json.dumps(req.required_capabilities),
                    req.status.value,
                    req.assigned_helper_id,
                    req.created_at.isoformat() if req.created_at else now,
                    req.updated_at.isoformat() if req.updated_at else now,
                ),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise
        return req

    def get_help_request(self, request_id: str) -> HelpRequest | None:
        """Fetch help request by ID."""
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM help_requests WHERE request_id = ?;", (request_id,))
        row = cur.fetchone()
        if not row:
            return None
        return HelpRequest(
            request_id=row["request_id"],
            project_id=row["project_id"],
            task_id=row["task_id"],
            issue_id=row["issue_id"],
            requester_agent_id=row["requester_agent_id"],
            target_agent_id=row["target_agent_id"],
            required_capabilities=json.loads(row["required_capabilities_json"] or "[]"),
            status=HelpRequestStatus(row["status"]),
            assigned_helper_id=row["assigned_helper_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_help_requests(
        self,
        project_id: str,
        task_id: str | None = None,
        status: HelpRequestStatus | None = None,
    ) -> list[HelpRequest]:
        """List help requests."""
        conn = self._get_conn()
        query = "SELECT * FROM help_requests WHERE project_id = ?"
        params: list[Any] = [project_id]

        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at ASC;"
        cur = conn.execute(query, params)
        return [
            HelpRequest(
                request_id=r["request_id"],
                project_id=r["project_id"],
                task_id=r["task_id"],
                issue_id=r["issue_id"],
                requester_agent_id=r["requester_agent_id"],
                target_agent_id=r["target_agent_id"],
                required_capabilities=json.loads(r["required_capabilities_json"] or "[]"),
                status=HelpRequestStatus(r["status"]),
                assigned_helper_id=r["assigned_helper_id"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in cur.fetchall()
        ]

    def claim_help_request(self, request_id: str, helper_agent_id: str) -> HelpRequest:
        """Assign helper to help request."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT status FROM help_requests WHERE request_id = ?;", (request_id,))
            row = cur.fetchone()
            if not row:
                raise ResourceNotFoundError(f"Help request {request_id} not found")

            if row["status"] != HelpRequestStatus.OPEN.value:
                raise ConflictError(f"Help request {request_id} is already '{row['status']}'")

            conn.execute(
                """
                UPDATE help_requests
                SET status = ?, assigned_helper_id = ?, updated_at = ?
                WHERE request_id = ?;
                """,
                (HelpRequestStatus.CLAIMED.value, helper_agent_id, now, request_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        req = self.get_help_request(request_id)
        if not req:
            raise ResourceNotFoundError(f"Help request {request_id} not found")
        return req

    def fulfill_help_request(self, request_id: str) -> HelpRequest:
        """Mark help request as fulfilled."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            cur = conn.execute("SELECT request_id FROM help_requests WHERE request_id = ?;", (request_id,))
            if not cur.fetchone():
                raise ResourceNotFoundError(f"Help request {request_id} not found")

            conn.execute(
                """
                UPDATE help_requests
                SET status = ?, updated_at = ?
                WHERE request_id = ?;
                """,
                (HelpRequestStatus.FULFILLED.value, now, request_id),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

        req = self.get_help_request(request_id)
        if not req:
            raise ResourceNotFoundError(f"Help request {request_id} not found")
        return req

    # =========================================================================
    # Coordination Events
    # =========================================================================

    def log_event(self, event: CoordinationEvent) -> None:
        """Persist a coordination event for audit tracking."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute(
                """
                INSERT INTO coordination_events (
                    event_id, project_id, event_type, agent_id,
                    task_id, payload_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.event_id,
                    event.project_id,
                    event.event_type,
                    event.agent_id,
                    event.task_id,
                    json.dumps(event.payload),
                    event.timestamp.isoformat() if event.timestamp else now,
                ),
            )
            conn.execute("COMMIT;")
        except Exception:
            self._rollback(conn)
            raise

    def list_events(
        self,
        project_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[CoordinationEvent]:
        """Fetch recorded audit events."""
        conn = self._get_conn()
        query = "SELECT * FROM coordination_events WHERE project_id = ?"
        params: list[Any] = [project_id]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY timestamp DESC LIMIT ?;"
        params.append(limit)

        cur = conn.execute(query, params)
        return [
            CoordinationEvent(
                event_id=r["event_id"],
                project_id=r["project_id"],
                event_type=r["event_type"],
                agent_id=r["agent_id"],
                task_id=r["task_id"],
                payload=json.loads(r["payload_json"] or "{}"),
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in cur.fetchall()
        ]
