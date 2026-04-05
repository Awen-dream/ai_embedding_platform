from __future__ import annotations

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.config import TaskOrchestratorSettings
from embedding_task_orchestrator.internal.queue import InMemoryTaskQueue, SqliteTaskQueue, TaskQueue


def create_task_queue(settings: TaskOrchestratorSettings) -> TaskQueue:
    """Create the queue backend selected by configuration."""
    backend = settings.queue_backend.lower()
    if backend == "inmemory":
        return InMemoryTaskQueue()
    if backend == "sqlite":
        return SqliteTaskQueue(
            path=settings.sqlite_path,
            poll_interval_seconds=settings.queue_poll_interval_seconds,
        )
    raise PlatformError(
        code="SYS-INTERNAL-500001",
        message=f"unsupported queue backend: {settings.queue_backend}",
        error_type="internal_error",
        status_code=500,
    )
