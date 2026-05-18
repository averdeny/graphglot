"""Tests for parser/parsers/statements.py.

Covers multi-statement parsing (MATCH+INSERT, MATCH+REMOVE, MATCH+SET)
which require no separator between SimpleDataAccessingStatements.
"""

import unittest

from graphglot import ast
from graphglot.ast.cypher import CreateClause, CypherWithStatement, MergeClause
from graphglot.dialect.neo4j import Neo4j


class TestSimpleLinearDataAccessingStatement(unittest.TestCase):
    """Test that MATCH followed by a data-modifying statement parses correctly.

    The GQL grammar defines SimpleLinearDataAccessingStatement as a list
    of SimpleDataAccessingStatements with NO separator (not comma-separated).
    """

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1)
        return self.neo4j.generate(results[0])

    def test_match_insert_parses(self):
        """MATCH ... INSERT ... should produce both MatchStatement and InsertStatement."""
        results = self._parse("MATCH (a:Person), (b:Person) INSERT (a)-[:KNOWS]->(b)")
        self.assertEqual(len(results), 1)
        matches = list(results[0].find_all(ast.MatchStatement))
        inserts = list(results[0].find_all(ast.InsertStatement))
        self.assertGreaterEqual(len(matches), 1, "Expected at least one MatchStatement")
        self.assertGreaterEqual(len(inserts), 1, "Expected at least one InsertStatement")

    def test_match_insert_no_next(self):
        """Round-trip should not insert a NEXT keyword between MATCH and INSERT.

        Neo4j ``KEYWORD_OVERRIDES`` spells GQL ``INSERT`` as Cypher ``CREATE``
        on the way out, so we assert the data-modifying clause is preserved
        under either spelling.
        """
        result = self._round_trip("MATCH (a:Person), (b:Person) INSERT (a)-[:KNOWS]->(b)")
        self.assertNotIn("NEXT", result)
        self.assertIn("MATCH", result)
        self.assertIn("CREATE", result)

    def test_match_remove_parses(self):
        """MATCH ... REMOVE ... should produce both MatchStatement and RemoveStatement."""
        results = self._parse("MATCH (n:Person) REMOVE n:Employee")
        self.assertEqual(len(results), 1)
        matches = list(results[0].find_all(ast.MatchStatement))
        removes = list(results[0].find_all(ast.RemoveStatement))
        self.assertGreaterEqual(len(matches), 1, "Expected at least one MatchStatement")
        self.assertGreaterEqual(len(removes), 1, "Expected at least one RemoveStatement")

    def test_match_remove_no_next(self):
        """Round-trip should not insert a NEXT keyword between MATCH and REMOVE."""
        result = self._round_trip("MATCH (n:Person) REMOVE n:Employee")
        self.assertNotIn("NEXT", result)

    def test_match_set_parses(self):
        """MATCH ... SET ... should produce both MatchStatement and SetStatement."""
        results = self._parse("MATCH (n:Person) SET n.x = 1")
        self.assertEqual(len(results), 1)
        matches = list(results[0].find_all(ast.MatchStatement))
        sets = list(results[0].find_all(ast.SetStatement))
        self.assertGreaterEqual(len(matches), 1, "Expected at least one MatchStatement")
        self.assertGreaterEqual(len(sets), 1, "Expected at least one SetStatement")

    def test_match_set_no_next(self):
        """Round-trip should not insert a NEXT keyword between MATCH and SET."""
        result = self._round_trip("MATCH (n:Person) SET n.x = 1")
        self.assertNotIn("NEXT", result)


class TestPrimitiveQueryStatementDispatch(unittest.TestCase):
    """Guards the token-based fast-path dispatch in
    ``_parse_cypher_primitive_query_statement``.  Each subTest covers one
    branch of the lead-token if/elif chain; adding a new candidate parser
    without a matching dispatch entry will surface here as a failure.
    """

    def setUp(self):
        self.neo4j = Neo4j()

    def test_dispatch_each_lead_token(self):
        cases = [
            ("MATCH (n) RETURN n", ast.MatchStatement),
            ("OPTIONAL MATCH (n) RETURN n", ast.MatchStatement),
            ("CREATE (n)", CreateClause),
            ("MERGE (n)", MergeClause),
            ("UNWIND [1, 2] AS x RETURN x", ast.ForStatement),
            ("WITH 1 AS x RETURN x", CypherWithStatement),
            ("MATCH (n) RETURN n ORDER BY n.x", ast.OrderByAndPageStatement),
            ("MATCH (n) RETURN n LIMIT 5", ast.OrderByAndPageStatement),
            ("MATCH (n) RETURN n SKIP 5", ast.OrderByAndPageStatement),
        ]
        for query, expected_type in cases:
            with self.subTest(query=query):
                results = self.neo4j.parse(query)
                found = list(results[0].find_all(expected_type))
                self.assertGreaterEqual(len(found), 1, f"Expected {expected_type.__name__} in AST")
