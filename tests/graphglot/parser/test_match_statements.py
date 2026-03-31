"""Tests for MATCH statement parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestMatchStatements(unittest.TestCase):
    """Test suite for MATCH statement parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_simple_match_statement(self):
        """Test that the parser can parse a simple match statement."""
        query = "MATCH (n:Person)"
        expr = self.helper.parse_single(query, ast.SimpleLinearQueryStatement)

        leaves = expr.leaf_list()
        self.assertEqual(len(leaves), 3)
        self.assertIsInstance(leaves[0], ast.DifferentEdgesMatchMode)
        self.assertIsInstance(leaves[1], ast.BindingVariable)
        self.assertEqual(leaves[1].name, "n")
        self.assertIsInstance(leaves[2], ast.Identifier)
        self.assertEqual(leaves[2].name, "Person")

    def test_match_statement_pattern(self):
        """Test that the parser can parse a match statement with pattern."""
        query = "MATCH (n:Person)-[r:KNOWS]->(m:Person)"
        self.helper.parse(query, ast.SimpleLinearQueryStatement)

    def test_optional_match_statement(self):
        """Test that the parser can parse an optional match statement."""
        query = "OPTIONAL MATCH (n:Person)"
        self.helper.parse(query, ast.SimpleLinearQueryStatement)

    def test_match_disconnected_path_pattern(self):
        """Test that the parser can parse a disconnected path pattern."""
        query = "MATCH (person IS Person), (location IS Location)"
        self.helper.parse(query, ast.SimpleLinearQueryStatement)

    def test_match_statement_with_return_all(self):
        """Test that the parser can parse a match statement with return all."""
        query = "MATCH (n:Person) RETURN *"
        self.helper.parse(query, ast.AmbientLinearQueryStatement)

    def test_match_with_yield_clause(self):
        """Test that the parser can parse a match statement with a yield clause."""
        query = "MATCH (n:Person) YIELD n RETURN n"
        self.helper.parse(query, ast.AmbientLinearQueryStatement)

    def test_graph_pattern_yield_clause(self):
        """Test that the parser can parse a graph pattern yield clause."""
        query = "YIELD a, b, c"
        self.helper.parse(query, ast.GraphPatternYieldClause)
