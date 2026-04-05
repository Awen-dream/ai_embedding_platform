from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RetrievalSettings:
    service_name: str = "retrieval"
    host: str = "0.0.0.0"
    port: int = 8084
    runtime_url: str = "http://127.0.0.1:8082"
    vector_store_url: str = "http://127.0.0.1:8083"
    default_model: str = "bge-m3"
    default_dimension: int = 16
    http_timeout_seconds: float = 5.0


def load_settings() -> RetrievalSettings:
    return RetrievalSettings(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8084")),
        runtime_url=os.getenv("APP_RUNTIME_URL", "http://127.0.0.1:8082"),
        vector_store_url=os.getenv("APP_VECTOR_STORE_URL", "http://127.0.0.1:8083"),
        default_model=os.getenv("APP_DEFAULT_MODEL", "bge-m3"),
        default_dimension=int(os.getenv("APP_DEFAULT_DIMENSION", "16")),
        http_timeout_seconds=float(os.getenv("APP_HTTP_TIMEOUT_SECONDS", "5")),
    )

