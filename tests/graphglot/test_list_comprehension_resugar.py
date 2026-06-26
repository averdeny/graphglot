"""Tests for list_comprehension_resugar transformation.

Re-sugars FullGQL's lowered ``VALUE {FOR x IN L FILTER WHERE P RETURN COLLECT_LIST(E)}``
subqueries back to Cypher's native ``[x IN L WHERE P | E]`` list comprehensions.

Inverse of ``generate_list_comprehension_gql`` in
``graphglot/generator/generators/cypher_compat.py``:

  [x IN L WHERE P | E]  ← VALUE {FOR x IN L FILTER WHERE P RETURN COLLECT_LIST(E)}
  [x IN L | E]          ← VALUE {FOR x IN L RETURN COLLECT_LIST(E)}
  [x IN L WHERE P]      ← VALUE {FOR x IN L FILTER WHERE P RETURN COLLECT_LIST(x)}
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import ListComprehension
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.transformations import (
    _match_lowered_comprehension,
    list_comprehension_resugar,
)


class TestListComprehensionResugar(unittest.TestCase):
    """Direct AST-level tests for list_comprehension_resugar."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lowered_ast(self, cypher_query: str) -> ast.Expression:
        """Cypher.parse → FullGQL.generate → FullGQL.parse — produces the lowered shape."""
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        return self.fullgql.parse(gql_text)[0]

    def _find_lc(self, tree: ast.Expression) -> ListComprehension | None:
        for node in tree.dfs():
            if isinstance(node, ListComprehension):
                return node
        return None

    def _count_value_query(self, tree: ast.Expression) -> int:
        return sum(1 for n in tree.dfs() if isinstance(n, ast.ValueQueryExpression))

    def test_basic_resugar(self):
        """``[x IN L WHERE P | E]`` round-trips to ListComprehension with all fields set."""
        tree = self._lowered_ast("RETURN [x IN [1, 2, 3] WHERE x > 0 | x * 2] AS r")
        list_comprehension_resugar(tree)
        lc = self._find_lc(tree)
        self.assertIsNotNone(lc, "Expected ListComprehension after transform")
        self.assertIsNotNone(lc.where_clause)
        self.assertIsNotNone(lc.projection)
        self.assertEqual(self._count_value_query(tree), 0, "ValueQueryExpression should be gone")

    def test_no_where_resugar(self):
        """``[x IN L | E]`` (no WHERE) → ListComprehension with where_clause=None."""
        tree = self._lowered_ast("RETURN [x IN [1, 2, 3] | x * 2] AS r")
        list_comprehension_resugar(tree)
        lc = self._find_lc(tree)
        self.assertIsNotNone(lc)
        self.assertIsNone(lc.where_clause)
        self.assertIsNotNone(lc.projection)
        self.assertEqual(self._count_value_query(tree), 0)

    def test_no_projection_resugar(self):
        """``[x IN L WHERE P]`` (no projection) → ListComprehension with projection=None.

        The lowering emits ``COLLECT_LIST(x)`` when projection is the bare alias.
        The matcher must collapse that back to projection=None so the round-trip
        emits the canonical ``[x IN L WHERE P]`` form.
        """
        tree = self._lowered_ast("RETURN [x IN [1, 2, 3] WHERE x > 0] AS r")
        list_comprehension_resugar(tree)
        lc = self._find_lc(tree)
        self.assertIsNotNone(lc)
        self.assertIsNotNone(lc.where_clause)
        self.assertIsNone(
            lc.projection, "projection must collapse to None for bare-alias COLLECT_LIST"
        )

    def test_idempotent(self):
        tree = self._lowered_ast("RETURN [x IN [1, 2] WHERE x > 0 | x * 2] AS r")
        list_comprehension_resugar(tree)
        before = self.cypher.generate(tree)
        list_comprehension_resugar(tree)
        after = self.cypher.generate(tree)
        self.assertEqual(before, after)

    def test_value_match_untouched(self):
        """``VALUE {MATCH (n) RETURN COLLECT_LIST(n)}`` is the pattern-comprehension
        lowered shape (out of scope) — must not be rewritten as list comprehension.
        """
        tree = self.fullgql.parse("RETURN VALUE {MATCH (n) RETURN COLLECT_LIST(n)} AS r")[0]
        list_comprehension_resugar(tree)
        self.assertIsNone(self._find_lc(tree))
        self.assertGreater(
            self._count_value_query(tree), 0, "ValueQueryExpression must be preserved"
        )

    def test_value_for_no_collect_list_untouched(self):
        """``VALUE {FOR x IN L RETURN x}`` — RETURN must be COLLECT_LIST, not bare."""
        tree = self.fullgql.parse("RETURN VALUE {FOR x IN [1] RETURN x} AS r")[0]
        list_comprehension_resugar(tree)
        self.assertIsNone(self._find_lc(tree))

    def test_value_for_extra_statement_untouched(self):
        """Body with more than FOR+FILTER → no rewrite."""
        tree = self.fullgql.parse(
            "RETURN VALUE {FOR x IN [1] FILTER WHERE x > 0 MATCH (n) RETURN COLLECT_LIST(x)} AS r"
        )[0]
        list_comprehension_resugar(tree)
        self.assertIsNone(self._find_lc(tree))

    def test_value_for_non_collect_aggregate_untouched(self):
        """Aggregate that isn't COLLECT_LIST (e.g. ``COUNT(x)``) → no rewrite."""
        tree = self.fullgql.parse("RETURN VALUE {FOR x IN [1] RETURN COUNT(x)} AS r")[0]
        list_comprehension_resugar(tree)
        self.assertIsNone(self._find_lc(tree))

    def test_value_for_distinct_collect_list_untouched(self):
        """``COLLECT_LIST(DISTINCT x)`` has no Cypher equivalent — must not be rewritten."""
        tree = self.fullgql.parse(
            "RETURN VALUE {FOR x IN [1] RETURN COLLECT_LIST(DISTINCT x)} AS r"
        )[0]
        list_comprehension_resugar(tree)
        self.assertIsNone(self._find_lc(tree))

    def test_value_for_ordered_return_untouched(self):
        """Subquery body with ORDER BY in its RETURN — no Cypher equivalent;
        the canonical lowering emits no ORDER BY in the subquery body.
        """
        tree = self.fullgql.parse(
            "RETURN VALUE {FOR x IN [1] RETURN COLLECT_LIST(x) ORDER BY x} AS r"
        )[0]
        list_comprehension_resugar(tree)
        self.assertIsNone(self._find_lc(tree))

    # ------------------------------------------------------------------
    # End-to-end round-trip
    # ------------------------------------------------------------------

    def _roundtrip(self, cypher_query: str) -> tuple[ast.Expression, ast.Expression]:
        cypher_ast_1 = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cypher_ast_1)
        gql_ast = self.fullgql.parse(gql_text)[0]
        cypher_text_2 = self.cypher.generate(gql_ast)
        cypher_ast_2 = self.cypher.parse(cypher_text_2)[0]
        return cypher_ast_1, cypher_ast_2

    def test_roundtrip_basic(self):
        ast1, ast2 = self._roundtrip("RETURN [x IN [1, 2, 3] WHERE x > 0 | x * 2] AS r")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_no_where(self):
        ast1, ast2 = self._roundtrip("RETURN [x IN [1, 2, 3] | x * 2] AS r")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_no_projection(self):
        ast1, ast2 = self._roundtrip("RETURN [x IN [1, 2, 3] WHERE x > 0] AS r")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_nested_in_where(self):
        """List comprehension as a subexpression in WHERE — verifies re-sugar
        works in non-RETURN positions.
        """
        ast1, ast2 = self._roundtrip(
            "MATCH (n) WHERE size([x IN [1, 2] WHERE x > 0 | x * 2]) > 0 RETURN n"
        )
        self.assertEqual(ast1, ast2)


class TestFullGQLEmissionShape(unittest.TestCase):
    """Pin the canonical lowered shape FullGQL emits for list comprehensions.

    ``list_comprehension_resugar`` (and ``_match_lowered_comprehension``)
    recognize the three canonical shapes emitted by
    ``graphglot/generator/generators/cypher_compat.py:generate_list_comprehension_gql``.
    If that emitter ever changes its output, these tests fail loudly,
    signalling that the matcher needs an update before silent ``_XCD_LC``
    round-trip regressions reappear.

    Each test pins **both** layers of the contract:

    1. The exact GQL text produced by ``FullGQL.generate``.
    2. ``_match_lowered_comprehension`` accepts the re-parsed AST.
    """

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lower_and_reparse(self, cypher_query: str) -> tuple[str, ast.ValueQueryExpression]:
        """Lower *cypher_query* via FullGQL and return ``(gql_text, vqe_node)``."""
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        gql_ast = self.fullgql.parse(gql_text)[0]
        vqe = next(n for n in gql_ast.dfs() if isinstance(n, ast.ValueQueryExpression))
        return gql_text, vqe

    def test_lc_with_where_and_projection(self):
        """``[x IN L WHERE P | E]`` emits ``VALUE {FOR x IN L FILTER WHERE P RETURN COLLECT_LIST(E)}``."""  # noqa: E501
        gql_text, vqe = self._lower_and_reparse("RETURN [x IN [1] WHERE x > 0 | x * 2] AS r")
        self.assertIn(
            "VALUE {FOR x IN [1] FILTER WHERE x > 0 RETURN COLLECT_LIST(x * 2)}",
            gql_text,
        )
        lc = _match_lowered_comprehension(vqe)
        self.assertIsNotNone(lc, "Matcher must accept the canonical WHERE+projection shape")
        self.assertIsNotNone(lc.where_clause)
        self.assertIsNotNone(lc.projection)

    def test_lc_no_where_emits_value_for_collect_list(self):
        """``[x IN L | E]`` emits ``VALUE {FOR x IN L RETURN COLLECT_LIST(E)}`` (no FILTER)."""
        gql_text, vqe = self._lower_and_reparse("RETURN [x IN [1] | x * 2] AS r")
        self.assertIn("VALUE {FOR x IN [1] RETURN COLLECT_LIST(x * 2)}", gql_text)
        self.assertNotIn("FILTER", gql_text)
        lc = _match_lowered_comprehension(vqe)
        self.assertIsNotNone(lc, "Matcher must accept the no-WHERE shape")
        self.assertIsNone(lc.where_clause)
        self.assertIsNotNone(lc.projection)

    def test_lc_no_projection_emits_collect_list_of_alias(self):
        """``[x IN L WHERE P]`` emits ``COLLECT_LIST(x)`` where x is the FOR alias.
        Matcher must collapse the projection back to None.
        """
        gql_text, vqe = self._lower_and_reparse("RETURN [x IN [1] WHERE x > 0] AS r")
        self.assertIn(
            "VALUE {FOR x IN [1] FILTER WHERE x > 0 RETURN COLLECT_LIST(x)}",
            gql_text,
        )
        lc = _match_lowered_comprehension(vqe)
        self.assertIsNotNone(lc, "Matcher must accept the no-projection shape")
        self.assertIsNotNone(lc.where_clause)
        self.assertIsNone(lc.projection, "Bare-alias projection must collapse to None")


if __name__ == "__main__":
    unittest.main()
