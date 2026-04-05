import unittest

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.config import TaskOrchestratorSettings
from embedding_task_orchestrator.internal.postgres_repository import PostgresTaskRepository
from embedding_task_orchestrator.internal.repository_factory import create_task_repository
from embedding_task_orchestrator.internal.sqlite_repository import SqliteTaskRepository
from embedding_task_orchestrator.internal.store import InMemoryTaskRepository


class RepositoryFactoryTest(unittest.TestCase):
    def test_factory_returns_inmemory_repository_by_default(self) -> None:
        repository = create_task_repository(TaskOrchestratorSettings())
        self.assertIsInstance(repository, InMemoryTaskRepository)

    def test_factory_returns_postgres_repository_when_selected(self) -> None:
        repository = create_task_repository(
            TaskOrchestratorSettings(
                repository_backend="postgres",
                postgres_dsn="postgresql://user:pass@localhost:5432/embedding",
            )
        )
        self.assertIsInstance(repository, PostgresTaskRepository)

    def test_factory_returns_sqlite_repository_when_selected(self) -> None:
        repository = create_task_repository(
            TaskOrchestratorSettings(
                repository_backend="sqlite",
                sqlite_path="/tmp/task-orchestrator-test.db",
            )
        )
        self.assertIsInstance(repository, SqliteTaskRepository)

    def test_factory_rejects_unknown_backend(self) -> None:
        with self.assertRaises(PlatformError):
            create_task_repository(TaskOrchestratorSettings(repository_backend="unknown"))
