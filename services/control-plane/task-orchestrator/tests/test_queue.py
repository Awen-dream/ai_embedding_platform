import asyncio
import tempfile
import unittest

from embedding_task_orchestrator.internal.queue import DeadLetterRecord, SqliteTaskQueue, TaskQueueMessage


class SqliteTaskQueueTest(unittest.TestCase):
    def test_sqlite_queue_persists_messages_and_dead_letters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = f"{temp_dir}/queue.db"
            queue = SqliteTaskQueue(path=path, poll_interval_seconds=0.01)
            asyncio.run(queue.enqueue(TaskQueueMessage(task_id="task-1", request_id="req-1", attempt=1)))

            claimed = asyncio.run(queue.dequeue())
            self.assertEqual(claimed.task_id, "task-1")
            self.assertIsNotNone(claimed.queue_id)

            queue.add_dead_letter(
                DeadLetterRecord(
                    task_id="task-1",
                    request_id="req-1",
                    attempt=1,
                    error_code="TASK-FAILED",
                    error_message="boom",
                )
            )
            queue.task_done(claimed)

            reloaded = SqliteTaskQueue(path=path, poll_interval_seconds=0.01)
            self.assertEqual(reloaded.qsize(), 0)
            self.assertEqual(reloaded.dead_letter_count(), 1)
