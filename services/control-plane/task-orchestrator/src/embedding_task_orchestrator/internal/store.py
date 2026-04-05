from __future__ import annotations

from threading import Lock
from typing import Optional

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.models import TaskRecord, utc_now
from embedding_task_orchestrator.state_machine import can_transition, public_status


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = Lock()

    def create(self, task: TaskRecord) -> TaskRecord:
        with self._lock:
            self._tasks[task.task_id] = task
            return task

    def get(self, task_id: str) -> TaskRecord:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise PlatformError(
                    code="TASK-NOTFOUND-404001",
                    message="task not found",
                    error_type="not_found_error",
                    status_code=404,
                )
            return task

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
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise PlatformError(
                    code="TASK-NOTFOUND-404001",
                    message="task not found",
                    error_type="not_found_error",
                    status_code=404,
                )
            current_status = task.status
            if current_status != next_status and not can_transition(current_status, next_status):
                raise PlatformError(
                    code="TASK-STATE-409001",
                    message=f"cannot transition task from {current_status} to {next_status}",
                    error_type="conflict_error",
                    status_code=409,
                )

            updated = task.model_copy(
                update={
                    "status": next_status,
                    "progress": task.progress if progress is None else progress,
                    "attempt_count": task.attempt_count if attempt_count is None else attempt_count,
                    "updated_at": utc_now(),
                    "error_code": error_code,
                    "error_message": error_message,
                }
            )
            self._tasks[task_id] = updated
            return updated

    def public_view(self, task_id: str) -> TaskRecord:
        task = self.get(task_id)
        return task.model_copy(update={"status": public_status(task.status)})
