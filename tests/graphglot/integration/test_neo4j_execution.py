"""Parse GQL -> generate Neo4j -> execute against seeded database -> verify results.

Replaces EXPLAIN-based probing with actual query execution against a canonical
seed graph (6 nodes, 7 edges). Mutations run in rolled-back transactions.
"""

from __future__ import annotations

import pytest

from graphglot.dialect.neo4j import Neo4j
from graphglot.error import GraphGlotError
from tests.graphglot.integration.queries import (
    _UNSET,
    ALL_QUERY_CASES,
    PARAM_VALUES,
    TRANSFORM_WITH_CASES,
)

pytestmark = pytest.mark.integration

_dialect = Neo4j()


def _generate(gql: str) -> str:
    """Parse a GQL query and re-generate it using the Neo4j dialect."""
    ast_nodes = _dialect.parse(gql)
    assert ast_nodes, f"Parse failed: {gql[:80]}"
    return _dialect.generate(ast_nodes[0])


@pytest.mark.parametrize("tc", ALL_QUERY_CASES, ids=[tc.id for tc in ALL_QUERY_CASES])
def test_neo4j_execute(neo4j_exec_session, tc):
    """Parse GQL -> generate Neo4j SQL -> execute -> verify results."""
    if tc.xfail:
        pytest.xfail(tc.xfail)

    if tc.unsupported:
        with pytest.raises(GraphGlotError):
            _generate(tc.gql)
        return

    generated = _generate(tc.gql)

    # Build params dict for queries that use parameters
    params = {}
    if tc.category == "parameter":
        params = PARAM_VALUES

    if tc.mutation:
        tx = neo4j_exec_session.begin_transaction()
        try:
            result = tx.run(generated, **params)
            records = [dict(r) for r in result]
        finally:
            tx.rollback()
    else:
        result = neo4j_exec_session.run(generated, **params)
        records = [dict(r) for r in result]

    if tc.expected_value is not _UNSET:
        assert len(records) == 1, (
            f"Expected 1 row, got {len(records)} for {tc.id}\n  Generated: {generated}"
        )
        actual = next(iter(records[0].values()))
        if isinstance(tc.expected_value, float):
            assert actual == pytest.approx(tc.expected_value, rel=1e-3), (
                f"[{tc.id}] Expected {tc.expected_value}, got {actual}"
            )
        else:
            assert actual == tc.expected_value, (
                f"[{tc.id}] Expected {tc.expected_value!r}, got {actual!r}"
            )
    elif tc.expected_rows is not None:
        assert len(records) == tc.expected_rows, (
            f"[{tc.id}] Expected {tc.expected_rows} rows, got {len(records)}\n"
            f"  Generated: {generated}"
        )


def _transform_and_generate(cypher: str) -> str:
    """Parse Cypher, apply WITH→NEXT transformation, generate Neo4j output."""
    ast_nodes = _dialect.parse(cypher)
    assert ast_nodes, f"Parse failed: {cypher[:80]}"
    transformed = _dialect.transform(ast_nodes)
    return _dialect.generate(transformed[0])


@pytest.mark.parametrize("tc", TRANSFORM_WITH_CASES, ids=[tc.id for tc in TRANSFORM_WITH_CASES])
def test_neo4j_transform_execute(neo4j_exec_session, tc):
    """Parse Cypher WITH -> transform to RETURN...NEXT -> generate -> execute."""
    generated = _transform_and_generate(tc.gql)

    result = neo4j_exec_session.run(generated)
    records = [dict(r) for r in result]

    if tc.expected_value is not _UNSET:
        assert len(records) == 1, (
            f"Expected 1 row, got {len(records)} for {tc.id}\n  Generated: {generated}"
        )
        actual = next(iter(records[0].values()))
        if isinstance(tc.expected_value, float):
            assert actual == pytest.approx(tc.expected_value, rel=1e-3), (
                f"[{tc.id}] Expected {tc.expected_value}, got {actual}"
            )
        else:
            assert actual == tc.expected_value, (
                f"[{tc.id}] Expected {tc.expected_value!r}, got {actual!r}"
            )
    elif tc.expected_rows is not None:
        assert len(records) == tc.expected_rows, (
            f"[{tc.id}] Expected {tc.expected_rows} rows, got {len(records)}\n"
            f"  Generated: {generated}"
        )
