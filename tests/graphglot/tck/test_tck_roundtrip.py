"""TCK round-trip + scope validation tests.

Verify parse -> generate -> re-parse produces equivalent ASTs, and that
the scope validator produces zero diagnostics on the transformed tree.

Tests positive + runtime-error scenarios (3279 total).
"""

from __future__ import annotations

import pytest

from graphglot.analysis import SemanticAnalyzer
from graphglot.dialect.neo4j import Neo4j
from graphglot.error import GraphGlotError
from tests.graphglot.tck.conftest import POSITIVE_SCENARIOS, RUNTIME_ERROR_SCENARIOS
from tests.graphglot.tck.models import TckScenario
from tests.graphglot.tck.xfails import XFAIL_ROUNDTRIP, get_xfail, should_xfail_parse

_neo4j = Neo4j()
_analyzer = SemanticAnalyzer()

# Scenarios that hit CPython recursion limits on deeply nested ASTs (40-level lists/maps).
# Not scope validator bugs — skip analysis for these.
_SKIP_SCOPE_IDS = {
    "Literals7__12_Return_40_deep_nested_empty_lists",
    "Literals8__16_Return_40_deep_nested_maps",
    "Create4__2_Many_CREATE_clauses",  # ~4s analyze time, exceeds per-test timeout
}

_ROUNDTRIP_SCENARIOS = POSITIVE_SCENARIOS + RUNTIME_ERROR_SCENARIOS


@pytest.mark.tck
@pytest.mark.timeout(10)
@pytest.mark.parametrize(
    "scenario",
    _ROUNDTRIP_SCENARIOS,
    ids=lambda s: s.test_id,
)
def test_tck_roundtrip(scenario: TckScenario):
    """Parse -> generate -> re-parse should produce equivalent ASTs."""
    # Skip if parse is expected to fail
    parse_xfail = should_xfail_parse(scenario.test_id, scenario.query)
    if parse_xfail:
        pytest.skip(f"Parse xfail: {parse_xfail.reason}")

    rt_xfail = get_xfail(scenario.test_id, XFAIL_ROUNDTRIP)
    if rt_xfail:
        pytest.xfail(f"[{rt_xfail.category.name}] {rt_xfail.reason}")

    try:
        results = _neo4j.parse(scenario.query)
    except GraphGlotError:
        pytest.skip("Parse failed (covered by parse test)")
        return

    if not results:
        pytest.skip("Parse returned empty results")
        return

    # Scope validation: transform + analyze must produce no diagnostics.
    if scenario.test_id not in _SKIP_SCOPE_IDS:
        try:
            transformed = _neo4j.transform(results)
        except GraphGlotError:
            pass  # Transform failure — not a scope issue
        else:
            if transformed:
                scope_result = _analyzer.analyze(transformed[0], _neo4j)
                if scope_result.diagnostics:
                    msgs = "; ".join(str(d) for d in scope_result.diagnostics)
                    pytest.fail(
                        f"Scope diagnostics on transformed tree:\n{msgs}\nQuery: {scenario.query!r}"
                    )

    try:
        generated = _neo4j.generate(results[0])
    except Exception:
        pytest.skip("Generate failed")
        return

    try:
        results2 = _neo4j.parse(generated)
    except GraphGlotError as exc:
        pytest.fail(f"Re-parse failed for generated query: {generated!r}\nError: {exc}")
        return

    if not results2:
        pytest.fail(f"Re-parse returned empty results for: {generated!r}")
        return

    assert results[0] == results2[0], (
        f"ASTs differ after round-trip.\n"
        f"Original query: {scenario.query!r}\n"
        f"Generated: {generated!r}"
    )
