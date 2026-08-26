from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_ACTIONS = {"launch", "stop", "tap", "type", "wait", "swipe", "back", "screenshot"}
SUPPORTED_ASSERTIONS = {"exists", "not_exists", "text_equals", "text_contains", "value_equals"}
SUPPORTED_STRATEGIES = {"test_id", "accessibility", "role", "text", "css", "xpath", "ocr", "image"}


@dataclass(frozen=True)
class Selector:
    strategy: str
    value: str
    alternatives: tuple["Selector", ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Selector":
        return cls(
            strategy=str(value["strategy"]),
            value=str(value["value"]),
            alternatives=tuple(cls.from_dict(item) for item in value.get("alternatives", [])),
        )


@dataclass(frozen=True)
class Assertion:
    kind: str
    selector: Selector | None = None
    expected: Any = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Assertion":
        selector = Selector.from_dict(value["selector"]) if value.get("selector") else None
        return cls(kind=str(value["kind"]), selector=selector, expected=value.get("expected"))


@dataclass(frozen=True)
class FlowStep:
    id: str
    title: str
    action: str
    selector: Selector | None = None
    input: Any = None
    timeout_ms: int = 10_000
    assertions: tuple[Assertion, ...] = ()
    continue_on_failure: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FlowStep":
        selector = Selector.from_dict(value["selector"]) if value.get("selector") else None
        return cls(
            id=str(value["id"]),
            title=str(value["title"]),
            action=str(value["action"]),
            selector=selector,
            input=value.get("input"),
            timeout_ms=int(value.get("timeout_ms", 10_000)),
            assertions=tuple(Assertion.from_dict(item) for item in value.get("assertions", [])),
            continue_on_failure=bool(value.get("continue_on_failure", False)),
        )


@dataclass(frozen=True)
class Flow:
    schema_version: int
    id: str
    title: str
    platform: str
    steps: tuple[FlowStep, ...]
    tags: tuple[str, ...] = ()
    variables: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Flow":
        return cls(
            schema_version=int(value["schema_version"]),
            id=str(value["id"]),
            title=str(value["title"]),
            platform=str(value.get("platform", "any")),
            steps=tuple(FlowStep.from_dict(item) for item in value.get("steps", [])),
            tags=tuple(str(item) for item in value.get("tags", [])),
            variables=dict(value.get("variables", {})),
        )


def validate_flow(flow: Flow) -> list[str]:
    errors: list[str] = []
    if flow.schema_version != 1:
        errors.append("schema_version must be 1")
    if not flow.id or not flow.title:
        errors.append("flow id and title are required")
    if not flow.steps:
        errors.append("flow requires at least one step")
    seen: set[str] = set()
    for index, step in enumerate(flow.steps):
        prefix = f"steps[{index}]"
        if step.id in seen:
            errors.append(f"{prefix}.id is duplicated")
        seen.add(step.id)
        if step.action not in SUPPORTED_ACTIONS:
            errors.append(f"{prefix}.action is unsupported: {step.action}")
        if step.timeout_ms <= 0:
            errors.append(f"{prefix}.timeout_ms must be positive")
        selectors = [step.selector] if step.selector else []
        selectors.extend(assertion.selector for assertion in step.assertions if assertion.selector)
        for selector in selectors:
            assert selector is not None
            for candidate in (selector, *selector.alternatives):
                if candidate.strategy not in SUPPORTED_STRATEGIES:
                    errors.append(f"{prefix} selector strategy is unsupported: {candidate.strategy}")
        for assertion in step.assertions:
            if assertion.kind not in SUPPORTED_ASSERTIONS:
                errors.append(f"{prefix} assertion is unsupported: {assertion.kind}")
    return errors

