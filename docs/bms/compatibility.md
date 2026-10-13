# BMS Version Compatibility & Extensibility

## 1. Semantic Versioning for BMS

BMS versions follow `MAJOR.MINOR`:
- **Current Version:** `0.1`
- Minor version increments (e.g. `0.2`) introduce backward-compatible additions (e.g. new optional fields or new record types).
- Major version increments (e.g. `1.0`) may introduce breaking schema modifications or required field alterations.

---

## 2. Extensibility Mechanism

To prevent uncontrolled schema fragmentation while allowing experimental features:
- All top-level fields are strictly validated (`extra = "forbid"`).
- Models requiring customization (`Workspace`, `Project`, `AgentRecord`) inherit from `MetadataExtensibleModel`, providing a typed `metadata: dict[str, Any]` field.
- Custom agent tools, framework metadata, or runtime parameters should be placed within the `metadata` dictionary.

---

## 3. Forward and Backward Compatibility

- **Unknown Record Types:** Deserializers reject unknown record types explicitly to prevent silent data corruption.
- **Unsupported Versions:** Deserializers check `schema_version` and reject incompatible versions with human-readable error messages.
- **Null Safety:** Optional fields default to `None` or empty lists/dicts. Null values are never interpreted as implicit defaults.
