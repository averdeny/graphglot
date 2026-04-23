"""Tests for the path-mode default and ``PathPattern.effective_path_mode``.

Path mode is implementation-defined.  Parser is lossless (fields stay None
when the user omits the keyword); the effective value is resolved at
inspection time; cross-dialect preservation is handled by
``materialize_implementation_defaults``.
"""

import unittest

from graphglot import ast
from graphglot.dialect.base import Dialect
from graphglot.dialect.coregql import CoreGQL
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.fullgql import FullGQL
from graphglot.dialect.neo4j import Neo4j


def _first_path_pattern(tree: ast.Expression) -> ast.PathPattern:
    return next(iter(tree.find_all(ast.PathPattern)))


class TestDefaultPathModeDialect(unittest.TestCase):
    """Every dialect declares TRAIL as the default path mode."""

    def test_base_dialect_trail(self):
        self.assertIs(Dialect.DEFAULT_PATH_MODE, ast.PathMode.Mode.TRAIL)

    def test_fullgql_trail(self):
        self.assertIs(FullGQL.DEFAULT_PATH_MODE, ast.PathMode.Mode.TRAIL)

    def test_coregql_trail(self):
        self.assertIs(CoreGQL.DEFAULT_PATH_MODE, ast.PathMode.Mode.TRAIL)

    def test_cypher_trail(self):
        self.assertIs(CypherDialect.DEFAULT_PATH_MODE, ast.PathMode.Mode.TRAIL)

    def test_neo4j_trail(self):
        self.assertIs(Neo4j.DEFAULT_PATH_MODE, ast.PathMode.Mode.TRAIL)


class TestEffectivePathMode(unittest.TestCase):
    """`PathPattern.effective_path_mode` resolves across all prefix shapes."""

    def test_bare_pattern_returns_dialect_default(self):
        d = FullGQL()
        [tree] = d.parse("MATCH (a)-[r]-(b) RETURN a")
        pp = _first_path_pattern(tree)
        self.assertIsNone(pp.path_pattern_prefix)
        self.assertIs(pp.effective_path_mode(d), ast.PathMode.Mode.TRAIL)

    def test_path_mode_prefix_returns_written_mode(self):
        d = FullGQL()
        [tree] = d.parse("MATCH SIMPLE (a)-[r]-(b) RETURN a")
        pp = _first_path_pattern(tree)
        self.assertIsInstance(pp.path_pattern_prefix, ast.PathModePrefix)
        self.assertIs(pp.effective_path_mode(d), ast.PathMode.Mode.SIMPLE)

    def test_path_search_prefix_with_explicit_mode(self):
        # Regression: when the prefix is a PathSearchPrefix variant (e.g.
        # AllPathSearch), the inner path_mode must be honored — not the
        # dialect default.
        d = FullGQL()
        [tree] = d.parse("MATCH ALL SIMPLE (a)-[r]-(b) RETURN a")
        pp = _first_path_pattern(tree)
        self.assertIsInstance(pp.path_pattern_prefix, ast.AllPathSearch)
        self.assertIs(pp.effective_path_mode(d), ast.PathMode.Mode.SIMPLE)

    def test_path_search_prefix_without_mode_returns_default(self):
        d = FullGQL()
        [tree] = d.parse("MATCH ALL (a)-[r]-(b) RETURN a")
        pp = _first_path_pattern(tree)
        self.assertIsInstance(pp.path_pattern_prefix, ast.AllPathSearch)
        self.assertIsNone(pp.path_pattern_prefix.path_mode)
        self.assertIs(pp.effective_path_mode(d), ast.PathMode.Mode.TRAIL)


class TestPathModeParseLossless(unittest.TestCase):
    """Parser leaves path_pattern_prefix = None when the user omits the keyword."""

    def test_bare_pattern_has_no_prefix(self):
        [tree] = FullGQL().parse("MATCH (a)-[r]-(b) RETURN a")
        pp = _first_path_pattern(tree)
        self.assertIsNone(pp.path_pattern_prefix)

    def test_explicit_keyword_preserved(self):
        [tree] = FullGQL().parse("MATCH TRAIL (a)-[r]-(b) RETURN a")
        pp = _first_path_pattern(tree)
        self.assertIsInstance(pp.path_pattern_prefix, ast.PathModePrefix)
        self.assertIs(
            pp.path_pattern_prefix.path_mode.mode,
            ast.PathMode.Mode.TRAIL,
        )


class TestPathModeGeneration(unittest.TestCase):
    """Generator is lossless — emits what the user wrote, omits what they didn't."""

    def test_bare_roundtrip_stays_bare(self):
        d = FullGQL()
        out = d.generate(d.parse("MATCH (a)-[r]-(b) RETURN a")[0])
        for kw in ("WALK", "TRAIL", "SIMPLE", "ACYCLIC"):
            self.assertNotIn(kw, out)

    def test_explicit_non_default_preserved(self):
        d = FullGQL()
        out = d.generate(d.parse("MATCH SIMPLE (a)-[r]-(b) RETURN a")[0])
        self.assertIn("SIMPLE", out)

    def test_explicit_default_preserved(self):
        # Parser is lossless, so an explicit TRAIL (== dialect default)
        # round-trips unchanged — AST fidelity matters.
        d = FullGQL()
        out = d.generate(d.parse("MATCH TRAIL (a)-[r]-(b) RETURN a")[0])
        self.assertIn("TRAIL", out)


if __name__ == "__main__":
    unittest.main()
