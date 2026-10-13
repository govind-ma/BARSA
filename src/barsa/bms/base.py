"""Common base models and primitives for the Barsa Memory Standard (BMS v0.1)."""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

BMS_VERSION = "0.1"
BMS_FORMAT_IDENTIFIER = "barsa-memory-package"


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def generate_uuid_str() -> str:
    """Generate a standard string UUID."""
    return str(uuid4())


class BMSBaseModel(BaseModel):
    """Base model for all BMS entities.

    Enforces:
    - Extra fields forbidden by default to avoid accidental schema drift
    - UTC-aware datetime validation
    - Standard JSON serialization compatibility
    - String-based UUID/ID validation
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    schema_version: Annotated[str, Field(default=BMS_VERSION, description="BMS Schema Version (e.g. '0.1')")]

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        """Ensure schema version matches supported BMS versions."""
        if v != BMS_VERSION:
            msg = f"Unsupported BMS schema version '{v}'. Supported version is '{BMS_VERSION}'"
            raise ValueError(msg)
        return v

    @classmethod
    def ensure_utc(cls, dt: datetime) -> datetime:
        """Validate and guarantee that datetime is timezone-aware and converted to UTC."""
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            msg = "Datetime must be timezone-aware (UTC). Naive datetimes are prohibited in BMS."
            raise ValueError(msg)
        return dt.astimezone(UTC)


class BMSRecord(BMSBaseModel):
    """Base model for all standalone identifiable BMS records."""

    id: Annotated[
        str,
        Field(
            default_factory=generate_uuid_str,
            min_length=1,
            max_length=128,
            description="Globally unique identifier for the record",
        ),
    ]

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure ID is non-empty and stripped."""
        val = v.strip()
        if not val:
            msg = "Record ID cannot be empty or whitespace only"
            raise ValueError(msg)
        return val


class MetadataExtensibleModel(BMSRecord):
    """BMS Record with an explicit, structured metadata extensibility mechanism.

    Allows user-defined or agent-defined metadata dictionaries while still forbidding
    uncontrolled top-level schema attributes.
    """

    metadata: Annotated[
        dict[str, Any],
        Field(
            default_factory=dict,
            description="Arbitrary structured metadata dictionary for custom extensibility",
        ),
    ]
