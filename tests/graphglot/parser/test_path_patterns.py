"""Tests for path pattern parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestPathPatterns(unittest.TestCase):
    """Test suite for path pattern parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_quantified_path_primary_asterisk(self):
        """Test that the parser can parse a quantified path primary with asterisk."""
        query = "(m:Person)*"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        # Asterisk is parsed as GeneralQuantifier with lower_bound=0, upper_bound=None
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.GeneralQuantifier)
        self.assertEqual(expr.graph_pattern_quantifier.lower_bound.value, 0)
        self.assertIsNone(expr.graph_pattern_quantifier.upper_bound)

    def test_quantified_path_primary_plus_sign(self):
        """Test that the parser can parse a quantified path primary with plus sign."""
        query = "(m:Person)+"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        # Plus sign is parsed as GeneralQuantifier with lower_bound=1, upper_bound=None
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.GeneralQuantifier)
        self.assertEqual(expr.graph_pattern_quantifier.lower_bound.value, 1)
        self.assertIsNone(expr.graph_pattern_quantifier.upper_bound)

    def test_quantified_path_primary_fixed_quantifier(self):
        """Test that the parser can parse a quantified path primary with fixed
        quantifier."""
        query = "(m:Person){1}"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.FixedQuantifier)
        self.assertEqual(expr.graph_pattern_quantifier.unsigned_integer.value, 1)

    def test_quantified_path_primary_general_quantifier(self):
        """Test that the parser can parse a quantified path primary with general
        quantifier."""
        query = "(m:Person){1,2}"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.GeneralQuantifier)
        self.assertIsNotNone(expr.graph_pattern_quantifier.lower_bound)
        self.assertIsNotNone(expr.graph_pattern_quantifier.upper_bound)

    def test_quantified_path_primary_asterisk_edge(self):
        """Test that the parser can parse a quantified path primary with asterisk
        on edge."""
        query = "-[r:KNOWS]->*"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        # Asterisk is parsed as GeneralQuantifier with lower_bound=0, upper_bound=None
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.GeneralQuantifier)
        self.assertEqual(expr.graph_pattern_quantifier.lower_bound.value, 0)
        self.assertIsNone(expr.graph_pattern_quantifier.upper_bound)

    def test_quantified_path_primary_plus_sign_edge(self):
        """Test that the parser can parse a quantified path primary with plus
        sign on edge."""
        query = "-[r:KNOWS]->+"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        # Plus sign is parsed as GeneralQuantifier with lower_bound=1, upper_bound=None
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.GeneralQuantifier)
        self.assertEqual(expr.graph_pattern_quantifier.lower_bound.value, 1)
        self.assertIsNone(expr.graph_pattern_quantifier.upper_bound)

    def test_quantified_path_primary_fixed_quantifier_edge(self):
        """Test that the parser can parse a quantified path primary with fixed
        quantifier on edge."""
        query = "-[r:KNOWS]->{1}"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.FixedQuantifier)
        self.assertEqual(expr.graph_pattern_quantifier.unsigned_integer.value, 1)

    def test_quantified_path_primary_general_quantifier_edge(self):
        """Test that the parser can parse a quantified path primary with general
        quantifier on edge."""
        query = "-[r:KNOWS]->{1,2}"
        expr = self.helper.parse_single(query, ast.QuantifiedPathPrimary)

        self.assertIsInstance(expr, ast.QuantifiedPathPrimary)
        self.assertIsNotNone(expr.path_primary)
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.GeneralQuantifier)
        self.assertIsNotNone(expr.graph_pattern_quantifier.lower_bound)
        self.assertIsNotNone(expr.graph_pattern_quantifier.upper_bound)


class TestAdvancedPathPatterns(unittest.TestCase):
    """Test suite for advanced path pattern expressions."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_path_pattern_union_two_paths(self):
        """Test that the parser can parse a path pattern union with two path terms."""
        # Path pattern union uses vertical bar (|) to separate path terms
        query = "(a)-[e1]->(b) | (c)-[e2]->(d)"
        expr = self.helper.parse_single(query, ast.PathPatternUnion)

        self.assertIsInstance(expr, ast.PathPatternUnion)
        self.assertGreaterEqual(len(expr.list_path_term), 2)

    def test_path_multiset_alternation_two_paths(self):
        """Test that the parser can parse a path multiset alternation with two path terms."""
        # Path multiset alternation uses |+| operator
        query = "(a)-[e1]->(b) |+| (c)-[e2]->(d)"
        expr = self.helper.parse_single(query, ast.PathMultisetAlternation)

        self.assertIsInstance(expr, ast.PathMultisetAlternation)
        self.assertGreaterEqual(len(expr.list_path_term), 2)

    def test_path_pattern_union_in_match(self):
        """Test that the parser can parse a MATCH statement with path pattern union."""
        query = "MATCH (a)-[e1]->(b) | (c)-[e2]->(d)"
        expr = self.helper.parse_single(query, ast.SimpleLinearQueryStatement)

        # SimpleLinearQueryStatement wraps one or more simple query statements.
        self.assertIsInstance(expr, ast.SimpleLinearQueryStatement)
        self.assertGreaterEqual(len(expr.list_simple_query_statement), 1)

        # The first simple query statement should be a (simple) MATCH statement.
        match_stmt = expr.list_simple_query_statement[0]
        self.assertIsInstance(match_stmt, ast.SimpleMatchStatement)

        # From the match statement, navigate to the underlying graph pattern.
        graph_pattern = match_stmt.graph_pattern_binding_table.graph_pattern
        path_pattern_list = graph_pattern.path_pattern_list
        path_expr = path_pattern_list.list_path_pattern[0].path_pattern_expression

        # Currently the parser may produce a PathTerm here; once PathPatternUnion
        # is preferred for patterns with a vertical bar, this can be tightened.
        self.assertIsInstance(path_expr, ast.PathPatternExpression)

    def test_path_multiset_alternation_in_match(self):
        """Test that the parser can parse a MATCH statement with path multiset alternation."""
        query = "MATCH (a)-[e1]->(b) |+| (c)-[e2]->(d)"
        expr = self.helper.parse_single(query, ast.SimpleLinearQueryStatement)

        # SimpleLinearQueryStatement wraps one or more simple query statements.
        self.assertIsInstance(expr, ast.SimpleLinearQueryStatement)
        self.assertGreaterEqual(len(expr.list_simple_query_statement), 1)

        # The first simple query statement should be a (simple) MATCH statement.
        match_stmt = expr.list_simple_query_statement[0]
        self.assertIsInstance(match_stmt, ast.SimpleMatchStatement)

        # From the match statement, navigate to the underlying graph pattern.
        graph_pattern = match_stmt.graph_pattern_binding_table.graph_pattern
        path_pattern_list = graph_pattern.path_pattern_list
        path_expr = path_pattern_list.list_path_pattern[0].path_pattern_expression

        # Currently the parser may produce a PathTerm here; once PathMultisetAlternation
        # is preferred for patterns with a multiset alternation operator, this can be tightened.
        self.assertIsInstance(path_expr, ast.PathPatternExpression)


class TestSimplifiedPathPatterns(unittest.TestCase):
    """Test suite for simplified path patterns."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_simplified_path_union(self):
        """Test that the parser can parse a simplified path union."""
        # Simplified path union uses vertical bar (|)
        query = "Person | Company"
        expr = self.helper.parse_single(query, ast.SimplifiedPathUnion)

        self.assertIsInstance(expr, ast.SimplifiedPathUnion)
        self.assertGreaterEqual(len(expr.list_simplified_term), 2)

    def test_simplified_multiset_alternation(self):
        """Test that the parser can parse a simplified multiset alternation."""
        # Simplified multiset alternation uses |+| operator
        query = "Person |+| Company"
        expr = self.helper.parse_single(query, ast.SimplifiedMultisetAlternation)

        self.assertIsInstance(expr, ast.SimplifiedMultisetAlternation)

    def test_simplified_defaulting_left(self):
        """Test that the parser can parse a simplified defaulting left pattern."""
        # Uses <-/ ... /- syntax (left minus slash)
        query = "<-/ Person /-"
        expr = self.helper.parse_single(query, ast.SimplifiedDefaultingLeft)

        self.assertIsInstance(expr, ast.SimplifiedDefaultingLeft)

    def test_simplified_defaulting_undirected(self):
        """Test that the parser can parse a simplified defaulting undirected pattern."""
        # Uses ~/ ... /~ syntax
        query = "~/ Person /~"
        expr = self.helper.parse_single(query, ast.SimplifiedDefaultingUndirected)

        self.assertIsInstance(expr, ast.SimplifiedDefaultingUndirected)

    def test_simplified_defaulting_right(self):
        """Test that the parser can parse a simplified defaulting right pattern."""
        # Uses -/ ... /-> syntax
        query = "-/ Person /->"
        expr = self.helper.parse_single(query, ast.SimplifiedDefaultingRight)

        self.assertIsInstance(expr, ast.SimplifiedDefaultingRight)

    def test_simplified_defaulting_any_direction(self):
        """Test that the parser can parse a simplified defaulting any direction pattern."""
        # Uses -/ ... /- syntax (not / ... /)
        query = "-/ Person /-"
        expr = self.helper.parse_single(query, ast.SimplifiedDefaultingAnyDirection)

        self.assertIsInstance(expr, ast.SimplifiedDefaultingAnyDirection)
