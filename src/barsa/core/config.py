"""Application configuration using Pydantic Settings."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageProviderType(StrEnum):
    LOCAL = "local"
    MEMORY = "memory"
    GITHUB = "github"
    S3 = "s3"


class Settings(BaseSettings):
    """Barsa central configuration.

    Reads configuration values from environment variables and an optional .env file.
    Ensures safe handling of sensitive information and validates local paths.
    """

    model_config = SettingsConfigDict(
        env_prefix="BARSA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    app_name: str = Field(default="BARSA", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT,
        description="Deployment environment",
    )
    debug: bool = Field(default=False, description="Debug mode flag")

    # Server Bindings
    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")

    # Storage Settings (Local-first & storage-independent)
    data_dir: Path = Field(
        default=Path(".barsa"),
        description="Local data directory for local-first storage",
    )
    storage_provider: StorageProviderType = Field(
        default=StorageProviderType.LOCAL,
        description="Active storage backend provider type",
    )

    # Logging & Diagnostics
    log_level: str = Field(
        default="INFO",
        description="Application logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_json_format: bool = Field(
        default=False,
        description="Format log outputs as structured JSON",
    )

    # Security & Authentication (Phase 1 placeholders; safe secrets handling)
    secret_key: Annotated[
        SecretStr | None, Field(default=None, description="Internal signing secret")
    ]

    @field_validator("data_dir", mode="after")
    @classmethod
    def resolve_data_dir(cls, value: Path) -> Path:
        """Resolve and expand relative or tilde-prefixed data directory paths."""
        return value.expanduser()

    @field_validator("log_level", mode="after")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Ensure standard logging levels."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in valid_levels:
            msg = f"Invalid log level '{value}'. Must be one of {valid_levels}"
            raise ValueError(msg)
        return upper

    def ensure_data_dir(self) -> Path:
        """Ensure the local data directory exists on the filesystem and return resolved path."""
        resolved = self.data_dir.resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
