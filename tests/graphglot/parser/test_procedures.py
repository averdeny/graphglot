"""Tests for procedure parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestProcedures(unittest.TestCase):
    """Test suite for procedure parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_statement_block_match(self):
        """Test that the parser can parse a statement block with MATCH."""
        query = """
            MATCH
                (n:Person WHERE NOT n.name = 'Alice'),
                (l:Location {name: 'Barcelona'}),
                (n)-[r:LIKES]->(l)
            WHERE n.age > 30
            YIELD n, l
            RETURN AVG(n.age) AS average_age, l
        """
        self.helper.parse(query, ast.ProcedureBody)

    def test_match_with_at_schema_clause(self):
        """Test that the parser can parse MATCH with AT schema clause."""
        query = """
            AT HOME_SCHEMA
            MATCH a = (p:Person)-[r:KNOWS]->(m:Person)
            RETURN p.name, r, m.name
        """
        self.helper.parse(query, ast.ProcedureBody)

    def test_optional_match_statement(self):
        """Test that the parser can parse optional match in procedure body."""
        query = """
            MATCH (p:Person {name: 'Martin Sheen'})
            OPTIONAL MATCH (p)-[d:DIRECT]->(m)
            RETURN p.name, d, m.name
        """
        self.helper.parse(query, ast.ProcedureBody)

    def test_with_inline_call(self):
        """Test that the parser can parse inline CALL in procedure body."""
        query = """
            MATCH (s)
            CALL {
                MATCH (s)-(e)
                RETURN COUNT(e) as total
            }
            RETURN s._id as startNode, total
        """
        self.helper.parse(query, ast.ProcedureBody)

    def test_named_procedure_call(self):
        """Test that the parser can parse a named procedure call."""
        query = """
            CALL my_test_procedure(a, b, c)
            YIELD result
            RETURN result
        """
        self.helper.parse(query, ast.ProcedureBody)

    def test_named_procedure_call_with_parent(self):
        """Test that the parser can parse a named procedure call with parent."""
        query = """
            CALL my.test.proc(a, b, c)
            YIELD result
            RETURN result
        """
        self.helper.parse(query, ast.ProcedureBody)
