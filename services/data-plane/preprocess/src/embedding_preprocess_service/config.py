from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PreprocessSettings:
    service_name: str = "preprocess"
    host: str = "0.0.0.0"
    port: int = 8085
    default_chunk_size_words: int = 64
    default_overlap_words: int = 8


def load_settings() -> PreprocessSettings:
    return PreprocessSettings(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8085")),
        default_chunk_size_words=int(os.getenv("APP_DEFAULT_CHUNK_SIZE_WORDS", "64")),
        default_overlap_words=int(os.getenv("APP_DEFAULT_OVERLAP_WORDS", "8")),
    )

