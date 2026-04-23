"""Tests for implicit default match mode (see ISO/IEC 39075 §ID086).

Parser is lossless — ``GraphPattern.match_mode`` stays ``None`` when the user
omits the keyword.  ``GraphPattern.effective_match_mode(dialect)`` resolves
to the dialect default.  The generator omits the keyword when the explicit
value matches the dialect default, and the cross-dialect transpile pipeline
materializes source-dialect defaults when source and target disagree
(no-op today because all dialects use DifferentEdgesMatchMode).
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


class TestMatchModeParsingLossless(unittest.TestCase):
    """Parser leaves match_mode = None when the user omits the keyword."""

    def test_implicit_is_none(self):
        gp = _graph_pattern(_parse_gql("MATCH (n)-[e]->(m) RETURN n"))
        self.assertIsNone(gp.match_mode)

    def test_optional_match_implicit_is_none(self):
        gp = _graph_pattern(_parse_gql("OPTIONAL MATCH (n)-[e]->(m) RETURN n"))
        self.assertIsNone(gp.match_mode)

    def test_explicit_different_edges_preserved(self):
        gp = _graph_pattern(_parse_gql("MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n"))
        self.assertIsInstance(gp.match_mode, ast.DifferentEdgesMatchMode)

    def test_explicit_repeatable_elements_preserved(self):
        gp = _graph_pattern(_parse_gql("MATCH REPEATABLE ELEMENTS (n)-[e]->(m) RETURN n"))
        self.assertIsInstance(gp.match_mode, ast.RepeatableElementsMatchMode)


class TestEffectiveMatchMode(unittest.TestCase):
    """`effective_match_mode` resolves explicit-or-default under a dialect."""

    def test_implicit_returns_dialect_default(self):
        d = Dialect()
        gp = _graph_pattern(_parse_gql("MATCH (n) RETURN n"))
        self.assertIs(gp.effective_match_mode(d), ast.DifferentEdgesMatchMode)

    def test_explicit_repeatable_returned(self):
        d = Dialect()
        gp = _graph_pattern(_parse_gql("MATCH REPEATABLE ELEMENTS (n) RETURN n"))
        self.assertIs(gp.effective_match_mode(d), ast.RepeatableElementsMatchMode)


class TestMatchModeGeneration(unittest.TestCase):
    """Generator omits match mode when it matches the dialect default."""

    def setUp(self):
        self.dialect = Dialect()

    def test_implicit_not_emitted(self):
        tree = _parse_gql("MATCH (n)-[e]->(m) RETURN n")
        output = self.dialect.generate(tree)
        self.assertNotIn("DIFFERENT EDGES", output)
        self.assertNotIn("REPEATABLE ELEMENTS", output)

    def test_explicit_default_preserved(self):
        # The parser is lossless, so the generator emits exactly what the
        # user wrote.  An explicit DIFFERENT EDGES keyword (equal to the
        # dialect default) is preserved in the output.  Cross-dialect
        # semantic preservation is handled separately via materialization.
        tree = _parse_gql("MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n")
        output = self.dialect.generate(tree)
        self.assertIn("DIFFERENT EDGES", output)

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
