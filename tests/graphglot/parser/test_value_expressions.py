"""Tests for value expression parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestValueExpressions(unittest.TestCase):
    """Test suite for value expression parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_character_string_value_expression(self):
        """Test that the parser can parse a character string value expression."""
        query = '"Hello"'
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_boolean_true_literal(self):
        """Test that the parser can parse TRUE boolean literal."""
        query = "TRUE"
        expr = self.helper.parse_single(query, ast.ValueExpressionPrimary)

        self.assertIsInstance(expr, ast.BooleanLiteral)
        self.assertTrue(expr.value)

    def test_boolean_false_literal(self):
        """Test that the parser can parse FALSE boolean literal."""
        query = "FALSE"
        expr = self.helper.parse_single(query, ast.ValueExpressionPrimary)

        self.assertIsInstance(expr, ast.BooleanLiteral)
        self.assertFalse(expr.value)

    def test_null_literal(self):
        """Test that the parser can parse NULL literal."""
        query = "NULL"
        expr = self.helper.parse_single(query, ast.ValueExpressionPrimary)

        self.assertIsInstance(expr, ast.NullLiteral)

    def test_number_literal(self):
        """Test that the parser can parse a number literal."""
        query = "1.23"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_parameter_reference(self):
        """Test that the parser can parse a parameter reference."""
        query = "$param"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_empty_list_literal(self):
        """Test that the parser can parse an empty list literal."""
        query = "[]"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_non_empty_list_literal(self):
        """Test that the parser can parse a non-empty list literal."""
        query = "[1, 2, 3]"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_empty_record_literal(self):
        """Test that the parser can parse an empty record literal."""
        query = "RECORD {}"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_value_query_expression(self):
        """Test that the parser can parse a value query expression."""
        query = "VALUE { MATCH (n:Person) RETURN n }"
        self.helper.parse(query, ast.ValueQueryExpression)

    def test_date_literal(self):
        """Test that the parser can parse a DATE literal."""
        query = "DATE '2021-01-01'"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_time_literal(self):
        """Test that the parser can parse a TIME literal."""
        query = "TIME '12:00:00'"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_datetime_literal(self):
        """Test that the parser can parse a DATETIME literal."""
        query = "DATETIME '2021-01-01 12:00:00'"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_timestamp_literal(self):
        """Test that the parser can parse a TIMESTAMP literal."""
        query = "TIMESTAMP '2021-01-01 12:00:00'"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_duration_literal(self):
        """Test that the parser can parse a DURATION literal."""
        query = "DURATION '1 day'"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_count_star_expression(self):
        """Test that the parser can parse COUNT(*) expression."""
        query = "COUNT(*)"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_average_expression(self):
        """Test that the parser can parse AVG expression."""
        query = "AVG(7)"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_property_reference(self):
        """Test that the parser can parse a property reference."""
        query = "p.name"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_let_value_expression(self):
        """Test that the parser can parse a LET value expression."""
        query = "LET x = 1 IN [x, x + 1, x * 10] END"
        self.helper.parse(query, ast.LetValueExpression)

    def test_element_id_function(self):
        """Test that the parser can parse ELEMENT_ID function."""
        query = "ELEMENT_ID(p)"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_cast_expression_integer(self):
        """Test that the parser can parse CAST expression with INTEGER."""
        query = "CAST(p AS INTEGER (10))"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_cast_expression_double(self):
        """Test that the parser can parse CAST expression with DOUBLE."""
        query = "CAST(p AS DOUBLE)"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_coalesce_expression(self):
        """Test that the parser can parse COALESCE expression."""
        query = "COALESCE(a, b, c)"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_nullif_expression(self):
        """Test that the parser can parse NULLIF expression."""
        query = "NULLIF(a, b)"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_simple_case_expression(self):
        """Test that the parser can parse a simple CASE expression."""
        query = "CASE a WHEN 10 THEN b ELSE c END"
        self.helper.parse(query, ast.SimpleCase)

    def test_searched_case_expression(self):
        """Test that the parser can parse a searched CASE expression."""
        query = "CASE WHEN a > 10 THEN b ELSE c END"
        self.helper.parse(query, ast.ValueExpressionPrimary)

    def test_let_statement(self):
        """Test that the parser can parse a LET statement."""
        query = "LET n = 1"
        self.helper.parse(query, ast.LetStatement)

    def test_exists_predicate(self):
        """Test that the parser can parse an EXISTS predicate."""
        query = "EXISTS { (n:Person)-[r:KNOWS]->(m:Person) }"
        self.helper.parse(query, ast.ExistsPredicate)

    def test_search_condition(self):
        """Test that the parser can parse a search condition."""
        query = "WHERE n.name = 'John'"
        self.helper.parse(query, ast.ElementPatternWhereClause)
