from __future__ import annotations

from typing import Optional, Protocol

from embedding_task_orchestrator.models import TaskRecord


class TaskRepository(Protocol):
    """Storage abstraction for task lifecycle state and public task views."""

    def create(self, task: TaskRecord) -> TaskRecord:
        """Persist a newly created task record."""
        ...

    def get(self, task_id: str) -> TaskRecord:
        """Load the full internal task record by task_id."""
        ...

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
        """Apply a state transition and persist the updated task snapshot."""
        ...

    def public_view(self, task_id: str) -> TaskRecord:
        """Return the externalized task view with internal states folded to public ones."""
        ...
