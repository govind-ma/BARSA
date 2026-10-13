"""Comprehensive validation logic for BMS v0.1 records and packages."""

from typing import Any

from pydantic import ValidationError

from barsa.bms.base import BMS_VERSION
from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.records import (
    RECORD_TYPE_MAP,
    AnyBMSRecord,
    CommitChange,
)


class BMSValidationError(ValueError):
    """Detailed domain error raised when BMS validation fails."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or [message]


def validate_bms_record_data(data: dict[str, Any]) -> AnyBMSRecord:
    """Validate a raw dictionary against BMS record models."""
    if not isinstance(data, dict):
        msg = f"Expected record data to be a dictionary, got {type(data).__name__}"
        raise BMSValidationError(msg)

    schema_version = data.get("schema_version", BMS_VERSION)
    if schema_version != BMS_VERSION:
        msg = f"Unsupported schema version '{schema_version}'. Supported version is '{BMS_VERSION}'"
        raise BMSValidationError(msg)

    record_type = data.get("record_type")
    if not record_type or not isinstance(record_type, str):
        msg = "Missing or invalid 'record_type' discriminator in record data"
        raise BMSValidationError(msg)

    record_cls = RECORD_TYPE_MAP.get(record_type)
    if not record_cls:
        valid_types = list(RECORD_TYPE_MAP.keys())
        msg = f"Unknown BMS record type '{record_type}'. Supported types: {valid_types}"
        raise BMSValidationError(msg)

    try:
        return record_cls.model_validate(data)
    except ValidationError as err:
        error_msgs = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in err.errors()]
        msg = f"Validation failed for record type '{record_type}': {'; '.join(error_msgs)}"
        raise BMSValidationError(msg, errors=error_msgs) from err


def validate_bms_package(package: BarsaMemoryPackage) -> list[str]:
    """Perform full referential integrity and consistency validation on a BarsaMemoryPackage.

    Returns a list of validation error strings. If empty, the package is valid.
    """
    errors: list[str] = []

    # 1. Project & Workspace Consistency
    if package.project.workspace_id != package.workspace.id:
        errors.append(
            f"Project workspace_id '{package.project.workspace_id}' "
            f"does not match Workspace id '{package.workspace.id}'"
        )

    project_id = package.project.id

    # 2. Collect all valid record IDs & check for duplicates across the entire package
    all_record_ids: set[str] = {package.workspace.id, package.project.id}
    duplicate_ids: set[str] = set()

    record_lists = [
        ("knowledge", package.records.knowledge),
        ("decision", package.records.decisions),
        ("task", package.records.tasks),
        ("agent", package.records.agents),
        ("artifact", package.records.artifacts),
        ("checkpoint", package.records.checkpoints),
    ]

    for type_name, r_list in record_lists:
        for r in r_list:
            if r.id in all_record_ids:
                duplicate_ids.add(r.id)
            all_record_ids.add(r.id)

            # Check project_id consistency
            if hasattr(r, "project_id") and r.project_id != project_id:
                errors.append(
                    f"{type_name.capitalize()} '{r.id}' has project_id '{r.project_id}' "
                    f"which does not match Package Project id '{project_id}'"
                )

    if duplicate_ids:
        errors.append(f"Duplicate record IDs found in package: {sorted(duplicate_ids)}")

    # 3. Validate Agents References
    agent_ids = {a.id for a in package.records.agents}

    for k in package.records.knowledge:
        if k.created_by not in agent_ids and k.created_by != package.workspace.owner_id:
            # Note: created_by can be an agent or the workspace owner
            pass

    for t in package.records.tasks:
        if t.assigned_agent_id and t.assigned_agent_id not in agent_ids:
            errors.append(f"Task '{t.id}' assigned to unknown agent '{t.assigned_agent_id}'")

    # 4. Validate Task Dependencies
    task_ids = {t.id for t in package.records.tasks}
    for t in package.records.tasks:
        for dep in t.dependencies:
            if dep == t.id:
                errors.append(f"Task '{t.id}' has direct self-dependency.")
            elif dep not in task_ids:
                errors.append(f"Task '{t.id}' has missing dependency task '{dep}'")

    # 5. Validate Decision References
    for d in package.records.decisions:
        for ref in d.evidence_refs:
            if ref not in all_record_ids:
                errors.append(f"Decision '{d.id}' has broken evidence_ref '{ref}'")

    # 6. Validate Checkpoints
    checkpoint_ids = {c.id for c in package.records.checkpoints}
    for c in package.records.checkpoints:
        if c.task_id not in task_ids:
            errors.append(f"ResumeCheckpoint '{c.id}' references unknown task_id '{c.task_id}'")
        for d_ref in c.decision_refs:
            if d_ref not in all_record_ids:
                errors.append(f"ResumeCheckpoint '{c.id}' has broken decision_ref '{d_ref}'")
        for a_ref in c.artifact_refs:
            if a_ref not in all_record_ids:
                errors.append(f"ResumeCheckpoint '{c.id}' has broken artifact_ref '{a_ref}'")
        for ctx_ref in c.context_refs:
            if ctx_ref not in all_record_ids:
                errors.append(f"ResumeCheckpoint '{c.id}' has broken context_ref '{ctx_ref}'")

    # Latest checkpoint reference check
    if package.latest_checkpoint_id and package.latest_checkpoint_id not in checkpoint_ids:
        errors.append(
            f"Package latest_checkpoint_id '{package.latest_checkpoint_id}' does not exist in package checkpoints"
        )

    # 7. Validate Relationships
    rel_ids: set[str] = set()
    for rel in package.relationships:
        if rel.id in rel_ids:
            errors.append(f"Duplicate relationship ID found: '{rel.id}'")
        rel_ids.add(rel.id)

        if rel.project_id != project_id:
            errors.append(
                f"Relationship '{rel.id}' has project_id '{rel.project_id}' "
                f"which does not match Package Project id '{project_id}'"
            )

        if rel.source_id not in all_record_ids:
            errors.append(f"Relationship '{rel.id}' has unknown source_id '{rel.source_id}'")

        if rel.target_id not in all_record_ids:
            errors.append(f"Relationship '{rel.id}' has unknown target_id '{rel.target_id}'")

    # 8. Validate Commits
    commit_ids = {c.id for c in package.commits}
    for commit in package.commits:
        if commit.project_id != project_id:
            errors.append(
                f"Commit '{commit.id}' has project_id '{commit.project_id}' "
                f"which does not match Package Project id '{project_id}'"
            )

        for p_id in commit.parent_commit_ids:
            if p_id not in commit_ids:
                # In distributed git-like commits, parent might be in prior package or present
                pass

        for change in commit.changes:
            if not isinstance(change, CommitChange):
                errors.append(f"Commit '{commit.id}' contains invalid change item structure")

    return errors
