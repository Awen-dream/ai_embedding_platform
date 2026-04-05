from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class EmbeddingRuntimeSettings:
    service_name: str = "embedding-runtime"
    host: str = "0.0.0.0"
    port: int = 8082
    default_dimension: int = 16
    max_dimension: int = 64


def load_settings() -> EmbeddingRuntimeSettings:
    return EmbeddingRuntimeSettings(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8082")),
        default_dimension=int(os.getenv("APP_DEFAULT_DIMENSION", "16")),
        max_dimension=int(os.getenv("APP_MAX_DIMENSION", "64")),
    )

