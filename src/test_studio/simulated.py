from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .driver import Driver, Evidence
from .models import Assertion, FlowStep, Selector


class SimulatedDriver(Driver):
    """Deterministic adapter used for demos, CI and contract tests."""

    name = "simulated"

    def __init__(self) -> None:
        self.running = False
        self.elements: dict[str, dict[str, Any]] = {
            "new-note": {"exists": True, "text": "New note", "value": None},
            "title": {"exists": True, "text": "", "value": ""},
            "save": {"exists": True, "text": "Save", "value": None},
            "saved-status": {"exists": False, "text": "Saved", "value": None},
        }

    def resolve(self, selector: Selector) -> str:
        for candidate in (selector, *selector.alternatives):
            if candidate.value in self.elements:
                return candidate.value
        raise LookupError(f"element not found: {selector.strategy}={selector.value}")

    def perform(self, step: FlowStep, variables: dict[str, Any]) -> None:
        if step.action == "launch":
            self.running = True
            return
        if step.action == "stop":
            self.running = False
            return
        if not self.running:
            raise RuntimeError("application is not running")
        if step.action in {"wait", "screenshot", "back", "swipe"}:
            return
        if not step.selector:
            raise ValueError(f"{step.action} requires a selector")
        key = self.resolve(step.selector)
        if step.action == "type":
            self.elements[key]["value"] = step.input
            self.elements[key]["text"] = str(step.input)
        elif step.action == "tap" and key == "save":
            self.elements["saved-status"]["exists"] = True

    def assert_that(self, assertion: Assertion, variables: dict[str, Any]) -> None:
        if not assertion.selector:
            raise ValueError(f"{assertion.kind} requires a selector")
        key = self.resolve(assertion.selector)
        element = self.elements[key]
        checks = {
            "exists": bool(element["exists"]),
            "not_exists": not bool(element["exists"]),
            "text_equals": element["text"] == assertion.expected,
            "text_contains": str(assertion.expected) in str(element["text"]),
            "value_equals": element["value"] == assertion.expected,
        }
        if not checks[assertion.kind]:
            raise AssertionError(
                f"{assertion.kind} failed for {key}: expected={assertion.expected!r}, actual={element!r}"
            )

    def capture_failure(self, directory: Path, step: FlowStep, error: Exception) -> list[Evidence]:
        directory.mkdir(parents=True, exist_ok=True)
        state_path = directory / f"{step.id}-state.json"
        state_path.write_text(json.dumps(self.elements, indent=2), encoding="utf-8")
        return [Evidence(kind="state", path=str(state_path))]

