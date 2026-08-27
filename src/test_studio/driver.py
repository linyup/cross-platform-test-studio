from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Assertion, FlowStep, Selector


@dataclass(frozen=True)
class Evidence:
    kind: str
    path: str


class Driver(ABC):
    """Platform boundary implemented by desktop, Android, iOS or simulation adapters."""

    name = "abstract"

    def status(self) -> dict[str, Any]:
        return {"ready": True, "driver": self.name}

    def inspect(self, goal: str = "") -> dict[str, Any]:
        return {"driver": self.name, "goal": goal, "elements": [], "warnings": ["driver does not expose inspection"]}

    def snapshot(self, include_image: bool = False) -> dict[str, Any]:
        inspection = self.inspect()
        fingerprint = hashlib.sha256(json.dumps(inspection, sort_keys=True, default=str).encode()).hexdigest()[:20]
        return {**inspection, "page_fingerprint": fingerprint, "image_base64": None, "image_included": False}

    def compare_state(self, page_fingerprint: str) -> dict[str, Any]:
        current = self.snapshot(False)["page_fingerprint"]
        return {"previous": page_fingerprint, "current": current, "changed": current != page_fingerprint}

    @abstractmethod
    def perform(self, step: FlowStep, variables: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def assert_that(self, assertion: Assertion, variables: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def capture_failure(self, directory: Path, step: FlowStep, error: Exception) -> list[Evidence]:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, selector: Selector) -> str:
        """Return the resolved selector description, trying declared alternatives in order."""
        raise NotImplementedError
