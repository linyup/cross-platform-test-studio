from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .exploration import ExplorationSession, ToolCommand
from .models import Assertion, FlowStep, Selector


def _selector(value: dict[str, Any] | None) -> Selector | None:
    return Selector.from_dict(value) if value else None


def _assertion(value: dict[str, Any] | None) -> Assertion | None:
    return Assertion.from_dict(value) if value else None


def create_mcp_server(driver):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:
        raise RuntimeError("install the MCP extra: pip install 'cross-platform-test-studio[mcp]'") from error

    server = FastMCP("cross-platform-test-studio")
    traces: dict[str, ExplorationSession] = {}

    def trace_or_error(trace_id: str):
        return traces.get(trace_id)

    @server.tool(name="test_get_status")
    def get_status() -> dict[str, Any]:
        return driver.status()

    @server.tool(name="test_inspect")
    def inspect(goal: str = "") -> dict[str, Any]:
        return driver.inspect(goal)

    @server.tool(name="test_snapshot")
    def snapshot(include_image: bool = False) -> dict[str, Any]:
        return driver.snapshot(include_image)

    @server.tool(name="test_compare_state")
    def compare_state(page_fingerprint: str) -> dict[str, Any]:
        return driver.compare_state(page_fingerprint)

    @server.tool(name="test_create_trace")
    def create_trace(platform: str = "any") -> dict[str, Any]:
        trace = ExplorationSession(driver, platform)
        traces[trace.id] = trace
        return {"success": True, "trace_id": trace.id, "platform": platform}

    @server.tool(name="test_perform")
    def perform(trace_id: str, action: str, title: str, selector: dict[str, Any] | None = None, value: Any = None, assertion: dict[str, Any] | None = None, idempotency_key: str = "") -> dict[str, Any]:
        trace = trace_or_error(trace_id)
        if trace is None:
            return {"success": False, "code": "TRACE_NOT_FOUND"}
        try:
            result = trace.perform(ToolCommand(action, title, _selector(selector), value, _assertion(assertion), idempotency_key or None))
        except ValueError as error:
            return {"success": False, "code": "TRACE_CLOSED", "message": str(error)}
        return {"success": result.ok, **asdict(result)}

    @server.tool(name="test_assert")
    def assert_state(trace_id: str, title: str, assertion: dict[str, Any]) -> dict[str, Any]:
        trace = trace_or_error(trace_id)
        if trace is None:
            return {"success": False, "code": "TRACE_NOT_FOUND"}
        parsed = _assertion(assertion)
        assert parsed is not None
        started = ToolCommand("wait", title, assertion=parsed)
        try:
            result = trace.perform(started)
        except ValueError as error:
            return {"success": False, "code": "TRACE_CLOSED", "message": str(error)}
        return {"success": result.ok, **asdict(result)}

    @server.tool(name="test_run_journey")
    def run_journey(trace_id: str, steps: list[dict[str, Any]], authorize_side_effects: bool = False, idempotency_key: str = "") -> dict[str, Any]:
        trace = trace_or_error(trace_id)
        if trace is None:
            return {"success": False, "code": "TRACE_NOT_FOUND"}
        if any(step.get("action") in {"tap", "type"} for step in steps) and not authorize_side_effects:
            return {"success": False, "code": "SIDE_EFFECT_NOT_AUTHORIZED"}
        results = []
        start = len(trace.steps)
        for index, step in enumerate(steps):
            try:
                result = trace.perform(ToolCommand(
                    str(step["action"]), str(step.get("title") or step["action"]), _selector(step.get("selector")),
                    step.get("value"), _assertion(step.get("assertion")),
                    f"{idempotency_key}:{index}" if idempotency_key else None,
                ))
            except ValueError as error:
                return {"success": False, "code": "TRACE_CLOSED", "message": str(error), "results": results}
            results.append(asdict(result))
            if not result.ok:
                for trace_step in trace.steps[start:]:
                    trace_step.discarded = True
                break
        return {"success": bool(results) and all(item["ok"] for item in results), "results": results}

    @server.tool(name="test_get_trace")
    def get_trace(trace_id: str) -> dict[str, Any]:
        trace = trace_or_error(trace_id)
        return {"success": False, "code": "TRACE_NOT_FOUND"} if trace is None else {"success": True, "trace_id": trace.id, "status": trace.status, "events": trace.events()}

    @server.tool(name="test_complete_trace")
    def complete_trace(trace_id: str, status: str = "completed") -> dict[str, Any]:
        trace = trace_or_error(trace_id)
        if trace is None:
            return {"success": False, "code": "TRACE_NOT_FOUND"}
        try:
            trace.complete(status)
        except ValueError as error:
            return {"success": False, "code": "INVALID_ARGUMENT", "message": str(error)}
        return {"success": True, "trace_id": trace.id, "status": trace.status}

    @server.tool(name="test_discard_trace_step")
    def discard_trace_step(trace_id: str, index: int) -> dict[str, Any]:
        trace = trace_or_error(trace_id)
        if trace is None:
            return {"success": False, "code": "TRACE_NOT_FOUND"}
        try:
            trace.discard(index)
        except IndexError:
            return {"success": False, "code": "STEP_NOT_FOUND"}
        except ValueError as error:
            return {"success": False, "code": "TRACE_CLOSED", "message": str(error)}
        return {"success": True, "index": index}

    @server.tool(name="test_compile_flow_draft")
    def compile_flow_draft(trace_id: str, flow_id: str, title: str, cleanup_declared: bool = False) -> dict[str, Any]:
        trace = trace_or_error(trace_id)
        if trace is None:
            return {"success": False, "code": "TRACE_NOT_FOUND"}
        try:
            return {"success": True, "flow": trace.draft_payload(flow_id, title, cleanup_declared)}
        except ValueError as error:
            return {"success": False, "code": "PROMOTION_GATE", "message": str(error)}

    return server
