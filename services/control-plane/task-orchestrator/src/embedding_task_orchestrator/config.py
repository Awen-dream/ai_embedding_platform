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
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_stream_key: str = "embedding:tasks"
    redis_consumer_group: str = "embedding-task-workers"
    redis_consumer_name: str = "task-orchestrator-1"
    redis_dead_letter_stream_key: str = "embedding:tasks:dlq"
    redis_block_milliseconds: int = 1000
    kafka_bootstrap_servers: str = "127.0.0.1:9092"
    kafka_topic: str = "embedding.tasks"
    kafka_dead_letter_topic: str = "embedding.tasks.dlq"
    kafka_group_id: str = "embedding-task-workers"
    kafka_client_id: str = "task-orchestrator"
    kafka_poll_timeout_milliseconds: int = 1000
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
        redis_url=os.getenv("APP_REDIS_URL", "redis://127.0.0.1:6379/0"),
        redis_stream_key=os.getenv("APP_REDIS_STREAM_KEY", "embedding:tasks"),
        redis_consumer_group=os.getenv("APP_REDIS_CONSUMER_GROUP", "embedding-task-workers"),
        redis_consumer_name=os.getenv("APP_REDIS_CONSUMER_NAME", "task-orchestrator-1"),
        redis_dead_letter_stream_key=os.getenv("APP_REDIS_DEAD_LETTER_STREAM_KEY", "embedding:tasks:dlq"),
        redis_block_milliseconds=int(os.getenv("APP_REDIS_BLOCK_MILLISECONDS", "1000")),
        kafka_bootstrap_servers=os.getenv("APP_KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
        kafka_topic=os.getenv("APP_KAFKA_TOPIC", "embedding.tasks"),
        kafka_dead_letter_topic=os.getenv("APP_KAFKA_DEAD_LETTER_TOPIC", "embedding.tasks.dlq"),
        kafka_group_id=os.getenv("APP_KAFKA_GROUP_ID", "embedding-task-workers"),
        kafka_client_id=os.getenv("APP_KAFKA_CLIENT_ID", "task-orchestrator"),
        kafka_poll_timeout_milliseconds=int(os.getenv("APP_KAFKA_POLL_TIMEOUT_MILLISECONDS", "1000")),
        preprocess_url=os.getenv("APP_PREPROCESS_URL", "http://127.0.0.1:8085"),
        runtime_url=os.getenv("APP_RUNTIME_URL", "http://127.0.0.1:8082"),
        vector_store_url=os.getenv("APP_VECTOR_STORE_URL", "http://127.0.0.1:8083"),
        http_timeout_seconds=float(os.getenv("APP_HTTP_TIMEOUT_SECONDS", "5")),
        default_index_id=os.getenv("APP_DEFAULT_INDEX_ID", "default-index"),
        max_attempts=int(os.getenv("APP_MAX_ATTEMPTS", "3")),
        retry_backoff_seconds=float(os.getenv("APP_RETRY_BACKOFF_SECONDS", "0.1")),
    )
