import unittest

from test_studio.exploration import ExplorationSession, ToolCommand
from test_studio.models import Selector
from test_studio.simulated import SimulatedDriver


class ExplorationTests(unittest.TestCase):
    def test_trace_compiles_only_successful_steps(self):
        session = ExplorationSession(SimulatedDriver(), "desktop")
        session.perform(ToolCommand("launch", "Launch"))
        session.perform(ToolCommand("tap", "Save", Selector("test_id", "save"), idempotency_key="save"))
        session.perform(ToolCommand("tap", "Missing", Selector("text", "missing")))
        flow = session.compile_draft("draft", "Draft", cleanup_declared=True)
        self.assertEqual(["launch", "tap"], [step.action for step in flow.steps])
        self.assertIn("needs-review", flow.tags)

    def test_side_effect_is_idempotent_and_requires_cleanup(self):
        session = ExplorationSession(SimulatedDriver(), "desktop")
        session.perform(ToolCommand("launch", "Launch"))
        command = ToolCommand("tap", "Save", Selector("test_id", "save"), idempotency_key="save")
        first = session.perform(command)
        self.assertIs(first, session.perform(command))
        with self.assertRaisesRegex(ValueError, "cleanup"):
            session.compile_draft("draft", "Draft")


if __name__ == "__main__":
    unittest.main()
