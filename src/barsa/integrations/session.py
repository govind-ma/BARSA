"""Agent session management for Phase 12 Cross-AI workflows.

Ensures clean isolation between AI environments:
Agent A and Agent B operate in separate sessions with zero shared in-memory conversation state.
Continuity is achieved solely through authoritative Barsa checkpoints and memory DAG commits.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from barsa.integrations.models import ClientHandoffContext, ClientSessionConfig, TaskContinuationResult

if TYPE_CHECKING:
    from barsa.integrations.adapter import AIClientAdapter

logger = logging.getLogger("barsa.integrations.session")


class AgentSession:
    """Represents an isolated, independent AI agent work session."""

    def __init__(self, config: ClientSessionConfig, adapter: AIClientAdapter) -> None:
        self.config = config
        self.adapter = adapter
        self.context: ClientHandoffContext | None = None
        self.session_conversation_log: list[dict[str, str]] = []
        self._start_time: float = 0.0

    async def start(self, project_id: str) -> ClientHandoffContext:
        """Initialize session, connect to Barsa transport, and load project context."""
        self._start_time = time.time()
        await self.adapter.connect()
        await self.adapter.authenticate(self.config.api_key)
        await self.adapter.select_project(project_id)

        # Retrieve authoritative context via Smart Context Engine / MCP
        self.context = await self.adapter.get_context()

        # Log initial prompt in isolated session history
        self.session_conversation_log.append(
            {
                "role": "system",
                "content": f"Session initialized for {self.config.client_id} ({self.config.provider.value}). Project: {project_id}",
            }
        )
        self.session_conversation_log.append(
            {
                "role": "user",
                "content": f"Connect to Barsa project {project_id} and resume work.",
            }
        )
        self.session_conversation_log.append(
            {
                "role": "assistant",
                "content": f"Retrieved project state. Next task is: '{self.context.next_task}'",
            }
        )

        return self.context

    def inspect_understanding(self) -> dict[str, Any]:
        """Audit the agent's derived understanding of the project strictly from Barsa state."""
        if not self.context:
            raise RuntimeError("Session has not been started")

        return {
            "project_id": self.context.project_id,
            "project_name": self.context.project_name,
            "next_task": self.context.next_task,
            "completed_actions": list(self.context.completed_actions),
            "pending_actions": list(self.context.pending_actions),
            "blockers": list(self.context.blockers),
            "has_checkpoint": self.context.latest_checkpoint is not None,
            "total_tokens_consumed": self.context.total_tokens,
        }

    async def complete_work_and_commit(
        self,
        task_id: str,
        task_title: str,
        action_performed: str,
        new_records: list[dict[str, Any]],
        next_task_for_future_agent: str,
        commit_message: str,
        test_results: dict[str, Any] | None = None,
        branch_name: str = "main",
    ) -> TaskContinuationResult:
        """Record work completed, save checkpoint, and commit to the Barsa memory DAG."""
        if not self.context:
            raise RuntimeError("Session has not been started")

        from barsa.bms.base import BMS_VERSION

        # 1. Prepare candidate changes
        changes = []
        for rec in new_records:
            rec_id = rec.get("id") or rec.get("record_id")
            rec_type = rec.get("record_type", "task")
            # Ensure schema_version and id are populated
            rec["schema_version"] = BMS_VERSION
            if "id" not in rec and rec_id:
                rec["id"] = rec_id
            changes.append(
                {
                    "record_id": rec_id,
                    "record_type": rec_type,
                    "operation": "create",
                    "after_state": rec,
                }
            )

        # 2. Add or update Checkpoint record conforming to BMS ResumeCheckpoint
        new_checkpoint_id = f"chk-{self.config.client_id}-{int(time.time() * 1000)}"
        base_rev = "initial"
        if self.context.latest_checkpoint:
            base_rev = (
                self.context.latest_checkpoint.get("id")
                or self.context.latest_checkpoint.get("checkpoint_id")
                or "initial"
            )

        checkpoint_rec = {
            "id": new_checkpoint_id,
            "schema_version": BMS_VERSION,
            "record_type": "checkpoint",
            "project_id": self.context.project_id,
            "task_id": task_id,
            "status": "active",
            "completed_actions": [*self.context.completed_actions, action_performed],
            "pending_actions": [p for p in self.context.pending_actions if p != task_title],
            "next_action": next_task_for_future_agent,
            "blockers": [],
            "decision_refs": [
                d.get("id") for d in self.context.recent_decisions if isinstance(d, dict) and d.get("id")
            ],
            "artifact_refs": [
                a.get("id") for a in self.context.relevant_artifacts if isinstance(a, dict) and a.get("id")
            ],
            "base_revision": base_rev,
            "created_by": self.config.client_id,
        }
        changes.append(
            {
                "record_id": new_checkpoint_id,
                "record_type": "checkpoint",
                "operation": "create",
                "after_state": checkpoint_rec,
            }
        )

        # 3. Commit to Version Control Engine via adapter
        commit_res = await self.adapter.commit(
            message=commit_message,
            branch_name=branch_name,
            changes=changes,
            author_name=f"{self.config.client_id} ({self.config.provider.value})",
        )

        commit_hash = commit_res.get("commit_hash") or commit_res.get("commit_id") or "commit_hash_unknown"
        elapsed = time.time() - self._start_time

        result = TaskContinuationResult(
            agent_id=self.config.client_id,
            provider=self.config.provider.value,
            model=self.config.model,
            starting_checkpoint_id=self.context.latest_checkpoint.get("id") if self.context.latest_checkpoint else None,
            task_id=task_id,
            task_title=task_title,
            action_performed=action_performed,
            test_results=test_results or {"passed": True},
            new_commit_hash=commit_hash,
            new_checkpoint_id=new_checkpoint_id,
            execution_time_seconds=elapsed,
        )

        # Log in local agent history
        self.session_conversation_log.append(
            {
                "role": "assistant",
                "content": f"Completed '{action_performed}'. Created commit {commit_hash} with checkpoint {new_checkpoint_id}.",
            }
        )

        return result

    async def finish(self) -> None:
        """Disconnect and release session resources."""
        await self.adapter.disconnect()
