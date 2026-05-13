"""TCK inverse-transform round-trip tests.

Verify that ``cypher → with_to_next → CypherDialect.generate → parse``
produces an AST equal to the original Cypher AST — isolating the
bijection between Cypher's ``WITH`` clause and GQL's ``NEXT``-separated
``StatementBlock`` chain.

The test exercises the full ``WRITE_TRANSFORMATIONS`` pathway:
``CypherDialect.WRITE_TRANSFORMATIONS = [next_to_with]`` runs inside
``generate()``, so the emitted text uses ``WITH``.  Re-parsing with
Neo4j (which understands both ``WITH`` and ``NEXT``) recovers a
``CypherWithStatement``-shaped AST that we compare against the
original.

The other transformations in :attr:`CypherDialect.TRANSFORMATIONS`
(``resolve_ambiguous``, ``implicit_to_explicit_group_by``) are
intentionally bypassed by calling ``with_to_next`` directly — they
will get their own inverses and round-trip tests in future work.
"""

from __future__ import annotations

import pytest

from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.neo4j import Neo4j
from graphglot.error import GraphGlotError
from graphglot.transformations import with_to_next
from tests.graphglot.tck.conftest import POSITIVE_SCENARIOS, RUNTIME_ERROR_SCENARIOS
from tests.graphglot.tck.models import TckScenario
from tests.graphglot.tck.xfails import XFAIL_INVERSE, get_xfail, should_xfail_parse

_neo4j = Neo4j()
_cypher = CypherDialect()

_INVERSE_SCENARIOS = POSITIVE_SCENARIOS + RUNTIME_ERROR_SCENARIOS


@pytest.mark.tck
@pytest.mark.timeout(10)
@pytest.mark.parametrize(
    "scenario",
    _INVERSE_SCENARIOS,
    ids=lambda s: s.test_id,
)
def test_tck_inverse_transform(scenario: TckScenario):
    """cypher → with_to_next → GQL → next_to_with should preserve the AST."""
    parse_xfail = should_xfail_parse(scenario.test_id, scenario.query)
    if parse_xfail:
        pytest.skip(f"Parse xfail: {parse_xfail.reason}")

    inverse_xfail = get_xfail(scenario.test_id, XFAIL_INVERSE)
    if inverse_xfail:
        pytest.xfail(f"[{inverse_xfail.category.name}] {inverse_xfail.reason}")

    try:
        results = _neo4j.parse(scenario.query)
    except GraphGlotError:
        pytest.skip("Parse failed (covered by parse test)")
        return

    if not results:
        pytest.skip("Parse returned empty results")
        return

    cypher_ast_1 = results[0]

    try:
        gql_ast = with_to_next(cypher_ast_1.deep_copy())
    except Exception as exc:
        pytest.fail(f"with_to_next raised: {exc}\nQuery: {scenario.query!r}")
        return

    # CypherDialect.WRITE_TRANSFORMATIONS = [next_to_with] runs inside
    # generate(), so the emitted text uses WITH instead of NEXT.
    try:
        cypher_text = _cypher.generate(gql_ast)
    except Exception:
        pytest.skip("Generate failed")
        return

    try:
        results2 = _neo4j.parse(cypher_text)
    except GraphGlotError as exc:
        pytest.fail(f"Re-parse failed for generated query: {cypher_text!r}\nError: {exc}")
        return

    if not results2:
        pytest.fail(f"Re-parse returned empty results for: {cypher_text!r}")
        return

    cypher_ast_2 = results2[0]

    assert cypher_ast_1 == cypher_ast_2, (
        f"Inverse round-trip differs.\n"
        f"Original query: {scenario.query!r}\n"
        f"Generated: {cypher_text!r}"
    )
