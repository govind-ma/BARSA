"""Safe deterministic context compression without LLM dependencies."""

from typing import Any


def compress_task_record(task_data: dict[str, Any]) -> dict[str, Any]:
    """Compress a task record into a token-efficient structured summary."""
    props = task_data.get("properties", task_data)
    t_id = task_data.get("raw_id") or task_data.get("id") or props.get("id")
    return {
        "id": t_id,
        "title": props.get("title", ""),
        "status": props.get("status", "unknown"),
        "priority": props.get("priority", "medium"),
        "assignee_id": props.get("assignee_id"),
        "tags": props.get("tags", []),
    }


def compress_decision_record(decision_data: dict[str, Any]) -> dict[str, Any]:
    """Compress a decision record preserving rationale and status without noisy envelopes."""
    props = decision_data.get("properties", decision_data)
    d_id = decision_data.get("raw_id") or decision_data.get("id") or props.get("id")
    return {
        "id": d_id,
        "title": props.get("title", ""),
        "status": props.get("status", "approved"),
        "summary": props.get("summary", ""),
        "rationale": props.get("rationale", ""),
        "selected_option": props.get("selected_option", ""),
    }


def compress_checkpoint_record(checkpoint_data: dict[str, Any]) -> dict[str, Any]:
    """Compress a checkpoint record ensuring next_action and completed actions remain explicit."""
    props = checkpoint_data.get("properties", checkpoint_data)
    cp_id = checkpoint_data.get("raw_id") or checkpoint_data.get("id") or props.get("id")
    return {
        "id": cp_id,
        "task_id": props.get("task_id"),
        "status": props.get("status", "active"),
        "completed_actions": props.get("completed_actions", []),
        "pending_actions": props.get("pending_actions", []),
        "next_action": props.get("next_action"),
        "blockers": props.get("blockers", []),
    }


def compress_knowledge_record(knowledge_data: dict[str, Any]) -> dict[str, Any]:
    """Compress knowledge records while strictly preserving verification status."""
    props = knowledge_data.get("properties", knowledge_data)
    k_id = knowledge_data.get("raw_id") or knowledge_data.get("id") or props.get("id")
    return {
        "id": k_id,
        "title": props.get("title", ""),
        "content": props.get("content", ""),
        "is_verified": props.get("is_verified", False),
        "source": props.get("source", ""),
    }


def compress_generic_record(record: dict[str, Any]) -> dict[str, Any]:
    """Strip redundant wrapper fields from generic records."""
    r_type = record.get("record_type") or record.get("node_type")
    if r_type == "task":
        return compress_task_record(record)
    if r_type == "decision":
        return compress_decision_record(record)
    if r_type == "checkpoint":
        return compress_checkpoint_record(record)
    if r_type == "knowledge":
        return compress_knowledge_record(record)

    # Generic clean-up
    props = record.get("properties", record)
    clean = {}
    for k, v in props.items():
        if k not in ("_sqlite_id", "metadata_json", "vector_embedding", "raw_payload"):
            clean[k] = v
    if "id" not in clean and ("raw_id" in record or "id" in record):
        clean["id"] = record.get("raw_id") or record.get("id")
    return clean
