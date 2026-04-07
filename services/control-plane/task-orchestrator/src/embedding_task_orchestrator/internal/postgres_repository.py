from __future__ import annotations

import json
import re
from typing import Any, Optional

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.internal.repository import TaskRepository
from embedding_task_orchestrator.models import TaskRecord
from embedding_task_orchestrator.persistence import DurableTaskRecord, to_durable_task_record
from embedding_task_orchestrator.state_machine import can_transition, public_status

SCHEMA_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PostgresTaskRepository(TaskRepository):
    def __init__(self, *, dsn: str, schema: str = "public") -> None:
        self._dsn = dsn
        self._schema = self._validate_schema(schema)
        self._driver = self._load_driver()

    def create(self, task: TaskRecord) -> TaskRecord:
        self._ensure_supported()
        durable = self.serialize(task)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._qualified_table('embedding_tasks')} (
                        task_id, tenant_id, task_type, modality, model, source_payload,
                        callback_url, status, progress, attempt_count, error_code,
                        error_message, version, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s::jsonb,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    """,
                    (
                        durable.task_id,
                        durable.tenant_id,
                        durable.task_type,
                        durable.modality,
                        durable.model,
                        json.dumps(durable.source_payload),
                        durable.callback_url,
                        durable.status,
                        durable.progress,
                        durable.attempt_count,
                        durable.error_code,
                        durable.error_message,
                        durable.version,
                        durable.created_at,
                        durable.updated_at,
                    ),
                )
                cur.execute(
                    f"""
                    INSERT INTO {self._qualified_table('embedding_task_state_history')} (
                        task_id, from_status, to_status, attempt_count, progress,
                        error_code, error_message, operator
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        durable.task_id,
                        None,
                        durable.status,
                        durable.attempt_count,
                        durable.progress,
                        durable.error_code,
                        durable.error_message,
                        "system",
                    ),
                )
        return task

    def get(self, task_id: str) -> TaskRecord:
        self._ensure_supported()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT task_id, tenant_id, model, source_payload, callback_url,
                           status, progress, attempt_count, error_code, error_message,
                           created_at, updated_at
                    FROM {self._qualified_table('embedding_tasks')}
                    WHERE task_id = %s
                    """,
                    (task_id,),
                )
                row = cur.fetchone()
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
        self._ensure_supported()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT task_id, tenant_id, model, source_payload, callback_url,
                           status, progress, attempt_count, error_code, error_message,
                           created_at, updated_at
                    FROM {self._qualified_table('embedding_tasks')}
                    WHERE task_id = %s
                    FOR UPDATE
                    """,
                    (task_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise PlatformError(
                        code="TASK-NOTFOUND-404001",
                        message="task not found",
                        error_type="not_found_error",
                        status_code=404,
                    )

                task = self._row_to_task(row)
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
                        "error_code": error_code,
                        "error_message": error_message,
                    }
                )
                cur.execute(
                    f"""
                    UPDATE {self._qualified_table('embedding_tasks')}
                    SET status = %s,
                        progress = %s,
                        attempt_count = %s,
                        error_code = %s,
                        error_message = %s,
                        updated_at = NOW(),
                        version = version + 1
                    WHERE task_id = %s
                    """,
                    (
                        updated.status,
                        updated.progress,
                        updated.attempt_count,
                        updated.error_code,
                        updated.error_message,
                        task_id,
                    ),
                )
                cur.execute(
                    f"""
                    INSERT INTO {self._qualified_table('embedding_task_state_history')} (
                        task_id, from_status, to_status, attempt_count, progress,
                        error_code, error_message, operator
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task_id,
                        current_status,
                        next_status,
                        updated.attempt_count,
                        updated.progress,
                        updated.error_code,
                        updated.error_message,
                        "system",
                    ),
                )
                cur.execute(
                    f"""
                    SELECT task_id, tenant_id, model, source_payload, callback_url,
                           status, progress, attempt_count, error_code, error_message,
                           created_at, updated_at
                    FROM {self._qualified_table('embedding_tasks')}
                    WHERE task_id = %s
                    """,
                    (task_id,),
                )
                refreshed = cur.fetchone()
        return self._row_to_task(refreshed) if refreshed is not None else updated

    def public_view(self, task_id: str) -> TaskRecord:
        task = self.get(task_id)
        return task.model_copy(update={"status": public_status(task.status)})

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

    def _connect(self) -> Any:
        return self._driver.connect(self._dsn)

    def _qualified_table(self, table_name: str) -> str:
        return f'"{self._schema}"."{table_name}"'

    def _row_to_task(self, row: Any) -> TaskRecord:
        source_payload = row[3]
        if isinstance(source_payload, str):
            source_payload = json.loads(source_payload)
        return TaskRecord(
            task_id=row[0],
            tenant_id=row[1],
            model=row[2],
            source=source_payload,
            callback_url=row[4],
            status=row[5],
            progress=float(row[6]),
            attempt_count=int(row[7]),
            error_code=row[8],
            error_message=row[9],
            created_at=row[10].isoformat() if hasattr(row[10], "isoformat") else str(row[10]),
            updated_at=row[11].isoformat() if hasattr(row[11], "isoformat") else str(row[11]),
        )

    @staticmethod
    def _validate_schema(schema: str) -> str:
        if not SCHEMA_PATTERN.match(schema):
            raise PlatformError(
                code="SYS-INTERNAL-500001",
                message=f"invalid postgres schema name: {schema}",
                error_type="internal_error",
                status_code=500,
            )
        return schema

    @staticmethod
    def _load_driver() -> Any:
        try:
            import psycopg2  # type: ignore
        except ModuleNotFoundError as exc:
            raise PlatformError(
                code="SYS-INTERNAL-500001",
                message="psycopg2 is required for postgres repository support",
                error_type="internal_error",
                status_code=500,
            ) from exc
        return psycopg2
