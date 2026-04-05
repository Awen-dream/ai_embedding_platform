from __future__ import annotations

import json
import os
import sqlite3
from threading import Lock
from typing import Optional

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.internal.repository import TaskRepository
from embedding_task_orchestrator.models import TaskRecord, utc_now
from embedding_task_orchestrator.state_machine import can_transition, public_status


class SqliteTaskRepository(TaskRepository):
    """Single-node durable task repository backed by SQLite."""

    def __init__(self, *, path: str) -> None:
        self._path = path
        self._lock = Lock()
        self._conn = self._connect(path)
        self._initialize()

    def create(self, task: TaskRecord) -> TaskRecord:
        """Insert a new task snapshot."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO tasks (
                    task_id, tenant_id, model, source_json, callback_url,
                    status, progress, attempt_count, created_at, updated_at,
                    error_code, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.tenant_id,
                    task.model,
                    json.dumps(task.source, ensure_ascii=False, sort_keys=True),
                    task.callback_url,
                    task.status,
                    task.progress,
                    task.attempt_count,
                    task.created_at,
                    task.updated_at,
                    task.error_code,
                    task.error_message,
                ),
            )
            self._conn.commit()
        return task

    def get(self, task_id: str) -> TaskRecord:
        """Fetch a task by primary key and convert it back to the domain model."""
        with self._lock:
            row = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            raise PlatformError(
                code="TASK-NOTFOUND-404001",
                message="task not found",
                error_type="not_found_error",
                status_code=404,
            )
        return self._row_to_task(row)

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
        """Validate and persist a task state transition."""
        with self._lock:
            row = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                raise PlatformError(
                    code="TASK-NOTFOUND-404001",
                    message="task not found",
                    error_type="not_found_error",
                    status_code=404,
                )
            current = self._row_to_task(row)
            if current.status != next_status and not can_transition(current.status, next_status):
                raise PlatformError(
                    code="TASK-STATE-409001",
                    message=f"cannot transition task from {current.status} to {next_status}",
                    error_type="conflict_error",
                    status_code=409,
                )

            updated = current.model_copy(
                update={
                    "status": next_status,
                    "progress": current.progress if progress is None else progress,
                    "attempt_count": current.attempt_count if attempt_count is None else attempt_count,
                    "updated_at": utc_now(),
                    "error_code": error_code,
                    "error_message": error_message,
                }
            )
            self._conn.execute(
                """
                UPDATE tasks
                SET status = ?, progress = ?, attempt_count = ?, updated_at = ?, error_code = ?, error_message = ?
                WHERE task_id = ?
                """,
                (
                    updated.status,
                    updated.progress,
                    updated.attempt_count,
                    updated.updated_at,
                    updated.error_code,
                    updated.error_message,
                    updated.task_id,
                ),
            )
            self._conn.commit()
        return updated

    def public_view(self, task_id: str) -> TaskRecord:
        """Return the task in public status form."""
        task = self.get(task_id)
        return task.model_copy(update={"status": public_status(task.status)})

    def _initialize(self) -> None:
        """Create the tasks table if it does not exist yet."""
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    source_json TEXT NOT NULL,
                    callback_url TEXT,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_code TEXT,
                    error_message TEXT
                )
                """
            )
            self._conn.commit()

    @staticmethod
    def _connect(path: str) -> sqlite3.Connection:
        """Open a SQLite connection and ensure its parent directory exists."""
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> TaskRecord:
        """Convert a raw SQLite row back into a TaskRecord."""
        return TaskRecord(
            task_id=str(row["task_id"]),
            tenant_id=str(row["tenant_id"]),
            model=str(row["model"]),
            source=json.loads(str(row["source_json"])),
            callback_url=row["callback_url"],
            status=str(row["status"]),
            progress=float(row["progress"]),
            attempt_count=int(row["attempt_count"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            error_code=row["error_code"],
            error_message=row["error_message"],
        )
