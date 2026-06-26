"""Tests for pattern_comprehension_resugar transformation.

Re-sugars FullGQL's lowered ``VALUE {MATCH <pattern> [FILTER WHERE P] RETURN COLLECT_LIST(E)}``
subqueries back to Cypher's native ``[<pattern> [WHERE P] | E]`` pattern comprehensions.

Inverse of ``generate_pattern_comprehension_gql`` in
``graphglot/generator/generators/cypher_compat.py``.
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import CypherPatternComprehension
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.transformations import (
    _match_lowered_pattern_comprehension,
    pattern_comprehension_resugar,
)


class TestPatternComprehensionResugar(unittest.TestCase):
    """Direct AST-level tests for pattern_comprehension_resugar."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lowered_ast(self, cypher_query: str) -> ast.Expression:
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        return self.fullgql.parse(gql_text)[0]

    def _find_pc(self, tree: ast.Expression) -> CypherPatternComprehension | None:
        for node in tree.dfs():
            if isinstance(node, CypherPatternComprehension):
                return node
        return None

    def _count_value_query(self, tree: ast.Expression) -> int:
        return sum(1 for n in tree.dfs() if isinstance(n, ast.ValueQueryExpression))

    def test_basic_resugar(self):
        """``[(a)-[:T]->(m) | m]`` round-trips to CypherPatternComprehension."""
        tree = self._lowered_ast("MATCH (a) RETURN [(a)-[:T]->(m) | m] AS r")
        pattern_comprehension_resugar(tree)
        pc = self._find_pc(tree)
        self.assertIsNotNone(pc, "Expected CypherPatternComprehension after transform")
        self.assertIsNone(pc.where_clause)
        self.assertIsNotNone(pc.projection)
        self.assertEqual(self._count_value_query(tree), 0)

    def test_with_where(self):
        """Pattern comprehension with WHERE survives via FilterStatement."""
        tree = self._lowered_ast("MATCH (a) RETURN [(a)-[:T]->(m) WHERE m.age > 0 | m.name] AS r")
        pattern_comprehension_resugar(tree)
        pc = self._find_pc(tree)
        self.assertIsNotNone(pc)
        self.assertIsNotNone(pc.where_clause)
        self.assertIsNotNone(pc.projection)

    def test_value_for_untouched(self):
        """FOR-bodied (list comprehension) shape must not match here."""
        tree = self.fullgql.parse("RETURN VALUE {FOR x IN [1] RETURN COLLECT_LIST(x)} AS r")[0]
        pattern_comprehension_resugar(tree)
        self.assertIsNone(self._find_pc(tree))

    def test_value_multi_path_untouched(self):
        """MATCH with multiple path patterns (comma-separated) is not a
        comprehension shape.
        """
        tree = self.fullgql.parse("RETURN VALUE {MATCH (a), (b) RETURN COLLECT_LIST(a)} AS r")[0]
        pattern_comprehension_resugar(tree)
        self.assertIsNone(self._find_pc(tree))

    def test_value_for_no_collect_list_untouched(self):
        """``RETURN <bare expr>`` instead of COLLECT_LIST → no rewrite."""
        tree = self.fullgql.parse("RETURN VALUE {MATCH (a) RETURN a} AS r")[0]
        pattern_comprehension_resugar(tree)
        self.assertIsNone(self._find_pc(tree))

    def test_value_for_extra_statement_untouched(self):
        """Body with more than MATCH+FILTER → no rewrite."""
        tree = self.fullgql.parse(
            "RETURN VALUE {MATCH (a) FILTER WHERE a.x > 0 MATCH (b) RETURN COLLECT_LIST(a)} AS r"
        )[0]
        pattern_comprehension_resugar(tree)
        self.assertIsNone(self._find_pc(tree))

    def test_idempotent(self):
        tree = self._lowered_ast("MATCH (a) RETURN [(a)-->() | 1] AS r")
        pattern_comprehension_resugar(tree)
        before = self.cypher.generate(tree)
        pattern_comprehension_resugar(tree)
        after = self.cypher.generate(tree)
        self.assertEqual(before, after)

    # ------------------------------------------------------------------
    # End-to-end round-trip
    # ------------------------------------------------------------------

    def _roundtrip(self, cypher_query: str) -> tuple[ast.Expression, ast.Expression]:
        ast1 = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(ast1)
        gql_ast = self.fullgql.parse(gql_text)[0]
        cy2 = self.cypher.generate(gql_ast)
        ast2 = self.cypher.parse(cy2)[0]
        return ast1, ast2

    def test_roundtrip_basic(self):
        ast1, ast2 = self._roundtrip("MATCH (a) RETURN [(a)-[:T]->(m) | m] AS r")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_with_where(self):
        ast1, ast2 = self._roundtrip(
            "MATCH (a) RETURN [(a)-[:T]->(m) WHERE m.age > 0 | m.name] AS r"
        )
        self.assertEqual(ast1, ast2)

    def test_roundtrip_inside_size(self):
        """The shape that all 4 `_XCD_PC` scenarios use."""
        ast1, ast2 = self._roundtrip("MATCH (a) RETURN size([(a)-->() | 1]) AS length")
        self.assertEqual(ast1, ast2)


class TestFullGQLEmissionShape(unittest.TestCase):
    """Pin the canonical lowered shape for pattern comprehension."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lower_and_reparse(self, cypher_query: str) -> tuple[str, ast.ValueQueryExpression]:
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        gql_ast = self.fullgql.parse(gql_text)[0]
        vqe = next(n for n in gql_ast.dfs() if isinstance(n, ast.ValueQueryExpression))
        return gql_text, vqe

    def test_pc_basic_emission(self):
        """Bare pattern comprehension emits VALUE{MATCH … RETURN COLLECT_LIST(…)}."""
        gql_text, vqe = self._lower_and_reparse("MATCH (a) RETURN [(a)-->(m) | m] AS r")
        self.assertIn("VALUE {MATCH", gql_text)
        self.assertIn("RETURN COLLECT_LIST(m)}", gql_text)
        pc = _match_lowered_pattern_comprehension(vqe)
        self.assertIsNotNone(pc, "Matcher must accept the basic PC shape")
        self.assertIsNone(pc.where_clause)

    def test_pc_with_where_emission(self):
        """Pattern comprehension with WHERE emits FILTER WHERE in the body."""
        gql_text, vqe = self._lower_and_reparse(
            "MATCH (a) RETURN [(a)-->(m) WHERE m.x > 0 | m] AS r"
        )
        self.assertIn("FILTER WHERE m.x > 0", gql_text)
        pc = _match_lowered_pattern_comprehension(vqe)
        self.assertIsNotNone(pc, "Matcher must accept the with-WHERE PC shape")
        self.assertIsNotNone(pc.where_clause)


if __name__ == "__main__":
    unittest.main()
