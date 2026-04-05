from __future__ import annotations

from typing import Optional

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.internal.repository import TaskRepository
from embedding_task_orchestrator.models import TaskRecord
from embedding_task_orchestrator.persistence import DurableTaskRecord, to_durable_task_record


class PostgresTaskRepository(TaskRepository):
    def __init__(self, *, dsn: str, schema: str = "public") -> None:
        self._dsn = dsn
        self._schema = schema

    def create(self, task: TaskRecord) -> TaskRecord:
        self._ensure_supported()
        raise self._not_implemented(task)

    def get(self, task_id: str) -> TaskRecord:
        self._ensure_supported()
        raise self._not_implemented(task_id)

    def transition(
        self,
        task_id: str,
        next_status: str,
        *,
        progress: Optional[float] = None,
        attempt_count: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> TaskRecord:
        self._ensure_supported()
        raise self._not_implemented(task_id)

    def public_view(self, task_id: str) -> TaskRecord:
        self._ensure_supported()
        raise self._not_implemented(task_id)

    def serialize(self, task: TaskRecord) -> DurableTaskRecord:
        return to_durable_task_record(task)

    def _ensure_supported(self) -> None:
        if not self._dsn:
            raise PlatformError(
                code="SYS-INTERNAL-500001",
                message="postgres repository selected but APP_POSTGRES_DSN is empty",
                error_type="internal_error",
                status_code=500,
            )

    def _not_implemented(self, _subject: object) -> NotImplementedError:
        return NotImplementedError(
            f"PostgreSQL repository wiring for schema '{self._schema}' is not implemented in the MVP scaffold"
        )
