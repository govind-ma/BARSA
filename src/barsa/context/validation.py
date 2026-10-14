"""Context package completeness, freshness, and security validator (Phase 8)."""

from typing import Any

from barsa.context.models import CompletenessStatus


class ContextCompletenessValidator:
    """Validates structural completeness, graph freshness, and project isolation for context packages."""

    @staticmethod
    def validate_package(
        project_id: str,
        target_task_id: str | None,
        authoritative_commit: str,
        graph_commit: str | None,
        current_task: dict[str, Any] | None,
        latest_checkpoint: dict[str, Any] | None,
        blockers: list[str],
        approved_decisions: list[dict[str, Any]],
        omitted_refs: list[str],
        base_completeness: CompletenessStatus,
        all_included_records: list[dict[str, Any]],
    ) -> tuple[CompletenessStatus, list[str], list[str]]:
        """Validate package integrity.

        Returns (final_status, completeness_reasons, warnings).
        """
        reasons: list[str] = []
        warnings: list[str] = []
        status = base_completeness

        # 1. Tenant & Project Isolation check
        for rec in all_included_records:
            rec_proj = rec.get("project_id")
            if rec_proj and rec_proj != project_id:
                raise ValueError(
                    f"Cross-project isolation violation! Record '{rec.get('id')}' belongs to '{rec_proj}', not '{project_id}'."
                )

        # 2. Graph Freshness Check
        if graph_commit and graph_commit != authoritative_commit:
            status = CompletenessStatus.STALE
            warnings.append(
                f"Knowledge graph projection is lagging (applied commit: {graph_commit[:8]}, "
                f"authoritative HEAD: {authoritative_commit[:8]})."
            )
            reasons.append("Graph relationships were resolved using a prior commit.")
        elif graph_commit is None:
            warnings.append("Graph projection metadata unavailable; authoritative SQLite state used directly.")

        # 3. Task Consistency Check
        if target_task_id and not current_task:
            warnings.append(f"Target task '{target_task_id}' was requested but could not be located in project memory.")
            if status != CompletenessStatus.INSUFFICIENT:
                status = CompletenessStatus.PARTIAL
                reasons.append("Requested task was missing from project records.")

        # 4. Checkpoint Consistency Check
        if latest_checkpoint:
            cp_task = latest_checkpoint.get("task_id")
            if target_task_id and cp_task and cp_task != target_task_id:
                warnings.append(
                    f"Latest project checkpoint '{latest_checkpoint.get('id')}' targets task '{cp_task}', "
                    f"differing from requested task '{target_task_id}'."
                )

        # 5. Blockers Check
        if blockers:
            reasons.append(f"{len(blockers)} unresolved blocker(s) actively flagged in context.")

        # 6. Approved Decisions Check
        if approved_decisions:
            reasons.append(f"{len(approved_decisions)} approved architectural decision(s) active.")
        else:
            warnings.append("Zero approved decisions recorded for this project.")

        # 7. Omission Check
        if omitted_refs:
            if status == CompletenessStatus.SUFFICIENT:
                status = CompletenessStatus.PARTIAL
            reasons.append(f"{len(omitted_refs)} optional record(s) omitted due to token budget.")

        return status, reasons, warnings
