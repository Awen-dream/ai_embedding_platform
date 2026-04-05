from __future__ import annotations

import math
from typing import Any


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions must match")

    dot_product = sum(lv * rv for lv, rv in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if metadata.get(key) != expected:
            return False
    return True

