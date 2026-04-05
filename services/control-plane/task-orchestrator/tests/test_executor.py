import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from embedding_platform_common.errors import PlatformError
from embedding_platform_common.ids import generate_id
from embedding_task_orchestrator.internal.executor import execute_embedding_task, normalize_inline_source
from embedding_task_orchestrator.internal.store import TaskStore
from embedding_task_orchestrator.models import TaskRecord


class TaskExecutorTest(unittest.TestCase):
    def test_normalize_inline_source_accepts_strings_and_objects(self) -> None:
        source = normalize_inline_source(
            {
                "type": "inline",
                "index_id": "demo-index",
                "items": [
                    "hello world",
                    {"id": "doc-2", "text": "industrial embedding", "metadata": {"scene": "rag"}},
                ],
            },
            "default-index",
        )

        self.assertEqual(source.index_id, "demo-index")
        self.assertEqual(len(source.items), 2)
        self.assertEqual(source.items[1].item_id, "doc-2")
        self.assertEqual(source.items[1].metadata["scene"], "rag")
        self.assertEqual(source.preprocess, {})

    def test_normalize_inline_source_rejects_unsupported_source_type(self) -> None:
        with self.assertRaises(PlatformError):
            normalize_inline_source({"type": "object_storage", "items": []}, "default-index")

    def test_execute_embedding_task_marks_task_succeeded(self) -> None:
        store = TaskStore()
        task = TaskRecord(
            task_id=generate_id("task"),
            tenant_id="tenant-a",
            model="bge-m3",
            source={
                "type": "inline",
                "index_id": "demo-index",
                "items": [{"id": "doc-1", "text": "hello world", "metadata": {"scene": "rag"}}],
            },
            status="queued",
        )
        store.create(task)
        settings = SimpleNamespace(default_index_id="default-index")
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)

        with patch(
            "embedding_task_orchestrator.internal.executor._preprocess_items",
            AsyncMock(
                return_value=(
                    [
                        SimpleNamespace(
                            chunk_id="chunk-1",
                            item_id="doc-1",
                            text="hello world",
                            metadata={"scene": "rag"},
                            start_word=0,
                            end_word=2,
                        )
                    ],
                    0,
                )
            ),
        ), patch(
            "embedding_task_orchestrator.internal.executor._generate_embeddings",
            AsyncMock(return_value=[[0.1, 0.2, 0.3]]),
        ), patch(
            "embedding_task_orchestrator.internal.executor._upsert_embeddings",
            AsyncMock(return_value=1),
        ):
            import asyncio

            asyncio.run(
                execute_embedding_task(
                    request_id="req_test",
                    task=task,
                    store=store,
                    settings=settings,
                    logger=logger,
                )
            )

        result = store.get(task.task_id)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.progress, 1.0)
