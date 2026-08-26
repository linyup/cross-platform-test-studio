from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from test_studio.models import Flow, validate_flow
from test_studio.runner import FlowRunner
from test_studio.simulated import SimulatedDriver


ROOT = Path(__file__).resolve().parents[1]


class FlowRunnerTests(unittest.TestCase):
    def load_demo(self) -> Flow:
        payload = json.loads((ROOT / "examples/create-note.flow.json").read_text())
        return Flow.from_dict(payload)

    def test_demo_flow_is_valid(self):
        self.assertEqual([], validate_flow(self.load_demo()))

    def test_demo_flow_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = FlowRunner(SimulatedDriver(), Path(directory)).run(self.load_demo())
        self.assertEqual("passed", result.status)
        self.assertEqual(3, len(result.steps))

    def test_failure_stops_and_captures_evidence(self):
        payload = json.loads((ROOT / "examples/create-note.flow.json").read_text())
        payload["steps"][1]["selector"]["value"] = "missing"
        payload["steps"][1]["selector"]["alternatives"] = []
        with tempfile.TemporaryDirectory() as directory:
            result = FlowRunner(SimulatedDriver(), Path(directory)).run(Flow.from_dict(payload))
            self.assertEqual("failed", result.status)
            self.assertEqual(2, len(result.steps))
            self.assertEqual("state", result.steps[-1].evidence[0].kind)
            self.assertTrue(Path(result.steps[-1].evidence[0].path).exists())


if __name__ == "__main__":
    unittest.main()

