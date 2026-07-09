"""Tests for Cypher list/string concatenation generation.

Cypher uses ``+`` for list and string concatenation; GQL uses ``||``.  The
base generators for ``ListValueExpression`` and ``ConcatenationValueExpression``
join with ``" || "`` per the GQL spec, so CypherDialect overrides them to emit
``" + "``.  This keeps the Cypher → GQL → Cypher round trip AST-stable: the
Cypher parser rebuilds the canonical ``ArithmeticValueExpression`` from the
``+`` form instead of a divergent ``ListValueExpression`` /
``ConcatenationValueExpression`` from ``||``.
"""

import unittest

from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.dialect.neo4j import Neo4j


class TestCypherListConcat(unittest.TestCase):
    def setUp(self) -> None:
        self.cypher = CypherDialect()
        self.fullgql = FullGQL()

    def _roundtrip_ast(self, query: str):
        """Cypher → GQL → Cypher, returning (source_ast, final_ast)."""
        source_ast = self.cypher.parse(query)[0]
        gql_text = self.fullgql.generate(source_ast)
        gql_ast = self.fullgql.parse(gql_text)[0]
        cypher_text = self.cypher.generate(gql_ast)
        final_ast = self.cypher.parse(cypher_text)[0]
        return source_ast, final_ast

    def test_single_list_no_concat_unchanged(self) -> None:
        """A plain list literal (single primary) must not gain a ``+``."""
        gql_ast = self.fullgql.parse("RETURN [1, 2, 3] AS r")[0]
        out = self.cypher.generate(gql_ast)
        self.assertIn("[1, 2, 3]", out)
        self.assertNotIn("+", out)

    def test_two_lists_emit_plus(self) -> None:
        """FullGQL ``[1, 2] || [3, 4]`` lowers to Cypher ``[1, 2] + [3, 4]``."""
        gql_ast = self.fullgql.parse("RETURN [1, 2] || [3, 4] AS r")[0]
        out = self.cypher.generate(gql_ast)
        self.assertIn("[1, 2] + [3, 4]", out)
        self.assertNotIn("||", out)

    def test_three_lists_emit_plus_chain(self) -> None:
        """Concatenation chains render with ``+`` between every operand."""
        gql_ast = self.fullgql.parse("RETURN [1] || [2] || [3] AS r")[0]
        out = self.cypher.generate(gql_ast)
        self.assertIn("[1] + [2] + [3]", out)
        self.assertNotIn("||", out)

    def test_roundtrip_list_concat(self) -> None:
        """RETURN-position list concat round-trips AST-equal."""
        source_ast, final_ast = self._roundtrip_ast("RETURN [1, 10, 100] + [4, 5] AS r")
        self.assertEqual(source_ast, final_ast)

    def test_roundtrip_inside_set_clause(self) -> None:
        """SET-clause concat (``ConcatenationValueExpression``) round-trips."""
        source_ast, final_ast = self._roundtrip_ast("MATCH (a) SET a.numbers = a.numbers + [4, 5]")
        self.assertEqual(source_ast, final_ast)

    def test_string_concat_unaffected(self) -> None:
        """String concat guards the ConcatenationValueExpression override."""
        source_ast, final_ast = self._roundtrip_ast("RETURN 'a' + 'b' AS r")
        self.assertEqual(source_ast, final_ast)

    def test_numeric_add_unaffected(self) -> None:
        """Numeric addition must not be rewritten by the concat overrides."""
        source_ast, final_ast = self._roundtrip_ast("RETURN 1 + 2 AS r")
        self.assertEqual(source_ast, final_ast)

    def test_concat_as_comparison_operand_roundtrips(self) -> None:
        """Concat nested in a larger expression keeps correct precedence."""
        source_ast, final_ast = self._roundtrip_ast(
            "MATCH (a) WHERE a.tags + ['x'] = ['y'] RETURN a"
        )
        self.assertEqual(source_ast, final_ast)

    def test_neo4j_inherits_concat_override(self) -> None:
        """Neo4j inherits CypherDialect's ``+`` overrides (no separate wiring)."""
        gql_ast = self.fullgql.parse("RETURN [1, 2] || [3, 4] AS r")[0]
        self.assertIn("[1, 2] + [3, 4]", Neo4j().generate(gql_ast))


if __name__ == "__main__":
    unittest.main()
