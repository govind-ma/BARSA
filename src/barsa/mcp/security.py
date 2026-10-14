"""Security boundaries, local identity, and input validation for Barsa MCP Server."""

import getpass
import os
import re
from typing import Any

from barsa.mcp.errors import BarsaMCPError, MCPErrorCode
from barsa.storage.protocol import StorageProvider

# Maximum limits to prevent denial-of-service and oversized payloads
MAX_QUERY_LENGTH = 500
MAX_RETURN_LIMIT = 100
DEFAULT_RETURN_LIMIT = 50
MAX_CHANGES_PER_COMMIT = 50
MAX_GRAPH_DEPTH = 5

# Safe identifier regex: alphanumeric, dash, underscore, dot
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
SAFE_BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\./]+$")


class LocalIdentity:
    """Represents the operating system account and local identity context."""

    def __init__(self, username: str | None = None) -> None:
        try:
            self.username = username or getpass.getuser()
        except Exception:
            self.username = os.environ.get("USERNAME") or os.environ.get("USER") or "local-user"

    def __repr__(self) -> str:
        return f"LocalIdentity(username='{self.username}')"


def get_current_identity() -> LocalIdentity:
    """Retrieve current authorized local identity."""
    return LocalIdentity()


def validate_identifier(name: str, value: str) -> str:
    """Ensure identifier contains only safe alphanumeric and delimiter characters."""
    val = value.strip()
    if not val:
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, f"{name} cannot be empty.")
    if len(val) > 128:
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, f"{name} exceeds maximum length of 128 characters.")
    if not SAFE_ID_PATTERN.match(val):
        raise BarsaMCPError(
            MCPErrorCode.INVALID_INPUT,
            f"{name} '{val}' contains invalid characters. Only alphanumeric, dash, dot, and underscore are allowed.",
        )
    return val


def validate_branch_name(branch: str) -> str:
    """Ensure branch name is safe and does not contain path traversal sequences."""
    val = branch.strip()
    if not val:
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, "Branch name cannot be empty.")
    if len(val) > 128:
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, "Branch name exceeds maximum length of 128 characters.")
    if ".." in val or val.startswith("/") or val.endswith("/"):
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, f"Invalid branch path formatting in '{val}'.")
    if not SAFE_BRANCH_PATTERN.match(val):
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, f"Branch name '{val}' contains invalid characters.")
    return val


def validate_query_string(query: str) -> str:
    """Ensure search query is bounded and non-empty."""
    val = query.strip()
    if not val:
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, "Search query cannot be empty.")
    if len(val) > MAX_QUERY_LENGTH:
        raise BarsaMCPError(
            MCPErrorCode.INVALID_INPUT,
            f"Search query exceeds maximum length of {MAX_QUERY_LENGTH} characters.",
        )
    return val


def validate_limit(limit: int | None, default: int = DEFAULT_RETURN_LIMIT, max_limit: int = MAX_RETURN_LIMIT) -> int:
    """Sanitize and clamp pagination / query limit."""
    if limit is None or limit <= 0:
        return default
    return min(limit, max_limit)


def validate_depth(depth: int | None, default: int = 2, max_depth: int = MAX_GRAPH_DEPTH) -> int:
    """Sanitize and clamp graph traversal depth."""
    if depth is None or depth <= 0:
        return default
    return min(depth, max_depth)


def validate_changes_payload(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verify changes list is non-empty and bounded."""
    if not changes:
        raise BarsaMCPError(MCPErrorCode.INVALID_INPUT, "Changes list cannot be empty.")
    if len(changes) > MAX_CHANGES_PER_COMMIT:
        raise BarsaMCPError(
            MCPErrorCode.INVALID_INPUT,
            f"Commit exceeds maximum limit of {MAX_CHANGES_PER_COMMIT} changes per commit.",
        )
    return changes


def verify_project_access(project_id: str, storage: StorageProvider) -> Any:
    """Verify project exists in authoritative storage and caller has access.

    Raises BarsaMCPError if not found.
    """
    clean_id = validate_identifier("project_id", project_id)
    try:
        project = storage.get_project(clean_id)
        if not project:
            raise BarsaMCPError(
                MCPErrorCode.PROJECT_NOT_FOUND,
                f"Project '{clean_id}' was not found in storage.",
                {"project_id": clean_id},
            )
        return project
    except BarsaMCPError:
        raise
    except Exception as exc:
        raise BarsaMCPError(
            MCPErrorCode.PROJECT_NOT_FOUND,
            f"Project '{clean_id}' does not exist or cannot be accessed.",
            {"project_id": clean_id, "error": str(exc)},
        ) from exc
