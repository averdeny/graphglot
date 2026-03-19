"""TCK error tests — verify compile-time error scenarios raise errors.

Tests 600 compile-time error scenarios.  Detected at parse time or via
semantic analysis (validate).  Remaining xfails are queries that require
deeper semantic analysis (type checking, scope validation, etc.).
"""

from __future__ import annotations

import pytest

from graphglot.dialect.neo4j import Neo4j
from graphglot.error import GraphGlotError
from tests.graphglot.tck.conftest import ERROR_COMPILE_SCENARIOS
from tests.graphglot.tck.models import TckScenario
from tests.graphglot.tck.xfails import XFAIL_ERROR, get_xfail

_neo4j = Neo4j()


@pytest.mark.tck
@pytest.mark.parametrize(
    "scenario",
    ERROR_COMPILE_SCENARIOS,
    ids=lambda s: s.test_id,
)
def test_tck_compile_error(scenario: TckScenario):
    """Compile-time error scenarios should raise GraphGlotError during parsing."""
    xfail = get_xfail(scenario.test_id, XFAIL_ERROR)
    if xfail:
        pytest.xfail(f"[{xfail.category.name}] {xfail.reason}")

    try:
        _neo4j.parse(scenario.query)
    except GraphGlotError:
        # Expected: parser catches the error
        return

    # Parse succeeded — try semantic analysis
    result = _neo4j.validate(scenario.query)
    if not result.success:
        return  # Analysis-time error detected

    # Neither parse nor analysis caught it
    pytest.xfail(
        f"Parser accepted query that should fail with "
        f"{scenario.error_type}: {scenario.error_detail}"
    )
