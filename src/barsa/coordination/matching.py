"""Capability-based deterministic task matching and scheduling for BARSA."""

import logging
from datetime import UTC, datetime

from barsa.coordination.models import (
    AgentProfile,
    AgentState,
    AssignmentDecision,
    CoordinationTask,
    VerificationLevel,
)

logger = logging.getLogger("barsa.coordination.matching")


class CapabilityMatcher:
    """Deterministic, explainable capability matcher."""

    @staticmethod
    def match_task_to_agents(
        task: CoordinationTask,
        candidates: list[AgentProfile],
        completed_task_ids: set[str] | None = None,
        heartbeat_cutoff_seconds: int = 120,
    ) -> AssignmentDecision:
        """Evaluate candidates against task requirements and return the best match with reasons."""
        decision = AssignmentDecision(task_id=task.task_id)
        now = datetime.now(UTC)

        # 1. Dependency check
        completed = completed_task_ids or set()
        unmet_deps = [d for d in task.dependencies if d not in completed]
        if unmet_deps:
            decision.reasons.append(f"Task has unmet dependencies: {', '.join(unmet_deps)}")
            return decision

        scored_candidates: list[tuple[float, str, AgentProfile, list[str]]] = []

        for agent in candidates:
            eligible = True
            agent_reasons: list[str] = []

            # 2. Availability & Heartbeat check
            if agent.availability_status in (AgentState.DISABLED, AgentState.OFFLINE):
                continue

            hb_diff = (now - agent.last_heartbeat).total_seconds()
            if hb_diff > heartbeat_cutoff_seconds:
                continue

            # 3. Project authorization
            if "*" not in agent.allowed_projects and task.project_id not in agent.allowed_projects:
                continue

            # 4. Workload check
            if agent.current_workload >= agent.maximum_concurrent_tasks:
                continue

            # 5. Tool verification
            missing_tools = [t for t in task.required_tools if t not in agent.supported_tools]
            if missing_tools:
                continue

            # 6. Capability verification
            agent_verified = set(agent.verified_capabilities)
            agent_claimed = set(agent.claimed_capabilities)

            score = 0.0

            if task.min_verified_level == VerificationLevel.VERIFIED:
                missing_caps = [c for c in task.required_capabilities if c not in agent_verified]
                if missing_caps:
                    eligible = False
                else:
                    agent_reasons.append(
                        f"All {len(task.required_capabilities)} required capabilities verified formally"
                    )
                    score += len(task.required_capabilities) * 10.0
            else:
                missing_caps = [
                    c for c in task.required_capabilities if c not in agent_verified and c not in agent_claimed
                ]
                if missing_caps:
                    eligible = False
                else:
                    verified_hits = [c for c in task.required_capabilities if c in agent_verified]
                    claimed_hits = [
                        c for c in task.required_capabilities if c in agent_claimed and c not in agent_verified
                    ]
                    score += len(verified_hits) * 10.0 + len(claimed_hits) * 5.0
                    agent_reasons.append(
                        f"Matched capabilities: {len(verified_hits)} verified, {len(claimed_hits)} claimed"
                    )

            if not eligible:
                continue

            # Tool match score
            if task.required_tools:
                score += len(task.required_tools) * 2.0
                agent_reasons.append(f"Supports all required tools: {', '.join(task.required_tools)}")

            # Workload factor: prioritize less loaded workers
            load_ratio = agent.current_workload / agent.maximum_concurrent_tasks
            workload_penalty = load_ratio * 5.0
            score -= workload_penalty
            agent_reasons.append(
                f"Workload {agent.current_workload}/{agent.maximum_concurrent_tasks} (penalty: -{workload_penalty:.1f})"
            )

            # Extra capabilities bonus
            extra_caps = len(agent_verified.union(agent_claimed) - set(task.required_capabilities))
            score += min(extra_caps * 0.2, 2.0)

            # Store: sort descending by score, then ascending by agent_id for pure determinism
            scored_candidates.append((score, agent.agent_id, agent, agent_reasons))

        if not scored_candidates:
            decision.reasons.append("No eligible agents met availability, capability, tool, and workload requirements")
            return decision

        # Sort descending by score, ascending by agent_id
        scored_candidates.sort(key=lambda x: (-x[0], x[1]))

        top_score, top_agent_id, top_agent, top_reasons = scored_candidates[0]
        decision.assigned_agent_id = top_agent_id
        decision.eligible_agents = [c[1] for c in scored_candidates]
        decision.score = round(top_score, 2)
        decision.reasons = [
            f"Selected optimal agent '{top_agent.display_name}' ({top_agent_id}) with composite score {top_score:.2f}",
            *top_reasons,
        ]
        if len(scored_candidates) > 1:
            decision.reasons.append(
                f"Evaluated {len(scored_candidates)} eligible candidates; runner up: {scored_candidates[1][1]} (score: {scored_candidates[1][0]:.2f})"
            )

        return decision
