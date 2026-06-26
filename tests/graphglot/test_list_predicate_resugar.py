"""Tests for list_predicate_resugar transformation.

Re-sugars FullGQL's lowered ``EXISTS {FOR x IN L FILTER WHERE P RETURN x}``
subqueries back to Cypher's native ``any/all/none(x IN L WHERE P)`` quantifiers.

Three lowering shapes are recognized (inverse of ``generate_list_predicate`` in
``graphglot/generator/generators/cypher_compat.py``):

  any(x IN L WHERE P)  ← EXISTS {FOR x IN L FILTER WHERE P RETURN x}
  none(x IN L WHERE P) ← (NOT EXISTS {FOR x IN L FILTER WHERE P RETURN x})
  all(x IN L WHERE P)  ← (NOT EXISTS {FOR x IN L FILTER WHERE NOT (P) RETURN x})
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import ListPredicateFunction
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.transformations import (
    _match_lowered_quantifier,
    list_predicate_resugar,
)


class TestListPredicateResugar(unittest.TestCase):
    """Direct AST-level tests for list_predicate_resugar."""

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lowered_ast(self, cypher_query: str) -> ast.Expression:
        """Cypher.parse → FullGQL.generate → FullGQL.parse — produces the lowered shape."""
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        return self.fullgql.parse(gql_text)[0]

    def _find_lpf(self, tree: ast.Expression) -> ListPredicateFunction | None:
        for node in tree.dfs():
            if isinstance(node, ListPredicateFunction):
                return node
        return None

    def _count_exists(self, tree: ast.Expression) -> int:
        return sum(1 for n in tree.dfs() if isinstance(n, ast.ExistsPredicate))

    def test_any_resugar(self):
        tree = self._lowered_ast("RETURN any(x IN [1, 2, 3] WHERE x > 0) AS r")
        list_predicate_resugar(tree)
        lpf = self._find_lpf(tree)
        self.assertIsNotNone(lpf, "Expected ListPredicateFunction after transform")
        self.assertEqual(lpf.kind, ListPredicateFunction.Kind.ANY)
        self.assertEqual(self._count_exists(tree), 0, "ExistsPredicate should be gone")

    def test_none_resugar(self):
        tree = self._lowered_ast("RETURN none(x IN [1, 2, 3] WHERE x > 0) AS r")
        list_predicate_resugar(tree)
        lpf = self._find_lpf(tree)
        self.assertIsNotNone(lpf)
        self.assertEqual(lpf.kind, ListPredicateFunction.Kind.NONE)
        self.assertEqual(self._count_exists(tree), 0)

    def test_all_resugar(self):
        tree = self._lowered_ast("RETURN all(x IN [1, 2, 3] WHERE x > 0) AS r")
        list_predicate_resugar(tree)
        lpf = self._find_lpf(tree)
        self.assertIsNotNone(lpf)
        self.assertEqual(lpf.kind, ListPredicateFunction.Kind.ALL)
        self.assertEqual(self._count_exists(tree), 0)

    def test_all_predicate_is_inner_not_negated(self):
        """The ``all`` form's lowering wraps the predicate in NOT (P).  After
        re-sugar the LPF predicate must be the inner ``P``, not ``NOT (P)``.
        """
        tree = self._lowered_ast("RETURN all(x IN [1] WHERE x > 0) AS r")
        list_predicate_resugar(tree)
        lpf = self._find_lpf(tree)
        # The Cypher canonical predicate for ``x > 0`` is a BooleanValueExpression
        # wrapping a ComparisonPredicate.  No top-level NOT.
        bf = lpf.predicate.boolean_term.list_boolean_factor[0]
        self.assertFalse(bf.not_, "ALL predicate should not start with NOT after re-sugar")

    def test_idempotent(self):
        tree = self._lowered_ast("RETURN any(x IN [1] WHERE x > 0) AS r")
        list_predicate_resugar(tree)
        before = self.cypher.generate(tree)
        list_predicate_resugar(tree)
        after = self.cypher.generate(tree)
        self.assertEqual(before, after)

    def test_exists_match_untouched(self):
        """``EXISTS {MATCH (n)-[]->()}`` parses with a non-NQS body
        (``_ExistsMatchStatementBlock``) and must not be rewritten — even
        though it textually looks like a subquery, the matcher only fires
        on the canonical ``NestedQuerySpecification`` body emitted by
        :func:`generate_list_predicate`.
        """
        tree = self.fullgql.parse("MATCH (n) RETURN EXISTS {MATCH (n)-[]->()} AS r")[0]
        list_predicate_resugar(tree)
        self.assertIsNone(self._find_lpf(tree))
        self.assertGreater(self._count_exists(tree), 0, "ExistsPredicate should be preserved")

    def test_exists_for_alias_mismatch_untouched(self):
        """RETURN target must equal the FOR alias.  Mismatch → no rewrite."""
        tree = self.fullgql.parse(
            "RETURN EXISTS {FOR x IN [1] FILTER WHERE x > 0 RETURN x + 1} AS r"
        )[0]
        list_predicate_resugar(tree)
        self.assertIsNone(self._find_lpf(tree))

    def test_exists_for_no_filter_untouched(self):
        """The body must have a FilterStatement.  Missing → no rewrite."""
        tree = self.fullgql.parse("RETURN EXISTS {FOR x IN [1] RETURN x} AS r")[0]
        list_predicate_resugar(tree)
        self.assertIsNone(self._find_lpf(tree))

    def test_exists_for_extra_statement_untouched(self):
        """Body with more than FOR+FILTER → no rewrite."""
        tree = self.fullgql.parse(
            "RETURN EXISTS {FOR x IN [1] FILTER WHERE x > 0 MATCH (n) RETURN x} AS r"
        )[0]
        list_predicate_resugar(tree)
        self.assertIsNone(self._find_lpf(tree))

    # ------------------------------------------------------------------
    # End-to-end round-trip (this is what test_tck_cross_dialect verifies)
    # ------------------------------------------------------------------

    def _roundtrip(self, cypher_query: str) -> tuple[ast.Expression, ast.Expression]:
        cypher_ast_1 = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cypher_ast_1)
        gql_ast = self.fullgql.parse(gql_text)[0]
        cypher_text_2 = self.cypher.generate(gql_ast)
        cypher_ast_2 = self.cypher.parse(cypher_text_2)[0]
        return cypher_ast_1, cypher_ast_2

    def test_roundtrip_any(self):
        ast1, ast2 = self._roundtrip("RETURN any(x IN [1, 2, 3] WHERE x > 0) AS r")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_none(self):
        ast1, ast2 = self._roundtrip("RETURN none(x IN [1, 2, 3] WHERE x > 0) AS r")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_all(self):
        ast1, ast2 = self._roundtrip("RETURN all(x IN [1, 2, 3] WHERE x > 0) AS r")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_nested_in_where(self):
        """Quantifier inside WHERE — verifies re-sugar handles non-RETURN positions."""
        ast1, ast2 = self._roundtrip("MATCH (n) WHERE any(x IN [1, 2] WHERE x > n.age) RETURN n")
        self.assertEqual(ast1, ast2)

    def test_roundtrip_nested_quantifier(self):
        """``all(x WHERE none(y WHERE ...))`` — both layers re-sugar.  The
        inner quantifier survives via stale ``_parent`` pointers (see
        :func:`_peel_outer_negation` docstring), so this case still takes
        the paren-wrapped branch twice.
        """
        ast1, ast2 = self._roundtrip(
            "RETURN all(x IN [1, 2] WHERE none(y IN [3, 4] WHERE x = y)) AS r"
        )
        self.assertEqual(ast1, ast2)

    def test_roundtrip_three_level_nested(self):
        """Three-level quantifier nesting — pins that the stale-parent-pointer
        trick survives more than one peel layer.
        """
        ast1, ast2 = self._roundtrip(
            "RETURN all(x IN [1] WHERE all(y IN [2] WHERE none(z IN [3] WHERE x = y + z))) AS r"
        )
        self.assertEqual(ast1, ast2)

    def test_roundtrip_quantifier_in_and_chain(self):
        """Quantifier as a single conjunct of a multi-factor ``BooleanTerm``
        (``none(...) AND foo``).  The matcher must recognize the inner
        single-factor BT inside the paren wrapper, not the outer multi-factor
        BT carrying the AND.
        """
        ast1, ast2 = self._roundtrip(
            "MATCH (n) WHERE none(x IN [1, 2] WHERE x > 0) AND n.age > 0 RETURN n"
        )
        self.assertEqual(ast1, ast2)

    def test_roundtrip_quantifier_in_or_chain(self):
        """Quantifier as a single OR operand on a ``BooleanValueExpression``
        with non-empty ``ops``.  Same shape concern as the AND case but at
        the BVE level instead of BT.
        """
        ast1, ast2 = self._roundtrip(
            "MATCH (n) WHERE any(x IN [1, 2] WHERE x > 0) OR n.age > 0 RETURN n"
        )
        self.assertEqual(ast1, ast2)

    def test_none_with_top_level_not_predicate_normalizes_to_all(self):
        """``none(x WHERE NOT P)`` is mathematically equivalent to
        ``all(x WHERE P)`` and lowers to the same GQL text.  The round-trip
        cannot recover which surface form the source used — both collapse
        to ``all(x WHERE P)`` after re-sugar.  This documents the inherent
        normalization loss (see ``_XCD_QN`` xfails for TCK examples).
        """
        ast1, _ = self._roundtrip("RETURN none(x IN [1, 2] WHERE NOT (x = 1)) AS r")
        ast2, _ = self._roundtrip("RETURN all(x IN [1, 2] WHERE x = 1) AS r")
        # Both source forms produce the same final AST — proving the loss
        # is structural, not a bug in this transform.
        _, ast1_rt = self._roundtrip("RETURN none(x IN [1, 2] WHERE NOT (x = 1)) AS r")
        _, ast2_rt = self._roundtrip("RETURN all(x IN [1, 2] WHERE x = 1) AS r")
        self.assertEqual(ast1_rt, ast2_rt)
        self.assertNotEqual(ast1, ast1_rt)  # original ``none`` form lost on round-trip
        self.assertEqual(ast2, ast2_rt)  # ``all`` form is the canonical normalization

    def test_roundtrip_none_with_multi_clause_predicate(self):
        """Multi-clause WHERE predicates round-trip without false ALL
        detection — the matcher must not interpret an inner AND/OR/IS NULL
        as the synthetic ``NOT (P)`` wrapper.
        """
        ast1, ast2 = self._roundtrip("RETURN none(x IN [1, 2, 3] WHERE x > 0 AND x < 10) AS r")
        self.assertEqual(ast1, ast2)


class TestFullGQLEmissionShape(unittest.TestCase):
    """Pin the canonical lowered shape FullGQL emits for any/all/none.

    ``list_predicate_resugar`` (and its ``_match_lowered_quantifier``) recognize
    exactly the three shapes emitted by
    ``graphglot/generator/generators/cypher_compat.py:generate_list_predicate``.
    If that emitter ever changes its output — different keyword order, dropped
    parens, alternate body shape — these tests fail loudly, signalling that the
    matcher needs an update before silent round-trip regressions reappear in
    the ``_XCD_LP`` / ``_XCD_FOR`` buckets.

    Each test pins **both** layers of the contract:

    1. The exact GQL text produced by ``FullGQL.generate``.
    2. The ``_match_lowered_quantifier`` accepts the re-parsed AST and produces
       the correct ``Kind``.

    A FullGQL change that breaks (1) but not (2) — or vice versa — is still
    caught by one of the two assertions.
    """

    def setUp(self):
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _lower_and_reparse(self, cypher_query: str) -> tuple[str, ast.ExistsPredicate]:
        """Lower *cypher_query* through FullGQL and return ``(gql_text, exists_node)``."""
        cy_ast = self.cypher.parse(cypher_query)[0]
        gql_text = self.fullgql.generate(cy_ast)
        gql_ast = self.fullgql.parse(gql_text)[0]
        exists = next(n for n in gql_ast.dfs() if isinstance(n, ast.ExistsPredicate))
        return gql_text, exists

    def test_any_lowers_to_bare_exists_for_filter_return(self):
        """``any(x WHERE P)`` emits ``EXISTS {FOR x IN L FILTER WHERE P RETURN x}``."""
        gql_text, exists = self._lower_and_reparse("RETURN any(x IN [1] WHERE x > 0) AS r")
        # Text shape — exactly this, no parens, no NOT.
        self.assertIn("EXISTS {FOR x IN [1] FILTER WHERE x > 0 RETURN x}", gql_text)
        self.assertNotIn("NOT EXISTS", gql_text)
        # Matcher accepts and identifies the kind.
        match = _match_lowered_quantifier(exists)
        self.assertIsNotNone(match, "Matcher must accept the canonical ANY shape")
        _, lpf = match
        self.assertEqual(lpf.kind, ListPredicateFunction.Kind.ANY)

    def test_none_lowers_to_paren_wrapped_not_exists(self):
        """``none(x WHERE P)`` emits ``(NOT EXISTS {FOR x IN L FILTER WHERE P RETURN x})``."""
        gql_text, exists = self._lower_and_reparse("RETURN none(x IN [1] WHERE x > 0) AS r")
        # Text shape — outer parens around the NOT EXISTS form.
        self.assertIn(
            "(NOT EXISTS {FOR x IN [1] FILTER WHERE x > 0 RETURN x})",
            gql_text,
        )
        # Matcher accepts and identifies the kind.
        match = _match_lowered_quantifier(exists)
        self.assertIsNotNone(match, "Matcher must accept the canonical NONE shape")
        _, lpf = match
        self.assertEqual(lpf.kind, ListPredicateFunction.Kind.NONE)

    def test_all_lowers_to_paren_wrapped_not_exists_with_inner_not(self):
        """``all(x WHERE P)`` emits ``(NOT EXISTS {FOR x IN L FILTER WHERE NOT (P) RETURN x})``."""
        gql_text, exists = self._lower_and_reparse("RETURN all(x IN [1] WHERE x > 0) AS r")
        # Text shape — outer parens + inner NOT (P).
        self.assertIn(
            "(NOT EXISTS {FOR x IN [1] FILTER WHERE NOT (x > 0) RETURN x})",
            gql_text,
        )
        # Matcher accepts, identifies kind, and recovers the un-negated inner predicate.
        match = _match_lowered_quantifier(exists)
        self.assertIsNotNone(match, "Matcher must accept the canonical ALL shape")
        _, lpf = match
        self.assertEqual(lpf.kind, ListPredicateFunction.Kind.ALL)
        # The recovered predicate must be the inner ``P``, not ``NOT (P)``.
        bf = lpf.predicate.boolean_term.list_boolean_factor[0]
        self.assertFalse(bf.not_, "Inner predicate must have NOT peeled")


if __name__ == "__main__":
    unittest.main()
