from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from embedding_task_orchestrator.models import TaskRecord


class DurableTaskRecord(BaseModel):
    task_id: str
    tenant_id: str
    task_type: str = "embedding_batch"
    modality: str = "text"
    model: str
    source_payload: dict
    callback_url: Optional[str] = None
    status: str
    progress: float
    attempt_count: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    version: int = 1


def to_durable_task_record(task: TaskRecord) -> DurableTaskRecord:
    return DurableTaskRecord(
        task_id=task.task_id,
        tenant_id=task.tenant_id,
        model=task.model,
        source_payload=task.source,
        callback_url=task.callback_url,
        status=task.status,
        progress=task.progress,
        attempt_count=task.attempt_count,
        error_code=task.error_code,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
