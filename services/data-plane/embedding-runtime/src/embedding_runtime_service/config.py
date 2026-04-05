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
    embedding_backend: str = "hashing"
    embedding_api_base_url: str = ""
    embedding_api_key: str = ""
    embedding_api_path: str = "/embeddings"
    http_timeout_seconds: float = 10.0


def load_settings() -> EmbeddingRuntimeSettings:
    return EmbeddingRuntimeSettings(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8082")),
        default_dimension=int(os.getenv("APP_DEFAULT_DIMENSION", "16")),
        max_dimension=int(os.getenv("APP_MAX_DIMENSION", "64")),
        embedding_backend=os.getenv("APP_EMBEDDING_BACKEND", "hashing"),
        embedding_api_base_url=os.getenv("APP_EMBEDDING_API_BASE_URL", ""),
        embedding_api_key=os.getenv("APP_EMBEDDING_API_KEY", ""),
        embedding_api_path=os.getenv("APP_EMBEDDING_API_PATH", "/embeddings"),
        http_timeout_seconds=float(os.getenv("APP_HTTP_TIMEOUT_SECONDS", "10")),
    )
