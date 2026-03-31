"""Tests for post-parse AST transformations.

Covers:
- with_to_next: Cypher WITH → GQL RETURN...NEXT chain
- resolve_ambiguous: Ambiguous AST → concrete GQL types
- Dialect.transform() integration
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import CypherWithStatement
from graphglot.dialect.base import Dialect
from graphglot.dialect.neo4j import Neo4j
from graphglot.transformations import resolve_ambiguous, with_to_next
from graphglot.typing import ExternalContext, GqlType, TypeAnnotator


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

    def test_dialect_transform_base_applies_resolve(self):
        """Base Dialect.transform() applies resolve_ambiguous (deep-copies)."""
        base = Dialect()
        trees = base.parse("MATCH (n) RETURN n")
        transformed = base.transform(trees)
        self.assertEqual(len(transformed), len(trees))
        # Deep-copied — NOT the same objects
        for orig, trans in zip(trees, transformed, strict=False):
            self.assertIsNot(orig, trans)
        # But generates the same output
        for orig, trans in zip(trees, transformed, strict=False):
            self.assertEqual(base.generate(orig), base.generate(trans))


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


class TestResolveAmbiguous(unittest.TestCase):
    """Test resolve_ambiguous transformation function."""

    def setUp(self):
        self.dialect = Dialect()

    def _parse_one(self, query: str, *, dialect=None) -> ast.Expression:
        d = dialect or self.dialect
        trees = d.parse(query)
        self.assertEqual(len(trees), 1)
        return trees[0]

    def _find_types(self, tree: ast.Expression, cls: type) -> list:
        return [n for n in tree.dfs() if isinstance(n, cls)]

    # ------------------------------------------------------------------
    # Arithmetic → NumericValueExpression
    # ------------------------------------------------------------------

    def test_arithmetic_numeric_resolved(self):
        """RETURN 1 + 2 → ArithmeticVE replaced by NumericVE."""
        tree = self._parse_one("RETURN 1 + 2")
        result = resolve_ambiguous(tree)
        nve = self._find_types(result, ast.NumericValueExpression)
        self.assertGreaterEqual(len(nve), 1, "Should have NumericValueExpression")
        ave = self._find_types(result, ast.ArithmeticValueExpression)
        self.assertEqual(len(ave), 0, "ArithmeticValueExpression should be gone")

    def test_arithmetic_multiply_resolved(self):
        """RETURN 3 * 4 → ArithmeticVE replaced by NumericVE."""
        tree = self._parse_one("RETURN 3 * 4")
        result = resolve_ambiguous(tree)
        nve = self._find_types(result, ast.NumericValueExpression)
        self.assertGreaterEqual(len(nve), 1, "Should have NumericValueExpression")
        ave = self._find_types(result, ast.ArithmeticValueExpression)
        self.assertEqual(len(ave), 0, "ArithmeticValueExpression should be gone")

    def test_arithmetic_unknown_stays(self):
        """MATCH (n) RETURN n.x + n.y → stays ArithmeticVE (unknown type)."""
        tree = self._parse_one("MATCH (n) RETURN n.x + n.y")
        result = resolve_ambiguous(tree)
        ave = self._find_types(result, ast.ArithmeticValueExpression)
        self.assertGreaterEqual(len(ave), 1, "ArithmeticVE should remain")

    def test_arithmetic_bare_unchanged(self):
        """RETURN 42 → no NumericValueExpression produced (no arithmetic ops)."""
        tree = self._parse_one("RETURN 42")
        result = resolve_ambiguous(tree)
        nve = self._find_types(result, ast.NumericValueExpression)
        self.assertEqual(len(nve), 0, "Bare literal should not produce NVE")

    # ------------------------------------------------------------------
    # Concatenation → typed concatenation
    # ------------------------------------------------------------------

    def test_concat_cast_string_resolved(self):
        """CAST-to-STRING || CAST-to-STRING → CharacterStringValueExpression."""
        tree = self._parse_one("RETURN CAST(1 AS STRING) || CAST(2 AS STRING)")
        result = resolve_ambiguous(tree)
        csv = self._find_types(result, ast.CharacterStringValueExpression)
        self.assertGreaterEqual(len(csv), 1, "Should have CharacterStringVE")
        cve = self._find_types(result, ast.ConcatenationValueExpression)
        self.assertEqual(len(cve), 0, "ConcatenationVE should be gone")

    def test_concat_path_vars_resolved(self):
        """Path variable || path variable → PathValueExpression."""
        tree = self._parse_one("MATCH p = (a)-[r]->(b), q2 = (c)-[s]->(d) RETURN p || q2")
        result = resolve_ambiguous(tree)
        pve = self._find_types(result, ast.PathValueExpression)
        self.assertGreaterEqual(len(pve), 1, "Should have PathValueExpression")
        cve = self._find_types(result, ast.ConcatenationValueExpression)
        self.assertEqual(len(cve), 0, "ConcatenationVE should be gone")

    def test_concat_unknown_stays(self):
        """MATCH (n) RETURN n.x || n.y → stays ConcatenationVE (unknown type)."""
        tree = self._parse_one("MATCH (n) RETURN n.x || n.y")
        result = resolve_ambiguous(tree)
        cve = self._find_types(result, ast.ConcatenationValueExpression)
        self.assertGreaterEqual(len(cve), 1, "ConcatenationVE should remain")

    # ------------------------------------------------------------------
    # ABS → typed ABS
    # ------------------------------------------------------------------

    def test_abs_numeric_resolved(self):
        """RETURN ABS(1 + 2) → AbsoluteValueExpression wrapping NumericVE."""
        tree = self._parse_one("RETURN ABS(1 + 2)")
        result = resolve_ambiguous(tree)
        avs = self._find_types(result, ast.AbsoluteValueExpression)
        self.assertGreaterEqual(len(avs), 1, "Should have AbsoluteValueExpression")
        self.assertIsInstance(avs[0].numeric_value_expression, ast.NumericValueExpression)
        aaf = self._find_types(result, ast.ArithmeticAbsoluteValueFunction)
        self.assertEqual(len(aaf), 0, "ArithmeticAbsoluteValueFunction should be gone")

    def test_abs_unknown_stays(self):
        """MATCH (n) RETURN ABS(n.x + n.y) → stays ArithmeticAbsoluteValueFunction."""
        tree = self._parse_one("MATCH (n) RETURN ABS(n.x + n.y)")
        result = resolve_ambiguous(tree)
        aaf = self._find_types(result, ast.ArithmeticAbsoluteValueFunction)
        self.assertGreaterEqual(len(aaf), 1, "ArithAbsVF should remain")

    # ------------------------------------------------------------------
    # Datetime arithmetic
    # ------------------------------------------------------------------

    def test_arithmetic_datetime_resolved(self):
        """date + duration → DatetimeValueExpression (with ExternalContext)."""
        ctx = ExternalContext(
            property_types={
                ("Person", "start_date"): GqlType.date(),
                ("Person", "dur"): GqlType.duration(),
            }
        )
        tree = self._parse_one("MATCH (n:Person) RETURN n.start_date + n.dur")
        # Pre-annotate with context, then use internal helper
        TypeAnnotator(external_context=ctx).annotate(tree)
        from graphglot.transformations import _resolve_ambiguous_nodes

        _resolve_ambiguous_nodes(tree)
        dtve = self._find_types(tree, ast.DatetimeValueExpression)
        self.assertGreaterEqual(len(dtve), 1, "Should have DatetimeValueExpression")
        ave = self._find_types(tree, ast.ArithmeticValueExpression)
        self.assertEqual(len(ave), 0, "ArithmeticVE should be gone")

    # ------------------------------------------------------------------
    # Preservation / idempotency
    # ------------------------------------------------------------------

    def test_span_preserved(self):
        """Replacement node preserves source span tokens."""
        tree = self._parse_one("RETURN 1 + 2")
        # Find the ArithmeticVE and note its span
        ave = self._find_types(tree, ast.ArithmeticValueExpression)
        self.assertTrue(len(ave) > 0, "Need ArithmeticVE to test span")
        original_span = ave[0].source_span
        result = resolve_ambiguous(tree)
        nve = self._find_types(result, ast.NumericValueExpression)
        self.assertTrue(len(nve) > 0)
        self.assertEqual(nve[0].source_span, original_span)

    def test_idempotent(self):
        """Running resolve_ambiguous twice produces same generated output."""
        tree = self._parse_one("RETURN 1 + 2")
        once = resolve_ambiguous(tree.deep_copy())
        twice = resolve_ambiguous(once.deep_copy())
        text1 = self.dialect.generate(once)
        text2 = self.dialect.generate(twice)
        self.assertEqual(text1, text2)

    def test_resolved_type_preserved(self):
        """Replacement node carries over _resolved_type from original."""
        tree = self._parse_one("RETURN 1 + 2")
        # Annotate to get the resolved type
        TypeAnnotator().annotate(tree)
        ave = self._find_types(tree, ast.ArithmeticValueExpression)
        self.assertTrue(len(ave) > 0)
        original_type = ave[0]._resolved_type
        self.assertIsNotNone(original_type)
        result = resolve_ambiguous(tree)
        nve = self._find_types(result, ast.NumericValueExpression)
        self.assertTrue(len(nve) > 0)
        self.assertEqual(nve[0]._resolved_type, original_type)


class TestCypherToGqlGeneration(unittest.TestCase):
    """Test cross-dialect generation: Cypher nodes → GQL output via base generators."""

    def setUp(self):
        self.neo4j = Neo4j()
        self.gql = Dialect.get_or_raise("fullgql")

    def _gql(self, query: str) -> str:
        """Parse with Neo4j, generate with FullGQL."""
        trees = self.neo4j.parse(query)
        return self.gql.generate(trees[0])

    def _cypher(self, query: str) -> str:
        """Parse and roundtrip with Neo4j."""
        trees = self.neo4j.parse(query)
        return self.neo4j.generate(trees[0])

    # ------------------------------------------------------------------
    # Chained comparison
    # ------------------------------------------------------------------

    def test_chained_lt_generates_and(self):
        result = self._gql("MATCH (n) WHERE 1 < n.num < 3 RETURN n.num")
        self.assertIn("AND", result)
        self.assertNotIn("< 3", result.split("AND")[0])  # split into two comparisons

    def test_chained_roundtrip_preserves_syntax(self):
        result = self._cypher("MATCH (n) WHERE 1 < n.num < 3 RETURN n.num")
        self.assertIn("1 < n.num < 3", result)

    # ------------------------------------------------------------------
    # STARTS WITH / ENDS WITH
    # ------------------------------------------------------------------

    def test_starts_with_generates_left(self):
        result = self._gql("MATCH (a) WHERE a.name STARTS WITH 'A' RETURN a")
        self.assertIn("LEFT(", result)
        self.assertIn("CHAR_LENGTH(", result)

    def test_ends_with_generates_right(self):
        result = self._gql("MATCH (a) WHERE a.name ENDS WITH 'Z' RETURN a")
        self.assertIn("RIGHT(", result)
        self.assertIn("CHAR_LENGTH(", result)

    def test_contains_raises_for_gql(self):
        trees = self.neo4j.parse("MATCH (a) WHERE a.name CONTAINS 'x' RETURN a")
        with self.assertRaises(NotImplementedError):
            self.gql.generate(trees[0])

    def test_starts_with_roundtrip_preserves_syntax(self):
        result = self._cypher("MATCH (a) WHERE a.name STARTS WITH 'A' RETURN a")
        self.assertIn("STARTS WITH", result)

    # ------------------------------------------------------------------
    # Pattern predicate
    # ------------------------------------------------------------------

    def test_pattern_predicate_generates_exists(self):
        result = self._gql("MATCH (a), (b) WHERE (a)-[:T]->(b) RETURN b")
        self.assertIn("EXISTS", result)

    def test_negated_pattern_generates_not_exists(self):
        result = self._gql("MATCH (n) WHERE NOT (n)-[:KNOWS]->() RETURN n")
        self.assertIn("NOT", result)
        self.assertIn("EXISTS", result)

    # ------------------------------------------------------------------
    # List predicates
    # ------------------------------------------------------------------

    def test_any_generates_exists(self):
        result = self._gql("MATCH (n) WHERE any(x IN n.tags WHERE x = 'a') RETURN n")
        self.assertIn("EXISTS", result)
        self.assertNotIn("NOT EXISTS", result)

    def test_none_generates_not_exists(self):
        result = self._gql("MATCH (n) WHERE none(x IN n.tags WHERE x = 'a') RETURN n")
        self.assertIn("NOT EXISTS", result)

    def test_all_generates_not_exists_not(self):
        result = self._gql("MATCH (n) WHERE all(x IN n.tags WHERE x > 0) RETURN n")
        self.assertIn("NOT EXISTS", result)
        self.assertIn("NOT (", result)

    def test_single_raises_for_gql(self):
        trees = self.neo4j.parse("MATCH (n) WHERE single(x IN n.tags WHERE x = 'a') RETURN n")
        with self.assertRaises(NotImplementedError):
            self.gql.generate(trees[0])

    def test_list_predicate_roundtrip_preserves_syntax(self):
        for kw in ["any", "none", "all", "single"]:
            result = self._cypher(f"MATCH (n) WHERE {kw}(x IN n.tags WHERE x = 'a') RETURN n")
            self.assertIn(f"{kw}(", result, f"{kw} should preserve Cypher syntax")

    def test_list_predicate_in_return(self):
        result = self._gql("MATCH (n) RETURN any(x IN [1, 2, 3] WHERE x > 1) AS has_big")
        self.assertIn("EXISTS", result)

    # ------------------------------------------------------------------
    # Predicate comparison
    # ------------------------------------------------------------------

    def test_predicate_comparison_generates(self):
        """none(...) = true → (NOT EXISTS {...}) = TRUE."""
        result = self._gql("RETURN none(x IN [1] WHERE x = 1) = true AS r")
        self.assertEqual(
            result,
            "RETURN (NOT EXISTS {FOR x IN [1] FILTER WHERE x = 1 RETURN x}) = TRUE AS r",
        )

    def test_null_predicate_comparison_generates(self):
        """false = true IS NULL → FALSE = TRUE IS NULL."""
        result = self._gql("RETURN false = true IS NULL AS r")
        self.assertEqual(result, "RETURN FALSE = TRUE IS NULL AS r")

    def test_predicate_comparison_roundtrip(self):
        """Cypher roundtrip preserves syntax."""
        result = self._cypher("RETURN none(x IN [1] WHERE x = 1) = true AS r")
        self.assertEqual(result, "RETURN none(x IN [1] WHERE x = 1) = TRUE AS r")

    # ------------------------------------------------------------------
    # Temporal functions: localdatetime
    # ------------------------------------------------------------------

    def test_localdatetime_no_arg_generates_local_datetime(self):
        result = self._gql("RETURN localdatetime() AS x")
        self.assertEqual(result, "RETURN LOCAL DATETIME() AS x")

    def test_localdatetime_with_arg_generates_local_datetime(self):
        result = self._gql("RETURN localdatetime('2024-01-15T10:30:00') AS x")
        self.assertEqual(result, "RETURN LOCAL DATETIME('2024-01-15T10:30:00') AS x")

    def test_localdatetime_roundtrip(self):
        result = self._cypher("RETURN localdatetime() AS x")
        self.assertEqual(result, "RETURN localdatetime() AS x")

    # ------------------------------------------------------------------
    # Temporal functions: localtime
    # ------------------------------------------------------------------

    def test_localtime_no_arg_generates_local_time(self):
        result = self._gql("RETURN localtime() AS x")
        self.assertEqual(result, "RETURN LOCAL TIME() AS x")

    def test_localtime_with_arg_generates_local_time(self):
        result = self._gql("RETURN localtime('10:30:00') AS x")
        self.assertEqual(result, "RETURN LOCAL TIME('10:30:00') AS x")

    def test_localtime_roundtrip(self):
        result = self._cypher("RETURN localtime() AS x")
        self.assertEqual(result, "RETURN localtime() AS x")

    # ------------------------------------------------------------------
    # Temporal functions: duration
    # ------------------------------------------------------------------

    def test_duration_generates_duration(self):
        result = self._gql("RETURN duration('P1Y2M') AS x")
        self.assertEqual(result, "RETURN DURATION('P1Y2M') AS x")

    def test_duration_roundtrip(self):
        result = self._cypher("RETURN duration('P1Y2M') AS x")
        self.assertEqual(result, "RETURN duration('P1Y2M') AS x")
