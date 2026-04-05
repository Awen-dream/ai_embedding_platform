from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from embedding_platform_common.errors import PlatformError, error_payload
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import configure_logging, log_event
from embedding_task_orchestrator.config import load_settings
from embedding_task_orchestrator.internal.queue import InMemoryTaskQueue, TaskQueueMessage
from embedding_task_orchestrator.internal.store import TaskStore
from embedding_task_orchestrator.internal.worker import run_worker_loop
from embedding_task_orchestrator.models import (
    EmbeddingTaskRequest,
    QueueStatsResponse,
    TaskAcceptedResponse,
    TaskRecord,
    TaskStatusResponse,
)


def create_app() -> FastAPI:
    settings = load_settings()
    logger = configure_logging(settings.service_name)
    store = TaskStore()
    queue = InMemoryTaskQueue()

    app = FastAPI(title="Embedding Task Orchestrator", version="0.1.0")
    app.state.store = store
    app.state.queue = queue
    app.state.logger = logger
    app.state.settings = settings
    app.state.worker_task = None

    @app.on_event("startup")
    async def startup_worker() -> None:
        app.state.worker_task = asyncio.create_task(
            run_worker_loop(
                queue=queue,
                store=store,
                settings=settings,
                logger=logger,
            )
        )

    @app.on_event("shutdown")
    async def shutdown_worker() -> None:
        worker_task = app.state.worker_task
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> JSONResponse:
        request.state.request_id = request.headers.get("x-request-id", generate_id("req"))
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    @app.exception_handler(PlatformError)
    async def handle_platform_error(request: Request, exc: PlatformError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_envelope(request.state.request_id).model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger,
            "task_orchestrator.unexpected_error",
            request_id=request.state.request_id,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(
                request_id=request.state.request_id,
                code="SYS-INTERNAL-500001",
                message="unexpected internal error",
                error_type="internal_error",
            ),
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        worker_running = app.state.worker_task is not None and not app.state.worker_task.done()
        return {"status": "ready" if worker_running else "not_ready"}

    @app.post("/internal/tasks/embedding", response_model=TaskAcceptedResponse, status_code=202)
    async def create_embedding_task(request: Request, body: EmbeddingTaskRequest) -> TaskAcceptedResponse:
        if not body.tenant_id or not body.model:
            raise PlatformError(
                code="TASK-VAL-400001",
                message="tenant_id and model are required",
                error_type="validation_error",
                status_code=400,
            )

        task = TaskRecord(
            task_id=generate_id("task"),
            tenant_id=body.tenant_id,
            model=body.model,
            source=body.source,
            callback_url=body.callback_url,
        )
        store.create(task)
        store.transition(task.task_id, "queued", progress=0.0, attempt_count=0, error_code=None, error_message=None)
        log_event(
            logger,
            "embedding.task.created",
            request_id=request.state.request_id,
            task_id=task.task_id,
            tenant_id=task.tenant_id,
        )
        await queue.enqueue(
            TaskQueueMessage(
                task_id=task.task_id,
                request_id=request.state.request_id,
                attempt=1,
            )
        )
        log_event(
            logger,
            "embedding.task.queued",
            request_id=request.state.request_id,
            task_id=task.task_id,
            attempt=1,
            queue_depth=queue.qsize(),
        )
        return TaskAcceptedResponse(task_id=task.task_id, status="queued")

    @app.get("/internal/tasks/{task_id}", response_model=TaskStatusResponse)
    async def get_task(task_id: str) -> TaskStatusResponse:
        task = store.public_view(task_id)
        return TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            attempt_count=task.attempt_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            error_code=task.error_code,
            error_message=task.error_message,
        )

    @app.get("/internal/queue/stats", response_model=QueueStatsResponse)
    async def get_queue_stats() -> QueueStatsResponse:
        worker_running = app.state.worker_task is not None and not app.state.worker_task.done()
        return QueueStatsResponse(
            queue_depth=queue.qsize(),
            dead_letter_count=queue.dead_letter_count(),
            worker_running=worker_running,
        )

    return app


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "embedding_task_orchestrator.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )
