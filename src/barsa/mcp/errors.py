"""Standardized error codes and exceptions for Barsa MCP Server."""

from enum import StrEnum
from typing import Any


class MCPErrorCode(StrEnum):
    """Standardized Barsa MCP error codes."""

    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    ACCESS_DENIED = "ACCESS_DENIED"
    INVALID_BMS_RECORD = "INVALID_BMS_RECORD"
    CHECKPOINT_NOT_FOUND = "CHECKPOINT_NOT_FOUND"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    BRANCH_NOT_FOUND = "BRANCH_NOT_FOUND"
    COMMIT_NOT_FOUND = "COMMIT_NOT_FOUND"
    STALE_REVISION = "STALE_REVISION"
    MERGE_CONFLICT = "MERGE_CONFLICT"
    GRAPH_UNAVAILABLE = "GRAPH_UNAVAILABLE"
    GRAPH_STALE = "GRAPH_STALE"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    INVALID_INPUT = "INVALID_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class BarsaMCPError(Exception):
    """Base exception for Barsa MCP server tool errors."""

    def __init__(self, code: MCPErrorCode | str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code if isinstance(code, str) else code.value
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Format as structured error dictionary."""
        return {
            "error_code": self.code,
            "message": self.message,
            "details": self.details,
        }
