"""Tests for string_match_predicate_resugar transformation.

Re-sugars FullGQL's lowered ``LEFT/RIGHT(x, COALESCE(CHAR_LENGTH(y), 0)) = y``
back to Cypher's native ``x STARTS WITH y`` / ``x ENDS WITH y`` predicates.

Inverse of ``generate_string_match_predicate`` in
``graphglot/generator/generators/cypher_compat.py``.  CONTAINS is out of
scope — the forward generator raises NotImplementedError for it.
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import StringMatchPredicate
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.transformations import (
    _match_lowered_string_match,
    string_match_predicate_resugar,
)


class TestStringMatchPredicateResugar(unittest.TestCase):
    """Direct AST-level tests for string_match_predicate_resugar."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lowered_ast(self, cypher_query: str) -> ast.Expression:
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        return self.fullgql.parse(gql_text)[0]

    def _find_smp(self, tree: ast.Expression) -> StringMatchPredicate | None:
        for node in tree.dfs():
            if isinstance(node, StringMatchPredicate):
                return node
        return None

    def test_starts_with_resugar(self):
        tree = self._lowered_ast("MATCH (a) WHERE a.name STARTS WITH 'A' RETURN a")
        string_match_predicate_resugar(tree)
        smp = self._find_smp(tree)
        self.assertIsNotNone(smp)
        self.assertEqual(smp.kind, StringMatchPredicate.MatchKind.STARTS_WITH)

    def test_ends_with_resugar(self):
        tree = self._lowered_ast("MATCH (a) WHERE a.name ENDS WITH 'A' RETURN a")
        string_match_predicate_resugar(tree)
        smp = self._find_smp(tree)
        self.assertIsNotNone(smp)
        self.assertEqual(smp.kind, StringMatchPredicate.MatchKind.ENDS_WITH)

    def test_left_with_non_coalesce_arg_untouched(self):
        """``LEFT(a.name, 5) = 'A'`` is not the canonical lowering — must not be rewritten."""
        tree = self.fullgql.parse("MATCH (a) WHERE LEFT(a.name, 5) = 'A' RETURN a")[0]
        string_match_predicate_resugar(tree)
        self.assertIsNone(self._find_smp(tree))

    def test_left_with_mismatched_rhs_untouched(self):
        """``LEFT(x, COALESCE(CHAR_LENGTH('A'), 0)) = 'B'`` — rhs doesn't match
        the CHAR_LENGTH operand, must not be rewritten.
        """
        tree = self.fullgql.parse(
            "MATCH (a) WHERE LEFT(a.name, COALESCE(CHAR_LENGTH('A'), 0)) = 'B' RETURN a"
        )[0]
        string_match_predicate_resugar(tree)
        self.assertIsNone(self._find_smp(tree))

    def test_left_with_non_zero_default_untouched(self):
        """COALESCE default of 1 instead of 0 — not the canonical shape."""
        tree = self.fullgql.parse(
            "MATCH (a) WHERE LEFT(a.name, COALESCE(CHAR_LENGTH('A'), 1)) = 'A' RETURN a"
        )[0]
        string_match_predicate_resugar(tree)
        self.assertIsNone(self._find_smp(tree))

    def test_idempotent(self):
        tree = self._lowered_ast("MATCH (a) WHERE a.name STARTS WITH 'A' RETURN a")
        string_match_predicate_resugar(tree)
        before = self.cypher.generate(tree)
        string_match_predicate_resugar(tree)
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

    def test_roundtrip_starts_with(self):
        ast1, ast2 = self._roundtrip("MATCH (a) WHERE a.name STARTS WITH 'A' RETURN a")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_ends_with(self):
        ast1, ast2 = self._roundtrip("MATCH (a) WHERE a.name ENDS WITH 'A' RETURN a")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_in_and_chain(self):
        ast1, ast2 = self._roundtrip(
            "MATCH (a) WHERE a.name STARTS WITH 'A' AND a.age > 0 RETURN a"
        )
        self.assertEqual(ast1, ast2)

    def test_roundtrip_null_rhs(self):
        """``STARTS WITH null`` round-trip.  This case is the reason the
        matcher compares *unwrapped* leaves on the two sides of ``=`` —
        FullGQL parses NULL on the comparison side via a different wrapper
        chain than NULL nested inside ``CHAR_LENGTH(...)``.
        """
        ast1, ast2 = self._roundtrip("MATCH (a) WHERE a.name STARTS WITH null RETURN a")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_non_string_operand(self):
        """``STARTS WITH`` where the operand is bound to a heterogeneous list
        (so the type isn't statically string).  FullGQL's parser uses
        ``BindingVariableReference`` wrappers that diverge between the
        two occurrences of the operand on lhs/rhs sides — the matcher's
        unwrapped-leaf comparison must handle this.
        """
        ast1, ast2 = self._roundtrip(
            "WITH [1, 'A', null] AS operands "
            "UNWIND operands AS op1 "
            "UNWIND operands AS op2 "
            "RETURN op1 STARTS WITH op2 AS v"
        )
        self.assertEqual(ast1, ast2)


class TestFullGQLEmissionShape(unittest.TestCase):
    """Pin the canonical lowered shape for STARTS WITH / ENDS WITH."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lower_and_reparse(self, cypher_query: str) -> tuple[str, ast.ComparisonPredicate]:
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        gql_ast = self.fullgql.parse(gql_text)[0]
        cmp = next(n for n in gql_ast.dfs() if isinstance(n, ast.ComparisonPredicate))
        return gql_text, cmp

    def test_starts_with_emits_left_coalesce_char_length(self):
        gql_text, cmp = self._lower_and_reparse("MATCH (a) WHERE a.name STARTS WITH 'A' RETURN a")
        self.assertIn("LEFT(a.name, COALESCE(CHAR_LENGTH('A'), 0)) = 'A'", gql_text)
        smp = _match_lowered_string_match(cmp)
        self.assertIsNotNone(smp)
        self.assertEqual(smp.kind, StringMatchPredicate.MatchKind.STARTS_WITH)

    def test_ends_with_emits_right_coalesce_char_length(self):
        gql_text, cmp = self._lower_and_reparse("MATCH (a) WHERE a.name ENDS WITH 'A' RETURN a")
        self.assertIn("RIGHT(a.name, COALESCE(CHAR_LENGTH('A'), 0)) = 'A'", gql_text)
        smp = _match_lowered_string_match(cmp)
        self.assertIsNotNone(smp)
        self.assertEqual(smp.kind, StringMatchPredicate.MatchKind.ENDS_WITH)


if __name__ == "__main__":
    unittest.main()
