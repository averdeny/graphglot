"""Data models for openCypher TCK test scenarios."""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from enum import Enum, auto


class ExpectedOutcome(Enum):
    """Expected outcome of a TCK scenario."""

    RESULT = auto()
    """Positive scenario — query should produce a result."""
    RESULT_EMPTY = auto()
    """Positive scenario — query should produce an empty result."""
    ERROR_COMPILE = auto()
    """Negative scenario — query should fail at compile time."""
    ERROR_RUNTIME = auto()
    """Negative scenario — query should fail at runtime."""
    ERROR_ANYTIME = auto()
    """Negative scenario — query should fail at compile or runtime."""

    @property
    def is_positive(self) -> bool:
        return self in (ExpectedOutcome.RESULT, ExpectedOutcome.RESULT_EMPTY)

    @property
    def is_compile_time_error(self) -> bool:
        return self == ExpectedOutcome.ERROR_COMPILE

    @property
    def is_runtime_error(self) -> bool:
        return self == ExpectedOutcome.ERROR_RUNTIME


_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


@dataclass(frozen=True)
class TckScenario:
    """A single TCK test scenario (possibly expanded from a Scenario Outline)."""

    feature_name: str
    scenario_name: str
    scenario_number: int
    tags: tuple[str, ...]
    query: str
    setup_queries: tuple[str, ...]
    outcome: ExpectedOutcome
    error_type: str | None
    error_detail: str | None
    source_file: str
    outline_row: int | None = None

    @property
    def test_id(self) -> str:
        """Generate a unique test ID for pytest parametrize."""
        # Extract feature base name: "Match1 - Match nodes" → "Match1"
        feature_slug = self.feature_name.split(" - ")[0].split(" ")[0]
        # Slug the scenario name
        name_slug = _SLUG_RE.sub("_", self.scenario_name).strip("_")
        # Truncate to keep IDs readable
        if len(name_slug) > 60:
            name_slug = name_slug[:60].rstrip("_")
        base = f"{feature_slug}__{self.scenario_number}_{name_slug}"
        if self.outline_row is not None:
            base = f"{base}__row{self.outline_row}"
        return base

    @property
    def is_positive(self) -> bool:
        return self.outcome.is_positive

    @property
    def is_compile_time_error(self) -> bool:
        return self.outcome.is_compile_time_error

    @property
    def is_runtime_error(self) -> bool:
        return self.outcome.is_runtime_error


@dataclass
class FeatureFile:
    """A parsed TCK .feature file."""

    path: str
    feature_name: str
    scenarios: list[TckScenario] = field(default_factory=list)
