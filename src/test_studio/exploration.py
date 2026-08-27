from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from .driver import Driver
from .models import Assertion, Flow, FlowStep, Selector, validate_flow

SIDE_EFFECT_ACTIONS = {"tap", "type"}


@dataclass(frozen=True)
class ToolCommand:
    action: str
    title: str
    selector: Selector | None = None
    input: Any = None
    assertion: Assertion | None = None
    idempotency_key: str | None = None


@dataclass
class ToolResult:
    command_id: str
    ok: bool
    command_success: bool
    evidence_success: bool
    state_changed: bool | None
    assertion_passed: bool | None
    duration_ms: int
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    page_fingerprint_before: str = ""
    page_fingerprint_after: str = ""


@dataclass
class TraceStep:
    command: ToolCommand
    result: ToolResult
    discarded: bool = False


class ExplorationSession:
    """Reviewable exploration that never mutates a committed Flow automatically."""

    def __init__(self, driver: Driver, platform: str, session_id: str | None = None) -> None:
        self.driver = driver
        self.platform = platform
        self.id = session_id or str(uuid.uuid4())
        self.steps: list[TraceStep] = []
        self._effects: dict[str, ToolResult] = {}
        self.status = "active"

    def perform(self, command: ToolCommand) -> ToolResult:
        if self.status != "active":
            raise ValueError(f"trace is {self.status} and cannot accept new steps")
        if command.action in SIDE_EFFECT_ACTIONS and command.idempotency_key and command.idempotency_key in self._effects:
            return self._effects[command.idempotency_key]
        started = time.monotonic()
        before = self.driver.snapshot(False)["page_fingerprint"]
        step = FlowStep(f"draft-{len(self.steps) + 1}", command.title, command.action, command.selector, command.input)
        try:
            self.driver.perform(step, {})
            assertion_passed = None
            if command.assertion:
                self.driver.assert_that(command.assertion, {})
                assertion_passed = True
            after = self.driver.snapshot(False)["page_fingerprint"]
            result = ToolResult(str(uuid.uuid4()), True, True, True, before != after, assertion_passed, int((time.monotonic() - started) * 1000), page_fingerprint_before=before, page_fingerprint_after=after)
        except Exception as error:
            result = ToolResult(str(uuid.uuid4()), False, False, False, None, False if command.assertion else None, int((time.monotonic() - started) * 1000), f"{type(error).__name__}: {error}", page_fingerprint_before=before)
        self.steps.append(TraceStep(command, result))
        if command.action in SIDE_EFFECT_ACTIONS and command.idempotency_key and result.command_success:
            self._effects[command.idempotency_key] = result
        return result

    def discard(self, index: int) -> None:
        if self.status != "active":
            raise ValueError(f"trace is {self.status} and cannot be edited")
        if index < 0 or index >= len(self.steps):
            raise IndexError(index)
        self.steps[index].discarded = True

    def complete(self, status: str = "completed") -> None:
        if status not in {"completed", "discarded"}:
            raise ValueError("trace status must be completed or discarded")
        self.status = status

    def events(self) -> list[dict[str, Any]]:
        return [{"index": index, "command": asdict(item.command), "result": asdict(item.result), "discarded": item.discarded} for index, item in enumerate(self.steps)]

    def compile_draft(self, flow_id: str, title: str, cleanup_declared: bool = False) -> Flow:
        included = [item for item in self.steps if not item.discarded and item.result.ok]
        if any(item.command.action in SIDE_EFFECT_ACTIONS for item in included) and not cleanup_declared:
            raise ValueError("side-effecting drafts require an explicit cleanup declaration")
        steps = tuple(FlowStep(f"step-{index + 1}", item.command.title, item.command.action, item.command.selector, item.command.input, assertions=(item.command.assertion,) if item.command.assertion else ()) for index, item in enumerate(included))
        flow = Flow(1, flow_id, title, self.platform, steps, tags=("draft", "needs-review"))
        errors = validate_flow(flow)
        if errors:
            raise ValueError("; ".join(errors))
        return flow

    def draft_payload(self, flow_id: str, title: str, cleanup_declared: bool = False) -> dict[str, Any]:
        flow = self.compile_draft(flow_id, title, cleanup_declared)
        payload = asdict(flow)
        payload["metadata"] = {"trace_id": self.id, "cleanup_declared": cleanup_declared}
        return payload
