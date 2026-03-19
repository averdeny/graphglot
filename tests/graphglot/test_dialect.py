"""Tests for the dialect module."""

import unittest

from graphglot.dialect import Dialect, Dialects
from graphglot.error import GraphGlotError
from graphglot.lineage.models import LineageGraph


class TestDialect(unittest.TestCase):
    def test_dialect_registration(self):
        """Test that dialects can be registered and looked up."""

        # Test getting a known dialect
        neo4j = Dialect.get("neo4j")
        self.assertIsNotNone(neo4j)
        self.assertEqual(neo4j.__name__, "Neo4j")

        # Test getting an unknown dialect
        unknown = Dialect.get("unknown")
        self.assertIsNone(unknown)

    def test_dialect_instantiation(self):
        """Test that dialects can be instantiated with parameters."""

        # Test basic instantiation
        dialect = Dialect.get_or_raise("neo4j")
        self.assertIsInstance(dialect, Dialect)

        # Test instantiation with parameters
        dialect = Dialect.get_or_raise("neo4j", version="4.4")
        self.assertIsInstance(dialect, Dialect)
        self.assertEqual(dialect.version, 4004000)  # Version is converted to integer

    def test_dialect_error_handling(self):
        """Test error handling for invalid dialects."""

        # Test invalid dialect name
        with self.assertRaises(ValueError) as cm:
            Dialect.get_or_raise("invalid_dialect")
        self.assertIn("Unknown dialect", str(cm.exception))

    def test_dialect_enum(self):
        """Test that dialect enums are properly defined."""

        # Test that all known dialects are in the enum
        self.assertIn(Dialects.NEO4J, Dialects)

        # Test enum values
        self.assertEqual(Dialects.NEO4J.value, "neo4j")

    def test_dialect_equality(self):
        """Test dialect equality comparisons."""

        # Test string comparison
        self.assertEqual(Dialect.get("neo4j"), "neo4j")

        # Test dialect comparison
        neo4j1 = Dialect.get_or_raise("neo4j")
        neo4j2 = Dialect.get_or_raise("neo4j")
        self.assertEqual(neo4j1, neo4j2)


class TestDialectLineage(unittest.TestCase):
    """Tests for Dialect.lineage() pipeline method."""

    def setUp(self):
        self.neo4j = Dialect.get_or_raise("neo4j")
        self.gql = Dialect.get_or_raise("")

    def test_returns_list_of_lineage_graphs(self):
        results = self.neo4j.lineage("MATCH (n) RETURN n.name")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], LineageGraph)

    def test_result_has_outputs(self):
        results = self.neo4j.lineage("MATCH (n) RETURN n.name AS name")
        graph = results[0]
        self.assertEqual(len(graph.outputs), 1)
        out = next(iter(graph.outputs.values()))
        self.assertEqual(out.alias, "name")

    def test_result_has_bindings(self):
        results = self.neo4j.lineage("MATCH (a)-[r]->(b) RETURN a, b")
        graph = results[0]
        names = {b.name for b in graph.bindings.values()}
        self.assertIn("a", names)
        self.assertIn("b", names)
        self.assertIn("r", names)

    def test_gql_dialect(self):
        results = self.gql.lineage("MATCH (n:Person) RETURN n.age")
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], LineageGraph)

    def test_invalid_query_raises(self):
        with self.assertRaises(GraphGlotError):
            self.neo4j.lineage("THIS IS NOT VALID GQL")

    def test_query_text_preserved(self):
        query = "MATCH (n) RETURN n.name"
        results = self.neo4j.lineage(query)
        self.assertEqual(results[0].query_text, query)
