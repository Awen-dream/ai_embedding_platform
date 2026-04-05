from __future__ import annotations

import hashlib
import math


def stable_embedding(text: str, dimension: int) -> list[float]:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("text must not be empty")

    tokens = cleaned.split()
    if not tokens:
        tokens = list(cleaned)

    vector = [0.0] * dimension
    for token_index, token in enumerate(tokens):
        digest = hashlib.sha256(f"{token_index}:{token}".encode("utf-8")).digest()
        for value_index in range(dimension):
            raw = digest[value_index % len(digest)]
            vector[value_index] += (raw / 127.5) - 1.0

    norm = math.sqrt(sum(component * component for component in vector)) or 1.0
    return [round(component / norm, 6) for component in vector]


def estimate_input_tokens(text: str) -> int:
    return max(len(text.split()), 1)

