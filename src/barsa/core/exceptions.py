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
