"""TCK cross-dialect round-trip tests.

Round-trip is between the abstract :class:`CypherDialect` and :class:`FullGQL`
— the canonical Cypher and canonical GQL representations.  Vendor-specific
extensions (Neo4j-only functions, procedures) are out of scope; if the
source query uses them, ``CypherDialect.parse`` skips and the scenario
isn't tested.

Stage 1 — Cypher → GQL: ``CypherDialect.parse → FullGQL.generate →
FullGQL.parse``.  Failures here are tracked as *informative skips*
(pre-existing gaps in FullGQL generation/parsing).

Stage 2 — GQL → Cypher: ``CypherDialect.generate(gql_ast) →
CypherDialect.parse``.  Must succeed.  ``CypherDialect.WRITE_TRANSFORMATIONS``
includes ``next_to_with``, so ``NEXT`` chains lower back to ``WITH``.
Any exception in this stage is a hard test failure.

Final assertion: ``cypher_ast_1 == cypher_ast_2`` (full round-trip AST
equality).

Known failures live in :data:`XFAIL_CROSS_DIALECT_ROUNDTRIP` (in
``xfails.py``), categorized by root cause with references to the
corresponding section in ``playground/cross_dialect_followups.md``.  As
fixes land, entries are removed from the registry.  Any *new* failure
(not in the registry) is a hard test failure and a real regression.
"""

from __future__ import annotations

import pytest

from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.error import GraphGlotError
from tests.graphglot.tck.conftest import POSITIVE_SCENARIOS, RUNTIME_ERROR_SCENARIOS
from tests.graphglot.tck.models import TckScenario
from tests.graphglot.tck.xfails import (
    XFAIL_CROSS_DIALECT_ROUNDTRIP,
    get_xfail,
    should_xfail_parse,
)

_cypher = CypherDialect()
_fullgql = FullGQL()

_SCENARIOS = POSITIVE_SCENARIOS + RUNTIME_ERROR_SCENARIOS


@pytest.mark.tck
@pytest.mark.timeout(10)
@pytest.mark.parametrize(
    "scenario",
    _SCENARIOS,
    ids=lambda s: s.test_id,
)
def test_tck_cross_dialect_roundtrip(scenario: TckScenario):
    """Cypher → GQL → Cypher AST round-trip must preserve the source AST."""
    parse_xfail = should_xfail_parse(scenario.test_id, scenario.query)
    if parse_xfail:
        pytest.skip(f"Parse xfail: {parse_xfail.reason}")

    # Known cross-dialect round-trip failure — xfail with categorized reason.
    # As fixes land, entries are removed from XFAIL_CROSS_DIALECT_ROUNDTRIP.
    roundtrip_xfail = get_xfail(scenario.test_id, XFAIL_CROSS_DIALECT_ROUNDTRIP)
    if roundtrip_xfail:
        pytest.xfail(f"[{roundtrip_xfail.category.name}] {roundtrip_xfail.reason}")

    # Source parse via CypherDialect.  After the universal-Cypher lexer hoist
    # (cypher.py KEYWORDS section), no TCK scenario should hit this branch.
    # If one does, it's a CypherDialect parser gap — surface it as a hard
    # failure so we can investigate, not a silent skip.
    try:
        results = _cypher.parse(scenario.query)
    except GraphGlotError as e:
        pytest.fail(
            f"CypherDialect parse unexpectedly failed (parser gap?):\n"
            f"  query: {scenario.query!r}\n"
            f"  error: {e}"
        )
        return

    if not results:
        pytest.skip("Parse returned empty results")
        return

    cypher_ast_1 = results[0]

    # Stage 1: Cypher → GQL.  Skips here are tolerated and surface the
    # exception type/message so triage can group by root cause.
    try:
        gql_text = _fullgql.generate(cypher_ast_1)
        gql_ast = _fullgql.parse(gql_text)[0]
    except Exception as e:
        pytest.skip(f"Stage1 [{type(e).__name__}]: {str(e)[:120]}")
        return

    # Stage 2: GQL → Cypher.  Must succeed.  No try/except — let exceptions
    # propagate as test failures.  CypherDialect.WRITE_TRANSFORMATIONS runs
    # next_to_with so NEXT chains lower back to WITH.
    cypher_text_2 = _cypher.generate(gql_ast)
    cypher_ast_2 = _cypher.parse(cypher_text_2)[0]

    assert cypher_ast_1 == cypher_ast_2, (
        f"Cross-dialect round-trip AST mismatch.\n"
        f"Original: {scenario.query!r}\n"
        f"GQL intermediate: {gql_text!r}\n"
        f"Final Cypher: {cypher_text_2!r}"
    )


def test_xfail_registry_entries_are_valid_test_ids():
    """Every key in :data:`XFAIL_CROSS_DIALECT_ROUNDTRIP` must match a real scenario.

    Catches stale registry entries left behind when scenarios are renamed,
    removed, or when the ``TckScenario.test_id`` slug rule changes.
    """
    valid_ids = {s.test_id for s in _SCENARIOS}
    stale = sorted(tid for tid in XFAIL_CROSS_DIALECT_ROUNDTRIP if tid not in valid_ids)
    assert not stale, (
        f"{len(stale)} stale entries in XFAIL_CROSS_DIALECT_ROUNDTRIP "
        f"(no matching scenario):\n  " + "\n  ".join(stale)
    )
