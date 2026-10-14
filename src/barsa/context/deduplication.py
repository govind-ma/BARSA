"""Safe record deduplication and contradiction preservation (Phase 8)."""

import hashlib
import json
from typing import Any


def compute_record_content_fingerprint(record: dict[str, Any]) -> str:
    """Generate a deterministic normalized fingerprint of a record's essential payload.

    Excludes volatile runtime metadata (e.g. projection status, internal timestamps)
    to detect true duplicate payloads.
    """
    normalized_keys = {}
    # Compare semantic fields
    for k in ("title", "summary", "content", "status", "rationale", "statement", "task_id", "uri"):
        val = record.get(k)
        if val is not None:
            if isinstance(val, str):
                normalized_keys[k] = " ".join(val.strip().split()).lower()
            else:
                normalized_keys[k] = val

    serialized = json.dumps(normalized_keys, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class RecordDeduplicator:
    """Deduplicates records based on stable ID and semantic fingerprint while preserving contradictions."""

    def __init__(self) -> None:
        self._seen_ids: set[str] = set()
        self._seen_fingerprints: set[str] = set()

    def filter_unique(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter out exact duplicate IDs and identical content payloads.

        Records with distinct IDs and distinct statements (e.g. contradictory architectural
        proposals like 'Use MySQL' vs 'Use PostgreSQL') are strictly preserved.
        """
        unique_records: list[dict[str, Any]] = []

        for rec in records:
            r_id = str(rec.get("id") or rec.get("raw_id") or "")
            if r_id and r_id in self._seen_ids:
                continue

            fp = compute_record_content_fingerprint(rec)
            # Only consider duplicate if fingerprint is non-empty and seen
            if fp and fp in self._seen_fingerprints:
                continue

            if r_id:
                self._seen_ids.add(r_id)
            if fp:
                self._seen_fingerprints.add(fp)

            unique_records.append(rec)

        return unique_records
