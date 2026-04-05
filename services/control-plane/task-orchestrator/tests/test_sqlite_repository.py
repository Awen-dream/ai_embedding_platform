import tempfile
import unittest

from embedding_task_orchestrator.internal.sqlite_repository import SqliteTaskRepository
from embedding_task_orchestrator.models import TaskRecord


class SqliteTaskRepositoryTest(unittest.TestCase):
    def test_sqlite_repository_persists_and_transitions_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = SqliteTaskRepository(path=f"{temp_dir}/tasks.db")
            task = TaskRecord(
                task_id="task_123",
                tenant_id="tenant-a",
                model="bge-m3",
                source={"type": "inline", "items": ["hello world"]},
            )

            repository.create(task)
            repository.transition(task.task_id, "queued", progress=0.1, attempt_count=1)

            reloaded = SqliteTaskRepository(path=f"{temp_dir}/tasks.db")
            stored = reloaded.get(task.task_id)

            self.assertEqual(stored.status, "queued")
            self.assertEqual(stored.attempt_count, 1)
            self.assertEqual(stored.source["type"], "inline")
