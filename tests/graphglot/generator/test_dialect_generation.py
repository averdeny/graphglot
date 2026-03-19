"""Tests for dialect-specific generation.

Verifies that keyword overrides and dialect-aware generation work correctly.
"""

import unittest

from graphglot import ast
from graphglot.dialect.base import Dialect
from graphglot.generator.base import Generator
from graphglot.lexer import Lexer
from graphglot.parser import Parser


def generate_with_dialect(expr: ast.Expression, dialect_name: str) -> str:
    dialect = Dialect.get_or_raise(dialect_name)
    return dialect.generate(expr)


def parse_and_generate(query: str, dialect_name: str | None = None) -> str:
    lexer = Lexer()
    parser = Parser()
    tokens = lexer.tokenize(query)
    parsed = parser.parse(tokens, query)[0]
    if dialect_name:
        dialect = Dialect.get_or_raise(dialect_name)
        return dialect.generate(parsed)
    return parsed.to_gql()


class TestKeywordMethod(unittest.TestCase):
    """Test the Generator.keyword() method directly."""

    def test_keyword_no_dialect(self):
        gen = Generator()
        self.assertEqual(gen.keyword("OFFSET"), "OFFSET")

    def test_keyword_no_dialect_uppercase(self):
        gen = Generator()
        self.assertEqual(gen.keyword("offset"), "OFFSET")

    def test_keyword_neo4j_offset_unchanged(self):
        """Neo4j GQL mode rejects OFFSET entirely (GQ12 unsupported) — no override needed."""
        dialect = Dialect.get_or_raise("neo4j")
        gen = Generator(dialect=dialect)
        self.assertEqual(gen.keyword("OFFSET"), "OFFSET")

    def test_keyword_neo4j_non_overridden(self):
        dialect = Dialect.get_or_raise("neo4j")
        gen = Generator(dialect=dialect)
        self.assertEqual(gen.keyword("MATCH"), "MATCH")

    def test_keyword_neo4j_return_unchanged(self):
        dialect = Dialect.get_or_raise("neo4j")
        gen = Generator(dialect=dialect)
        self.assertEqual(gen.keyword("RETURN"), "RETURN")

    def test_keyword_neo4j_where_unchanged(self):
        dialect = Dialect.get_or_raise("neo4j")
        gen = Generator(dialect=dialect)
        self.assertEqual(gen.keyword("WHERE"), "WHERE")

    def test_keyword_neo4j_limit_unchanged(self):
        dialect = Dialect.get_or_raise("neo4j")
        gen = Generator(dialect=dialect)
        self.assertEqual(gen.keyword("LIMIT"), "LIMIT")


class TestNeo4jDialectOverrides(unittest.TestCase):
    """Test Neo4j-specific keyword overrides."""

    def test_neo4j_has_keyword_overrides(self):
        """Neo4j remaps GQL function names to Cypher equivalents."""
        dialect_cls = Dialect.get("neo4j")
        self.assertIsNotNone(dialect_cls)
        overrides = getattr(dialect_cls, "KEYWORD_OVERRIDES", {})
        self.assertGreater(len(overrides), 0)
        self.assertIn("COLLECT_LIST", overrides)
        self.assertEqual(overrides["COLLECT_LIST"], "COLLECT")

    def test_all_overrides_are_string_pairs(self):
        dialect_cls = Dialect.get("neo4j")
        overrides = getattr(dialect_cls, "KEYWORD_OVERRIDES", {})
        for key, value in overrides.items():
            self.assertIsInstance(key, str, f"Key {key!r} is not a string")
            self.assertIsInstance(value, str, f"Value {value!r} for key {key!r} is not a string")
            self.assertEqual(key, key.upper(), f"Key {key!r} should be uppercase")
            self.assertEqual(value, value.upper(), f"Value {value!r} should be uppercase")


class TestNeo4jOffsetGeneration(unittest.TestCase):
    """Test OFFSET clause generation with Neo4j dialect.

    Neo4j GQL mode does not support OFFSET (GQ12 unsupported), so there
    is no OFFSET→SKIP override. OFFSET passes through unchanged.
    """

    def test_offset_clause_default_dialect(self):
        result = parse_and_generate("MATCH (n) RETURN n OFFSET 5 LIMIT 10")
        self.assertIn("OFFSET", result)
        self.assertNotIn("SKIP", result)

    def test_offset_clause_neo4j_dialect(self):
        result = parse_and_generate("MATCH (n) RETURN n OFFSET 5 LIMIT 10", "neo4j")
        self.assertIn("OFFSET", result)
        self.assertIn("LIMIT", result)

    def test_offset_only_neo4j(self):
        result = parse_and_generate("MATCH (n) RETURN n OFFSET 5", "neo4j")
        self.assertIn("OFFSET", result)
        self.assertIn("5", result)

    def test_limit_only_unchanged_neo4j(self):
        result = parse_and_generate("MATCH (n) RETURN n LIMIT 10", "neo4j")
        self.assertIn("LIMIT", result)
        self.assertNotIn("SKIP", result)


class TestNeo4jFullStatements(unittest.TestCase):
    """Test full statement generation with Neo4j dialect."""

    def test_match_return_with_offset_neo4j(self):
        result = parse_and_generate("MATCH (n) RETURN n OFFSET 5 LIMIT 10", "neo4j")
        self.assertIn("MATCH", result)
        self.assertIn("RETURN", result)
        self.assertIn("OFFSET", result)
        self.assertIn("LIMIT", result)

    def test_match_where_neo4j(self):
        result = parse_and_generate("MATCH (n) WHERE n.age > 21 RETURN n", "neo4j")
        self.assertIn("MATCH", result)
        self.assertIn("WHERE", result)
        self.assertIn("RETURN", result)

    def test_order_by_offset_limit_neo4j(self):
        result = parse_and_generate("MATCH (n) RETURN n ORDER BY n.name OFFSET 10 LIMIT 5", "neo4j")
        self.assertIn("ORDER BY", result)
        self.assertIn("OFFSET", result)
        self.assertIn("LIMIT", result)


class TestDefaultDialect(unittest.TestCase):
    """Test that the default (IR) dialect uses standard GQL keywords."""

    def test_default_dialect_offset(self):
        result = parse_and_generate("MATCH (n) RETURN n OFFSET 5 LIMIT 10")
        self.assertIn("OFFSET", result)

    def test_default_dialect_match(self):
        result = parse_and_generate("MATCH (n) RETURN n")
        self.assertIn("MATCH", result)
        self.assertIn("RETURN", result)

    def test_default_dialect_where(self):
        result = parse_and_generate("MATCH (n) WHERE n.age > 21 RETURN n")
        self.assertIn("WHERE", result)

    def test_default_dialect_order_by(self):
        result = parse_and_generate("MATCH (n) RETURN n ORDER BY n.name")
        self.assertIn("ORDER BY", result)

    def test_default_dialect_insert(self):
        result = parse_and_generate("INSERT (n:Person {name: 'Bob'})")
        self.assertIn("INSERT", result)

    def test_default_dialect_delete(self):
        result = parse_and_generate("MATCH (n) DELETE n")
        self.assertIn("DELETE", result)

    def test_default_dialect_set(self):
        result = parse_and_generate("MATCH (n) SET n.active = TRUE")
        self.assertIn("SET", result)


class TestDialectInstantiation(unittest.TestCase):
    """Test dialect loading and instantiation."""

    def test_neo4j_dialect_loadable(self):
        dialect = Dialect.get_or_raise("neo4j")
        self.assertIsNotNone(dialect)

    def test_default_dialect_loadable(self):
        dialect = Dialect.get_or_raise(None)
        self.assertIsNotNone(dialect)

    def test_ir_dialect_loadable(self):
        dialect = Dialect.get_or_raise("ir")
        self.assertIsNotNone(dialect)

    def test_unknown_dialect_raises(self):
        with self.assertRaises(ValueError):
            Dialect.get_or_raise("nonexistent_dialect")

    def test_neo4j_generator_has_dialect(self):
        dialect = Dialect.get_or_raise("neo4j")
        gen = dialect.generator()
        self.assertIsNotNone(gen.dialect)

    def test_default_generator_no_dialect(self):
        gen = Generator()
        self.assertIsNone(gen.dialect)
