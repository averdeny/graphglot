"""Fixtures and scenario collection for TCK tests."""

from __future__ import annotations

from tests.graphglot.tck.loader import load_all_scenarios
from tests.graphglot.tck.models import ExpectedOutcome

# Collect all scenarios at import time for parametrize
_ALL_SCENARIOS = load_all_scenarios()

PARSE_SCENARIOS = _ALL_SCENARIOS

POSITIVE_SCENARIOS = [s for s in _ALL_SCENARIOS if s.is_positive]

RUNTIME_ERROR_SCENARIOS = [s for s in _ALL_SCENARIOS if s.is_runtime_error]

ERROR_COMPILE_SCENARIOS = [s for s in _ALL_SCENARIOS if s.is_compile_time_error]

ERROR_ANYTIME_SCENARIOS = [s for s in _ALL_SCENARIOS if s.outcome == ExpectedOutcome.ERROR_ANYTIME]
