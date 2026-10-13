"""API Schemas for BMS endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class BMSVersionResponse(BaseModel):
    """Payload returned by /api/v1/bms/version."""

    bms_version: str = Field(..., description="Active BMS version")
    supported_versions: list[str] = Field(..., description="All supported BMS versions")
    format_identifier: str = Field(..., description="Package format identifier")
    supported_record_types: list[str] = Field(..., description="List of supported record types")


class BMSValidationResponse(BaseModel):
    """Standardized response payload for validation endpoints."""

    valid: bool = Field(..., description="Whether validation succeeded")
    record_type: str | None = Field(default=None, description="Record type if validating a record")
    record_id: str | None = Field(default=None, description="Record ID if available")
    errors: list[str] = Field(
        default_factory=list, description="Validation error messages if invalid"
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic details")
