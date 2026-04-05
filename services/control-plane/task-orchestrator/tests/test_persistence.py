import unittest

from embedding_task_orchestrator.models import TaskRecord
from embedding_task_orchestrator.persistence import to_durable_task_record


class TaskPersistenceMappingTest(unittest.TestCase):
    def test_to_durable_task_record_preserves_core_fields(self) -> None:
        task = TaskRecord(
            task_id="task_123",
            tenant_id="tenant-a",
            model="bge-m3",
            source={"type": "inline", "items": ["hello world"]},
            status="queued",
            progress=0.4,
            attempt_count=2,
        )

        durable = to_durable_task_record(task)

        self.assertEqual(durable.task_id, "task_123")
        self.assertEqual(durable.tenant_id, "tenant-a")
        self.assertEqual(durable.task_type, "embedding_batch")
        self.assertEqual(durable.modality, "text")
        self.assertEqual(durable.source_payload["type"], "inline")
        self.assertEqual(durable.attempt_count, 2)
