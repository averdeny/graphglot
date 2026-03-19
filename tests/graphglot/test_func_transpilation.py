"""Tests for Func-level transpilation: name translation + validation.

Covers:
- rename_func helper produces correct output
- Parser.FUNCTIONS contains expected Func types per dialect
- Validation rejects unsupported Func types, allows supported ones
- Anonymous functions bypass validation
- End-to-end roundtrip via transpile()
"""

import unittest

from graphglot.ast.functions import (
    Anonymous,
    Labels,
    PointDistance,
    RandomUUID,
    Replace,
)
from graphglot.dialect.base import Dialect
from graphglot.dialect.cypher import CypherDialect
from graphglot.error import FeatureError
from graphglot.generator import rename_func
from graphglot.generator.fragment import Fragment


def _neo4j() -> Dialect:
    return Dialect.get_or_raise("neo4j")


# =============================================================================
# rename_func helper
# =============================================================================


class TestRenameFunc(unittest.TestCase):
    """Test the rename_func helper."""

    def test_rename_func_no_args(self):
        gen_fn = rename_func("gen_random_uuid")
        node = RandomUUID(arguments=[])
        gen = _neo4j().generator()
        result = gen_fn(gen, node)
        self.assertIsInstance(result, Fragment)
        self.assertEqual(str(result), "gen_random_uuid()")

    def test_rename_func_with_args(self):
        gen_fn = rename_func("ERSETZEN")
        trees = _neo4j().parse("RETURN replace('abc', 'b', 'x')")
        func_nodes = list(trees[0].find_all(Replace))
        self.assertEqual(len(func_nodes), 1)
        result = gen_fn(_neo4j().generator(), func_nodes[0])
        self.assertIsInstance(result, Fragment)
        text = str(result)
        self.assertTrue(text.startswith("ERSETZEN("))
        self.assertIn("'abc'", text)


# =============================================================================
# Parser.FUNCTIONS coverage
# =============================================================================


class TestFunctionsDict(unittest.TestCase):
    """Test that Parser.FUNCTIONS contains expected Func types."""

    def test_cypher_contains_shared_functions(self):
        supported = set(CypherDialect.Parser.FUNCTIONS.values())
        self.assertIn(Replace, supported)
        self.assertIn(Labels, supported)

    def test_cypher_does_not_contain_neo4j_only(self):
        supported = set(CypherDialect.Parser.FUNCTIONS.values())
        self.assertNotIn(RandomUUID, supported)

    def test_neo4j_contains_all_cypher_plus_own(self):
        from graphglot.dialect.neo4j import Neo4j

        neo4j = set(Neo4j.Parser.FUNCTIONS.values())
        cypher = set(CypherDialect.Parser.FUNCTIONS.values())
        self.assertTrue(cypher.issubset(neo4j))
        self.assertIn(RandomUUID, neo4j)

    def test_neo4j_function_count(self):
        from graphglot.dialect.neo4j import Neo4j

        self.assertGreater(len(Neo4j.Parser.FUNCTIONS), 20)


# =============================================================================
# Validation
# =============================================================================


class TestFuncValidation(unittest.TestCase):
    """Test that unsupported functions are rejected during transpilation."""

    def test_neo4j_func_roundtrip(self):
        """Neo4j-only func roundtrips within Neo4j."""
        result = _neo4j().transpile("RETURN randomUUID()")[0]
        self.assertIn("randomuuid()", result.lower())

    def test_shared_func_passes(self):
        """Shared func (replace) passes validation in Neo4j."""
        result = _neo4j().transpile("RETURN replace('a', 'b', 'c')")[0]
        self.assertIn("replace", result.lower())

    def test_anonymous_passes_validation(self):
        """Anonymous (user-defined) functions bypass validation."""
        result = _neo4j().transpile("RETURN myCustomFunc(1, 2)")[0]
        self.assertIn("myCustomFunc", result)

    def test_unsupported_func_raises(self):
        """A Func type not in target dialect's FUNCTIONS raises FeatureError."""
        from graphglot.dialect.base import _validate_functions_for_dialect

        trees = _neo4j().parse("RETURN randomUUID()")
        cypher_dialect = CypherDialect()
        with self.assertRaises(FeatureError) as ctx:
            _validate_functions_for_dialect(trees, cypher_dialect)
        self.assertIn("randomUUID", str(ctx.exception))

    def test_supported_func_no_error(self):
        """A Func in target dialect's FUNCTIONS passes validation."""
        from graphglot.dialect.base import _validate_functions_for_dialect

        trees = _neo4j().parse("RETURN replace('a', 'b', 'c')")
        cypher_dialect = CypherDialect()
        _validate_functions_for_dialect(trees, cypher_dialect)

    def test_anonymous_not_validated(self):
        """Anonymous functions are never rejected."""
        from graphglot.dialect.base import _validate_functions_for_dialect

        trees = _neo4j().parse("RETURN unknownFunc(42)")
        cypher_dialect = CypherDialect()
        _validate_functions_for_dialect(trees, cypher_dialect)


# =============================================================================
# Dotted function names (e.g. apoc.text.join)
# =============================================================================


class TestDottedFunctionNames(unittest.TestCase):
    """Test dotted namespace function parsing and round-tripping."""

    def test_apoc_dotted_parses_as_anonymous(self):
        """apoc.text.join(...) parses as Anonymous with dotted name."""
        trees = _neo4j().parse("RETURN apoc.text.join(['a', 'b'], ',')")
        funcs = list(trees[0].find_all(Anonymous))
        self.assertEqual(len(funcs), 1)
        self.assertEqual(funcs[0].name, "apoc.text.join")

    def test_apoc_dotted_roundtrip(self):
        """apoc.text.join(...) round-trips preserving the dotted name."""
        result = _neo4j().transpile("RETURN apoc.text.join(['a', 'b'], ',')")[0]
        self.assertIn("apoc.text.join", result)

    def test_deep_dotted_namespace(self):
        """Deeply nested dotted namespace parses as Anonymous."""
        trees = _neo4j().parse("RETURN apoc.my.deep.ns.func()")
        funcs = list(trees[0].find_all(Anonymous))
        self.assertEqual(len(funcs), 1)
        self.assertEqual(funcs[0].name, "apoc.my.deep.ns.func")

    def test_point_distance_still_dispatches(self):
        """point.distance(...) still resolves to PointDistance (regression)."""
        trees = _neo4j().parse("RETURN point.distance(point({x: 1, y: 2}), point({x: 3, y: 4}))")
        funcs = list(trees[0].find_all(PointDistance))
        self.assertEqual(len(funcs), 1)

    def test_property_access_not_affected(self):
        """n.name (property access, no parens) still works correctly."""
        result = _neo4j().transpile("MATCH (n) RETURN n.name")[0]
        self.assertIn("n.name", result.lower())

    def test_coregql_rejects_anonymous_func(self):
        """CoreGQL rejects anonymous function calls (GG:FN01 not supported)."""
        d = Dialect.get_or_raise("coregql")
        with self.assertRaises(FeatureError):
            d.transpile("RETURN myFunc(1, 2)")

    def test_coregql_rejects_dotted_anonymous(self):
        """CoreGQL rejects dotted anonymous functions."""
        d = Dialect.get_or_raise("coregql")
        with self.assertRaises(FeatureError):
            d.transpile("RETURN apoc.text.join(['a'], ',')")
