"""Tests for query statement parsing functionality (FOR, FILTER, LET)."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestForStatement(unittest.TestCase):
    """Test suite for FOR statement parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_for_statement_basic(self):
        """Test that the parser can parse a basic FOR statement structure."""
        # Note: Full FOR statement parsing may have recursion issues with complex sources
        # This test verifies the parser recognizes the FOR statement structure
        query = "FOR x IN $binding_table"
        expr = self.helper.parse_single(query, ast.ForStatement)
        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)

    def test_for_statement_with_ordinality(self):
        """Test that the parser can parse a FOR statement with ordinality."""
        query = "FOR x IN $binding_table WITH ORDINALITY i"
        expr = self.helper.parse_single(query, ast.ForStatement)
        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)
        if expr.for_ordinality_or_offset:
            self.assertEqual(
                expr.for_ordinality_or_offset.mode,
                ast.ForOrdinalityOrOffset.Mode.ORDINALITY,
            )

    def test_for_statement_with_offset(self):
        """Test that the parser can parse a FOR statement with offset."""
        query = "FOR x IN $binding_table WITH OFFSET i"
        expr = self.helper.parse_single(query, ast.ForStatement)
        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)
        if expr.for_ordinality_or_offset:
            self.assertEqual(
                expr.for_ordinality_or_offset.mode,
                ast.ForOrdinalityOrOffset.Mode.OFFSET,
            )

    def test_for_statement_with_list_source(self):
        """Test that the parser can parse a FOR statement with a list value source."""
        query = "FOR x IN [1, 2, 3]"
        expr = self.helper.parse_single(query, ast.ForStatement)

        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)
        self.assertIsNone(expr.for_ordinality_or_offset)

    def test_for_statement_with_list_and_ordinality(self):
        """Test that the parser can parse a FOR statement with list source and ordinality."""
        query = "FOR x IN [1, 2, 3] WITH ORDINALITY i"
        expr = self.helper.parse_single(query, ast.ForStatement)

        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)
        self.assertIsNotNone(expr.for_ordinality_or_offset)
        self.assertEqual(
            expr.for_ordinality_or_offset.mode,
            ast.ForOrdinalityOrOffset.Mode.ORDINALITY,
        )

    def test_for_statement_with_list_and_offset(self):
        """Test that the parser can parse a FOR statement with list source and offset."""
        query = "FOR x IN [1, 2, 3] WITH OFFSET i"
        expr = self.helper.parse_single(query, ast.ForStatement)

        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)
        self.assertIsNotNone(expr.for_ordinality_or_offset)
        self.assertEqual(
            expr.for_ordinality_or_offset.mode,
            ast.ForOrdinalityOrOffset.Mode.OFFSET,
        )

    def test_for_statement_with_binding_table_nested_query(self):
        """Test FOR statement with nested query binding table."""
        query = "FOR x IN TABLE {MATCH (n:Person) RETURN n}"
        expr = self.helper.parse_single(query, ast.ForStatement)

        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)
        self.assertIsNone(expr.for_ordinality_or_offset)

    def test_for_statement_with_binding_table_and_ordinality(self):
        """Test FOR statement with binding table and ordinality."""
        query = "FOR person IN TABLE {MATCH (n:Person) RETURN n} WITH ORDINALITY idx"
        expr = self.helper.parse_single(query, ast.ForStatement)

        self.assertIsInstance(expr, ast.ForStatement)
        self.assertIsNotNone(expr.for_item)
        self.assertIsNotNone(expr.for_ordinality_or_offset)
        self.assertEqual(
            expr.for_ordinality_or_offset.mode,
            ast.ForOrdinalityOrOffset.Mode.ORDINALITY,
        )


class TestFilterStatement(unittest.TestCase):
    """Test suite for FILTER statement parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_filter_statement_with_where_clause(self):
        """Test that the parser can parse a FILTER statement with WHERE clause."""
        query = "FILTER WHERE n.age > 30"
        expr = self.helper.parse_single(query, ast.FilterStatement)

        self.assertIsInstance(expr, ast.FilterStatement)
        self.assertIsNotNone(expr.filter_statement)
        self.assertIsInstance(expr.filter_statement, ast.WhereClause)

    def test_filter_statement_with_search_condition(self):
        """Test that the parser can parse a FILTER statement with search condition."""
        query = "FILTER n.name = 'John'"
        expr = self.helper.parse_single(query, ast.FilterStatement)

        self.assertIsInstance(expr, ast.FilterStatement)
        self.assertIsNotNone(expr.filter_statement)
        self.assertIsInstance(expr.filter_statement, ast.SearchCondition)

    def test_filter_statement_complex_condition(self):
        """Test that the parser can parse a FILTER statement with complex condition."""
        query = "FILTER WHERE n.age > 30 AND n.name <> 'Alice'"
        expr = self.helper.parse_single(query, ast.FilterStatement)

        self.assertIsInstance(expr, ast.FilterStatement)
        self.assertIsNotNone(expr.filter_statement)

    def test_filter_statement_with_nested_conditions(self):
        """Test that the parser can parse a FILTER statement with nested conditions."""
        query = "FILTER WHERE n.age > 30 AND n.active = TRUE"
        expr = self.helper.parse_single(query, ast.FilterStatement)

        self.assertIsInstance(expr, ast.FilterStatement)
        self.assertIsNotNone(expr.filter_statement)

    def test_filter_statement_with_parenthesized_nested_conditions(self):
        """Test FILTER statement with parenthesized nested conditions."""
        query = "FILTER WHERE (n.age > 30 OR n.age < 18) AND n.active = TRUE"
        expr = self.helper.parse_single(query, ast.FilterStatement)

        self.assertIsInstance(expr, ast.FilterStatement)
        self.assertIsNotNone(expr.filter_statement)


class TestOrderByAndPageStatement(unittest.TestCase):
    """Test suite for OrderByAndPageStatement parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_order_by_and_page_statement_limit_only(self):
        """Test that the parser can parse a LIMIT only statement."""
        query = "LIMIT 10"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsInstance(expr.order_by_and_page_statement, ast.LimitClause)

    def test_order_by_and_page_statement_offset_only(self):
        """Test that the parser can parse an OFFSET only statement."""
        query = "OFFSET 5"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsInstance(
            expr.order_by_and_page_statement,
            ast.OrderByAndPageStatement._OffsetClauseLimitClause,
        )
        self.assertIsNotNone(expr.order_by_and_page_statement.offset_clause)
        self.assertIsNone(expr.order_by_and_page_statement.limit_clause)

    def test_order_by_and_page_statement_offset_with_limit(self):
        """Test that the parser can parse OFFSET with LIMIT."""
        query = "OFFSET 5 LIMIT 10"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsInstance(
            expr.order_by_and_page_statement,
            ast.OrderByAndPageStatement._OffsetClauseLimitClause,
        )
        self.assertIsNotNone(expr.order_by_and_page_statement.offset_clause)
        self.assertIsNotNone(expr.order_by_and_page_statement.limit_clause)

    def test_order_by_and_page_statement_order_by_only(self):
        """Test that the parser can parse ORDER BY only statement."""
        query = "ORDER BY n.name"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsInstance(
            expr.order_by_and_page_statement,
            ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause,
        )
        self.assertIsNotNone(expr.order_by_and_page_statement.order_by_clause)
        self.assertIsNone(expr.order_by_and_page_statement.offset_clause)
        self.assertIsNone(expr.order_by_and_page_statement.limit_clause)

    def test_order_by_and_page_statement_order_by_with_limit(self):
        """Test that the parser can parse ORDER BY with LIMIT."""
        query = "ORDER BY n.name LIMIT 10"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsInstance(
            expr.order_by_and_page_statement,
            ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause,
        )
        self.assertIsNotNone(expr.order_by_and_page_statement.order_by_clause)
        self.assertIsNone(expr.order_by_and_page_statement.offset_clause)
        self.assertIsNotNone(expr.order_by_and_page_statement.limit_clause)

    def test_order_by_and_page_statement_order_by_with_offset(self):
        """Test that the parser can parse ORDER BY with OFFSET."""
        query = "ORDER BY n.name OFFSET 5"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsInstance(
            expr.order_by_and_page_statement,
            ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause,
        )
        self.assertIsNotNone(expr.order_by_and_page_statement.order_by_clause)
        self.assertIsNotNone(expr.order_by_and_page_statement.offset_clause)
        self.assertIsNone(expr.order_by_and_page_statement.limit_clause)

    def test_order_by_and_page_statement_order_by_with_offset_and_limit(self):
        """Test that the parser can parse ORDER BY with OFFSET and LIMIT."""
        query = "ORDER BY n.name OFFSET 5 LIMIT 10"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsInstance(
            expr.order_by_and_page_statement,
            ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause,
        )
        self.assertIsNotNone(expr.order_by_and_page_statement.order_by_clause)
        self.assertIsNotNone(expr.order_by_and_page_statement.offset_clause)
        self.assertIsNotNone(expr.order_by_and_page_statement.limit_clause)

    def test_order_by_and_page_statement_order_by_multiple_columns(self):
        """Test that the parser can parse ORDER BY with multiple columns."""
        query = "ORDER BY n.name, n.age"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsNotNone(expr.order_by_and_page_statement.order_by_clause)

    def test_order_by_and_page_statement_order_by_with_asc(self):
        """Test that the parser can parse ORDER BY with ASC."""
        query = "ORDER BY n.name ASC"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsNotNone(expr.order_by_and_page_statement.order_by_clause)

    def test_order_by_and_page_statement_order_by_with_desc(self):
        """Test that the parser can parse ORDER BY with DESC."""
        query = "ORDER BY n.name DESC"
        expr = self.helper.parse_single(query, ast.OrderByAndPageStatement)

        self.assertIsInstance(expr, ast.OrderByAndPageStatement)
        self.assertIsNotNone(expr.order_by_and_page_statement.order_by_clause)
