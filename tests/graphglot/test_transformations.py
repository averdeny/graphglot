"""Tests for post-parse AST transformations (Plan 036).

Covers:
- with_to_next: Cypher WITH → GQL RETURN...NEXT chain
- Dialect.transform() integration
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import CypherWithStatement
from graphglot.dialect.base import Dialect
from graphglot.dialect.neo4j import Neo4j
from graphglot.transformations import with_to_next


class TestWithToNext(unittest.TestCase):
    """Test with_to_next transformation function."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse_one(self, query: str) -> ast.Expression:
        trees = self.neo4j.parse(query)
        self.assertEqual(len(trees), 1)
        return trees[0]

    def _has_cypher_with(self, tree: ast.Expression) -> bool:
        return any(isinstance(n, CypherWithStatement) for n in tree.dfs())

    def _transform(self, query: str) -> ast.Expression:
        tree = self._parse_one(query)
        return with_to_next(tree)

    def _find_block(self, tree: ast.Expression) -> ast.StatementBlock:
        """Find the innermost StatementBlock produced by the transformation."""
        for node in tree.dfs():
            if isinstance(node, ast.StatementBlock) and node.list_next_statement:
                return node
        self.fail("No StatementBlock with NextStatements found in tree")

    # ------------------------------------------------------------------
    # 1. Simple WITH → StatementBlock with 1 NextStatement
    # ------------------------------------------------------------------
    def test_simple_with_produces_statement_block(self):
        result = self._transform("MATCH (n) WITH n RETURN n")
        block = self._find_block(result)
        self.assertEqual(len(block.list_next_statement), 1)

    # ------------------------------------------------------------------
    # 2. WITH body → ReturnStatement
    # ------------------------------------------------------------------
    def test_with_alias_becomes_return(self):
        result = self._transform("MATCH (n) WITH n.age AS age RETURN age")
        block = self._find_block(result)
        # The first statement should have a ReturnStatement with the WITH body
        stmt = block.statement
        self.assertIsInstance(stmt, ast.CompositeQueryExpression)
        alqs = stmt.left_composite_query_primary
        self.assertIsInstance(alqs, ast.AmbientLinearQueryStatement)
        inner = alqs.ambient_linear_query_statement
        self.assertIsInstance(
            inner,
            ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement,
        )
        prs = inner.primitive_result_statement
        self.assertIsInstance(prs, ast.PrimitiveResultStatement)
        ret = prs.primitive_result_statement
        self.assertIsInstance(
            ret, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement
        )
        self.assertIsInstance(ret.return_statement, ast.ReturnStatement)

    # ------------------------------------------------------------------
    # 3. WHERE after WITH → FilterStatement in next segment
    # ------------------------------------------------------------------
    def test_where_after_with_becomes_filter(self):
        result = self._transform("MATCH (n) WITH n WHERE n.age > 25 RETURN n")
        block = self._find_block(result)
        # The next statement segment should contain a FilterStatement
        next_stmt = block.list_next_statement[0]
        cqe = next_stmt.statement
        alqs = cqe.left_composite_query_primary
        inner = alqs.ambient_linear_query_statement
        slqs = inner.simple_linear_query_statement
        self.assertIsNotNone(slqs)
        has_filter = any(
            isinstance(s, ast.FilterStatement) for s in slqs.list_simple_query_statement
        )
        self.assertTrue(has_filter, "WHERE after WITH should become FilterStatement")

    # ------------------------------------------------------------------
    # 4. Chained WITH → 2 NextStatements
    # ------------------------------------------------------------------
    def test_chained_with_produces_multiple_next(self):
        result = self._transform("MATCH (n) WITH n WITH n.name AS name RETURN name")
        block = self._find_block(result)
        self.assertEqual(len(block.list_next_statement), 2)

    # ------------------------------------------------------------------
    # 5. DISTINCT preserved in ReturnStatementBody
    # ------------------------------------------------------------------
    def test_distinct_preserved(self):
        result = self._transform("MATCH (n) WITH DISTINCT n RETURN n")
        block = self._find_block(result)
        stmt = block.statement
        alqs = stmt.left_composite_query_primary
        inner = alqs.ambient_linear_query_statement
        prs = inner.primitive_result_statement
        ret_inner = prs.primitive_result_statement
        body = ret_inner.return_statement.return_statement_body
        inner_body = body.return_statement_body
        self.assertIsNotNone(inner_body.set_quantifier)

    # ------------------------------------------------------------------
    # 6. ORDER BY/LIMIT on WITH → OrderByAndPageStatement
    # ------------------------------------------------------------------
    def test_order_by_limit_on_with(self):
        result = self._transform("MATCH (n) WITH n ORDER BY n.age LIMIT 10 RETURN n")
        block = self._find_block(result)
        stmt = block.statement
        alqs = stmt.left_composite_query_primary
        inner = alqs.ambient_linear_query_statement
        prs = inner.primitive_result_statement
        ret_inner = prs.primitive_result_statement
        self.assertIsNotNone(ret_inner.order_by_and_page_statement)

    # ------------------------------------------------------------------
    # 7. No WITH → tree unchanged (passthrough)
    # ------------------------------------------------------------------
    def test_no_with_passthrough(self):
        original = self._parse_one("MATCH (n) RETURN n")
        result = with_to_next(original.deep_copy())
        # Should NOT have any StatementBlock with NextStatements
        has_block = any(
            isinstance(n, ast.StatementBlock) and n.list_next_statement for n in result.dfs()
        )
        self.assertFalse(has_block)

    # ------------------------------------------------------------------
    # 8. WITH * (star projection)
    # ------------------------------------------------------------------
    def test_with_star(self):
        result = self._transform("MATCH (n) WITH * RETURN n")
        block = self._find_block(result)
        self.assertEqual(len(block.list_next_statement), 1)

    # ------------------------------------------------------------------
    # 9. Roundtrip: parse Cypher → transform → generate GQL
    # ------------------------------------------------------------------
    def test_roundtrip_generate_gql(self):
        tree = self._parse_one("MATCH (n) WITH n.age AS age RETURN age")
        transformed = with_to_next(tree)
        gql_dialect = Dialect()
        gql_text = gql_dialect.generate(transformed)
        self.assertIn("RETURN", gql_text)
        self.assertIn("NEXT", gql_text)
        self.assertNotIn("WITH", gql_text)

    # ------------------------------------------------------------------
    # 10. WITH + UNWIND (FOR) in chain
    # ------------------------------------------------------------------
    def test_with_followed_by_unwind(self):
        result = self._transform("MATCH (n) WITH n UNWIND [1, 2] AS x RETURN x")
        block = self._find_block(result)
        next_stmt = block.list_next_statement[0]
        cqe = next_stmt.statement
        alqs = cqe.left_composite_query_primary
        inner = alqs.ambient_linear_query_statement
        slqs = inner.simple_linear_query_statement
        self.assertIsNotNone(slqs)
        has_for = any(isinstance(s, ast.ForStatement) for s in slqs.list_simple_query_statement)
        self.assertTrue(has_for, "UNWIND after WITH should be ForStatement in next segment")

    # ------------------------------------------------------------------
    # 11. Multiple MATCH before WITH → all in first segment
    # ------------------------------------------------------------------
    def test_multiple_match_before_with(self):
        result = self._transform("MATCH (n) MATCH (m) WITH n, m RETURN n, m")
        block = self._find_block(result)
        stmt = block.statement
        alqs = stmt.left_composite_query_primary
        inner = alqs.ambient_linear_query_statement
        slqs = inner.simple_linear_query_statement
        self.assertIsNotNone(slqs)
        match_count = sum(
            1 for s in slqs.list_simple_query_statement if isinstance(s, ast.MatchStatement)
        )
        self.assertEqual(match_count, 2)

    # ------------------------------------------------------------------
    # 12. WITH with aggregation
    # ------------------------------------------------------------------
    def test_with_aggregation(self):
        result = self._transform("MATCH (n) WITH count(n) AS c RETURN c")
        block = self._find_block(result)
        self.assertIsNotNone(block.list_next_statement)
        self.assertFalse(self._has_cypher_with(result))

    # ------------------------------------------------------------------
    # 13. Idempotency: transform applied twice produces same result
    # ------------------------------------------------------------------
    def test_idempotency(self):
        tree = self._parse_one("MATCH (n) WITH n RETURN n")
        once = with_to_next(tree.deep_copy())
        twice = with_to_next(once.deep_copy())
        gql_dialect = Dialect()
        text1 = gql_dialect.generate(once)
        text2 = gql_dialect.generate(twice)
        self.assertEqual(text1, text2)

    # ------------------------------------------------------------------
    # 14. dialect.transform() integration
    # ------------------------------------------------------------------
    def test_dialect_transform_neo4j(self):
        """Neo4j dialect applies with_to_next via transform()."""
        trees = self.neo4j.parse("MATCH (n) WITH n RETURN n")
        transformed = self.neo4j.transform(trees)
        self.assertEqual(len(transformed), 1)
        self.assertFalse(self._has_cypher_with(transformed[0]))
        block = self._find_block(transformed[0])
        self.assertIsNotNone(block)

    def test_dialect_transform_base_noop(self):
        """Base Dialect.transform() is a no-op."""
        base = Dialect()
        trees = base.parse("MATCH (n) RETURN n")
        transformed = base.transform(trees)
        self.assertEqual(len(transformed), len(trees))
        for orig, trans in zip(trees, transformed, strict=False):
            self.assertIs(orig, trans)


class TestCypherWithOwnsWhere(unittest.TestCase):
    """CypherWithStatement should own its WHERE clause directly.

    After parsing ``WITH n WHERE n.age > 25``, the WHERE should be stored
    on ``CypherWithStatement.where_clause`` — NOT as a sibling
    ``FilterStatement`` in the ``SimpleLinearQueryStatement``.

    This enables correct generation in both paths:
    - Non-transformed: ``WITH n WHERE n.age > 25`` (Cypher)
    - Transformed: ``RETURN n NEXT FILTER WHERE n.age > 25`` (GQL)
    """

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse_one(self, query: str) -> ast.Expression:
        trees = self.neo4j.parse(query)
        self.assertEqual(len(trees), 1)
        return trees[0]

    def _find_with_stmts(self, tree: ast.Expression) -> list[CypherWithStatement]:
        return [n for n in tree.dfs() if isinstance(n, CypherWithStatement)]

    def _find_filter_siblings(self, tree: ast.Expression) -> list[ast.FilterStatement]:
        """Find FilterStatements that are siblings of CypherWithStatement."""
        filters = []
        for node in tree.dfs():
            if not isinstance(node, ast.SimpleLinearQueryStatement):
                continue
            stmts = node.list_simple_query_statement
            has_with = any(isinstance(s, CypherWithStatement) for s in stmts)
            if has_with:
                filters.extend(s for s in stmts if isinstance(s, ast.FilterStatement))
        return filters

    # ------------------------------------------------------------------
    # Parsing: WHERE absorbed into CypherWithStatement
    # ------------------------------------------------------------------

    def test_parse_with_where_has_where_clause(self):
        """WITH n WHERE ... → CypherWithStatement.where_clause is set."""
        tree = self._parse_one("MATCH (n) WITH n WHERE n.age > 25 RETURN n")
        withs = self._find_with_stmts(tree)
        self.assertEqual(len(withs), 1)
        self.assertIsNotNone(
            withs[0].where_clause,
            "CypherWithStatement should own the WHERE clause",
        )

    def test_parse_with_where_no_filter_sibling(self):
        """WHERE after WITH must NOT produce a sibling FilterStatement."""
        tree = self._parse_one("MATCH (n) WITH n WHERE n.age > 25 RETURN n")
        siblings = self._find_filter_siblings(tree)
        self.assertEqual(
            len(siblings),
            0,
            "FilterStatement should not appear as sibling of CypherWithStatement",
        )

    def test_parse_with_no_where_has_none(self):
        """WITH n (no WHERE) → where_clause is None."""
        tree = self._parse_one("MATCH (n) WITH n RETURN n")
        withs = self._find_with_stmts(tree)
        self.assertEqual(len(withs), 1)
        self.assertIsNone(withs[0].where_clause)

    def test_parse_with_order_by_and_where(self):
        """WITH n ORDER BY n.age WHERE n.age > 25 → both OBPS and where_clause set."""
        tree = self._parse_one("MATCH (n) WITH n ORDER BY n.age WHERE n.age > 25 RETURN n")
        withs = self._find_with_stmts(tree)
        self.assertEqual(len(withs), 1)
        self.assertIsNotNone(withs[0].order_by_and_page_statement)
        self.assertIsNotNone(withs[0].where_clause)

    def test_parse_chained_with_where(self):
        """Chained WITH...WHERE: each CypherWithStatement owns its WHERE."""
        tree = self._parse_one(
            "MATCH (n) WITH n WHERE n.age > 25 "
            "WITH n.name AS name WHERE name STARTS WITH 'A' RETURN name"
        )
        withs = self._find_with_stmts(tree)
        self.assertEqual(len(withs), 2)
        self.assertIsNotNone(withs[0].where_clause, "first WITH should own WHERE")
        self.assertIsNotNone(withs[1].where_clause, "second WITH should own WHERE")
        # No FilterStatement siblings
        siblings = self._find_filter_siblings(tree)
        self.assertEqual(len(siblings), 0)

    # ------------------------------------------------------------------
    # Non-transformed generation: WITH ... WHERE (Cypher output)
    # ------------------------------------------------------------------

    def test_generate_with_where_nontransformed(self):
        """Non-transformed: WITH n WHERE ... generates as Cypher WITH ... WHERE."""
        tree = self._parse_one("MATCH (n) WITH n WHERE n.age > 25 RETURN n")
        generated = self.neo4j.generate(tree)
        # Should produce WITH ... WHERE, NOT WITH ... FILTER WHERE
        self.assertIn("WITH", generated)
        self.assertIn("WHERE n.age > 25", generated)
        self.assertNotIn("FILTER", generated)

    def test_generate_chained_with_where_nontransformed(self):
        """Non-transformed chained WITH...WHERE generates correctly."""
        tree = self._parse_one("MATCH (n) WITH n WHERE n.age > 25 WITH n.name AS name RETURN name")
        generated = self.neo4j.generate(tree)
        self.assertIn("WITH", generated)
        self.assertIn("WHERE", generated)
        self.assertNotIn("FILTER", generated)

    # ------------------------------------------------------------------
    # Transformed generation: RETURN...NEXT FILTER WHERE (GQL output)
    # ------------------------------------------------------------------

    def test_generate_transformed_with_where(self):
        """Transformed: WITH n WHERE → RETURN n NEXT FILTER WHERE."""
        tree = self._parse_one("MATCH (n) WITH n WHERE n.age > 25 RETURN n.name AS name")
        transformed = self.neo4j.transform([tree])
        generated = self.neo4j.generate(transformed[0])
        self.assertIn("NEXT", generated)
        self.assertIn("FILTER WHERE", generated)
        self.assertNotIn("WITH", generated)

    def test_generate_transformed_chained_with_where(self):
        """Transformed chained: each WHERE becomes FILTER WHERE after NEXT."""
        tree = self._parse_one(
            "MATCH (n) WITH n.age AS age WHERE age > 25 WITH count(age) AS c RETURN c"
        )
        transformed = self.neo4j.transform([tree])
        generated = self.neo4j.generate(transformed[0])
        self.assertIn("NEXT", generated)
        self.assertIn("FILTER WHERE", generated)
        self.assertNotIn("WITH", generated)

    # ------------------------------------------------------------------
    # Transformation: WHERE extracted into FilterStatement in NextStatement
    # ------------------------------------------------------------------

    def test_transform_where_becomes_filter_in_next(self):
        """Transformation extracts where_clause → FilterStatement in NextStatement."""
        tree = self._parse_one("MATCH (n) WITH n WHERE n.age > 25 RETURN n")
        result = with_to_next(tree)
        # The transformed tree should have a FilterStatement inside a NextStatement
        filters = list(result.find_all(ast.FilterStatement))
        self.assertGreaterEqual(len(filters), 1, "WHERE should become FilterStatement")
        # But NO CypherWithStatement should remain
        withs = [n for n in result.dfs() if isinstance(n, CypherWithStatement)]
        self.assertEqual(len(withs), 0, "No CypherWithStatement should remain")

    # ------------------------------------------------------------------
    # Edge case: no Cypher FilterStatement generator override needed
    # ------------------------------------------------------------------

    def test_no_cypher_filter_override_needed(self):
        """Default GQL FilterStatement generator handles NEXT context correctly.

        After the proper fix, the Cypher Generator should use the same
        FilterStatement generator as the base GQL Generator (i.e., no
        Cypher-specific override).
        """
        from graphglot.generator.base import Generator as BaseGen

        cypher_gen_cls = self.neo4j.generator_class
        base_fn = BaseGen.GENERATORS.get(ast.FilterStatement)
        cypher_fn = cypher_gen_cls.GENERATORS.get(ast.FilterStatement)
        self.assertIs(
            cypher_fn,
            base_fn,
            "Cypher should not override FilterStatement — "
            "the default GQL generator handles FILTER WHERE correctly",
        )
