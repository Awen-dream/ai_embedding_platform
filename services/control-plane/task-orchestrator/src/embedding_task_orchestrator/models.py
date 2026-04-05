from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from typing import Optional

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EmbeddingTaskRequest(BaseModel):
    tenant_id: str
    model: str
    source: dict[str, Any]
    callback_url: Optional[str] = None


class TaskAcceptedResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    attempt_count: int = 0
    created_at: str
    updated_at: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class TaskRecord(BaseModel):
    task_id: str
    tenant_id: str
    model: str
    source: dict[str, Any]
    callback_url: Optional[str] = None
    status: str = "accepted"
    progress: float = 0.0
    attempt_count: int = 0
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class QueueStatsResponse(BaseModel):
    queue_depth: int
    dead_letter_count: int
    worker_running: bool
