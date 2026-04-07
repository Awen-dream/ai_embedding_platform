from __future__ import annotations

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.config import TaskOrchestratorSettings
from embedding_task_orchestrator.internal.kafka_queue import KafkaTaskQueue
from embedding_task_orchestrator.internal.queue import InMemoryTaskQueue, SqliteTaskQueue, TaskQueue
from embedding_task_orchestrator.internal.redis_stream_queue import RedisStreamTaskQueue


def create_task_queue(settings: TaskOrchestratorSettings) -> TaskQueue:
    """Create the queue backend selected by configuration."""
    backend = settings.queue_backend.lower().replace("-", "_")
    if backend == "inmemory":
        return InMemoryTaskQueue()
    if backend == "sqlite":
        return SqliteTaskQueue(
            path=settings.sqlite_path,
            poll_interval_seconds=settings.queue_poll_interval_seconds,
        )
    if backend in {"redis", "redis_stream"}:
        return RedisStreamTaskQueue(
            url=settings.redis_url,
            stream_key=settings.redis_stream_key,
            consumer_group=settings.redis_consumer_group,
            consumer_name=settings.redis_consumer_name,
            dead_letter_stream_key=settings.redis_dead_letter_stream_key,
            block_milliseconds=settings.redis_block_milliseconds,
        )
    if backend == "kafka":
        return KafkaTaskQueue(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            topic=settings.kafka_topic,
            dead_letter_topic=settings.kafka_dead_letter_topic,
            group_id=settings.kafka_group_id,
            client_id=settings.kafka_client_id,
            poll_timeout_milliseconds=settings.kafka_poll_timeout_milliseconds,
        )
    raise PlatformError(
        code="SYS-INTERNAL-500001",
        message=f"unsupported queue backend: {settings.queue_backend}",
        error_type="internal_error",
        status_code=500,
    )
