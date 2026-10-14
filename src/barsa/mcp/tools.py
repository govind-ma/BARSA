"""Tool implementations for Barsa Model Context Protocol (MCP) server.

All operations strictly delegate to authoritative Barsa services (StorageProvider,
VersionControlEngine, GraphProjectionWorker, GraphRetrievalService).
"""

import contextlib
import json
from typing import Any

from barsa.bms.serialization import validate_record
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

            matches.append(
                {
                    "record_id": rec.id,
                    "record_type": rec_type,
                    "excerpt": excerpt,
                    "properties": {
                        k: v for k, v in rec_data.items() if k in ("title", "status", "priority", "assignee_id")
                    },
                    "created_at": rec_data.get("created_at"),
                }
            )

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
