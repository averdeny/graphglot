"""Tests for pattern_predicate_resugar transformation.

Re-sugars FullGQL's lowered ``EXISTS{<graph pattern>}`` back to Cypher's
native pattern predicate ``(n)-->()`` form.

Inverse of ``generate_pattern_predicate`` in
``graphglot/generator/generators/cypher_compat.py``.
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import CypherPatternPredicate
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.transformations import (
    _match_lowered_pattern_predicate,
    pattern_predicate_resugar,
)


class TestPatternPredicateResugar(unittest.TestCase):
    """Direct AST-level tests for pattern_predicate_resugar."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lowered_ast(self, cypher_query: str) -> ast.Expression:
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        return self.fullgql.parse(gql_text)[0]

    def _find_cpp(self, tree: ast.Expression) -> CypherPatternPredicate | None:
        for node in tree.dfs():
            if isinstance(node, CypherPatternPredicate):
                return node
        return None

    def _count_exists(self, tree: ast.Expression) -> int:
        return sum(1 for n in tree.dfs() if isinstance(n, ast.ExistsPredicate))

    def test_node_relationship_resugar(self):
        """``EXISTS{(a)-[:T]->()}`` → ``CypherPatternPredicate(pattern=…)``."""
        tree = self._lowered_ast("MATCH (a) WHERE (a)-[:T]->() RETURN a")
        pattern_predicate_resugar(tree)
        cpp = self._find_cpp(tree)
        self.assertIsNotNone(cpp)
        self.assertEqual(self._count_exists(tree), 0)

    def test_negated_pattern_resugar(self):
        """``NOT EXISTS{(a)-->()}`` re-sugars to a CypherPatternPredicate
        underneath the existing ``BooleanFactor(not_=True)`` — the negation
        wrapper survives unchanged.
        """
        tree = self._lowered_ast("MATCH (a) WHERE NOT (a)-->() RETURN a")
        pattern_predicate_resugar(tree)
        cpp = self._find_cpp(tree)
        self.assertIsNotNone(cpp)
        self.assertEqual(self._count_exists(tree), 0)

    def test_exists_with_where_untouched(self):
        """``EXISTS{(a) WHERE a.x > 0}`` carries a graph_pattern_where_clause —
        not a bare pattern predicate, must not be rewritten.
        """
        tree = self.fullgql.parse("MATCH (a) WHERE EXISTS { (a) WHERE a.x > 0 } RETURN a")[0]
        pattern_predicate_resugar(tree)
        self.assertIsNone(self._find_cpp(tree))
        self.assertGreater(self._count_exists(tree), 0)

    def test_exists_nqs_body_untouched(self):
        """``EXISTS{MATCH (n) RETURN n}`` has a NestedQuerySpecification body
        (not _ExistsGraphPattern) — not a pattern predicate.
        """
        tree = self.fullgql.parse("MATCH (a) WHERE EXISTS {MATCH (n) RETURN n} RETURN a")[0]
        pattern_predicate_resugar(tree)
        self.assertIsNone(self._find_cpp(tree))

    def test_exists_multi_path_untouched(self):
        """``EXISTS{(a), (b)}`` (two disconnected paths) is structurally more
        than a single pattern predicate — must not be rewritten.
        """
        tree = self.fullgql.parse("MATCH (a), (b) WHERE EXISTS {(a), (b)} RETURN a")[0]
        pattern_predicate_resugar(tree)
        self.assertIsNone(self._find_cpp(tree))

    def test_idempotent(self):
        tree = self._lowered_ast("MATCH (a) WHERE (a)-->() RETURN a")
        pattern_predicate_resugar(tree)
        before = self.cypher.generate(tree)
        pattern_predicate_resugar(tree)
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

    def test_roundtrip_in_where(self):
        ast1, ast2 = self._roundtrip("MATCH (n) WHERE (n)-[]->() RETURN n")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_negated(self):
        ast1, ast2 = self._roundtrip("MATCH (n) WHERE NOT (n)-[]->() RETURN n")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_compound_and(self):
        ast1, ast2 = self._roundtrip("MATCH (n) WHERE (n)-->() AND n.age > 0 RETURN n")
        self.assertEqual(ast1, ast2)


class TestFullGQLEmissionShape(unittest.TestCase):
    """Pin the canonical lowered shape for pattern predicates."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lower_and_reparse(self, cypher_query: str) -> tuple[str, ast.ExistsPredicate]:
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        gql_ast = self.fullgql.parse(gql_text)[0]
        exists = next(n for n in gql_ast.dfs() if isinstance(n, ast.ExistsPredicate))
        return gql_text, exists

    def test_pattern_predicate_emits_exists_graph_pattern(self):
        """Cypher ``(n)-[:T]->()`` in WHERE emits ``EXISTS{(n) -[:T]-> ()}``.
        The body must be ``_ExistsGraphPattern``, not NQS.
        """
        gql_text, exists = self._lower_and_reparse("MATCH (n) WHERE (n)-[:T]->() RETURN n")
        self.assertIn("EXISTS {", gql_text)
        self.assertIsInstance(exists.exists_predicate, ast.ExistsPredicate._ExistsGraphPattern)
        cpp = _match_lowered_pattern_predicate(exists)
        self.assertIsNotNone(cpp, "Matcher must accept the canonical pattern shape")


if __name__ == "__main__":
    unittest.main()
