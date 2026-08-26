from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .driver import Driver, Evidence
from .models import Flow, validate_flow


@dataclass
class StepResult:
    step_id: str
    title: str
    status: str
    duration_ms: int
    error: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class RunResult:
    flow_id: str
    title: str
    driver: str
    status: str
    started_at_epoch_ms: int
    duration_ms: int
    steps: list[StepResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FlowRunner:
    def __init__(self, driver: Driver, artifact_dir: Path) -> None:
        self.driver = driver
        self.artifact_dir = artifact_dir

    def run(self, flow: Flow) -> RunResult:
        errors = validate_flow(flow)
        if errors:
            raise ValueError("; ".join(errors))
        started_wall = int(time.time() * 1000)
        started = time.monotonic()
        results: list[StepResult] = []
        for step in flow.steps:
            step_started = time.monotonic()
            try:
                self.driver.perform(step, flow.variables)
                for assertion in step.assertions:
                    self.driver.assert_that(assertion, flow.variables)
                result = StepResult(step.id, step.title, "passed", int((time.monotonic() - step_started) * 1000))
            except Exception as error:  # Driver errors are converted into stable run results.
                evidence = self.driver.capture_failure(self.artifact_dir, step, error)
                result = StepResult(
                    step.id,
                    step.title,
                    "failed",
                    int((time.monotonic() - step_started) * 1000),
                    f"{type(error).__name__}: {error}",
                    evidence,
                )
            results.append(result)
            if result.status == "failed" and not step.continue_on_failure:
                break
        status = "passed" if len(results) == len(flow.steps) and all(item.status == "passed" for item in results) else "failed"
        return RunResult(
            flow_id=flow.id,
            title=flow.title,
            driver=self.driver.name,
            status=status,
            started_at_epoch_ms=started_wall,
            duration_ms=int((time.monotonic() - started) * 1000),
            steps=results,
        )

