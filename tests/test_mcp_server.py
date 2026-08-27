import sys
import types
import unittest

from test_studio.mcp_server import create_mcp_server
from test_studio.simulated import SimulatedDriver


class FakeFastMCP:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, name):
        def register(function):
            self.tools[name] = function
            return function
        return register


class McpServerTests(unittest.TestCase):
    def setUp(self):
        self.previous = {name: sys.modules.get(name) for name in ("mcp", "mcp.server", "mcp.server.fastmcp")}
        sys.modules["mcp"] = types.ModuleType("mcp")
        sys.modules["mcp.server"] = types.ModuleType("mcp.server")
        module = types.ModuleType("mcp.server.fastmcp")
        module.FastMCP = FakeFastMCP
        sys.modules["mcp.server.fastmcp"] = module

    def tearDown(self):
        for name, value in self.previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

    def test_tools_cover_inspect_journey_trace_and_compile(self):
        server = create_mcp_server(SimulatedDriver())
        self.assertEqual(
            {"test_get_status", "test_inspect", "test_snapshot", "test_compare_state", "test_create_trace", "test_perform", "test_assert", "test_run_journey", "test_get_trace", "test_complete_trace", "test_discard_trace_step", "test_compile_flow_draft"},
            set(server.tools),
        )
        trace_id = server.tools["test_create_trace"]("desktop")["trace_id"]
        self.assertTrue(server.tools["test_perform"](trace_id, "launch", "Launch")["success"])
        journey = server.tools["test_run_journey"](
            trace_id,
            [{"action": "tap", "title": "Save", "selector": {"strategy": "test_id", "value": "save"}}],
            authorize_side_effects=True,
            idempotency_key="save-once",
        )
        self.assertTrue(journey["success"])
        draft = server.tools["test_compile_flow_draft"](trace_id, "draft-note", "Create note", True)
        self.assertTrue(draft["success"])
        self.assertTrue(draft["flow"]["metadata"]["cleanup_declared"])
        self.assertEqual("completed", server.tools["test_complete_trace"](trace_id)["status"])
        closed = server.tools["test_perform"](trace_id, "wait", "Too late")
        self.assertEqual("TRACE_CLOSED", closed["code"])

    def test_failed_journey_discards_provisional_steps(self):
        server = create_mcp_server(SimulatedDriver())
        trace_id = server.tools["test_create_trace"]("desktop")["trace_id"]
        server.tools["test_perform"](trace_id, "launch", "Launch")
        result = server.tools["test_run_journey"](
            trace_id,
            [{"action": "tap", "title": "Missing", "selector": {"strategy": "text", "value": "missing"}}],
            authorize_side_effects=True,
        )
        self.assertFalse(result["success"])
        events = server.tools["test_get_trace"](trace_id)["events"]
        self.assertTrue(events[-1]["discarded"])

    def test_snapshot_fingerprint_and_invalid_discard(self):
        server = create_mcp_server(SimulatedDriver())
        snapshot = server.tools["test_snapshot"]()
        self.assertTrue(snapshot["page_fingerprint"])
        self.assertFalse(server.tools["test_compare_state"](snapshot["page_fingerprint"])["changed"])
        trace_id = server.tools["test_create_trace"]("mobile")["trace_id"]
        self.assertEqual("STEP_NOT_FOUND", server.tools["test_discard_trace_step"](trace_id, -1)["code"])


if __name__ == "__main__":
    unittest.main()
