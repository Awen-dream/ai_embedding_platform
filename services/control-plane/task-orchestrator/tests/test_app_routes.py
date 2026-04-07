import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from embedding_task_orchestrator.app import create_app
from embedding_task_orchestrator.config import TaskOrchestratorSettings


class TaskOrchestratorAppRoutesTest(unittest.TestCase):
    def test_queue_stats_exposes_backend_semantics(self) -> None:
        settings = TaskOrchestratorSettings()

        with patch("embedding_task_orchestrator.app.load_settings", return_value=settings):
            app = create_app()

        with TestClient(app) as client:
            response = client.get("/internal/queue/stats")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["queue_backend"], "inmemory")
        self.assertEqual(body["delivery_semantics"], "at_least_once")
        self.assertEqual(body["queue_depth_mode"], "exact")
        self.assertEqual(body["dead_letter_count_mode"], "exact")
        self.assertIn("worker_running", body)
