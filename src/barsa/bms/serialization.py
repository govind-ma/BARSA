"""BMS Serialization and deserialization utilities."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from barsa.bms.base import BMSBaseModel
from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.records import AnyBMSRecord
from barsa.bms.validation import (
    BMSValidationError,
    validate_bms_package,
    validate_bms_record_data,
)


def serialize_record(record: BMSBaseModel) -> str:
    """Serialize a BMS record or model into a canonical, formatted JSON string."""
    return record.model_dump_json(indent=2, by_alias=True)


def deserialize_record(data: str | dict[str, Any]) -> AnyBMSRecord:
    """Deserialize a JSON string or dict into the corresponding BMS record type."""
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as err:
            msg = f"Malformed JSON string: {err.msg} at line {err.lineno} col {err.colno}"
            raise BMSValidationError(msg) from err
    elif isinstance(data, dict):
        parsed = data
    else:
        msg = f"Expected JSON string or dict, got {type(data).__name__}"
        raise BMSValidationError(msg)

    return validate_bms_record_data(parsed)


def validate_record(data: str | dict[str, Any]) -> tuple[bool, AnyBMSRecord | None, list[str]]:
    """Validate raw data against BMS record specifications.

    Returns:
        (is_valid, validated_record_or_none, list_of_error_messages)
    """
    try:
        record = deserialize_record(data)
        return True, record, []
    except BMSValidationError as err:
        return False, None, err.errors
    except Exception as err:  # noqa: BLE001
        return False, None, [str(err)]


def validate_package(
    data: str | dict[str, Any] | BarsaMemoryPackage,
) -> tuple[bool, BarsaMemoryPackage | None, list[str]]:
    """Validate a package including schema parsing and referential integrity checks.

    Returns:
        (is_valid, validated_package_or_none, list_of_error_messages)
    """
    pkg_model: BarsaMemoryPackage
    if isinstance(data, BarsaMemoryPackage):
        pkg_model = data
    elif isinstance(data, str):
        try:
            parsed = json.loads(data)
            pkg_model = BarsaMemoryPackage.model_validate(parsed)
        except json.JSONDecodeError as err:
            return False, None, [f"Malformed JSON: {err.msg}"]
        except ValidationError as err:
            errors = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in err.errors()]
            return False, None, errors
    elif isinstance(data, dict):
        try:
            pkg_model = BarsaMemoryPackage.model_validate(data)
        except ValidationError as err:
            errors = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in err.errors()]
            return False, None, errors
    else:
        return False, None, [f"Invalid input type: {type(data).__name__}"]

    referential_errors = validate_bms_package(pkg_model)
    if referential_errors:
        return False, pkg_model, referential_errors

    return True, pkg_model, []


def export_package(package: BarsaMemoryPackage, destination: str | Path) -> Path:
    """Export a BarsaMemoryPackage to a local JSON file after running full validation."""
    is_valid, _, errors = validate_package(package)
    if not is_valid:
        msg = f"Cannot export invalid BarsaMemoryPackage: {'; '.join(errors)}"
        raise BMSValidationError(msg, errors=errors)

    dest_path = Path(destination).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    json_content = serialize_record(package)
    dest_path.write_text(json_content, encoding="utf-8")
    return dest_path


def import_package(source: str | Path) -> BarsaMemoryPackage:
    """Import and validate a BarsaMemoryPackage from a local JSON file path or raw JSON string."""
    source_path = Path(source)
    if source_path.is_file():
        try:
            content = source_path.read_text(encoding="utf-8")
        except OSError as err:
            msg = f"Failed to read package file '{source}': {err}"
            raise BMSValidationError(msg) from err
    elif isinstance(source, str) and (source.strip().startswith("{") or "\n" in source):
        content = source
    else:
        msg = f"Source path '{source}' does not exist or is not a valid file"
        raise BMSValidationError(msg)

    is_valid, pkg, errors = validate_package(content)
    if not is_valid or pkg is None:
        msg = f"Imported package failed validation: {'; '.join(errors)}"
        raise BMSValidationError(msg, errors=errors)

    return pkg
