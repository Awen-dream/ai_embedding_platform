from __future__ import annotations

from typing import Iterable


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def chunk_words(words: list[str], chunk_size_words: int, overlap_words: int) -> Iterable[tuple[int, int, list[str]]]:
    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be greater than zero")
    if overlap_words < 0:
        raise ValueError("overlap_words must be greater than or equal to zero")
    if overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be smaller than chunk_size_words")

    start = 0
    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        yield start, end, words[start:end]
        if end >= len(words):
            break
        start = end - overlap_words

