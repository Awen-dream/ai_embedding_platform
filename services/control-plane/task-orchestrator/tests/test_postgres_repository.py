import unittest
from datetime import datetime, timezone

from embedding_task_orchestrator.internal.postgres_repository import PostgresTaskRepository
from embedding_task_orchestrator.models import TaskRecord


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((" ".join(str(query).split()), params))

    def fetchone(self):
        if self.rows:
            return self.rows.pop(0)
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PostgresTaskRepositoryTest(unittest.TestCase):
    def test_create_writes_task_and_history_rows(self) -> None:
        repository = PostgresTaskRepository(
            dsn="postgresql://user:pass@localhost:5432/embedding",
            schema="public",
        )
        cursor = FakeCursor()
        repository._connect = lambda: FakeConnection(cursor)  # type: ignore[method-assign]

        task = TaskRecord(
            task_id="task_123",
            tenant_id="tenant-a",
            model="bge-m3",
            source={"type": "inline", "items": ["hello world"]},
            status="queued",
        )

        created = repository.create(task)

        self.assertEqual(created.task_id, "task_123")
        self.assertEqual(len(cursor.executed), 2)
        self.assertIn('"public"."embedding_tasks"', cursor.executed[0][0])
        self.assertIn('"public"."embedding_task_state_history"', cursor.executed[1][0])

    def test_get_maps_row_to_task_record(self) -> None:
        repository = PostgresTaskRepository(
            dsn="postgresql://user:pass@localhost:5432/embedding",
            schema="public",
        )
        now = datetime.now(timezone.utc)
        cursor = FakeCursor(
            rows=[
                (
                    "task_123",
                    "tenant-a",
                    "bge-m3",
                    {"type": "inline", "items": ["hello world"]},
                    None,
                    "queued",
                    0.5,
                    2,
                    None,
                    None,
                    now,
                    now,
                )
            ]
        )
        repository._connect = lambda: FakeConnection(cursor)  # type: ignore[method-assign]

        task = repository.get("task_123")

        self.assertEqual(task.task_id, "task_123")
        self.assertEqual(task.attempt_count, 2)
        self.assertEqual(task.status, "queued")

    def test_transition_updates_task_and_records_history(self) -> None:
        repository = PostgresTaskRepository(
            dsn="postgresql://user:pass@localhost:5432/embedding",
            schema="public",
        )
        now = datetime.now(timezone.utc)
        initial_row = (
            "task_123",
            "tenant-a",
            "bge-m3",
            {"type": "inline", "items": ["hello world"]},
            None,
            "queued",
            0.0,
            1,
            None,
            None,
            now,
            now,
        )
        updated_row = (
            "task_123",
            "tenant-a",
            "bge-m3",
            {"type": "inline", "items": ["hello world"]},
            None,
            "preprocessing",
            0.2,
            1,
            None,
            None,
            now,
            now,
        )
        cursor = FakeCursor(rows=[initial_row, updated_row])
        repository._connect = lambda: FakeConnection(cursor)  # type: ignore[method-assign]

        updated = repository.transition("task_123", "preprocessing", progress=0.2)

        self.assertEqual(updated.status, "preprocessing")
        self.assertEqual(updated.progress, 0.2)
        self.assertIn("FOR UPDATE", cursor.executed[0][0])
        self.assertIn('"public"."embedding_task_state_history"', cursor.executed[2][0])
