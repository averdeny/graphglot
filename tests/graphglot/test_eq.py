"""Tests for Expression.__eq__ accuracy using _macro_aware_dump."""

from __future__ import annotations

import unittest

from graphglot.dialect.base import Dialect

_dialect = Dialect()


class TestEqAccuracy(unittest.TestCase):
    """Verify __eq__ uses _macro_aware_dump and correctly distinguishes ASTs."""

    def _parse(self, query: str):
        return _dialect.parse(query)[0]

    def test_different_where_clauses_not_equal(self):
        """BooleanTest with different boolean_primary must compare unequal."""
        a = self._parse("MATCH (n) WHERE n.age > 21 RETURN n")
        b = self._parse("MATCH (n) WHERE n.name = 'Bob' RETURN n")
        self.assertNotEqual(a, b)

    def test_identical_queries_equal(self):
        a = self._parse("MATCH (n) RETURN n")
        b = self._parse("MATCH (n) RETURN n")
        self.assertEqual(a, b)

    def test_trig_round_trip_eq(self):
        """SIN(n.x) should round-trip to an equal AST."""
        a = self._parse("MATCH (n) RETURN SIN(n.x)")
        gen = a.to_gql()
        b = self._parse(gen)
        self.assertEqual(a, b)

    def test_list_prefix_round_trip_eq(self):
        """LIST[1, 2, 3] should round-trip to an equal AST."""
        a = self._parse("RETURN LIST[1, 2, 3]")
        gen = a.to_gql()
        b = self._parse(gen)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
