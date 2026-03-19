"""Tests for query expression parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestQueryExpressions(unittest.TestCase):
    """Test suite for query expression parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_composite_query_expression_union(self):
        """Test that the parser can parse a composite query with UNION."""
        query = """
            MATCH (n:Person) LIMIT 10 RETURN n
            UNION
            MATCH (n:Person) LIMIT 10 RETURN n
        """
        self.helper.parse(query, ast.CompositeQueryExpression)

    def test_composite_query_expression_intersection(self):
        """Test that the parser can parse a composite query with INTERSECT."""
        query = """
            MATCH (n:Person) LIMIT 10 RETURN n
            INTERSECT
            MATCH (n:Person) LIMIT 10 RETURN n
        """
        self.helper.parse(query, ast.CompositeQueryExpression)

    def test_composite_query_expression_except(self):
        """Test that the parser can parse a composite query with EXCEPT."""
        query = """
            MATCH (n:Person) LIMIT 10 RETURN n
            EXCEPT
            MATCH (n:Person) LIMIT 10 RETURN n
        """
        self.helper.parse(query, ast.CompositeQueryExpression)


class TestTransactionActivity(unittest.TestCase):
    """Test suite for transaction activity parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_match_with_graph_clause(self):
        """Test that the parser can parse MATCH with graph clause in transaction activity."""
        query = """
            MATCH (p:Person)-[r:KNOWS]->(m:Person)
            RETURN p.name, r, m.name
        """
        self.helper.parse(query, ast.TransactionActivity)
