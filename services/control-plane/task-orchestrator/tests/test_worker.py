import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from embedding_platform_common.errors import PlatformError
from embedding_platform_common.ids import generate_id
from embedding_task_orchestrator.internal.queue import InMemoryTaskQueue, TaskQueueMessage
from embedding_task_orchestrator.internal.store import TaskStore
from embedding_task_orchestrator.internal.worker import process_queue_message
from embedding_task_orchestrator.models import TaskRecord


class TaskWorkerTest(unittest.TestCase):
    def test_retryable_error_requeues_task(self) -> None:
        store = TaskStore()
        queue = InMemoryTaskQueue()
        task = TaskRecord(
            task_id=generate_id("task"),
            tenant_id="tenant-a",
            model="bge-m3",
            source={"type": "inline", "items": ["hello world"]},
            status="queued",
        )
        store.create(task)
        settings = SimpleNamespace(max_attempts=3, retry_backoff_seconds=0)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)

        with patch(
            "embedding_task_orchestrator.internal.worker.execute_embedding_task",
            AsyncMock(
                side_effect=PlatformError(
                    code="SYS-DEP-502001",
                    message="dependency unavailable",
                    error_type="dependency_error",
                    status_code=502,
                    retryable=True,
                )
            ),
        ):
            asyncio.run(
                process_queue_message(
                    message=TaskQueueMessage(task_id=task.task_id, request_id="req_test", attempt=1),
                    queue=queue,
                    store=store,
                    settings=settings,
                    logger=logger,
                )
            )

        result = store.get(task.task_id)
        self.assertEqual(result.status, "queued")
        self.assertEqual(result.attempt_count, 1)
        self.assertEqual(asyncio.run(queue.qsize()), 1)
        self.assertEqual(asyncio.run(queue.dead_letter_count()), 0)

    def test_non_retryable_error_moves_task_to_dead_letter(self) -> None:
        store = TaskStore()
        queue = InMemoryTaskQueue()
        task = TaskRecord(
            task_id=generate_id("task"),
            tenant_id="tenant-a",
            model="bge-m3",
            source={"type": "inline", "items": ["hello world"]},
            status="queued",
        )
        store.create(task)
        settings = SimpleNamespace(max_attempts=2, retry_backoff_seconds=0)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)

        with patch(
            "embedding_task_orchestrator.internal.worker.execute_embedding_task",
            AsyncMock(
                side_effect=PlatformError(
                    code="TASK-VAL-400001",
                    message="invalid task payload",
                    error_type="validation_error",
                    status_code=400,
                    retryable=False,
                )
            ),
        ):
            asyncio.run(
                process_queue_message(
                    message=TaskQueueMessage(task_id=task.task_id, request_id="req_test", attempt=1),
                    queue=queue,
                    store=store,
                    settings=settings,
                    logger=logger,
                )
            )

        result = store.get(task.task_id)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "TASK-VAL-400001")
        self.assertEqual(asyncio.run(queue.dead_letter_count()), 1)
