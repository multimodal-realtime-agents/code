"""Source-record contract for production research handoffs.

The runnable Chapter 9 research workflow is a protocol-composition demo. When a
research specialist is used for publication-grade evidence, the coordinator
should require structured source records before synthesis.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

REQUIRED_SOURCE_FIELDS = (
    "source_url",
    "title",
    "retrieved_at",
    "claim",
    "confidence",
)


def validate_source_record(record: Mapping[str, Any]) -> dict[str, str]:
    missing = [name for name in REQUIRED_SOURCE_FIELDS if name not in record]
    if missing:
        raise ValueError(f"Missing source-record fields: {', '.join(missing)}")

    validated: dict[str, str] = {}
    for name in REQUIRED_SOURCE_FIELDS:
        value = record[name]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Source-record field {name!r} must be a non-empty string.")
        validated[name] = value.strip()

    if not validated["source_url"].startswith(("https://", "http://")):
        raise ValueError("source_url must be an absolute HTTP(S) URL.")

    confidence = validated["confidence"].lower()
    if confidence not in {"high", "medium", "low", "uncertain"}:
        raise ValueError("confidence must be high, medium, low, or uncertain.")

    validated["confidence"] = confidence
    return validated


def format_source_records(records: Iterable[Mapping[str, Any]]) -> str:
    validated = [validate_source_record(record) for record in records]
    if not validated:
        raise ValueError("At least one source record is required.")

    lines: list[str] = []
    for index, record in enumerate(validated, start=1):
        lines.append(
            "\n".join(
                [
                    f"[{index}] {record['title']}",
                    f"URL: {record['source_url']}",
                    f"Retrieved: {record['retrieved_at']}",
                    f"Confidence: {record['confidence']}",
                    f"Claim: {record['claim']}",
                ]
            )
        )
    return "\n\n".join(lines)
