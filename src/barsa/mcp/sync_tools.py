"""MCP tool implementations for BYOS and Cloud Synchronization (Phase 13)."""

from __future__ import annotations

import logging
from typing import Any

from barsa.core.config import Settings
from barsa.core.exceptions import BarsaError
from barsa.mcp.errors import BarsaMCPError, MCPErrorCode
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.sync.service import SyncService

logger = logging.getLogger("barsa.mcp.sync_tools")


def list_remotes_tool(
    storage: SQLiteStorageProvider,
    settings: Settings,
    project_id: str,
) -> list[dict[str, Any]]:
    """MCP implementation for barsa_list_remotes."""
    try:
        service = SyncService(storage=storage, settings=settings)
        remotes = service.list_remotes(project_id)
        return [r.model_dump(mode="json") for r in remotes]
    except BarsaError as e:
        raise BarsaMCPError(code=MCPErrorCode.INVALID_PARAMS, message=str(e)) from e
    except Exception as e:
        logger.exception("Error in list_remotes_tool")
        raise BarsaMCPError(code=MCPErrorCode.INTERNAL_ERROR, message=f"Failed to list remotes: {e}") from e


async def get_sync_status_tool(
    storage: SQLiteStorageProvider,
    settings: Settings,
    remote_id: str,
    branch: str = "main",
    passphrase: str | None = None,
) -> dict[str, Any]:
    """MCP implementation for barsa_get_sync_status."""
    try:
        service = SyncService(storage=storage, settings=settings)
        status_report = await service.get_status(remote_id, branch_name=branch, passphrase=passphrase)
        return status_report.model_dump(mode="json")
    except BarsaError as e:
        raise BarsaMCPError(code=MCPErrorCode.RESOURCE_NOT_FOUND, message=str(e)) from e
    except Exception as e:
        logger.exception("Error in get_sync_status_tool")
        raise BarsaMCPError(code=MCPErrorCode.INTERNAL_ERROR, message=f"Failed to get sync status: {e}") from e


async def pull_remote_tool(
    storage: SQLiteStorageProvider,
    settings: Settings,
    remote_id: str,
    branch: str = "main",
    passphrase: str | None = None,
) -> dict[str, Any]:
    """MCP implementation for barsa_pull_remote."""
    try:
        service = SyncService(storage=storage, settings=settings)
        res = await service.pull(remote_id, branch_name=branch, passphrase=passphrase)
        return res.model_dump(mode="json")
    except BarsaError as e:
        raise BarsaMCPError(code=MCPErrorCode.INTERNAL_ERROR, message=str(e)) from e
    except Exception as e:
        logger.exception("Error in pull_remote_tool")
        raise BarsaMCPError(code=MCPErrorCode.INTERNAL_ERROR, message=f"Failed to pull from remote: {e}") from e


async def push_remote_tool(
    storage: SQLiteStorageProvider,
    settings: Settings,
    remote_id: str,
    branch: str = "main",
    force: bool = False,
    passphrase: str | None = None,
) -> dict[str, Any]:
    """MCP implementation for barsa_push_remote."""
    try:
        service = SyncService(storage=storage, settings=settings)
        res = await service.push(remote_id, branch_name=branch, force=force, passphrase=passphrase)
        return res.model_dump(mode="json")
    except BarsaError as e:
        raise BarsaMCPError(code=MCPErrorCode.INTERNAL_ERROR, message=str(e)) from e
    except Exception as e:
        logger.exception("Error in push_remote_tool")
        raise BarsaMCPError(code=MCPErrorCode.INTERNAL_ERROR, message=f"Failed to push to remote: {e}") from e
