"""Tests for configuration, logging redaction, and storage protocols."""

from pathlib import Path

import pytest

from barsa.core.config import Settings, StorageProviderType
from barsa.core.exceptions import StorageError
from barsa.core.logging import redact_sensitive_data
from barsa.storage.factory import get_storage_provider
from barsa.storage.protocol import StorageProvider


def test_settings_default_values(tmp_path: Path) -> None:
    """Test default settings initialization and data directory creation."""
    settings = Settings(data_dir=tmp_path / "custom_barsa")
    assert settings.app_name == "BARSA"
    assert settings.storage_provider == StorageProviderType.LOCAL
    resolved_dir = settings.ensure_data_dir()
    assert resolved_dir.exists()
    assert resolved_dir.is_dir()


def test_secret_redaction() -> None:
    """Ensure sensitive tokens and keys are redacted by logging helpers."""
    test_str = "Authorization: Bearer my-secret-token-12345 with api_key: super_secret_key"
    redacted = redact_sensitive_data(test_str)
    assert "my-secret-token-12345" not in redacted
    assert "super_secret_key" not in redacted
    assert "[REDACTED]" in redacted


def test_storage_provider_protocol_runtime_check() -> None:
    """Test runtime checkable protocol behavior."""

    class IncompleteProvider:
        pass

    assert not isinstance(IncompleteProvider(), StorageProvider)


def test_storage_factory_unimplemented_provider(test_settings: Settings) -> None:
    """Storage provider factory raises clean error when provider not registered."""
    with pytest.raises(StorageError) as exc_info:
        get_storage_provider(test_settings)
    assert exc_info.value.code == "STORAGE_PROVIDER_NOT_IMPLEMENTED"
    assert exc_info.value.status_code == 501
