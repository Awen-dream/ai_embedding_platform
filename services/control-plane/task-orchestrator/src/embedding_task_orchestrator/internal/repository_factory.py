from __future__ import annotations

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.config import TaskOrchestratorSettings
from embedding_task_orchestrator.internal.postgres_repository import PostgresTaskRepository
from embedding_task_orchestrator.internal.repository import TaskRepository
from embedding_task_orchestrator.internal.sqlite_repository import SqliteTaskRepository
from embedding_task_orchestrator.internal.store import InMemoryTaskRepository


def create_task_repository(settings: TaskOrchestratorSettings) -> TaskRepository:
    backend = settings.repository_backend.lower()
    if backend == "inmemory":
        return InMemoryTaskRepository()
    if backend == "sqlite":
        return SqliteTaskRepository(path=settings.sqlite_path)
    if backend == "postgres":
        return PostgresTaskRepository(
            dsn=settings.postgres_dsn,
            schema=settings.postgres_schema,
        )
    raise PlatformError(
        code="SYS-INTERNAL-500001",
        message=f"unsupported repository backend: {settings.repository_backend}",
        error_type="internal_error",
        status_code=500,
    )
