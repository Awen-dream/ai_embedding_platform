import unittest

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.config import TaskOrchestratorSettings
from embedding_task_orchestrator.internal.kafka_queue import KafkaTaskQueue
from embedding_task_orchestrator.internal.queue import InMemoryTaskQueue, SqliteTaskQueue
from embedding_task_orchestrator.internal.queue_factory import create_task_queue
from embedding_task_orchestrator.internal.redis_stream_queue import RedisStreamTaskQueue


class QueueFactoryTest(unittest.TestCase):
    def test_factory_returns_inmemory_queue_by_default(self) -> None:
        queue = create_task_queue(TaskOrchestratorSettings())
        self.assertIsInstance(queue, InMemoryTaskQueue)

    def test_factory_returns_sqlite_queue_when_selected(self) -> None:
        queue = create_task_queue(
            TaskOrchestratorSettings(
                queue_backend="sqlite",
                sqlite_path="/tmp/task-orchestrator-queue-test.db",
            )
        )
        self.assertIsInstance(queue, SqliteTaskQueue)

    def test_factory_returns_redis_stream_queue_when_selected(self) -> None:
        queue = create_task_queue(
            TaskOrchestratorSettings(
                queue_backend="redis_stream",
                redis_url="redis://127.0.0.1:6379/0",
            )
        )
        self.assertIsInstance(queue, RedisStreamTaskQueue)

    def test_factory_returns_kafka_queue_when_selected(self) -> None:
        queue = create_task_queue(
            TaskOrchestratorSettings(
                queue_backend="kafka",
                kafka_bootstrap_servers="127.0.0.1:9092",
            )
        )
        self.assertIsInstance(queue, KafkaTaskQueue)

    def test_factory_rejects_unknown_backend(self) -> None:
        with self.assertRaises(PlatformError):
            create_task_queue(TaskOrchestratorSettings(queue_backend="unknown"))
