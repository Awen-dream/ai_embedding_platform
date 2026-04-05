import unittest

from embedding_task_orchestrator.state_machine import can_transition, public_status


class TaskStateMachineTest(unittest.TestCase):
    def test_can_transition_from_accepted_to_queued(self) -> None:
        self.assertTrue(can_transition("accepted", "queued"))

    def test_public_status_maps_internal_running_states(self) -> None:
        self.assertEqual(public_status("embedding"), "running")
