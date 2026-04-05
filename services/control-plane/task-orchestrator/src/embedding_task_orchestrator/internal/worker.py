from __future__ import annotations

import asyncio
from typing import Any

from embedding_platform_common.errors import PlatformError
from embedding_platform_common.observability import log_event
from embedding_task_orchestrator.internal.executor import execute_embedding_task
from embedding_task_orchestrator.internal.queue import DeadLetterRecord, TaskQueue, TaskQueueMessage
from embedding_task_orchestrator.internal.repository import TaskRepository
from embedding_task_orchestrator.state_machine import TERMINAL_STATES


async def run_worker_loop(
    *,
    queue: TaskQueue,
    store: TaskRepository,
    settings: Any,
    logger: Any,
) -> None:
    while True:
        message = await queue.dequeue()
        try:
            await process_queue_message(
                message=message,
                queue=queue,
                store=store,
                settings=settings,
                logger=logger,
            )
        finally:
            queue.task_done(message)


async def process_queue_message(
    *,
    message: TaskQueueMessage,
    queue: TaskQueue,
    store: TaskRepository,
    settings: Any,
    logger: Any,
) -> None:
    task = store.get(message.task_id)
    if task.status in TERMINAL_STATES:
        return

    store.transition(task.task_id, task.status, attempt_count=message.attempt)
    log_event(
        logger,
        "embedding.task.started",
        request_id=message.request_id,
        task_id=task.task_id,
        attempt=message.attempt,
    )

    try:
        await execute_embedding_task(
            request_id=message.request_id,
            task=task,
            store=store,
            settings=settings,
            logger=logger,
        )
    except PlatformError as exc:
        await _handle_execution_error(
            message=message,
            queue=queue,
            store=store,
            settings=settings,
            logger=logger,
            error=exc,
        )
    except Exception as exc:
        await _handle_execution_error(
            message=message,
            queue=queue,
            store=store,
            settings=settings,
            logger=logger,
            error=PlatformError(
                code="SYS-INTERNAL-500001",
                message=str(exc),
                error_type="internal_error",
                status_code=500,
                retryable=False,
            ),
        )


async def _handle_execution_error(
    *,
    message: TaskQueueMessage,
    queue: TaskQueue,
    store: TaskRepository,
    settings: Any,
    logger: Any,
    error: PlatformError,
) -> None:
    task = store.get(message.task_id)
    if error.retryable and message.attempt < settings.max_attempts:
        store.transition(
            task.task_id,
            "retrying",
            progress=task.progress,
            attempt_count=message.attempt,
            error_code=error.code,
            error_message=error.message,
        )
        log_event(
            logger,
            "embedding.task.retrying",
            request_id=message.request_id,
            task_id=task.task_id,
            attempt=message.attempt,
            next_attempt=message.attempt + 1,
            error_code=error.code,
        )
        await asyncio.sleep(settings.retry_backoff_seconds * message.attempt)
        store.transition(
            task.task_id,
            "queued",
            progress=task.progress,
            attempt_count=message.attempt,
            error_code=None,
            error_message=None,
        )
        await queue.enqueue(
            TaskQueueMessage(
                task_id=task.task_id,
                request_id=message.request_id,
                attempt=message.attempt + 1,
            )
        )
        log_event(
            logger,
            "embedding.task.queued",
            request_id=message.request_id,
            task_id=task.task_id,
            attempt=message.attempt + 1,
        )
        return

    store.transition(
        task.task_id,
        "failed",
        progress=1.0,
        attempt_count=message.attempt,
        error_code=error.code,
        error_message=error.message,
    )
    queue.add_dead_letter(
        DeadLetterRecord(
            task_id=task.task_id,
            request_id=message.request_id,
            attempt=message.attempt,
            error_code=error.code,
            error_message=error.message,
        )
    )
    log_event(
        logger,
        "embedding.task.failed",
        request_id=message.request_id,
        task_id=task.task_id,
        attempt=message.attempt,
        error_code=error.code,
        error_message=error.message,
    )
