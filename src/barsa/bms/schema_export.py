"""Automated JSON Schema export tool for BMS v0.1 records and packages."""

import json
from pathlib import Path
from typing import Any

from barsa.bms.base import BMS_VERSION
from barsa.bms.package import BarsaMemoryPackage
from barsa.bms.records import (
    RECORD_TYPE_MAP,
)


def export_all_json_schemas(output_dir: Path | str | None = None) -> dict[str, Path]:
    """Generate and write standard JSON Schemas for all BMS records and the package container.

    Writes to schemas/bms/v0.1/ by default.
    Returns mapping of record_type -> schema file path.
    """
    target_dir = Path("schemas") / "bms" / f"v{BMS_VERSION}" if output_dir is None else Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated_files: dict[str, Path] = {}

    # 1. Export all core record schemas
    for record_name, model_cls in RECORD_TYPE_MAP.items():
        schema: dict[str, Any] = model_cls.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["title"] = f"BMS v{BMS_VERSION} {model_cls.__name__}"

        schema_file = target_dir / f"{record_name}.json"
        schema_file.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        generated_files[record_name] = schema_file

    # 2. Export package schema
    pkg_schema: dict[str, Any] = BarsaMemoryPackage.model_json_schema()
    pkg_schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    pkg_schema["title"] = f"BMS v{BMS_VERSION} BarsaMemoryPackage"

    pkg_schema_file = target_dir / "package.json"
    pkg_schema_file.write_text(json.dumps(pkg_schema, indent=2), encoding="utf-8")
    generated_files["package"] = pkg_schema_file

    return generated_files


if __name__ == "__main__":
    files = export_all_json_schemas()
    print(f"Generated {len(files)} BMS JSON schemas:")
    for name, path in files.items():
        print(f" - {name}: {path}")
