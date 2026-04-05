from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class TaskOrchestratorSettings:
    service_name: str = "task-orchestrator"
    host: str = "0.0.0.0"
    port: int = 8081
    repository_backend: str = "inmemory"
    queue_backend: str = "inmemory"
    sqlite_path: str = ".data/task-orchestrator.db"
    queue_poll_interval_seconds: float = 0.1
    postgres_dsn: str = ""
    postgres_schema: str = "public"
    preprocess_url: str = "http://127.0.0.1:8085"
    runtime_url: str = "http://127.0.0.1:8082"
    vector_store_url: str = "http://127.0.0.1:8083"
    http_timeout_seconds: float = 5.0
    default_index_id: str = "default-index"
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.1


def load_settings() -> TaskOrchestratorSettings:
    return TaskOrchestratorSettings(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8081")),
        repository_backend=os.getenv("APP_REPOSITORY_BACKEND", "inmemory"),
        queue_backend=os.getenv("APP_QUEUE_BACKEND", "inmemory"),
        sqlite_path=os.getenv("APP_SQLITE_PATH", ".data/task-orchestrator.db"),
        queue_poll_interval_seconds=float(os.getenv("APP_QUEUE_POLL_INTERVAL_SECONDS", "0.1")),
        postgres_dsn=os.getenv("APP_POSTGRES_DSN", ""),
        postgres_schema=os.getenv("APP_POSTGRES_SCHEMA", "public"),
        preprocess_url=os.getenv("APP_PREPROCESS_URL", "http://127.0.0.1:8085"),
        runtime_url=os.getenv("APP_RUNTIME_URL", "http://127.0.0.1:8082"),
        vector_store_url=os.getenv("APP_VECTOR_STORE_URL", "http://127.0.0.1:8083"),
        http_timeout_seconds=float(os.getenv("APP_HTTP_TIMEOUT_SECONDS", "5")),
        default_index_id=os.getenv("APP_DEFAULT_INDEX_ID", "default-index"),
        max_attempts=int(os.getenv("APP_MAX_ATTEMPTS", "3")),
        retry_backoff_seconds=float(os.getenv("APP_RETRY_BACKOFF_SECONDS", "0.1")),
    )
