"""Tests for implicit default match mode (ISO/IEC 39075 ID086).

The parser injects DifferentEdgesMatchMode when no explicit match mode is
specified.  The generator omits the match mode when it matches the write
dialect's DEFAULT_MATCH_MODE.
"""

import unittest

from graphglot import ast
from graphglot.dialect.base import Dialect
from graphglot.dialect.neo4j import Neo4j
from graphglot.lexer import Lexer
from graphglot.parser import Parser


def _parse_gql(query: str) -> ast.GqlProgram:
    tokens = Lexer().tokenize(query)
    return Parser().parse(tokens, query)[0]


def _graph_pattern(tree: ast.GqlProgram) -> ast.GraphPattern:
    return next(iter(tree.find_all(ast.GraphPattern)))


class TestDefaultMatchModeParsing(unittest.TestCase):
    """Base parser injects DIFFERENT EDGES when no match mode is specified."""

    def test_implicit_different_edges(self):
        gp = _graph_pattern(_parse_gql("MATCH (n)-[e]->(m) RETURN n"))
        self.assertIsInstance(gp.match_mode, ast.DifferentEdgesMatchMode)
        self.assertEqual(gp.match_mode.mode, ast.DifferentEdgesMatchMode.Mode.EDGES)

    def test_optional_match(self):
        gp = _graph_pattern(_parse_gql("OPTIONAL MATCH (n)-[e]->(m) RETURN n"))
        self.assertIsInstance(gp.match_mode, ast.DifferentEdgesMatchMode)

    def test_explicit_different_edges_preserved(self):
        gp = _graph_pattern(_parse_gql("MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n"))
        self.assertIsInstance(gp.match_mode, ast.DifferentEdgesMatchMode)

    def test_explicit_repeatable_elements_preserved(self):
        gp = _graph_pattern(_parse_gql("MATCH REPEATABLE ELEMENTS (n)-[e]->(m) RETURN n"))
        self.assertIsInstance(gp.match_mode, ast.RepeatableElementsMatchMode)


class TestDefaultMatchModeGeneration(unittest.TestCase):
    """Generator omits match mode when it matches the dialect default."""

    def setUp(self):
        self.dialect = Dialect()

    def test_default_omitted(self):
        tree = _parse_gql("MATCH (n)-[e]->(m) RETURN n")
        output = self.dialect.generate(tree)
        self.assertNotIn("DIFFERENT EDGES", output)

    def test_non_default_emitted(self):
        tree = _parse_gql("MATCH REPEATABLE ELEMENTS (n)-[e]->(m) RETURN n")
        output = self.dialect.generate(tree)
        self.assertIn("REPEATABLE ELEMENTS", output)

    def test_cypher_roundtrip_suppresses(self):
        neo4j = Neo4j()
        output = neo4j.transpile("MATCH (n)-[e]->(m) RETURN n")
        self.assertNotIn("DIFFERENT", output[0])


class TestDefaultMatchModeDialect(unittest.TestCase):
    """Dialect.DEFAULT_MATCH_MODE is DifferentEdgesMatchMode."""

    def test_base_dialect(self):
        self.assertIs(Dialect.DEFAULT_MATCH_MODE, ast.DifferentEdgesMatchMode)

    def test_neo4j_inherits(self):
        self.assertIs(Neo4j.DEFAULT_MATCH_MODE, ast.DifferentEdgesMatchMode)
