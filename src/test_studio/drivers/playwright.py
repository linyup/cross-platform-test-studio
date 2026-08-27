from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from ..driver import Driver, Evidence
from ..models import Assertion, FlowStep, Selector


class PlaywrightDriver(Driver):
    name = "playwright"

    def __init__(self, base_url: str, headless: bool = True, cdp_url: str | None = None) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError("install the desktop extra: pip install '.[desktop]' && playwright install chromium") from error
        self.base_url = base_url
        self._runtime = sync_playwright().start()
        self._cdp_url = cdp_url
        self._browser = self._runtime.chromium.connect_over_cdp(cdp_url) if cdp_url else self._runtime.chromium.launch(headless=headless)
        self.page = self._select_page() if cdp_url else self._browser.new_page()

    def _select_page(self):
        pages = [page for context in self._browser.contexts for page in context.pages if not page.is_closed()]
        if not pages:
            raise RuntimeError("CDP connected but no live page is available")
        return max(pages, key=lambda page: len(page.url or ""))

    def _active_page(self):
        if self.page.is_closed():
            self.page = self._select_page()
        return self.page

    def close(self) -> None:
        if not self._cdp_url:
            self._browser.close()
        self._runtime.stop()

    def _locator(self, selector: Selector):
        failures: list[str] = []
        for candidate in (selector, *selector.alternatives):
            try:
                if candidate.strategy == "test_id":
                    locator = self._active_page().get_by_test_id(candidate.value)
                elif candidate.strategy == "role":
                    locator = self._active_page().get_by_role(candidate.value)
                elif candidate.strategy == "text":
                    locator = self._active_page().get_by_text(candidate.value, exact=True)
                elif candidate.strategy == "css":
                    locator = self._active_page().locator(candidate.value)
                elif candidate.strategy == "xpath":
                    locator = self._active_page().locator(f"xpath={candidate.value}")
                elif candidate.strategy == "accessibility":
                    locator = self._active_page().get_by_label(candidate.value)
                else:
                    failures.append(f"unsupported by Playwright: {candidate.strategy}")
                    continue
                for index in range(locator.count()):
                    match = locator.nth(index)
                    if match.is_visible():
                        return match
            except Exception as error:
                failures.append(str(error))
        raise LookupError(f"no selector matched: {selector}; failures={failures}")

    def resolve(self, selector: Selector) -> str:
        return str(self._locator(selector))

    def status(self) -> dict[str, Any]:
        page = self._active_page()
        return {"ready": True, "driver": self.name, "url": page.url, "cdp": bool(self._cdp_url)}

    def inspect(self, goal: str = "") -> dict[str, Any]:
        elements = self._active_page().locator("button, input, textarea, select, a, [role], [data-testid]").evaluate_all(
            """nodes => nodes.filter(n => { const r=n.getBoundingClientRect(); return r.width>0 && r.height>0; }).slice(0,200).map(n => ({
              tag:n.tagName.toLowerCase(), role:n.getAttribute('role')||'', test_id:n.getAttribute('data-testid')||'',
              label:n.getAttribute('aria-label')||'', text:(n.innerText||n.value||'').trim().slice(0,160)
            }))"""
        )
        return {"driver": self.name, "goal": goal, "url": self._active_page().url, "elements": elements, "warnings": []}

    def snapshot(self, include_image: bool = False) -> dict[str, Any]:
        page = self._active_page()
        inspection = self.inspect()
        try:
            visible_text = " ".join(page.locator("body").inner_text(timeout=3000).split())[:50_000]
        except Exception:
            visible_text = ""
        state = {
            "url": page.url,
            "title": page.title(),
            "visible_text": visible_text,
            "elements": inspection.get("elements", []),
        }
        fingerprint = hashlib.sha256(
            json.dumps(state, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:20]
        payload = {
            **inspection,
            "page_fingerprint": fingerprint,
            "image_base64": None,
            "image_included": False,
        }
        if include_image:
            payload["image_base64"] = base64.b64encode(page.screenshot()).decode("ascii")
            payload["image_included"] = True
        return payload

    def perform(self, step: FlowStep, variables: dict[str, Any]) -> None:
        if step.action == "launch":
            self.page.goto(str(step.input or self.base_url), wait_until="domcontentloaded")
        elif step.action == "stop":
            self.page.goto("about:blank")
        elif step.action == "wait":
            self.page.wait_for_timeout(int(step.input or 250))
        elif step.action == "back":
            self.page.go_back()
        elif step.action == "screenshot":
            return
        elif step.action == "swipe":
            delta = step.input if isinstance(step.input, dict) else {"x": 0, "y": 500}
            self.page.mouse.wheel(float(delta.get("x", 0)), float(delta.get("y", 500)))
        else:
            if not step.selector:
                raise ValueError(f"{step.action} requires a selector")
            locator = self._locator(step.selector)
            if step.action == "tap":
                locator.click(timeout=step.timeout_ms)
            elif step.action == "type":
                locator.fill(str(step.input or ""), timeout=step.timeout_ms)

    def assert_that(self, assertion: Assertion, variables: dict[str, Any]) -> None:
        if not assertion.selector:
            raise ValueError(f"{assertion.kind} requires a selector")
        try:
            locator = self._locator(assertion.selector)
        except LookupError:
            if assertion.kind == "not_exists":
                return
            raise
        if assertion.kind == "exists" and not locator.is_visible():
            raise AssertionError("element is not visible")
        if assertion.kind == "not_exists" and locator.is_visible():
            raise AssertionError("element is visible")
        if assertion.kind == "text_equals" and locator.inner_text() != assertion.expected:
            raise AssertionError(f"text differs: {locator.inner_text()!r}")
        if assertion.kind == "text_contains" and str(assertion.expected) not in locator.inner_text():
            raise AssertionError(f"text does not contain {assertion.expected!r}")
        if assertion.kind == "value_equals" and locator.input_value() != assertion.expected:
            raise AssertionError(f"value differs: {locator.input_value()!r}")

    def capture_failure(self, directory: Path, step: FlowStep, error: Exception) -> list[Evidence]:
        directory.mkdir(parents=True, exist_ok=True)
        screenshot = directory / f"{step.id}.png"
        dom = directory / f"{step.id}.html"
        details = directory / f"{step.id}.json"
        self.page.screenshot(path=str(screenshot), full_page=True)
        dom.write_text(self.page.content(), encoding="utf-8")
        details.write_text(json.dumps({"error": f"{type(error).__name__}: {error}"}, indent=2), encoding="utf-8")
        return [Evidence("screenshot", str(screenshot)), Evidence("dom", str(dom)), Evidence("error", str(details))]
