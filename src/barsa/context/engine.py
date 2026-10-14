"""Barsa Smart Context Engine (SCE) — Core Orchestrator (Phase 8)."""

import logging
from typing import Any

from barsa.context.budget import TokenBudgetAllocator
from barsa.context.compression import (
    compress_checkpoint_record,
    compress_decision_record,
    compress_generic_record,
    compress_task_record,
)
from barsa.context.deduplication import RecordDeduplicator
from barsa.context.incremental import IncrementalSyncService
from barsa.context.models import (
    BarsaContextPackage,
    ContextEstimateResponse,
    ContextLevel,
    ContextRequest,
    ContextStatusResponse,
    RankingExplanation,
)
from barsa.context.ranking import RelevanceRanker
from barsa.context.token_counter import TokenCounter, get_token_counter
from barsa.context.validation import ContextCompletenessValidator
from barsa.core.exceptions import ResourceNotFoundError
from barsa.graph.retrieval import GraphRetrievalService
from barsa.storage.protocol import StorageProvider
from barsa.versioning.engine import VersionControlEngine

logger = logging.getLogger("barsa.context.engine")


class SmartContextEngine:
    """Core Smart Context Engine providing token-efficient, graph-aware, three-level memory retrieval."""

    def __init__(
        self,
        storage: StorageProvider,
        vc: VersionControlEngine,
        graph_retrieval: GraphRetrievalService | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self.storage = storage
        self.vc = vc
        self.graph = graph_retrieval
        self.default_counter = token_counter or get_token_counter()
        self.ranker = RelevanceRanker()
        self.incremental_service = IncrementalSyncService(vc)

    def _resolve_target_counter(self, target_model: str | None) -> TokenCounter:
        if target_model:
            return get_token_counter(target_model)
        return self.default_counter

    def get_context_status(self, project_id: str) -> ContextStatusResponse:
        """Inspect context readiness, graph freshness, and record counts."""
        proj = self.storage.get_project(project_id)
        if not proj:
            raise ResourceNotFoundError(f"Project '{project_id}' not found.", "Project", project_id)

        main_branch = self.vc.get_branch(project_id, "main")
        authoritative_commit = main_branch.head_commit_id if main_branch else "none"

        graph_status_str = "UNAVAILABLE"
        graph_commit = None
        is_fresh = False

        if self.graph:
            node = self.graph.get_node(project_id, project_id)
            if node and "projection_status" in node:
                p_meta = node["projection_status"]
                graph_status_str = p_meta.get("status", "UP_TO_DATE")
                graph_commit = p_meta.get("last_applied_commit_id")
                is_fresh = graph_commit == authoritative_commit
            else:
                graph_status_str = "UP_TO_DATE"
                is_fresh = True

        all_records = self.storage.list_records(project_id, limit=100000)
        tasks = [
            r
            for r in all_records
            if (isinstance(r, tuple) and getattr(r[0], "record_type", "") == "task")
            or getattr(r, "record_type", "") == "task"
        ]
        decisions = [
            r
            for r in all_records
            if (isinstance(r, tuple) and getattr(r[0], "record_type", "") == "decision")
            or getattr(r, "record_type", "") == "decision"
        ]
        checkpoints = [
            r
            for r in all_records
            if (isinstance(r, tuple) and getattr(r[0], "record_type", "") == "checkpoint")
            or getattr(r, "record_type", "") == "checkpoint"
        ]

        latest_cp_id = None
        if checkpoints:
            checkpoints.sort(
                key=lambda x: str(getattr(x[0] if isinstance(x, tuple) else x, "created_at", "")), reverse=True
            )
            first_cp = checkpoints[0][0] if isinstance(checkpoints[0], tuple) else checkpoints[0]
            latest_cp_id = getattr(first_cp, "id", None)

        return ContextStatusResponse(
            project_id=project_id,
            authoritative_commit=authoritative_commit,
            graph_projection_status=graph_status_str,
            applied_graph_commit=graph_commit,
            is_graph_fresh=is_fresh,
            total_records_count=len(all_records),
            active_tasks_count=len(tasks),
            approved_decisions_count=len(decisions),
            latest_checkpoint_id=latest_cp_id,
        )

    def estimate_tokens(self, request: ContextRequest) -> ContextEstimateResponse:
        """Estimate token usage and budget feasibility without full packaging."""
        proj = self.storage.get_project(request.project_id)
        if not proj:
            raise ResourceNotFoundError(f"Project '{request.project_id}' not found.", "Project", request.project_id)

        counter = self._resolve_target_counter(request.target_model)
        records = self.storage.list_records(request.project_id, limit=100000)
        clean_records = [
            r[0].model_dump(mode="json") if isinstance(r, tuple) else r.model_dump(mode="json") for r in records
        ]

        # Rough mandatory Level 1 estimate (project info + active task + latest checkpoint + approved decisions)
        mandatory_sample = clean_records[: min(4, len(clean_records))]
        import json

        mandatory_tokens = counter.count(json.dumps(mandatory_sample, ensure_ascii=False))

        # Total candidate tokens
        total_sample_tokens = counter.count(json.dumps(clean_records, ensure_ascii=False))
        fits = total_sample_tokens <= request.max_context_tokens

        recommended_level = ContextLevel.WORKING
        if total_sample_tokens > request.max_context_tokens * 1.5:
            recommended_level = ContextLevel.ESSENTIAL
        elif fits:
            recommended_level = ContextLevel.DETAILED if request.include_history else ContextLevel.WORKING

        return ContextEstimateResponse(
            project_id=request.project_id,
            estimated_tokens=total_sample_tokens,
            budget=request.max_context_tokens,
            fits_budget=fits,
            tokenizer=counter.name,
            estimation_method=counter.estimation_method,
            candidate_records_count=len(clean_records),
            mandatory_tokens=mandatory_tokens,
            recommended_level=recommended_level,
        )

    def build_context(self, request: ContextRequest) -> BarsaContextPackage:
        """Build a validated, token-optimized context package according to the pipeline."""
        # 1. Verify project exists
        proj = self.storage.get_project(request.project_id)
        if not proj:
            raise ResourceNotFoundError(f"Project '{request.project_id}' not found.", "Project", request.project_id)

        # 2. Resolve authoritative commit & branch
        main_branch = self.vc.get_branch(request.project_id, "main")
        if not main_branch:
            main_branch = self.vc.initialize_project_main_branch(request.project_id)
        authoritative_commit = main_branch.head_commit_id

        counter = self._resolve_target_counter(request.target_model)

        # 3. Incremental Delta Check
        incremental_meta = None
        if request.known_revision:
            incremental_meta, _delta = self.incremental_service.compute_incremental_sync(
                request.project_id, request.known_revision, authoritative_commit
            )

        # 4. Gather Authoritative State from Storage
        all_raw_records = self.storage.list_records(request.project_id, limit=100000)
        all_records: list[dict[str, Any]] = [
            r[0].model_dump(mode="json") if isinstance(r, tuple) else r.model_dump(mode="json") for r in all_raw_records
        ]

        # 5. Graph Retrieval for Topological Proximity
        graph_commit = None
        graph_dependencies: list[dict[str, Any]] = []
        graph_blockers: list[str] = []
        graph_neighbor_ids: set[str] = set()

        if self.graph:
            try:
                overview = self.graph.get_project_overview(request.project_id)
                if overview.projection_status:
                    graph_commit = overview.projection_status.last_applied_commit_id

                if request.task_id:
                    resume_ctx = self.graph.get_resume_context(request.project_id, request.task_id)
                    graph_dependencies = resume_ctx.dependencies
                    graph_blockers = resume_ctx.blockers
                    for dep in graph_dependencies:
                        dep_id = dep.get("raw_id") or dep.get("id")
                        if dep_id:
                            graph_neighbor_ids.add(dep_id)
            except Exception as exc:
                logger.warning("Graph retrieval non-fatal exception: %s", exc)

        # 6. Separate into Levels
        # Identify Target Task
        target_task: dict[str, Any] | None = None
        if request.task_id:
            for r in all_records:
                if r.get("record_type") == "task" and (
                    r.get("id") == request.task_id or r.get("raw_id") == request.task_id
                ):
                    target_task = compress_task_record(r)
                    break
        else:
            # Pick first in_progress or open task
            for r in all_records:
                if r.get("record_type") == "task" and r.get("status") in ("in_progress", "active"):
                    target_task = compress_task_record(r)
                    break

        # Identify Latest Applicable Checkpoint
        latest_cp: dict[str, Any] | None = None
        matching_cps = []
        for r in all_records:
            if r.get("record_type") == "checkpoint" and (
                target_task and r.get("task_id") == target_task.get("id") or not target_task
            ):
                matching_cps.append(r)
        if matching_cps:
            matching_cps.sort(
                key=lambda x: (
                    1 if x.get("status") == "active" else 0,
                    str(x.get("created_at", "")),
                    str(x.get("id", "")),
                ),
                reverse=True,
            )
            latest_cp = compress_checkpoint_record(matching_cps[0])
        elif not matching_cps:
            all_cps = [r for r in all_records if r.get("record_type") == "checkpoint"]
            if all_cps:
                all_cps.sort(
                    key=lambda x: (
                        1 if x.get("status") == "active" else 0,
                        str(x.get("created_at", "")),
                        str(x.get("id", "")),
                    ),
                    reverse=True,
                )
                latest_cp = compress_checkpoint_record(all_cps[0])

        # Next Action & Blockers
        next_action = latest_cp.get("next_action") if latest_cp else None
        completed_actions = latest_cp.get("completed_actions", []) if latest_cp else []
        pending_actions = latest_cp.get("pending_actions", []) if latest_cp else []

        combined_blockers: list[str] = list(set(graph_blockers + (latest_cp.get("blockers", []) if latest_cp else [])))

        # Approved Decisions (Level 1)
        approved_decisions: list[dict[str, Any]] = []
        superseded_or_proposed_decisions: list[dict[str, Any]] = []
        for r in all_records:
            if r.get("record_type") == "decision":
                if r.get("status") == "approved":
                    approved_decisions.append(compress_decision_record(r))
                else:
                    superseded_or_proposed_decisions.append(compress_decision_record(r))

        # Level 1 Mandatory Set
        mandatory_components: list[dict[str, Any]] = []
        if target_task:
            mandatory_components.append({"type": "task", "data": target_task})
        if latest_cp:
            mandatory_components.append({"type": "checkpoint", "data": latest_cp})
        for ad in approved_decisions:
            mandatory_components.append({"type": "approved_decision", "data": ad})

        # Candidate Optional Records (Level 2 & Level 3)
        candidate_optional: list[dict[str, Any]] = []

        # Dependencies & Requirements (Level 2)
        dependencies: list[dict[str, Any]] = []
        requirements: list[dict[str, Any]] = []
        working_knowledge: list[dict[str, Any]] = []
        references: list[str] = []

        for r in all_records:
            r_type = r.get("record_type")
            r_id = r.get("id") or r.get("raw_id")

            # Avoid re-adding mandatory items
            if target_task and r_id == target_task.get("id"):
                continue
            if latest_cp and r_id == latest_cp.get("id"):
                continue
            if any(ad.get("id") == r_id for ad in approved_decisions):
                continue

            if r_type == "task":
                dependencies.append(compress_task_record(r))
            elif r_type in ("knowledge", "fact", "rule"):
                working_knowledge.append(compress_generic_record(r))
            elif r_type == "artifact":
                uri = r.get("uri") or r.get("path")
                if uri:
                    references.append(uri)
            elif r_type == "requirement":
                requirements.append(compress_generic_record(r))
            elif r_type == "decision":
                candidate_optional.append(compress_decision_record(r))
            elif r_type == "checkpoint" and (request.include_history or request.context_level == ContextLevel.DETAILED):
                candidate_optional.append(compress_checkpoint_record(r))

        if request.context_level in (ContextLevel.WORKING, ContextLevel.ADAPTIVE, ContextLevel.DETAILED):
            candidate_optional.extend(dependencies)
            candidate_optional.extend(requirements)
            candidate_optional.extend(working_knowledge)

        # Level 3 Historical Commits (if explicitly requested)
        historical_commits: list[dict[str, Any]] = []
        if request.include_history or request.context_level == ContextLevel.DETAILED:
            commits = self.vc.get_history(request.project_id, limit=10)
            for c in commits:
                historical_commits.append(
                    {
                        "commit_id": c.commit_id,
                        "message": c.message,
                        "author_id": c.author_id,
                        "created_at": c.created_at.isoformat(),
                    }
                )
            candidate_optional.extend(historical_commits)

        # 7. Deduplication
        deduplicator = RecordDeduplicator()
        unique_candidates = deduplicator.filter_unique(candidate_optional)

        # 8. Relevance Ranking
        ranked_candidates: list[tuple[dict[str, Any], RankingExplanation]] = []
        target_t_id = target_task.get("id") if target_task else request.task_id

        for c_rec in unique_candidates:
            c_id = str(c_rec.get("id") or "")
            dist = 1 if c_id in graph_neighbor_ids else (2 if graph_neighbor_ids else None)
            is_dep = any(d.get("id") == c_id for d in dependencies)
            is_cp_ref = c_id in (latest_cp.get("completed_actions", []) if latest_cp else [])
            explanation = self.ranker.rank_record(
                record=c_rec,
                target_task_id=target_t_id,
                query=request.query,
                graph_distance=dist,
                is_dependency=is_dep,
                is_checkpoint_ref=is_cp_ref,
            )
            ranked_candidates.append((c_rec, explanation))

        # 9. Token Budget Allocation
        allocator = TokenBudgetAllocator(counter)
        allocation = allocator.allocate(
            max_tokens=request.max_context_tokens,
            reserved_overhead=request.reserved_overhead_tokens,
            mandatory_records=mandatory_components,
            candidate_optional=ranked_candidates,
        )

        # 10. Filter Selected Optional Records into Structured Buckets
        included_opt_ids = {str(r.get("id") or r.get("commit_id")) for r in allocation.included_optional}
        final_dependencies = [d for d in dependencies if d.get("id") in included_opt_ids]
        final_requirements = [req for req in requirements if req.get("id") in included_opt_ids]
        final_working_knowledge = [wk for wk in working_knowledge if wk.get("id") in included_opt_ids]
        final_history = [hc for hc in historical_commits if hc.get("commit_id") in included_opt_ids]

        all_included = (
            ([target_task] if target_task else [])
            + ([latest_cp] if latest_cp else [])
            + approved_decisions
            + allocation.included_optional
        )

        # 11. Completeness Validation
        final_completeness, completeness_reasons, warnings = ContextCompletenessValidator.validate_package(
            project_id=request.project_id,
            target_task_id=target_t_id,
            authoritative_commit=authoritative_commit,
            graph_commit=graph_commit,
            current_task=target_task,
            latest_checkpoint=latest_cp,
            blockers=combined_blockers,
            approved_decisions=approved_decisions,
            omitted_refs=allocation.omitted_record_refs,
            base_completeness=allocation.completeness,
            all_included_records=all_included,
        )
        completeness_reasons.extend(allocation.completeness_reasons)

        # 12. Build Final Context Package
        return BarsaContextPackage(
            context_format_version="0.1",
            project_id=request.project_id,
            authoritative_commit=authoritative_commit,
            task_id=target_t_id,
            goal=proj.description or "",
            current_task=target_task,
            latest_checkpoint=latest_cp,
            completed=completed_actions,
            pending=pending_actions,
            next_action=next_action,
            blockers=combined_blockers,
            approved_decisions=approved_decisions,
            dependencies=final_dependencies,
            requirements=final_requirements,
            working_knowledge=final_working_knowledge,
            historical_context=final_history,
            references=references,
            omitted_record_refs=allocation.omitted_record_refs,
            ranking_explanations=[exp for _rec, exp in ranked_candidates],
            incremental_sync=incremental_meta,
            token_usage=allocation.token_usage,
            completeness=final_completeness,
            completeness_reasons=list(dict.fromkeys(completeness_reasons)),
            warnings=warnings,
        )
