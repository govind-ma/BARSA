"""Comprehensive tests for BMS v0.1 models, records, validation, and serialization."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from barsa.bms.base import BMS_VERSION
from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.records import (
    AgentRecord,
    ArtifactReference,
    ArtifactType,
    CheckpointStatus,
    CommitChange,
    CommitOperation,
    DecisionRecord,
    DecisionStatus,
    KnowledgeRecord,
    KnowledgeType,
    MemoryCommit,
    Project,
    ProjectStatus,
    RelationshipRecord,
    RelationshipType,
    ResumeCheckpoint,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    VerificationStatus,
    Workspace,
)
from barsa.bms.serialization import (
    deserialize_record,
    export_package,
    import_package,
    serialize_record,
    validate_record,
)
from barsa.bms.validation import BMSValidationError, validate_bms_package


def test_every_valid_record_type_instantiation() -> None:
    """Verify that every BMS v0.1 record type can be instantiated cleanly."""
    ws = Workspace(
        id="ws-1",
        name="Workspace 1",
        owner_id="user-1",
        description="Desc",
        created_at=datetime.now(UTC),
    )
    assert ws.record_type == "workspace"
    assert ws.schema_version == BMS_VERSION

    prj = Project(
        id="prj-1",
        workspace_id=ws.id,
        name="Project 1",
        status=ProjectStatus.ACTIVE,
        goals=["Goal 1"],
    )
    assert prj.record_type == "project"

    kn = KnowledgeRecord(
        id="kn-1",
        project_id=prj.id,
        content="Fact 1",
        knowledge_type=KnowledgeType.FACT,
        verification_status=VerificationStatus.VERIFIED,
        created_by="agent-1",
    )
    assert kn.record_type == "knowledge"

    dec = DecisionRecord(
        id="dec-1",
        project_id=prj.id,
        title="Dec Title",
        decision="Adopt X",
        rationale="Because Y",
        status=DecisionStatus.APPROVED,
        created_by="agent-1",
        alternatives=["Alt A"],
        evidence_refs=[kn.id],
    )
    assert dec.record_type == "decision"

    tsk = TaskRecord(
        id="tsk-1",
        project_id=prj.id,
        title="Task 1",
        description="Do something",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        dependencies=[],
        assigned_agent_id="agent-1",
    )
    assert tsk.record_type == "task"

    ag = AgentRecord(
        id="agent-1",
        name="Claude Agent",
        provider="anthropic",
        capabilities=["coding"],
        model="claude-3-7-sonnet",
    )
    assert ag.record_type == "agent"

    art = ArtifactReference(
        id="art-1",
        project_id=prj.id,
        artifact_type=ArtifactType.SOURCE_CODE,
        uri="src/main.py",
        size_bytes=1024,
    )
    assert art.record_type == "artifact"

    rel = RelationshipRecord(
        id="rel-1",
        project_id=prj.id,
        source_id=tsk.id,
        target_id=dec.id,
        relationship_type=RelationshipType.IMPLEMENTS,
    )
    assert rel.record_type == "relationship"

    chk = ResumeCheckpoint(
        id="chk-1",
        project_id=prj.id,
        task_id=tsk.id,
        status=CheckpointStatus.ACTIVE,
        completed_actions=["Created files"],
        pending_actions=["Run tests"],
        next_action="Run pytest",
        blockers=[],
        decision_refs=[dec.id],
        artifact_refs=[art.id],
        base_revision="git-commit-123",
        created_by=ag.id,
        environment_description="Python 3.12",
        context_refs=[kn.id],
    )
    assert chk.record_type == "checkpoint"

    cmt = MemoryCommit(
        id="cmt-1",
        project_id=prj.id,
        parent_commit_ids=[],
        author_id=ag.id,
        message="Initial state",
        changes=[
            CommitChange(
                id="chg-1",
                operation=CommitOperation.CREATE,
                record_id=kn.id,
                record_type="knowledge",
            )
        ],
    )
    assert cmt.record_type == "commit"


def test_missing_required_fields() -> None:
    """Verify that omitting required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        # Missing owner_id
        Workspace(name="Incomplete")  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        # Missing decision and rationale
        DecisionRecord(  # type: ignore[call-arg]
            project_id="prj-1",
            title="Title",
            created_by="agent-1",
        )


def test_invalid_enums() -> None:
    """Verify that invalid enum strings are rejected."""
    with pytest.raises(ValidationError):
        TaskRecord(  # type: ignore[arg-type]
            project_id="prj-1",
            title="Task",
            status="not_a_valid_status",
        )


def test_naive_timestamps_rejected() -> None:
    """Verify that naive datetimes (lacking timezone information) are strictly rejected."""
    naive_dt = datetime(2026, 10, 13, 12, 0, 0)  # noqa: DTZ001
    with pytest.raises(
        ValueError, match="naive datetimes are prohibited" if False else "timezone-aware"
    ):
        Workspace(
            name="Test WS",
            owner_id="user-1",
            created_at=naive_dt,
        )


def test_unsupported_schema_version() -> None:
    """Verify that unsupported schema versions are rejected."""
    with pytest.raises(ValidationError):
        Workspace(
            name="Test WS",
            owner_id="user-1",
            schema_version="999.0",
        )


def test_task_self_dependency_rejected() -> None:
    """Verify tasks cannot list themselves in dependencies."""
    with pytest.raises(ValidationError, match="cannot list itself as a dependency"):
        TaskRecord(
            id="task-x",
            project_id="prj-1",
            title="Self-dependent task",
            dependencies=["task-x"],
        )


def test_relationship_self_referencing_rejected() -> None:
    """Verify relationship source and target cannot be identical."""
    with pytest.raises(ValidationError, match="Self-referencing relationship not allowed"):
        RelationshipRecord(
            id="rel-self",
            project_id="prj-1",
            source_id="item-1",
            target_id="item-1",
            relationship_type=RelationshipType.RELATES_TO
            if hasattr(RelationshipType, "RELATES_TO")
            else RelationshipType.RELATED_TO,
        )


def test_json_serialization_round_trip() -> None:
    """Verify round-trip JSON serialization and deserialization."""
    agent = AgentRecord(
        id="ag-tester",
        name="Tester Agent",
        provider="anthropic",
        capabilities=["testing"],
        metadata={"role": "qa"},
    )
    json_str = serialize_record(agent)
    assert '"record_type": "agent"' in json_str

    deserialized = deserialize_record(json_str)
    assert isinstance(deserialized, AgentRecord)
    assert deserialized.id == agent.id
    assert deserialized.metadata == {"role": "qa"}


def test_malformed_json_handling() -> None:
    """Verify malformed JSON raises BMSValidationError with clean diagnostics."""
    with pytest.raises(BMSValidationError, match="Malformed JSON"):
        deserialize_record("{invalid-json-content")


def test_validate_record_utility() -> None:
    """Verify validate_record returns clean tuples."""
    is_valid, record, errors = validate_record(
        {
            "record_type": "workspace",
            "id": "ws-ok",
            "name": "Valid WS",
            "owner_id": "usr-1",
            "created_at": datetime.now(UTC).isoformat(),
            "schema_version": "0.1",
        }
    )
    assert is_valid is True
    assert record is not None
    assert errors == []

    # Invalid record
    is_valid, record, errors = validate_record(
        {
            "record_type": "workspace",
            "id": "ws-bad",
            # missing name and owner_id
            "schema_version": "0.1",
        }
    )
    assert is_valid is False
    assert record is None
    assert len(errors) > 0


def test_example_package_spring_boot_validation() -> None:
    """Verify example Java Spring Boot package validates and imports cleanly."""
    example_path = Path("examples") / "bms" / "spring_boot_project.json"
    assert example_path.exists()

    pkg = import_package(example_path)
    assert isinstance(pkg, BarsaMemoryPackage)
    assert pkg.workspace.id == "ws-spring-enterprise"
    assert pkg.project.id == "prj-order-service"
    assert len(pkg.records.tasks) == 2
    assert len(pkg.records.agents) == 2
    assert pkg.latest_checkpoint_id == "chk-resume-idempotency"


def test_example_package_multi_agent_research_validation() -> None:
    """Verify example Multi-Agent Research package validates and imports cleanly."""
    example_path = Path("examples") / "bms" / "multi_agent_research.json"
    assert example_path.exists()

    pkg = import_package(example_path)
    assert isinstance(pkg, BarsaMemoryPackage)
    assert pkg.project.id == "prj-genomics-variant-analysis"
    assert len(pkg.records.knowledge) == 2
    assert len(pkg.records.decisions) == 1
    assert len(pkg.relationships) == 2


def test_package_export_and_import_roundtrip(tmp_path: Path) -> None:
    """Verify package can be exported to file and imported back without data loss."""
    source_example = Path("examples") / "bms" / "spring_boot_project.json"
    pkg = import_package(source_example)

    target_path = tmp_path / "exported_spring_boot.json"
    exported_file = export_package(pkg, target_path)
    assert exported_file.is_file()

    reimported = import_package(exported_file)
    assert reimported.workspace.id == pkg.workspace.id
    assert reimported.project.id == pkg.project.id
    assert len(reimported.records.tasks) == len(pkg.records.tasks)


def test_package_referential_integrity_checks() -> None:
    """Verify package validation detects cross-project references and broken references."""
    source_example = Path("examples") / "bms" / "spring_boot_project.json"
    pkg = import_package(source_example)

    # 1. Broken task dependency
    pkg.records.tasks[1].dependencies.append("non-existent-task-id")
    errors = validate_bms_package(pkg)
    assert any("missing dependency task 'non-existent-task-id'" in e for e in errors)

    # 2. Duplicate record IDs
    pkg.records.tasks[1].dependencies.remove("non-existent-task-id")
    # Duplicate agent ID
    pkg.records.knowledge[0].id = pkg.records.tasks[0].id
    errors = validate_bms_package(pkg)
    assert any("Duplicate record IDs found" in e for e in errors)

    # 3. Cross-project mismatch
    pkg.records.knowledge[0].id = "kn-unique"
    pkg.records.tasks[0].project_id = "alien-project-id"
    errors = validate_bms_package(pkg)
    assert any("alien-project-id" in e for e in errors)
