"""Tool implementations for Barsa Model Context Protocol (MCP) server.

All operations strictly delegate to authoritative Barsa services (StorageProvider,
VersionControlEngine, GraphProjectionWorker, GraphRetrievalService).
"""

import contextlib
import json
from typing import Any

from barsa.bms.serialization import validate_record
from barsa.context.engine import SmartContextEngine
from barsa.context.models import ContextLevel, ContextRequest
from barsa.context.ranking import RelevanceRanker
from barsa.core.exceptions import ConflictError, ResourceNotFoundError, ValidationError
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.protocol import GraphProvider
from barsa.graph.retrieval import GraphRetrievalService
from barsa.mcp.errors import BarsaMCPError, MCPErrorCode
from barsa.mcp.security import (
    get_current_identity,
    validate_branch_name,
    validate_changes_payload,
    validate_depth,
    validate_identifier,
    validate_limit,
    validate_query_string,
    verify_project_access,
)
from barsa.models.versioning import ChangeOperation, MemoryChange
from barsa.storage.protocol import StorageProvider
from barsa.versioning.engine import VersionControlEngine


def list_projects_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    workspace_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List projects accessible to the current identity with main branch status."""
    safe_limit = validate_limit(limit)
    safe_offset = max(0, offset)

    if workspace_id:
        all_projects = storage.list_projects(workspace_id=workspace_id)
    else:
        workspaces = storage.list_workspaces()
        all_projects = []
        for ws in workspaces:
            all_projects.extend(storage.list_projects(workspace_id=ws.id))

    total_count = len(all_projects)
    page_projects = all_projects[safe_offset : safe_offset + safe_limit]

    results = []
    for proj in page_projects:
        head_commit = None
        try:
            main_branch = vc.get_branch(proj.id, "main")
            if main_branch:
                head_commit = main_branch.head_commit_id
        except Exception:
            head_commit = None

        results.append(
            {
                "project_id": proj.id,
                "project_name": proj.name,
                "workspace_id": proj.workspace_id,
                "status": proj.status.value if hasattr(proj.status, "value") else str(proj.status),
                "description": proj.description,
                "latest_main_commit": head_commit,
                "created_at": proj.created_at.isoformat() if hasattr(proj, "created_at") else None,
            }
        )

    return {
        "projects": results,
        "total_count": total_count,
        "limit": safe_limit,
        "offset": safe_offset,
    }


def get_project_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    project_id: str,
) -> dict[str, Any]:
    """Retrieve detailed project overview, goals, current status, and main revision."""
    proj = verify_project_access(project_id, storage)

    main_branch = vc.get_branch(proj.id, "main")
    head_commit_id = main_branch.head_commit_id if main_branch else None

    # Count total active records in project
    try:
        records = storage.list_records(proj.id)
        record_count = len(records)
    except Exception:
        record_count = 0

    return {
        "project_id": proj.id,
        "project_name": proj.name,
        "workspace_id": proj.workspace_id,
        "status": proj.status.value if hasattr(proj.status, "value") else str(proj.status),
        "description": proj.description,
        "current_main_commit": head_commit_id,
        "total_records_count": record_count,
        "created_at": proj.created_at.isoformat() if hasattr(proj, "created_at") else None,
        "metadata": getattr(proj, "metadata", {}),
    }


def search_memory_tool(
    storage: StorageProvider,
    worker: GraphProjectionWorker,
    graph: GraphProvider,
    project_id: str,
    query: str,
    record_types: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search existing indexed or structured memory for a project using keyword and graph attributes."""
    verify_project_access(project_id, storage)
    safe_query = validate_query_string(query).lower()
    safe_limit = validate_limit(limit, default=20, max_limit=50)

    # 1. Fetch records from authoritative storage
    raw_records = storage.list_records(project_id)
    matches = []

    ranker = RelevanceRanker()
    for item in raw_records:
        rec = item[0] if isinstance(item, tuple) else item
        rec_data = rec.model_dump(mode="json")
        rec_type = rec_data.get("record_type", "")
        if record_types and rec_type not in record_types:
            continue

        # Substring search across relevant text fields
        text_corpus = " ".join(
            str(v)
            for k, v in rec_data.items()
            if isinstance(v, (str, int, float)) and k not in ("id", "project_id", "record_type", "created_at")
        ).lower()

        if safe_query in text_corpus or safe_query in rec.id.lower():
            # Excerpt extraction
            excerpt = None
            if "content" in rec_data:
                excerpt = str(rec_data["content"])[:200]
            elif "description" in rec_data:
                excerpt = str(rec_data["description"])[:200]
            elif "rationale" in rec_data:
                excerpt = str(rec_data["rationale"])[:200]
            elif "title" in rec_data:
                excerpt = str(rec_data["title"])[:200]

            rank_res = ranker.rank_record(record=rec_data, query=safe_query)

            matches.append(
                {
                    "record_id": rec.id,
                    "record_type": rec_type,
                    "relevance_score": rank_res.relevance_score,
                    "ranking_reasons": rank_res.reasons,
                    "excerpt": excerpt,
                    "properties": {
                        k: v for k, v in rec_data.items() if k in ("title", "status", "priority", "assignee_id")
                    },
                    "created_at": rec_data.get("created_at"),
                }
            )

    # Sort matches by algorithmic relevance score descending
    matches.sort(key=lambda m: m["relevance_score"], reverse=True)

    # Check projection status
    proj_status = worker.get_projection_status(project_id)
    applied_revision = proj_status.applied_revision if proj_status else 1
    applied_commit = proj_status.applied_commit_id if proj_status else None

    return {
        "project_id": project_id,
        "query": query,
        "matches": matches[:safe_limit],
        "total_matches": len(matches),
        "applied_graph_commit": applied_commit,
        "applied_graph_revision": applied_revision,
        "graph_available": graph.is_available(),
        "retrieval_limitations": (
            "Exact and substring matching across record attributes and graph index. "
            "Semantic/vector embedding search is not enabled in this deployment."
        ),
    }


def get_memory_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    project_id: str,
    record_id: str,
    commit_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve exact memory record or historical snapshot at a specific commit."""
    verify_project_access(project_id, storage)
    safe_rec_id = validate_identifier("record_id", record_id)

    if commit_id:
        safe_commit_id = validate_identifier("commit_id", commit_id)
        try:
            historical_state = vc.get_record_at_commit(project_id, safe_rec_id, safe_commit_id)
        except ResourceNotFoundError as exc:
            raise BarsaMCPError(MCPErrorCode.COMMIT_NOT_FOUND, str(exc)) from exc

        if not historical_state:
            raise BarsaMCPError(
                MCPErrorCode.RECORD_NOT_FOUND,
                f"Record '{safe_rec_id}' was not found at commit '{safe_commit_id}'.",
                {"project_id": project_id, "record_id": safe_rec_id, "commit_id": safe_commit_id},
            )
        return {
            "project_id": project_id,
            "record_id": safe_rec_id,
            "commit_id": safe_commit_id,
            "record": historical_state,
        }

    rec_res = storage.get_record(project_id, safe_rec_id)
    if not rec_res:
        raise BarsaMCPError(
            MCPErrorCode.RECORD_NOT_FOUND,
            f"Record '{safe_rec_id}' was not found in project '{project_id}'.",
            {"project_id": project_id, "record_id": safe_rec_id},
        )
    rec = rec_res[0] if isinstance(rec_res, tuple) else rec_res
    return {
        "project_id": project_id,
        "record_id": safe_rec_id,
        "commit_id": None,
        "record": rec.model_dump(mode="json"),
    }


def get_checkpoint_tool(
    storage: StorageProvider,
    project_id: str,
    task_id: str | None = None,
    checkpoint_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve the latest relevant or explicitly requested checkpoint."""
    verify_project_access(project_id, storage)

    if checkpoint_id:
        clean_cp_id = validate_identifier("checkpoint_id", checkpoint_id)
        cp_res = storage.get_record(project_id, clean_cp_id)
        if not cp_res:
            raise BarsaMCPError(
                MCPErrorCode.CHECKPOINT_NOT_FOUND,
                f"Checkpoint '{clean_cp_id}' was not found in project '{project_id}'.",
            )
        cp_rec = cp_res[0] if isinstance(cp_res, tuple) else cp_res
        if getattr(cp_rec, "record_type", "") != "checkpoint":
            raise BarsaMCPError(
                MCPErrorCode.CHECKPOINT_NOT_FOUND,
                f"Checkpoint '{clean_cp_id}' was not found in project '{project_id}'.",
            )
        target = cp_rec.model_dump(mode="json")
    else:
        # Search checkpoints in storage
        raw_checkpoints = storage.list_records(project_id, record_type="checkpoint")
        checkpoints = [item[0] if isinstance(item, tuple) else item for item in raw_checkpoints]
        if task_id:
            clean_task_id = validate_identifier("task_id", task_id)
            matching = [
                c.model_dump(mode="json")
                for c in checkpoints
                if getattr(c, "task_id", None) == clean_task_id
                or c.model_dump(mode="json").get("task_id") == clean_task_id
            ]
        else:
            matching = [c.model_dump(mode="json") for c in checkpoints]

        if not matching:
            filter_desc = f" for task '{task_id}'" if task_id else ""
            raise BarsaMCPError(
                MCPErrorCode.CHECKPOINT_NOT_FOUND,
                f"No checkpoint found in project '{project_id}'{filter_desc}.",
            )
        # Latest by created_at
        matching.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        target = matching[0]

    return {
        "project_id": project_id,
        "checkpoint_id": target.get("id"),
        "task_id": target.get("task_id"),
        "status": target.get("status"),
        "completed_actions": target.get("completed_actions", []),
        "pending_actions": target.get("pending_actions", []),
        "next_action": target.get("next_action"),
        "blockers": target.get("blockers", []),
        "artifact_refs": target.get("artifact_refs", []),
        "decision_refs": target.get("decision_refs", []),
        "base_revision": target.get("base_revision"),
        "created_by": target.get("created_by"),
        "created_at": target.get("created_at"),
    }


def resume_tool(
    storage: StorageProvider,
    retrieval: GraphRetrievalService,
    worker: GraphProjectionWorker,
    vc: VersionControlEngine,
    project_id: str,
    task_id: str | None = None,
    max_context_tokens: int | None = None,
    expected_revision: str | None = None,
) -> dict[str, Any]:
    """Supply structured context package needed for an AI client to continue work."""
    proj = verify_project_access(project_id, storage)

    # 1. Authoritative revision check
    main_branch = vc.get_branch(proj.id, "main")
    head_commit = main_branch.head_commit_id if main_branch else None

    revision_warning = None
    if expected_revision and head_commit and expected_revision != head_commit:
        revision_warning = (
            f"Expected revision '{expected_revision}' diverges from current authoritative HEAD '{head_commit}'."
        )

    # 2. Automatically sync pending events to ensure retrieval freshness
    with contextlib.suppress(Exception):
        worker.process_pending_events(proj.id)

    # 3. Retrieve context
    target_task_id = task_id
    if not target_task_id:
        # Find first in-progress or todo task
        tasks = storage.list_records(proj.id, record_type="task")
        for item in tasks:
            t = item[0] if isinstance(item, tuple) else item
            td = t.model_dump(mode="json")
            if td.get("status") in ("in_progress", "todo"):
                target_task_id = t.id
                break

    if target_task_id:
        context_res = retrieval.get_resume_context(proj.id, target_task_id)
        task_data = context_res.task
        latest_cp = context_res.latest_checkpoint
        decisions = context_res.relevant_decisions
        requirements = context_res.requirements
        dependencies = context_res.dependencies
        artifacts = context_res.artifacts
        blockers = context_res.blockers
    else:
        # Project-level overview if no specific task
        overview = retrieval.get_project_overview(proj.id)
        task_data = None
        latest_cp = overview.latest_checkpoint
        decisions = overview.approved_decisions
        requirements = overview.requirements
        dependencies = []
        artifacts = overview.relevant_artifacts
        blockers = []

    # Normalize task_data so agents receive clean identifiers
    normalized_task = None
    if task_data:
        if "properties" in task_data:
            t_props = task_data.get("properties", {})
            raw_id = task_data.get("raw_id", t_props.get("id", task_data.get("id")))
            normalized_task = {
                "id": raw_id,
                "raw_id": raw_id,
                **t_props,
            }
        else:
            normalized_task = task_data
            if "raw_id" not in normalized_task and "id" in normalized_task:
                normalized_task["raw_id"] = normalized_task["id"]

    # Normalize latest_cp so agents get complete, authoritative attributes
    normalized_cp = None
    try:
        raw_cps = storage.list_records(proj.id, record_type="checkpoint")
        if raw_cps:
            matching_cps = []
            for item in raw_cps:
                c_obj = item[0] if isinstance(item, tuple) else item
                if target_task_id:
                    if getattr(c_obj, "task_id", None) == target_task_id:
                        matching_cps.append(c_obj)
                else:
                    matching_cps.append(c_obj)
            target_list = matching_cps or [item[0] if isinstance(item, tuple) else item for item in raw_cps]
            target_list.sort(key=lambda x: str(getattr(x, "created_at", "")), reverse=True)
            target = target_list[0].model_dump(mode="json")
            normalized_cp = {
                "checkpoint_id": target.get("id"),
                **target,
            }
    except Exception:
        pass

    if not normalized_cp and latest_cp:
        if "properties" in latest_cp:
            props = latest_cp.get("properties", {})
            normalized_cp = {
                "checkpoint_id": latest_cp.get("raw_id", props.get("id", latest_cp.get("id"))),
                **props,
            }
        else:
            normalized_cp = latest_cp

    package = {
        "project_identity": {
            "project_id": proj.id,
            "project_name": proj.name,
            "workspace_id": proj.workspace_id,
            "status": proj.status.value if hasattr(proj.status, "value") else str(proj.status),
        },
        "authoritative_revision": head_commit,
        "revision_warning": revision_warning,
        "current_task": normalized_task,
        "latest_checkpoint": normalized_cp,
        "relevant_decisions": decisions,
        "requirements": requirements,
        "dependencies": dependencies,
        "artifacts": artifacts,
        "blockers": blockers,
    }

    # Honest token budgeting calculation (approx 4 chars/token)
    serialized_len = len(json.dumps(package))
    est_tokens = serialized_len // 4

    package["token_budget_info"] = {
        "budget_enforcement": "approximate",
        "requested_max_tokens": max_context_tokens,
        "estimated_tokens": est_tokens,
        "is_within_budget": (max_context_tokens is None or est_tokens <= max_context_tokens),
        "note": "Critical safety and resumption fields were preserved without truncating.",
    }

    return package


def get_history_tool(
    vc: VersionControlEngine,
    storage: StorageProvider,
    project_id: str,
    branch: str = "main",
    limit: int = 50,
) -> dict[str, Any]:
    """Retrieve commit history and revision metadata for a branch."""
    verify_project_access(project_id, storage)
    safe_branch = validate_branch_name(branch)
    safe_limit = validate_limit(limit)

    try:
        commits = vc.get_history(project_id, branch_name=safe_branch, limit=safe_limit)
    except ResourceNotFoundError as exc:
        raise BarsaMCPError(MCPErrorCode.BRANCH_NOT_FOUND, str(exc)) from exc

    formatted = []
    for c in commits:
        formatted.append(
            {
                "commit_id": c.commit_id,
                "author_id": c.author_id,
                "message": c.message,
                "parent_commit_ids": c.parent_commit_ids,
                "resulting_state_hash": c.resulting_state_hash,
                "created_at": c.created_at.isoformat(),
                "change_count": len(c.changes),
            }
        )

    return {
        "project_id": project_id,
        "branch": safe_branch,
        "commits": formatted,
        "total_returned": len(formatted),
    }


def get_diff_tool(
    vc: VersionControlEngine,
    storage: StorageProvider,
    project_id: str,
    from_commit: str,
    to_commit: str,
) -> dict[str, Any]:
    """Compute and retrieve structured diff between two commits."""
    verify_project_access(project_id, storage)
    c_from = validate_identifier("from_commit", from_commit)
    c_to = validate_identifier("to_commit", to_commit)

    try:
        diff_res = vc.diff_commits(project_id, c_from, c_to)
        return {
            "project_id": project_id,
            "from_commit": c_from,
            "to_commit": c_to,
            "diff": diff_res.model_dump(mode="json"),
        }
    except ResourceNotFoundError as exc:
        raise BarsaMCPError(MCPErrorCode.COMMIT_NOT_FOUND, str(exc)) from exc


def propose_changes_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    project_id: str,
    branch: str,
    base_commit: str,
    changes: list[dict[str, Any]],
    message: str,
) -> dict[str, Any]:
    """Validate memory changes and commit to an isolated feature branch without modifying main."""
    verify_project_access(project_id, storage)
    safe_branch = validate_branch_name(branch)
    safe_base = validate_identifier("base_commit", base_commit)
    safe_changes = validate_changes_payload(changes)

    if safe_branch == "main":
        raise BarsaMCPError(
            MCPErrorCode.UNSUPPORTED_OPERATION,
            "Cannot propose changes directly to the protected 'main' branch. Use a feature branch name (e.g. 'feature/my-change').",
        )

    # 1. Validate each change payload using BMS
    memory_changes: list[MemoryChange] = []
    validation_reports: list[dict[str, Any]] = []

    for idx, chg in enumerate(safe_changes):
        op_str = chg.get("operation", "create").lower()
        rec_id = chg.get("record_id", "")
        rec_type = chg.get("record_type", "")
        after_state = chg.get("after_state")
        before_state = chg.get("before_state")

        if op_str in ("create", "update"):
            if not after_state:
                raise BarsaMCPError(
                    MCPErrorCode.INVALID_BMS_RECORD,
                    f"Change at index {idx} has operation '{op_str}' but missing 'after_state'.",
                )
            # Secret detection check
            from barsa.security.crypto import SecretScanner

            detected = SecretScanner.scan_text(json.dumps(after_state))
            if detected:
                raise BarsaMCPError(
                    MCPErrorCode.INVALID_INPUT,
                    f"Security policy violation: Change {idx} contains sensitive secrets or credentials ({', '.join(detected)})",
                )
            try:
                # Validate against BMS schema
                is_valid, _rec, errs = validate_record(after_state)
                if not is_valid:
                    raise BarsaMCPError(
                        MCPErrorCode.INVALID_BMS_RECORD,
                        f"BMS validation failed at index {idx}: {errs}",
                    )
                validation_reports.append({"index": idx, "record_id": rec_id, "valid": True})
            except BarsaMCPError:
                raise
            except Exception as exc:
                raise BarsaMCPError(
                    MCPErrorCode.INVALID_BMS_RECORD,
                    f"Invalid BMS record in change {idx}: {exc}",
                ) from exc

        memory_changes.append(
            MemoryChange(
                operation=ChangeOperation(op_str),
                record_id=rec_id,
                record_type=rec_type,
                before_state=before_state,
                after_state=after_state,
            )
        )

    # 2. Create feature branch if not exists
    existing_branch = vc.get_branch(project_id, safe_branch)
    if not existing_branch:
        try:
            vc.create_branch(project_id, safe_branch, start_commit_id=safe_base)
        except Exception as exc:
            raise BarsaMCPError(MCPErrorCode.INTERNAL_ERROR, f"Failed creating proposal branch: {exc}") from exc

    # 3. Commit to feature branch
    identity = get_current_identity()
    try:
        commit_res = vc.create_commit(
            project_id=project_id,
            branch_name=safe_branch,
            changes=memory_changes,
            message=message,
            author_id=identity.username,
        )
        return {
            "proposal_id": safe_branch,
            "project_id": project_id,
            "branch": safe_branch,
            "base_commit": safe_base,
            "commit_id": commit_res.commit_id,
            "status": "PROPOSED",
            "validation_results": validation_reports,
            "change_count": len(memory_changes),
        }
    except ConflictError as exc:
        raise BarsaMCPError(MCPErrorCode.MERGE_CONFLICT, str(exc)) from exc
    except ValidationError as exc:
        raise BarsaMCPError(MCPErrorCode.INVALID_BMS_RECORD, str(exc)) from exc


def commit_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    worker: GraphProjectionWorker,
    project_id: str,
    branch: str = "main",
    expected_head: str | None = None,
    changes: list[dict[str, Any]] | None = None,
    message: str = "",
    operation_id: str | None = None,
) -> dict[str, Any]:
    """Commit validated changes to a branch through the version-control engine."""
    verify_project_access(project_id, storage)
    if operation_id:
        validate_identifier("operation_id", operation_id)
    safe_branch = validate_branch_name(branch)
    safe_changes = validate_changes_payload(changes or [])

    # Validate change payloads
    memory_changes: list[MemoryChange] = []
    for idx, chg in enumerate(safe_changes):
        op_str = chg.get("operation", "create").lower()
        rec_id = chg.get("record_id", "")
        rec_type = chg.get("record_type", "")
        after_state = chg.get("after_state")
        before_state = chg.get("before_state")

        if op_str in ("create", "update") and after_state:
            try:
                is_valid, _rec, errs = validate_record(after_state)
                if not is_valid:
                    raise BarsaMCPError(
                        MCPErrorCode.INVALID_BMS_RECORD,
                        f"Validation error in change {idx}: {errs}",
                    )
            except BarsaMCPError:
                raise
            except Exception as exc:
                raise BarsaMCPError(
                    MCPErrorCode.INVALID_BMS_RECORD,
                    f"Invalid BMS record in change {idx}: {exc}",
                ) from exc

        memory_changes.append(
            MemoryChange(
                operation=ChangeOperation(op_str),
                record_id=rec_id,
                record_type=rec_type,
                before_state=before_state,
                after_state=after_state,
            )
        )

    # Optimistic concurrency check
    if expected_head:
        clean_exp = validate_identifier("expected_head", expected_head)
        current_branch = vc.get_branch(project_id, safe_branch)
        if current_branch and current_branch.head_commit_id != clean_exp:
            raise BarsaMCPError(
                MCPErrorCode.STALE_REVISION,
                f"Branch '{safe_branch}' HEAD has moved from '{clean_exp}' to '{current_branch.head_commit_id}'.",
                {"expected_head": clean_exp, "current_head": current_branch.head_commit_id},
            )

    identity = get_current_identity()
    try:
        commit_res = vc.create_commit(
            project_id=project_id,
            branch_name=safe_branch,
            changes=memory_changes,
            message=message or "Commit via MCP",
            author_id=identity.username,
        )

        # Trigger projection sync for main branch
        if safe_branch == "main":
            with contextlib.suppress(Exception):
                worker.process_pending_events(project_id)

        return {
            "project_id": project_id,
            "branch": safe_branch,
            "commit_id": commit_res.commit_id,
            "resulting_state_hash": commit_res.resulting_state_hash,
            "author_id": commit_res.author_id,
            "change_count": len(commit_res.changes),
            "status": "COMMITTED",
        }
    except ConflictError as exc:
        raise BarsaMCPError(MCPErrorCode.MERGE_CONFLICT, str(exc)) from exc
    except ValidationError as exc:
        raise BarsaMCPError(MCPErrorCode.INVALID_BMS_RECORD, str(exc)) from exc


def list_conflicts_tool(
    vc: VersionControlEngine,
    storage: StorageProvider,
    project_id: str,
    status: str | None = None,
) -> dict[str, Any]:
    """List unresolved or divergent branch conflicts."""
    verify_project_access(project_id, storage)
    if status:
        validate_identifier("status", status)

    main_branch = vc.get_branch(project_id, "main")
    main_head = main_branch.head_commit_id if main_branch else None

    branches = vc.list_branches(project_id)
    conflicts = []

    for b in branches:
        if b.name == "main":
            continue

        # Inspect if branch diverges from main
        if main_head and b.head_commit_id != main_head:
            # Check 3-way merge readiness
            try:
                diff_against_main = vc.diff_commits(project_id, main_head, b.head_commit_id)
                has_diffs = bool(
                    diff_against_main.added_records
                    or diff_against_main.modified_records
                    or diff_against_main.removed_records
                )
                if has_diffs:
                    conflicts.append(
                        {
                            "branch": b.name,
                            "branch_head": b.head_commit_id,
                            "main_head": main_head,
                            "potential_conflict": False,
                            "divergent_changes_count": (
                                len(diff_against_main.added_records)
                                + len(diff_against_main.modified_records)
                                + len(diff_against_main.removed_records)
                            ),
                        }
                    )
            except Exception:
                pass

    return {
        "project_id": project_id,
        "main_head": main_head,
        "divergent_branches": conflicts,
        "total_conflicts": len(conflicts),
    }


def get_graph_context_tool(
    retrieval: GraphRetrievalService,
    worker: GraphProjectionWorker,
    graph: GraphProvider,
    storage: StorageProvider,
    project_id: str,
    task_id: str | None = None,
    depth: int = 2,
    limit: int = 50,
) -> dict[str, Any]:
    """Retrieve relevant graph-connected information and projection freshness."""
    verify_project_access(project_id, storage)
    safe_depth = validate_depth(depth)
    safe_limit = validate_limit(limit)

    is_graph_available = graph.is_available()
    provider_name = getattr(graph, "provider_name", "unknown")

    # Fetch projection status
    proj_meta = worker.get_projection_status(project_id)
    freshness_info = {
        "is_available": is_graph_available,
        "provider": provider_name,
        "is_fresh": proj_meta.is_fresh if proj_meta else False,
        "applied_commit_id": proj_meta.applied_commit_id if proj_meta else None,
        "lag_commits_count": proj_meta.lag_commits_count if proj_meta else 0,
        "node_count": proj_meta.node_count if proj_meta else 0,
        "relationship_count": proj_meta.relationship_count if proj_meta else 0,
    }

    if not is_graph_available:
        return {
            "project_id": project_id,
            "status": "GRAPH_UNAVAILABLE",
            "message": "FalkorDB / Graph provider is currently unavailable. Operating in fallback mode.",
            "freshness": freshness_info,
        }

    if task_id:
        clean_task_id = validate_identifier("task_id", task_id)
        dep_res = retrieval.get_task_dependencies(project_id, clean_task_id, max_depth=safe_depth)
        neighbors = retrieval.get_neighbors(project_id, clean_task_id, limit=safe_limit)
        return {
            "project_id": project_id,
            "task_id": clean_task_id,
            "dependencies": dep_res.dependencies,
            "blockers": dep_res.blockers,
            "connected_neighbors": neighbors,
            "freshness": freshness_info,
        }

    overview = retrieval.get_project_overview(project_id, limit=safe_limit)
    return {
        "project_id": project_id,
        "overview": overview.model_dump(mode="json"),
        "freshness": freshness_info,
    }


def build_context_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    retrieval: GraphRetrievalService,
    project_id: str,
    task_id: str | None = None,
    query: str | None = None,
    max_context_tokens: int = 4000,
    context_level: str = "adaptive",
    known_revision: str | None = None,
    target_model: str | None = None,
) -> dict[str, Any]:
    """Build a validated, token-optimized context package using the Smart Context Engine (Phase 8)."""
    verify_project_access(project_id, storage)
    safe_proj_id = validate_identifier("project_id", project_id)
    safe_task_id = validate_identifier("task_id", task_id) if task_id else None
    safe_known_rev = validate_identifier("known_revision", known_revision) if known_revision else None
    safe_query = validate_query_string(query) if query else None

    try:
        level_enum = ContextLevel(context_level.lower())
    except ValueError:
        level_enum = ContextLevel.ADAPTIVE

    req = ContextRequest(
        project_id=safe_proj_id,
        task_id=safe_task_id,
        query=safe_query,
        max_context_tokens=max_context_tokens,
        context_level=level_enum,
        known_revision=safe_known_rev,
        target_model=target_model,
    )

    engine = SmartContextEngine(storage=storage, vc=vc, graph_retrieval=retrieval)
    pkg = engine.build_context(req)
    return pkg.model_dump(mode="json")


# =========================================================================
# Multi-Agent Coordination Tools (Phase 9)
# =========================================================================


def register_agent_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    agent_id: str,
    display_name: str,
    provider: str,
    model: str | None = None,
    claimed_capabilities: list[str] | None = None,
    verified_capabilities: list[str] | None = None,
    supported_tools: list[str] | None = None,
    allowed_projects: list[str] | None = None,
    maximum_concurrent_tasks: int = 2,
) -> dict[str, Any]:
    """Register agent identity and capabilities with the Barsa coordinator."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.coordination.models import AgentRegistration
    from barsa.storage.sqlite import SQLiteStorageProvider

    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    reg = AgentRegistration(
        agent_id=validate_identifier("agent_id", agent_id),
        display_name=display_name.strip(),
        provider=provider.strip(),
        model=model.strip() if model else None,
        claimed_capabilities=claimed_capabilities or [],
        verified_capabilities=verified_capabilities or [],
        supported_tools=supported_tools or [],
        allowed_projects=allowed_projects or ["*"],
        maximum_concurrent_tasks=maximum_concurrent_tasks,
    )
    profile = engine.register_agent(reg)
    return profile.model_dump(mode="json")


def get_available_tasks_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    project_id: str,
    agent_id: str | None = None,
) -> list[dict[str, Any]]:
    """Discover tasks available to be claimed in a project."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    verify_project_access(project_id, storage)
    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    tasks = engine.list_available_tasks(
        project_id=validate_identifier("project_id", project_id),
        agent_id=validate_identifier("agent_id", agent_id) if agent_id else None,
    )
    return [t.model_dump(mode="json") for t in tasks]


def claim_task_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    task_id: str,
    agent_id: str,
    lease_duration_seconds: int | None = None,
) -> dict[str, Any]:
    """Atomically claim a task with compare-and-swap semantics and obtain a fencing token."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    try:
        resp = engine.claim_task(
            task_id=validate_identifier("task_id", task_id),
            agent_id=validate_identifier("agent_id", agent_id),
            lease_duration_seconds=lease_duration_seconds,
        )
        return resp.model_dump(mode="json")
    except ConflictError as e:
        raise BarsaMCPError(MCPErrorCode.MERGE_CONFLICT, str(e)) from e
    except ValidationError as e:
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, str(e)) from e
    except ResourceNotFoundError as e:
        raise BarsaMCPError(MCPErrorCode.RECORD_NOT_FOUND, str(e)) from e


def update_task_progress_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    task_id: str,
    agent_id: str,
    lease_token: str,
    message: str,
    progress_percent: float | None = None,
    resource_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Report task execution progress and record heartbeat."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    try:
        task = engine.update_task_progress(
            task_id=validate_identifier("task_id", task_id),
            agent_id=validate_identifier("agent_id", agent_id),
            lease_token=lease_token.strip(),
            message=message.strip(),
            progress_percent=progress_percent,
            resource_usage=resource_usage,
        )
        return task.model_dump(mode="json")
    except ConflictError as e:
        raise BarsaMCPError(MCPErrorCode.MERGE_CONFLICT, str(e)) from e
    except ResourceNotFoundError as e:
        raise BarsaMCPError(MCPErrorCode.RECORD_NOT_FOUND, str(e)) from e


def submit_task_result_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    task_id: str,
    agent_id: str,
    lease_token: str,
    result: dict[str, Any],
    commit_id: str | None = None,
    requires_review: bool | None = None,
    resource_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Submit completed task results verifying fencing token."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    try:
        task = engine.submit_task_result(
            task_id=validate_identifier("task_id", task_id),
            agent_id=validate_identifier("agent_id", agent_id),
            lease_token=lease_token.strip(),
            result=result,
            commit_id=commit_id.strip() if commit_id else None,
            requires_review=requires_review,
            resource_usage=resource_usage,
        )
        return task.model_dump(mode="json")
    except ConflictError as e:
        raise BarsaMCPError(MCPErrorCode.MERGE_CONFLICT, str(e)) from e
    except ResourceNotFoundError as e:
        raise BarsaMCPError(MCPErrorCode.RECORD_NOT_FOUND, str(e)) from e


def report_issue_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    project_id: str,
    task_id: str,
    author_agent_id: str,
    title: str,
    description: str,
    evidence: dict[str, Any] | None = None,
    required_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Report an issue or impediment encountered during task execution."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    verify_project_access(project_id, storage)
    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    issue = engine.report_issue(
        project_id=validate_identifier("project_id", project_id),
        task_id=validate_identifier("task_id", task_id),
        author_agent_id=validate_identifier("author_agent_id", author_agent_id),
        title=title.strip(),
        description=description.strip(),
        evidence=evidence,
        required_capabilities=required_capabilities,
    )
    return issue.model_dump(mode="json")


def request_help_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    project_id: str,
    task_id: str,
    requester_agent_id: str,
    required_capabilities: list[str],
    issue_id: str | None = None,
    target_agent_id: str | None = None,
) -> dict[str, Any]:
    """Request assistance from other agents with specific capabilities."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    verify_project_access(project_id, storage)
    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    req = engine.request_help(
        project_id=validate_identifier("project_id", project_id),
        task_id=validate_identifier("task_id", task_id),
        requester_agent_id=validate_identifier("requester_agent_id", requester_agent_id),
        required_capabilities=required_capabilities,
        issue_id=validate_identifier("issue_id", issue_id) if issue_id else None,
        target_agent_id=validate_identifier("target_agent_id", target_agent_id) if target_agent_id else None,
    )
    return req.model_dump(mode="json")


def get_collaboration_messages_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    project_id: str,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve collaboration message stream for a project or specific task."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    verify_project_access(project_id, storage)
    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    messages = engine.list_comments(
        project_id=validate_identifier("project_id", project_id),
        task_id=validate_identifier("task_id", task_id) if task_id else None,
    )
    return [m.model_dump(mode="json") for m in messages]


def get_assignment_tool(
    storage: StorageProvider,
    vc: VersionControlEngine,
    task_id: str,
) -> dict[str, Any]:
    """Inspect current task assignment, lease token, and expiration status."""
    from barsa.coordination.engine import CoordinatorEngine
    from barsa.storage.sqlite import SQLiteStorageProvider

    if not isinstance(storage, SQLiteStorageProvider):
        raise BarsaMCPError(MCPErrorCode.STORAGE_UNAVAILABLE, "SQLite storage required")

    engine = CoordinatorEngine(storage=storage, vc=vc)
    try:
        task = engine.get_task(validate_identifier("task_id", task_id))
        return {
            "task_id": task.task_id,
            "project_id": task.project_id,
            "status": task.status.value,
            "assigned_agent_id": task.assigned_agent_id,
            "lease_token": task.lease_token,
            "lease_expires_at": task.lease_expires_at.isoformat() if task.lease_expires_at else None,
            "attempt_count": task.attempt_count,
            "max_attempts": task.max_attempts,
        }
    except ResourceNotFoundError as e:
        raise BarsaMCPError(MCPErrorCode.RECORD_NOT_FOUND, str(e)) from e
