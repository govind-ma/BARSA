"""Core exceptions for the Barsa platform."""

from typing import Any


class BarsaError(Exception):
    """Base exception for all Barsa platform errors."""

    def __init__(
        self,
        message: str,
        code: str = "BARSA_INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(BarsaError):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            status_code=500,
            details=details,
        )


class StorageError(BarsaError):
    """Raised when a storage provider operation fails."""

    def __init__(
        self,
        message: str,
        code: str = "STORAGE_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class ResourceNotFoundError(BarsaError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str, resource_type: str = "Resource", identifier: str = "") -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "identifier": identifier},
        )


class ValidationError(BarsaError):
    """Raised when domain entity validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class ConflictError(BarsaError):
    """Raised when an optimistic concurrency conflict or uniqueness violation occurs."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            status_code=409,
            details=details,
        )


class AuthenticationError(BarsaError):
    """Raised when authentication credentials are missing, invalid, expired, or revoked."""

    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=401,
            details=details,
        )


class AuthorizationError(BarsaError):
    """Raised when an authenticated principal lacks required role, project access, or scope."""

    def __init__(self, message: str = "Access denied", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=403,
            details=details,
        )


PermissionDeniedError = AuthorizationError


class FalkorDBUnavailableError(StorageError):
    """Raised when FalkorDB graph engine is offline, unreachable, or required for an essential graph capability."""

    def __init__(
        self,
        message: str = "FalkorDB is required for graph-powered memory reasoning and project continuation, but is currently offline or unreachable.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="FALKORDB_UNAVAILABLE",
            status_code=503,
            details=details,
        )
