from __future__ import annotations

from typing import Optional


def has_query_or_vector(query: Optional[str], vector: Optional[list[float]]) -> bool:
    return bool((query and query.strip()) or vector)
