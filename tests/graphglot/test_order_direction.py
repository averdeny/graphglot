"""Tests for ORDER BY direction defaults (ASC/DESC).

Implementation-defined default sort direction.  Verified live: Neo4j and every
GQL engine we support default to ASC.  The pattern: declare ``DEFAULT_ORDER_DIRECTION``
on Dialect, parser stays lossless, ``effective_order_direction`` resolves at
inspection time, generator elides redundant ASC, and cross-dialect transpile
materializes the source's default when source and target disagree (no-op today).
"""

import unittest

from graphglot import ast
from graphglot.dialect.base import Dialect
from graphglot.dialect.coregql import CoreGQL
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.dialect.neo4j import Neo4j


def _first_sort_spec(tree: ast.Expression) -> ast.SortSpecification:
    return next(iter(tree.find_all(ast.SortSpecification)))


class TestDefaultOrderDirectionDialect(unittest.TestCase):
    """Every dialect declares ASC as the default sort direction."""

    def test_base_dialect_asc(self):
        self.assertIs(Dialect.DEFAULT_ORDER_DIRECTION, ast.OrderingSpecification.Order.ASC)

    def test_fullgql_asc(self):
        self.assertIs(FullGQL.DEFAULT_ORDER_DIRECTION, ast.OrderingSpecification.Order.ASC)

    def test_coregql_asc(self):
        self.assertIs(CoreGQL.DEFAULT_ORDER_DIRECTION, ast.OrderingSpecification.Order.ASC)

    def test_cypher_asc(self):
        self.assertIs(CypherDialect.DEFAULT_ORDER_DIRECTION, ast.OrderingSpecification.Order.ASC)

    def test_neo4j_asc(self):
        self.assertIs(Neo4j.DEFAULT_ORDER_DIRECTION, ast.OrderingSpecification.Order.ASC)


class TestEffectiveOrderDirection(unittest.TestCase):
    """`effective_order_direction` resolves explicit-or-default."""

    def test_implicit_returns_dialect_default(self):
        d = FullGQL()
        [tree] = d.parse("MATCH (n) RETURN n ORDER BY n.x")
        ss = _first_sort_spec(tree)
        self.assertIsNone(ss.ordering_specification)
        self.assertIs(ss.effective_order_direction(d), ast.OrderingSpecification.Order.ASC)

    def test_explicit_desc_preserved(self):
        d = FullGQL()
        [tree] = d.parse("MATCH (n) RETURN n ORDER BY n.x DESC")
        ss = _first_sort_spec(tree)
        self.assertIs(ss.effective_order_direction(d), ast.OrderingSpecification.Order.DESC)


class TestOrderDirectionGeneration(unittest.TestCase):
    """Generator elides ASC (matches default) and emits DESC."""

    def test_implicit_stays_bare(self):
        d = FullGQL()
        out = d.generate(d.parse("MATCH (n) RETURN n ORDER BY n.x")[0])
        self.assertNotIn("ASC", out)
        self.assertNotIn("DESC", out)

    def test_explicit_asc_preserved(self):
        # Parser is lossless; generator emits what the user wrote.  An
        # explicit ASC is kept — round-trip AST fidelity matters, and
        # cross-dialect semantic preservation is handled elsewhere by
        # the materialization transformation.
        d = FullGQL()
        out = d.generate(d.parse("MATCH (n) RETURN n ORDER BY n.x ASC")[0])
        self.assertIn("ASC", out)

    def test_explicit_desc_emitted(self):
        d = FullGQL()
        out = d.generate(d.parse("MATCH (n) RETURN n ORDER BY n.x DESC")[0])
        self.assertIn("DESC", out)


class TestCrossDialectOrderDirection(unittest.TestCase):
    """Cross-dialect transpile preserves DESC and stays bare on implicit ASC."""

    def test_cross_dialect_implicit_stays_bare(self):
        # All current dialects share ASC as default — bare round-trips bare.
        from click.testing import CliRunner

        from graphglot.cli import cli

        runner = CliRunner()
        r = runner.invoke(
            cli,
            ["transpile", "-r", "neo4j", "-w", "fullgql", "MATCH (n) RETURN n ORDER BY n.x"],
        )
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertNotIn("ASC", r.output)
        self.assertNotIn("DESC", r.output)

    def test_cross_dialect_desc_preserved(self):
        from click.testing import CliRunner

        from graphglot.cli import cli

        runner = CliRunner()
        r = runner.invoke(
            cli,
            ["transpile", "-r", "neo4j", "-w", "fullgql", "MATCH (n) RETURN n ORDER BY n.x DESC"],
        )
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("DESC", r.output)


if __name__ == "__main__":
    unittest.main()
