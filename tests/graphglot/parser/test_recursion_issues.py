"""Tests for parser recursion handling.

Validates that the parser cleanly handles constructs that previously caused
RecursionError due to the ValueType → DynamicUnionType → ComponentTypeList →
ValueType cycle. Token-based lookahead guards in parse_value_type prevent
infinite recursion; invalid bare type keywords now raise ParseError.
"""

import unittest

from graphglot import ast
from graphglot.error import ParseError

from .helpers import ParserTestHelper


class TestParserRecursionPassing(unittest.TestCase):
    """Constructs that were suspected of recursion issues but parse successfully."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_byte_length_function(self):
        """BYTE_LENGTH function parses successfully."""
        expr = self.helper.parse_single("MATCH (n) RETURN BYTE_LENGTH(n.name)", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_cardinality_function(self):
        """CARDINALITY function parses successfully."""
        expr = self.helper.parse_single("MATCH (n) RETURN CARDINALITY(n.friends)", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_for_statement(self):
        """FOR statement parses successfully."""
        expr = self.helper.parse_single("FOR x IN [1, 2, 3] RETURN x", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_byte_string_literal(self):
        """ByteStringLiteral parses successfully."""
        expr = self.helper.parse_single("RETURN X'48656C6C6F'", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)


class TestBareTypeKeywordsRejectCleanly(unittest.TestCase):
    """Bare type keywords that are not valid GQL type syntax.

    These previously caused RecursionError via the ValueType → DynamicUnionType →
    ComponentTypeList → ValueType cycle. With lookahead guards they now cleanly
    raise ParseError:
    - DURATION requires DURATION(qualifier) syntax
    - NUMERIC is not a valid GQL type keyword (use INT, FLOAT, etc.)
    - DATETIME requires ZONED DATETIME or LOCAL DATETIME
    - TIME requires ZONED TIME or LOCAL TIME
    """

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_duration_type(self):
        """Bare DURATION is not valid GQL type syntax; parser rejects cleanly."""
        with self.assertRaises(ParseError):
            self.helper.parse_single(
                "MATCH (n) WHERE n.x IS TYPED DURATION RETURN n", ast.GqlProgram
            )

    def test_numeric_type(self):
        """Bare NUMERIC is not valid GQL type syntax; parser rejects cleanly."""
        with self.assertRaises(ParseError):
            self.helper.parse_single(
                "MATCH (n) WHERE n.x IS TYPED NUMERIC RETURN n", ast.GqlProgram
            )

    def test_datetime_type(self):
        """Bare DATETIME is not valid GQL type syntax; parser rejects cleanly."""
        with self.assertRaises(ParseError):
            self.helper.parse_single(
                "MATCH (n) WHERE n.x IS TYPED DATETIME RETURN n", ast.GqlProgram
            )

    def test_time_type(self):
        """Bare TIME is not valid GQL type syntax; parser rejects cleanly."""
        with self.assertRaises(ParseError):
            self.helper.parse_single("MATCH (n) WHERE n.x IS TYPED TIME RETURN n", ast.GqlProgram)
