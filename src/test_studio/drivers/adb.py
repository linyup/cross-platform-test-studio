from __future__ import annotations

import base64
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

from ..driver import Driver, Evidence
from ..models import Assertion, FlowStep, Selector


class AdbDriver(Driver):
    name = "adb"

    def __init__(self, serial: str, package: str | None = None, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        self.serial = serial
        self.package = package
        self._runner = runner

    def _adb(self, *args: str, binary: bool = False):
        return self._runner(
            ["adb", "-s", self.serial, *args],
            check=True,
            capture_output=True,
            text=not binary,
        ).stdout

    def _hierarchy(self) -> ET.Element:
        self._adb("shell", "uiautomator", "dump", "/sdcard/window.xml")
        xml = self._adb("shell", "cat", "/sdcard/window.xml")
        return ET.fromstring(xml)

    @staticmethod
    def _center(bounds: str) -> tuple[int, int]:
        values = [int(value) for value in bounds.replace("][", ",").strip("[]").split(",")]
        return (values[0] + values[2]) // 2, (values[1] + values[3]) // 2

    def _node(self, selector: Selector) -> ET.Element:
        for candidate in (selector, *selector.alternatives):
            attribute = {"test_id": "resource-id", "accessibility": "content-desc", "text": "text"}.get(candidate.strategy)
            if not attribute:
                continue
            for node in self._hierarchy().iter("node"):
                if node.attrib.get(attribute) == candidate.value:
                    return node
        raise LookupError(f"element not found: {selector}")

    def resolve(self, selector: Selector) -> str:
        return self._node(selector).attrib.get("bounds", "")

    def status(self) -> dict[str, Any]:
        state = str(self._adb("get-state")).strip()
        return {"ready": state == "device", "driver": self.name, "serial": self.serial}

    def inspect(self, goal: str = "") -> dict[str, Any]:
        elements = []
        for node in self._hierarchy().iter("node"):
            attrs = node.attrib
            if attrs.get("text") or attrs.get("content-desc") or attrs.get("resource-id"):
                elements.append({key: attrs.get(key, "") for key in ("text", "content-desc", "resource-id", "class", "bounds", "clickable")})
        return {"driver": self.name, "goal": goal, "elements": elements[:300], "warnings": []}

    def snapshot(self, include_image: bool = False) -> dict[str, Any]:
        payload = super().snapshot(False)
        if include_image:
            image = self._adb("exec-out", "screencap", "-p", binary=True)
            payload["image_base64"] = base64.b64encode(image).decode("ascii")
            payload["image_included"] = True
        return payload

    def perform(self, step: FlowStep, variables: dict[str, Any]) -> None:
        if step.action == "launch":
            if not self.package:
                raise ValueError("package is required for launch")
            self._adb("shell", "monkey", "-p", self.package, "1")
        elif step.action == "stop":
            if self.package:
                self._adb("shell", "am", "force-stop", self.package)
        elif step.action == "back":
            self._adb("shell", "input", "keyevent", "4")
        elif step.action == "wait" or step.action == "screenshot":
            return
        elif step.action == "swipe":
            points = step.input or [500, 1500, 500, 500, 300]
            self._adb("shell", "input", "swipe", *[str(value) for value in points])
        else:
            if not step.selector:
                raise ValueError(f"{step.action} requires a selector")
            x, y = self._center(self._node(step.selector).attrib["bounds"])
            self._adb("shell", "input", "tap", str(x), str(y))
            if step.action == "type":
                escaped = str(step.input or "").replace(" ", "%s")
                self._adb("shell", "input", "text", escaped)

    def assert_that(self, assertion: Assertion, variables: dict[str, Any]) -> None:
        try:
            node = self._node(assertion.selector) if assertion.selector else None
        except LookupError:
            if assertion.kind == "not_exists":
                return
            raise
        if assertion.kind == "not_exists":
            raise AssertionError("element exists")
        if assertion.kind == "text_equals" and node.attrib.get("text") != assertion.expected:
            raise AssertionError(f"text differs: {node.attrib.get('text')!r}")
        if assertion.kind == "text_contains" and str(assertion.expected) not in node.attrib.get("text", ""):
            raise AssertionError("text does not contain expected value")
        if assertion.kind == "value_equals" and node.attrib.get("text") != assertion.expected:
            raise AssertionError("value differs")

    def capture_failure(self, directory: Path, step: FlowStep, error: Exception) -> list[Evidence]:
        directory.mkdir(parents=True, exist_ok=True)
        screenshot = directory / f"{step.id}.png"
        hierarchy = directory / f"{step.id}.xml"
        screenshot.write_bytes(self._adb("exec-out", "screencap", "-p", binary=True))
        self._adb("shell", "uiautomator", "dump", "/sdcard/window.xml")
        hierarchy.write_text(self._adb("shell", "cat", "/sdcard/window.xml"), encoding="utf-8")
        return [Evidence("screenshot", str(screenshot)), Evidence("hierarchy", str(hierarchy))]
