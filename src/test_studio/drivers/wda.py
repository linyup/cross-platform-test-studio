from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from ..driver import Driver, Evidence
from ..models import Assertion, FlowStep, Selector


class WdaDriver(Driver):
    name = "wda"

    def __init__(self, base_url: str, bundle_id: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.bundle_id = bundle_id
        self.session_id: str | None = None

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"{}")

    def _session_path(self, suffix: str) -> str:
        if not self.session_id:
            raise RuntimeError("WDA session is not started")
        return f"/session/{self.session_id}{suffix}"

    def _element(self, selector: Selector) -> str:
        mappings = {"test_id": "accessibility id", "accessibility": "accessibility id", "text": "name", "xpath": "xpath"}
        for candidate in (selector, *selector.alternatives):
            using = mappings.get(candidate.strategy)
            if not using:
                continue
            try:
                value = self._request("POST", self._session_path("/element"), {"using": using, "value": candidate.value})["value"]
                return value.get("ELEMENT") or value.get("element-6066-11e4-a52e-4f735466cecf")
            except Exception:
                continue
        raise LookupError(f"element not found: {selector}")

    def resolve(self, selector: Selector) -> str:
        return self._element(selector)

    def perform(self, step: FlowStep, variables: dict[str, Any]) -> None:
        if step.action == "launch":
            response = self._request("POST", "/session", {"capabilities": {"alwaysMatch": {"bundleId": self.bundle_id}}})
            self.session_id = response.get("sessionId") or response.get("value", {}).get("sessionId")
        elif step.action == "stop":
            if self.session_id:
                self._request("DELETE", f"/session/{self.session_id}")
                self.session_id = None
        elif step.action == "back":
            self._request("POST", self._session_path("/wda/deactivateApp"), {"duration": 1})
        elif step.action in {"wait", "screenshot"}:
            return
        elif step.action == "swipe":
            self._request("POST", self._session_path("/wda/dragfromtoforduration"), step.input or {})
        else:
            if not step.selector:
                raise ValueError(f"{step.action} requires a selector")
            element = self._element(step.selector)
            if step.action == "tap":
                self._request("POST", self._session_path(f"/element/{element}/click"), {})
            elif step.action == "type":
                self._request("POST", self._session_path(f"/element/{element}/value"), {"value": list(str(step.input or ""))})

    def assert_that(self, assertion: Assertion, variables: dict[str, Any]) -> None:
        try:
            element = self._element(assertion.selector) if assertion.selector else None
        except LookupError:
            if assertion.kind == "not_exists":
                return
            raise
        if assertion.kind == "not_exists":
            raise AssertionError("element exists")
        if assertion.kind in {"text_equals", "text_contains", "value_equals"}:
            attribute = "value" if assertion.kind == "value_equals" else "label"
            actual = self._request("GET", self._session_path(f"/element/{element}/attribute/{attribute}"))["value"]
            if assertion.kind.endswith("equals") and actual != assertion.expected:
                raise AssertionError(f"value differs: {actual!r}")
            if assertion.kind == "text_contains" and str(assertion.expected) not in str(actual):
                raise AssertionError("text does not contain expected value")

    def capture_failure(self, directory: Path, step: FlowStep, error: Exception) -> list[Evidence]:
        import base64

        directory.mkdir(parents=True, exist_ok=True)
        screenshot = directory / f"{step.id}.png"
        source = directory / f"{step.id}.xml"
        screenshot.write_bytes(base64.b64decode(self._request("GET", self._session_path("/screenshot"))["value"]))
        source.write_text(str(self._request("GET", self._session_path("/source"))["value"]), encoding="utf-8")
        return [Evidence("screenshot", str(screenshot)), Evidence("hierarchy", str(source))]

