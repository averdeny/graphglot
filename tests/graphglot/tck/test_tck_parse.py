"""TCK parse tests — verify that the Neo4j dialect can parse each TCK query.

Tests all 3897 TCK scenarios (positive + error + runtime).  100% pass rate.
xfails are tracked in xfails.py (XFAIL_PARSE — currently empty).

This suite tests *parsing only*.  Round-trip and error-detection are
tested separately in test_tck_roundtrip.py and test_tck_errors.py.
"""

from __future__ import annotations

import pytest

from graphglot.dialect.neo4j import Neo4j
from graphglot.error import GraphGlotError
from tests.graphglot.tck.conftest import PARSE_SCENARIOS
from tests.graphglot.tck.models import TckScenario
from tests.graphglot.tck.xfails import should_xfail_parse

_neo4j = Neo4j()


@pytest.mark.tck
@pytest.mark.timeout(5)
@pytest.mark.parametrize(
    "scenario",
    PARSE_SCENARIOS,
    ids=lambda s: s.test_id,
)
def test_tck_parse(scenario: TckScenario):
    """Parse each TCK query with the Neo4j dialect."""
    xfail = should_xfail_parse(scenario.test_id, scenario.query)
    if xfail:
        pytest.xfail(f"[{xfail.category.name}] {xfail.reason}")

    try:
        result = _neo4j.parse(scenario.query)
    except GraphGlotError:
        if scenario.is_compile_time_error:
            return
        raise

    if scenario.is_positive or scenario.is_runtime_error:
        assert result is not None, f"Parse returned None for: {scenario.query}"
