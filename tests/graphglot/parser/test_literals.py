"""Tests for literal parsing functionality."""

import unittest

from decimal import Decimal

from graphglot import ast
from graphglot.dialect.neo4j import Neo4j
from graphglot.error import GraphGlotError

from .helpers import ParserTestHelper


class TestCharacterStringLiteral(unittest.TestCase):
    """Test suite for character string literal parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_single_quoted_string(self):
        expr = self.helper.parse_single("'hello'", ast.CharacterStringLiteral)
        self.assertIsInstance(expr, ast.CharacterStringLiteral)
        self.assertEqual(expr.value, "hello")

    def test_double_quoted_string(self):
        expr = self.helper.parse_single('"world"', ast.CharacterStringLiteral)
        self.assertIsInstance(expr, ast.CharacterStringLiteral)
        self.assertEqual(expr.value, "world")

    def test_empty_string(self):
        expr = self.helper.parse_single("''", ast.CharacterStringLiteral)
        self.assertIsInstance(expr, ast.CharacterStringLiteral)
        self.assertEqual(expr.value, "")


class TestByteStringLiteral(unittest.TestCase):
    """Test suite for byte string literal parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_byte_string_uppercase_x(self):
        expr = self.helper.parse_single("X'00FF'", ast.ByteStringLiteral)
        self.assertIsInstance(expr, ast.ByteStringLiteral)
        self.assertEqual(expr.value, "00FF")

    def test_byte_string_lowercase_x(self):
        expr = self.helper.parse_single("x'AB'", ast.ByteStringLiteral)
        self.assertIsInstance(expr, ast.ByteStringLiteral)
        self.assertEqual(expr.value, "AB")


class TestUnsignedNumericLiteral(unittest.TestCase):
    """Test suite for unsigned numeric literal parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_integer(self):
        expr = self.helper.parse_single("42", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, 42)

    def test_decimal(self):
        expr = self.helper.parse_single("3.14", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, Decimal("3.14"))

    def test_scientific_notation(self):
        expr = self.helper.parse_single("1.23e10", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, Decimal("1.23e10"))

    def test_scientific_notation_integer_base(self):
        """Scientific notation without decimal point (e.g. 3e10)."""
        expr = self.helper.parse_single("3e10", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, Decimal("3e10"))

    def test_exact_suffix_integer(self):
        """Integer with exact number suffix M (GL05)."""
        expr = self.helper.parse_single("10M", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, 10)

    def test_exact_suffix_decimal(self):
        """Decimal with exact number suffix m (GL05)."""
        expr = self.helper.parse_single("3.14m", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, Decimal("3.14"))

    def test_float_suffix(self):
        """Decimal with approximate number suffix f (GL09)."""
        expr = self.helper.parse_single("3.14f", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, Decimal("3.14"))

    def test_double_suffix(self):
        """Decimal with approximate number suffix d (GL10)."""
        expr = self.helper.parse_single("3.14d", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, Decimal("3.14"))


class TestSignedNumericLiteral(unittest.TestCase):
    """Test suite for signed numeric literal parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_negative_integer(self):
        expr = self.helper.parse_single("-42", ast.SignedNumericLiteral)
        self.assertIsInstance(expr, ast.SignedNumericLiteral)
        self.assertEqual(expr.sign, ast.Sign.MINUS_SIGN)
        self.assertEqual(expr.unsigned_numeric_literal.value, 42)

    def test_positive_integer(self):
        expr = self.helper.parse_single("+3", ast.SignedNumericLiteral)
        self.assertIsInstance(expr, ast.SignedNumericLiteral)
        self.assertEqual(expr.sign, ast.Sign.PLUS_SIGN)
        self.assertEqual(expr.unsigned_numeric_literal.value, 3)

    def test_unsigned_defaults_to_plus(self):
        expr = self.helper.parse_single("99", ast.SignedNumericLiteral)
        self.assertIsInstance(expr, ast.SignedNumericLiteral)
        self.assertEqual(expr.sign, ast.Sign.PLUS_SIGN)
        self.assertEqual(expr.unsigned_numeric_literal.value, 99)


class TestLiteral(unittest.TestCase):
    """Test suite for top-level literal routing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_literal_routes_to_signed_numeric(self):
        expr = self.helper.parse_single("-42", ast.Literal)
        self.assertIsInstance(expr, ast.SignedNumericLiteral)

    def test_literal_routes_to_general_literal(self):
        expr = self.helper.parse_single("'hello'", ast.Literal)
        self.assertIsInstance(expr, ast.CharacterStringLiteral)


class TestGeneralLiteral(unittest.TestCase):
    """Test suite for general literal routing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_routes_to_character_string(self):
        expr = self.helper.parse_single("'hello'", ast.GeneralLiteral)
        self.assertIsInstance(expr, ast.CharacterStringLiteral)

    def test_routes_to_boolean(self):
        expr = self.helper.parse_single("TRUE", ast.GeneralLiteral)
        self.assertIsInstance(expr, ast.BooleanLiteral)

    def test_routes_to_null(self):
        expr = self.helper.parse_single("NULL", ast.GeneralLiteral)
        self.assertIsInstance(expr, ast.NullLiteral)


class TestUnsignedLiteral(unittest.TestCase):
    """Test suite for unsigned literal routing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_routes_to_unsigned_numeric(self):
        expr = self.helper.parse_single("42", ast.UnsignedLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)

    def test_routes_to_general_literal_string(self):
        expr = self.helper.parse_single("'hi'", ast.UnsignedLiteral)
        self.assertIsInstance(expr, ast.CharacterStringLiteral)


class TestTemporalLiteral(unittest.TestCase):
    """Test suite for temporal literal routing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_routes_to_date_literal(self):
        expr = self.helper.parse_single("DATE '2021-01-01'", ast.TemporalLiteral)
        self.assertIsInstance(expr, ast.DateLiteral)

    def test_routes_to_time_literal(self):
        expr = self.helper.parse_single("TIME '12:00:00'", ast.TemporalLiteral)
        self.assertIsInstance(expr, ast.TimeLiteral)

    def test_routes_to_datetime_literal(self):
        expr = self.helper.parse_single("DATETIME '2021-01-01T12:00:00'", ast.TemporalLiteral)
        self.assertIsInstance(expr, ast.DatetimeLiteral)


class TestSqlIntervalLiteral(unittest.TestCase):
    """Test suite for SQL interval literal parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_interval_year(self):
        expr = self.helper.parse_single("INTERVAL '1' YEAR", ast.SqlIntervalLiteral)
        self.assertIsInstance(expr, ast.SqlIntervalLiteral)
        self.assertEqual(expr.start_field, ast.SqlIntervalLiteral.DatetimeField.YEAR)
        self.assertIsNone(expr.end_field)

    def test_interval_year_to_month(self):
        expr = self.helper.parse_single("INTERVAL '1-6' YEAR TO MONTH", ast.SqlIntervalLiteral)
        self.assertIsInstance(expr, ast.SqlIntervalLiteral)
        self.assertEqual(expr.start_field, ast.SqlIntervalLiteral.DatetimeField.YEAR)
        self.assertEqual(expr.end_field, ast.SqlIntervalLiteral.DatetimeField.MONTH)

    def test_interval_with_sign(self):
        expr = self.helper.parse_single("INTERVAL -'5' DAY", ast.SqlIntervalLiteral)
        self.assertIsInstance(expr, ast.SqlIntervalLiteral)
        self.assertEqual(expr.sign, ast.Sign.MINUS_SIGN)
        self.assertEqual(expr.start_field, ast.SqlIntervalLiteral.DatetimeField.DAY)


class TestUnicodeEscapeValidation(unittest.TestCase):
    """Test unicode escape sequence validation in the lexer."""

    def setUp(self):
        self.neo4j = Neo4j()

    def test_valid_unicode_4_digit(self):
        """\\u01FF should parse to the character ǿ."""
        results = self.neo4j.parse("RETURN '\\u01FF'")
        self.assertTrue(len(results) > 0)

    def test_valid_unicode_6_digit(self):
        """\\U01F600 should parse to a valid codepoint."""
        results = self.neo4j.parse("RETURN '\\U01F600'")
        self.assertTrue(len(results) > 0)

    def test_invalid_unicode_escape(self):
        """\\uH is not a valid unicode escape — should raise error."""
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("RETURN '\\uH'")

    def test_incomplete_unicode_escape(self):
        """\\u01 has only 2 hex digits instead of 4 — should raise error."""
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("RETURN '\\u01'")


class TestNegativeSkipLimit(unittest.TestCase):
    """Test that negative/float SKIP and LIMIT are rejected in Cypher."""

    def setUp(self):
        self.neo4j = Neo4j()

    def test_skip_negative_rejected(self):
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("MATCH (n) RETURN n SKIP -1")

    def test_limit_negative_rejected(self):
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("MATCH (n) RETURN n LIMIT -1")

    def test_limit_float_rejected(self):
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("MATCH (n) RETURN n LIMIT 1.5")

    def test_skip_float_rejected(self):
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("MATCH (n) RETURN n SKIP 1.5")

    def test_skip_positive_ok(self):
        results = self.neo4j.parse("MATCH (n) RETURN n SKIP 5")
        self.assertTrue(len(results) > 0)

    def test_limit_param_ok(self):
        results = self.neo4j.parse("MATCH (n) RETURN n LIMIT $x")
        self.assertTrue(len(results) > 0)


class TestIntegerOverflow(unittest.TestCase):
    """Test int64 overflow detection in numeric literals."""

    def setUp(self):
        self.helper = ParserTestHelper()
        self.neo4j = Neo4j()

    def test_int64_max_ok(self):
        """2^63 - 1 should parse fine."""
        expr = self.helper.parse_single("9223372036854775807", ast.UnsignedNumericLiteral)
        self.assertEqual(expr.value, 9223372036854775807)

    def test_int64_overflow(self):
        """2^63 should overflow."""
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("RETURN 9223372036854775808")

    def test_int64_min_ok(self):
        """-(2^63 - 1) should parse fine as a signed literal."""
        results = self.neo4j.parse("RETURN -9223372036854775807")
        self.assertTrue(len(results) > 0)

    def test_int64_underflow(self):
        """-(2^63 + 1) should underflow (unsigned part exceeds int64 max)."""
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("RETURN -9223372036854775809")

    def test_hex_overflow(self):
        """0x8000000000000000 = 2^63 should overflow."""
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("RETURN 0x8000000000000000")

    def test_octal_overflow(self):
        """0o1000000000000000000000 = 2^63 should overflow."""
        with self.assertRaises(GraphGlotError):
            self.neo4j.parse("RETURN 0o1000000000000000000000")


class TestFloatOverflow(unittest.TestCase):
    """Test float overflow detection in numeric literals."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_large_float_ok(self):
        """1.0E308 is within IEEE 754 double range."""
        expr = self.helper.parse_single("1.0E308", ast.UnsignedNumericLiteral)
        self.assertIsInstance(expr, ast.UnsignedNumericLiteral)

    def test_float_overflow(self):
        """1.34E999 exceeds IEEE 754 double max."""
        with self.assertRaises(GraphGlotError):
            self.helper.parse_single("1.34E999", ast.UnsignedNumericLiteral)
