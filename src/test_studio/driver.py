from __future__ import annotations

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

