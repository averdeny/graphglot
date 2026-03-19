"""Tests for function infrastructure (Func base class, FUNC_REGISTRY, Anonymous).

Covers:
- Func base class and auto-registry (FUNC_REGISTRY)
- Parser FUNCTIONS dict dispatch (CypherDialect + Neo4j)
- Special-syntax functions (reduce, point.distance, point.withinBBox)
- Anonymous fallback for unknown function names
- Round-trip fidelity
- Edge cases (nested calls, non-RETURN contexts)
"""

import unittest

from graphglot.ast.cypher import CypherReduce
from graphglot.ast.functions import FUNC_REGISTRY, Anonymous, Func
from graphglot.dialect.base import Dialect
from graphglot.error import FeatureError, ParseError


def _neo4j() -> Dialect:
    return Dialect.get_or_raise("neo4j")


# =============================================================================
# Func base class and registry
# =============================================================================


class TestFuncRegistry(unittest.TestCase):
    """Test the Func auto-registry infrastructure."""

    def test_registry_populated(self):
        self.assertIn("REPLACE", FUNC_REGISTRY)
        self.assertIn("PI", FUNC_REGISTRY)
        self.assertIn("RANDOMUUID", FUNC_REGISTRY)
        self.assertIn("ISEMPTY", FUNC_REGISTRY)

    def test_registry_maps_to_subclasses(self):
        for name, cls in FUNC_REGISTRY.items():
            self.assertTrue(issubclass(cls, Func), f"{name} → {cls} is not Func")

    def test_all_subclasses_registered(self):
        for cls in Func.__subclasses__():
            if cls is not Anonymous and cls.func_name:
                self.assertIn(
                    cls.func_name.upper(),
                    FUNC_REGISTRY,
                    f"{cls.__name__} (func_name={cls.func_name!r}) not in registry",
                )

    def test_anonymous_not_in_registry(self):
        self.assertNotIn("", FUNC_REGISTRY)


# =============================================================================
# Generic Func parse + round-trip
# =============================================================================


class TestFuncParse(unittest.TestCase):
    """Parse tests for generic Func functions."""

    def _parse(self, query: str):
        return _neo4j().parse(query)

    def _rt(self, query: str) -> str:
        return _neo4j().transpile(query)[0]

    # --- Cypher standard functions (in CypherDialect.Parser.FUNCTIONS) ---

    def test_replace_parse(self):
        self._parse("RETURN replace('abc', 'b', 'x')")

    def test_replace_roundtrip(self):
        result = self._rt("RETURN replace('abc', 'b', 'x')")
        self.assertIn("replace", result.lower())
        self.assertIn("'abc'", result)

    def test_replace_ast_type(self):
        trees = self._parse("RETURN replace('abc', 'b', 'x')")
        nodes = list(trees[0].find_all(Func))
        self.assertTrue(len(nodes) > 0, "No Func node found in AST")
        func = nodes[0]
        self.assertEqual(func.func_name, "replace")
        self.assertEqual(len(func.arguments), 3)

    def test_pi_parse(self):
        self._parse("RETURN pi()")

    def test_pi_roundtrip(self):
        result = self._rt("RETURN pi()")
        self.assertIn("pi()", result.lower())

    def test_isempty_parse(self):
        self._parse("RETURN isEmpty('')")

    def test_isempty_roundtrip(self):
        result = self._rt("RETURN isEmpty('')")
        self.assertIn("isempty", result.lower())

    def test_isnan_parse(self):
        self._parse("RETURN isNaN(0.0 / 0.0)")

    def test_atan2_parse(self):
        self._parse("RETURN atan2(1, 2)")

    def test_atan2_roundtrip(self):
        result = self._rt("RETURN atan2(1, 2)")
        self.assertIn("atan2", result.lower())

    def test_haversin_parse(self):
        self._parse("RETURN haversin(0.5)")

    # --- Neo4j utility functions (in Neo4j.Parser.FUNCTIONS) ---

    def test_randomuuid_parse(self):
        self._parse("RETURN randomUUID()")

    def test_randomuuid_roundtrip(self):
        result = self._rt("RETURN randomUUID()")
        self.assertIn("randomuuid()", result.lower())

    def test_timestamp_parse(self):
        self._parse("RETURN timestamp()")

    def test_timestamp_roundtrip(self):
        result = self._rt("RETURN timestamp()")
        self.assertIn("timestamp()", result.lower())

    def test_valuetype_parse(self):
        self._parse("MATCH (n) RETURN valueType(n.prop)")

    def test_tostringornull_parse(self):
        self._parse("RETURN toStringOrNull(123)")

    def test_tobooleanornull_parse(self):
        self._parse("RETURN toBooleanOrNull('true')")

    def test_tointegerornull_parse(self):
        self._parse("RETURN toIntegerOrNull('42')")

    def test_tofloatornull_parse(self):
        self._parse("RETURN toFloatOrNull('3.14')")

    def test_tobooleanlist_parse(self):
        self._parse("RETURN toBooleanList(['true', 'false'])")

    def test_tointegerlist_parse(self):
        self._parse("RETURN toIntegerList(['1', '2'])")

    def test_tofloatlist_parse(self):
        self._parse("RETURN toFloatList(['1.0', '2.0'])")

    def test_tostringlist_parse(self):
        self._parse("RETURN toStringList([1, 2, 3])")

    def test_elementid_parse(self):
        self._parse("MATCH (n) RETURN elementId(n)")

    def test_elementid_roundtrip(self):
        result = self._rt("MATCH (n) RETURN elementId(n)")
        # Neo4j maps elementId → ELEMENTID via GQL ELEMENT_ID path
        self.assertIn("ELEMENTID", result.upper())


# =============================================================================
# Anonymous function
# =============================================================================


class TestAnonymousFunction(unittest.TestCase):
    """Test that unknown function names parse as Anonymous."""

    def test_unknown_function_parses_as_anonymous(self):
        trees = _neo4j().parse("RETURN myCustomFunc(1, 2)")
        nodes = list(trees[0].find_all(Anonymous))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, "myCustomFunc")
        self.assertEqual(len(nodes[0].arguments), 2)

    def test_anonymous_roundtrip(self):
        result = _neo4j().transpile("RETURN myCustomFunc(1, 2)")[0]
        self.assertIn("myCustomFunc", result)

    def test_anonymous_no_args(self):
        trees = _neo4j().parse("RETURN myFunc()")
        nodes = list(trees[0].find_all(Anonymous))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, "myFunc")
        self.assertEqual(len(nodes[0].arguments), 0)


# =============================================================================
# Special syntax
# =============================================================================


class TestCypherReduce(unittest.TestCase):
    """Tests for reduce(acc = init, x IN list | expr)."""

    def test_reduce_parse(self):
        _neo4j().parse("RETURN reduce(s = 0, x IN [1, 2, 3] | s + x)")

    def test_reduce_roundtrip(self):
        d = _neo4j()
        tree = d.parse("RETURN reduce(s = 0, x IN [1, 2, 3] | s + x)")[0]
        result = str(d.generator().generate(tree))
        self.assertIn("reduce", result.lower())
        self.assertIn("s = 0", result)
        self.assertIn("IN", result)

    def test_reduce_ast_type(self):
        trees = _neo4j().parse("RETURN reduce(s = 0, x IN [1, 2, 3] | s + x)")
        nodes = list(trees[0].find_all(CypherReduce))
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.accumulator.name, "s")
        self.assertEqual(node.variable.name, "x")


class TestCypherPointFunctions(unittest.TestCase):
    """Tests for point(), point.distance(), point.withinBBox()."""

    def test_point_constructor_parse(self):
        _neo4j().parse("RETURN point({x: 1, y: 2})")

    def test_point_constructor_roundtrip(self):
        result = _neo4j().transpile("RETURN point({x: 1, y: 2})")[0]
        self.assertIn("point", result.lower())

    def test_point_distance_parse(self):
        _neo4j().parse("RETURN point.distance(point({x: 1, y: 2}), point({x: 3, y: 4}))")

    def test_point_distance_roundtrip(self):
        result = _neo4j().transpile(
            "RETURN point.distance(point({x: 1, y: 2}), point({x: 3, y: 4}))"
        )[0]
        self.assertIn("point.distance", result.lower())

    def test_point_withinbbox_parse(self):
        _neo4j().parse(
            "RETURN point.withinBBox(point({x: 1, y: 2}), point({x: 0, y: 0}), point({x: 3, y: 3}))"
        )


# =============================================================================
# Feature gating (CoreGQL doesn't parse Cypher functions)
# =============================================================================


class TestFuncDialectGating(unittest.TestCase):
    """Non-Cypher dialects reject Cypher functions."""

    def test_randomuuid_fails_under_coregql(self):
        d = Dialect.get_or_raise("coregql")
        with self.assertRaises((FeatureError, ParseError)):
            d.transpile("RETURN randomUUID()")

    def test_timestamp_fails_under_coregql(self):
        d = Dialect.get_or_raise("coregql")
        with self.assertRaises((FeatureError, ParseError)):
            d.parse("RETURN timestamp()")

    def test_point_fails_under_coregql(self):
        d = Dialect.get_or_raise("coregql")
        with self.assertRaises((FeatureError, ParseError)):
            d.transpile("RETURN point({x: 1, y: 2})")


# =============================================================================
# Edge cases
# =============================================================================


class TestFuncEdgeCases(unittest.TestCase):
    """Edge cases: nested calls, in WHERE/ORDER BY."""

    def test_nested_function_calls(self):
        _neo4j().parse("RETURN replace(toString(123), '1', '9')")

    def test_function_in_where(self):
        _neo4j().parse("MATCH (n) WHERE isEmpty(n.name) = true RETURN n")

    def test_function_in_order_by(self):
        _neo4j().parse("MATCH (n) RETURN n ORDER BY replace(n.name, 'a', 'b')")

    def test_function_in_case_expression(self):
        _neo4j().parse("RETURN CASE WHEN isEmpty('') = true THEN 1 ELSE 0 END")

    def test_function_with_property_access(self):
        """Functions used alongside property access should parse correctly."""
        _neo4j().parse("MATCH (n) RETURN replace(n.name, 'old', 'new')")
