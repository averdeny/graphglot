"""Tests for known parser bugs identified by the openCypher TCK.

Bug 1: Boolean literals in boolean expressions (12 TCK scenarios)
  - `RETURN true AND false` fails because CommonValueExpression greedily
    consumes `true` before BooleanValueExpression gets a chance.

Bug 2: NOT with boolean literal (3 TCK scenarios)
  - `RETURN NOT true` already works via backtracking.
  - `RETURN NOT NOT true` is not valid GQL (BooleanFactor allows only one NOT);
    needs parentheses: `NOT (NOT true)`.  This is Cypher-only syntax.

Bug 3: Deep nested lists hit RecursionError (3 TCK scenarios)
  - `RETURN [[[[[[[]]]]]]]` blows the Python call stack due to ~65-70
    frames per nesting level in the recursive descent parser.
"""

import unittest

from graphglot import ast
from graphglot.error import ParseError
from graphglot.generator import Generator
from graphglot.lexer import Lexer

from .helpers import ParserTestHelper


class TestBooleanLiteralExpressions(unittest.TestCase):
    """Bug 1: Boolean literals as operands in boolean expressions."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_true_and_false(self):
        """RETURN true AND false AS tf"""
        expr = self.helper.parse_single("RETURN true AND false AS tf", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_true_or_false(self):
        """RETURN true OR false AS tf"""
        expr = self.helper.parse_single("RETURN true OR false AS tf", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_true_xor_false(self):
        """RETURN true XOR false AS tf"""
        expr = self.helper.parse_single("RETURN true XOR false AS tf", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_true_or_false_equals_false(self):
        """RETURN true OR false = false AS a"""
        expr = self.helper.parse_single("RETURN true OR false = false AS a", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_false_and_true(self):
        """RETURN false AND true AS ft"""
        expr = self.helper.parse_single("RETURN false AND true AS ft", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_chained_boolean_ops(self):
        """RETURN true AND false OR true AS r"""
        expr = self.helper.parse_single("RETURN true AND false OR true AS r", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_boolean_in_where(self):
        """WHERE clause with boolean literal expression."""
        expr = self.helper.parse_single(
            "MATCH (n) WHERE true AND n.active RETURN n", ast.GqlProgram
        )
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_unknown_and_true(self):
        """RETURN UNKNOWN AND true AS r"""
        expr = self.helper.parse_single("RETURN UNKNOWN AND true AS r", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)


class TestNotBooleanLiteral(unittest.TestCase):
    """Bug 2: NOT with boolean literal."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_not_true(self):
        """RETURN NOT true AS nt"""
        expr = self.helper.parse_single("RETURN NOT true AS nt", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_not_not_true_requires_parens(self):
        """NOT NOT true is not valid GQL — BooleanFactor allows only one NOT."""
        with self.assertRaises(ParseError):
            self.helper.parse_single("RETURN NOT NOT true AS nnt", ast.GqlProgram)

    def test_not_parenthesized_not_true(self):
        """NOT (NOT true) works with parentheses."""
        expr = self.helper.parse_single("RETURN NOT (NOT true) AS nnt", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_not_false(self):
        """RETURN NOT false AS nf"""
        expr = self.helper.parse_single("RETURN NOT false AS nf", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_not_false_gte_false(self):
        """RETURN NOT false >= false AS a"""
        expr = self.helper.parse_single("RETURN NOT false >= false AS a", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)


class TestDeepNestedLists(unittest.TestCase):
    """Bug 3: Deep nested lists hit RecursionError."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def _nested_list(self, depth: int) -> str:
        return "RETURN " + "[" * depth + "1" + "]" * depth + " AS literal"

    def test_nested_list_7_levels(self):
        """7 levels of nested lists."""
        expr = self.helper.parse_single(self._nested_list(7), ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_nested_list_20_levels(self):
        """20 levels of nested lists."""
        expr = self.helper.parse_single(self._nested_list(20), ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_nested_list_40_levels(self):
        """40 levels of nested lists."""
        expr = self.helper.parse_single(self._nested_list(40), ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_nested_empty_list_20_levels(self):
        """20 levels of nested empty lists: [[[[...[]...]]]]"""
        query = "RETURN " + "[" * 20 + "]" * 20 + " AS literal"
        expr = self.helper.parse_single(query, ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)


class TestRoundTripBooleanExpressions(unittest.TestCase):
    """Round-trip: parse → generate → re-parse for boolean literal expressions."""

    def setUp(self):
        self.helper = ParserTestHelper()
        self.gen = Generator()
        self.lexer = Lexer()

    def _round_trip(self, query: str):
        ast1 = self.helper.parse_single(query, ast.GqlProgram)
        generated = self.gen.generate(ast1)
        tokens2 = self.lexer.tokenize(generated)
        ast2 = self.helper.parser.parse(tokens2, generated)[0]
        self.assertEqual(
            ast1, ast2, f"Round-trip mismatch:\n  input:     {query}\n  generated: {generated}"
        )

    def test_true_and_false_round_trip(self):
        self._round_trip("RETURN true AND false AS tf")

    def test_true_or_false_round_trip(self):
        self._round_trip("RETURN true OR false AS tf")

    def test_not_true_round_trip(self):
        self._round_trip("RETURN NOT true AS nt")

    def test_nested_list_round_trip(self):
        self._round_trip("RETURN [[1, 2], [3]] AS nested")
