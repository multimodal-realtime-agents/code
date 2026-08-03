"""Parse model output into search queries for the Query Generator agent."""

from __future__ import annotations

import re


def parse_queries(text: str, limit: int = 3) -> list[str]:
    queries: list[str] = []
    for line in text.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        cleaned = cleaned.strip("\"'")
        if cleaned:
            queries.append(cleaned)
        if len(queries) == limit:
            break
    return queries
