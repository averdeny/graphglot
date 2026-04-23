"""Tests for ``materialize_implementation_defaults``.

The transformation fills in implementation-defined defaults from the source
dialect wherever the target dialect's default differs, so cross-dialect
output preserves semantics.

All built-in dialects currently agree on every monitored default
(PATH_MODE=TRAIL, ORDER_DIRECTION=ASC, MATCH_MODE=DifferentEdgesMatchMode),
so the tests here define small mock dialects that disagree in order to
exercise the transformation in each dimension.
"""

import typing as t
import unittest

from graphglot import ast
from graphglot.dialect.fullgql import FullGQL
from graphglot.transformations import materialize_implementation_defaults


class _WalkDialect(FullGQL):
    """Mock source dialect whose path-mode default differs from FullGQL."""

    DEFAULT_PATH_MODE: t.ClassVar[ast.PathMode.Mode] = ast.PathMode.Mode.WALK


class _DescDialect(FullGQL):
    """Mock source dialect whose ORDER-BY default differs from FullGQL."""

    DEFAULT_ORDER_DIRECTION: t.ClassVar[ast.OrderingSpecification.Order] = (
        ast.OrderingSpecification.Order.DESC
    )


class _RepeatableDialect(FullGQL):
    """Mock source dialect whose match-mode default differs from FullGQL."""

    DEFAULT_MATCH_MODE: t.ClassVar[type] = ast.RepeatableElementsMatchMode


def _first(tree: ast.Expression, type_: type) -> ast.Expression:
    return next(iter(tree.find_all(type_)))


class TestMaterializeNoOp(unittest.TestCase):
    """No-op paths: same dialect identity, or agreeing defaults."""

    def test_same_instance_is_noop(self):
        d = FullGQL()
        [tree] = d.parse("MATCH (a)-[r]-(b) RETURN a ORDER BY a.x")
        pp_before = _first(tree, ast.PathPattern)
        ss_before = _first(tree, ast.SortSpecification)
        self.assertIsNone(pp_before.path_pattern_prefix)
        self.assertIsNone(ss_before.ordering_specification)

        materialize_implementation_defaults(tree, source=d, target=d)

        self.assertIsNone(pp_before.path_pattern_prefix)
        self.assertIsNone(ss_before.ordering_specification)

    def test_agreeing_defaults_is_noop(self):
        # Different instances but same defaults across the board.
        src = FullGQL()
        tgt = FullGQL()
        [tree] = src.parse("MATCH (a)-[r]-(b) RETURN a")
        pp = _first(tree, ast.PathPattern)
        self.assertIsNone(pp.path_pattern_prefix)

        materialize_implementation_defaults(tree, source=src, target=tgt)

        self.assertIsNone(pp.path_pattern_prefix)


class TestMaterializePathMode(unittest.TestCase):
    """Source's path-mode default differs from target: insert explicit prefix."""

    def setUp(self):
        self.src = _WalkDialect()  # PATH_MODE = WALK
        self.tgt = FullGQL()  # PATH_MODE = TRAIL

    def test_bare_pattern_gets_source_default(self):
        [tree] = self.src.parse("MATCH (a)-[r]-(b) RETURN a")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)

        pp = _first(tree, ast.PathPattern)
        self.assertIsInstance(pp.path_pattern_prefix, ast.PathModePrefix)
        self.assertIs(pp.path_pattern_prefix.path_mode.mode, ast.PathMode.Mode.WALK)

    def test_path_search_without_mode_gets_source_default(self):
        [tree] = self.src.parse("MATCH ALL (a)-[r]-(b) RETURN a")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)

        aps = _first(tree, ast.AllPathSearch)
        self.assertIsNotNone(aps.path_mode)
        self.assertIs(aps.path_mode.mode, ast.PathMode.Mode.WALK)

    def test_explicit_keyword_left_alone(self):
        [tree] = self.src.parse("MATCH SIMPLE (a)-[r]-(b) RETURN a")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)

        pp = _first(tree, ast.PathPattern)
        # User wrote SIMPLE explicitly — must not be overwritten.
        self.assertIs(pp.path_pattern_prefix.path_mode.mode, ast.PathMode.Mode.SIMPLE)

    def test_generator_emits_materialized_keyword(self):
        [tree] = self.src.parse("MATCH (a)-[r]-(b) RETURN a")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)
        out = self.tgt.generate(tree)
        self.assertIn("WALK", out)


class TestMaterializeOrderDirection(unittest.TestCase):
    """Source's ORDER direction default differs: insert explicit direction."""

    def setUp(self):
        self.src = _DescDialect()  # ORDER = DESC
        self.tgt = FullGQL()  # ORDER = ASC

    def test_bare_sort_gets_source_default(self):
        [tree] = self.src.parse("MATCH (n) RETURN n ORDER BY n.x")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)

        ss = _first(tree, ast.SortSpecification)
        self.assertIsNotNone(ss.ordering_specification)
        self.assertIs(
            ss.ordering_specification.ordering_specification,
            ast.OrderingSpecification.Order.DESC,
        )

    def test_explicit_asc_left_alone(self):
        [tree] = self.src.parse("MATCH (n) RETURN n ORDER BY n.x ASC")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)

        ss = _first(tree, ast.SortSpecification)
        self.assertIs(
            ss.ordering_specification.ordering_specification,
            ast.OrderingSpecification.Order.ASC,
        )

    def test_generator_emits_materialized_direction(self):
        [tree] = self.src.parse("MATCH (n) RETURN n ORDER BY n.x")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)
        out = self.tgt.generate(tree)
        self.assertIn("DESC", out)


class TestMaterializeMatchMode(unittest.TestCase):
    """Source's match-mode default differs: insert explicit MatchMode."""

    def setUp(self):
        self.src = _RepeatableDialect()  # MATCH_MODE = RepeatableElementsMatchMode
        self.tgt = FullGQL()  # MATCH_MODE = DifferentEdgesMatchMode

    def test_bare_match_gets_source_default(self):
        [tree] = self.src.parse("MATCH (n)-[e]->(m) RETURN n")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)

        gp = _first(tree, ast.GraphPattern)
        self.assertIsInstance(gp.match_mode, ast.RepeatableElementsMatchMode)

    def test_explicit_match_mode_left_alone(self):
        [tree] = self.src.parse("MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)

        gp = _first(tree, ast.GraphPattern)
        self.assertIsInstance(gp.match_mode, ast.DifferentEdgesMatchMode)

    def test_generator_emits_materialized_keyword(self):
        [tree] = self.src.parse("MATCH (n)-[e]->(m) RETURN n")
        materialize_implementation_defaults(tree, source=self.src, target=self.tgt)
        out = self.tgt.generate(tree)
        self.assertIn("REPEATABLE ELEMENTS", out)


if __name__ == "__main__":
    unittest.main()
