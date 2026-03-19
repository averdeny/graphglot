"""Tests for value type parsing functionality."""

import unittest

import pytest

from pydantic import ValidationError

from graphglot import ast

from .helpers import ParserTestHelper


class TestValueType(unittest.TestCase):
    """Test suite for ValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_value_type_boolean(self):
        """Test that the parser can parse a boolean value type."""
        query = "BOOLEAN"
        expr = self.helper.parse_single(query, ast.ValueType)

        self.assertIsInstance(expr, ast.PredefinedType)
        self.assertIsInstance(expr, ast.BooleanType)

    def test_value_type_character_string(self):
        """Test that the parser can parse a character string value type."""
        query = "STRING"
        expr = self.helper.parse_single(query, ast.ValueType)

        self.assertIsInstance(expr, ast.PredefinedType)
        self.assertIsInstance(expr, ast.CharacterStringType)

    def test_value_type_path(self):
        """Test that the parser can parse a path value type."""
        query = "PATH"
        expr = self.helper.parse_single(query, ast.ValueType)

        self.assertIsInstance(expr, ast.ConstructedValueType)
        self.assertIsInstance(expr, ast.PathValueType)

    def test_value_type_list(self):
        """Test that the parser can parse a list value type."""
        query = "LIST<INTEGER>"
        expr = self.helper.parse_single(query, ast.ValueType)

        self.assertIsInstance(expr, ast.ConstructedValueType)
        self.assertIsInstance(expr, ast.ListValueType)


class TestPredefinedType(unittest.TestCase):
    """Test suite for PredefinedType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_predefined_type_boolean(self):
        """Test that the parser can parse a boolean predefined type."""
        query = "BOOLEAN"
        expr = self.helper.parse_single(query, ast.PredefinedType)

        self.assertIsInstance(expr, ast.BooleanType)

    def test_predefined_type_character_string(self):
        """Test that the parser can parse a character string predefined type."""
        query = "STRING"
        expr = self.helper.parse_single(query, ast.PredefinedType)

        self.assertIsInstance(expr, ast.CharacterStringType)

    def test_predefined_type_numeric(self):
        """Test that the parser can parse a numeric predefined type."""
        query = "INTEGER"
        expr = self.helper.parse_single(query, ast.PredefinedType)

        self.assertIsInstance(expr, ast.NumericType)


class TestBooleanType(unittest.TestCase):
    """Test suite for BooleanType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_boolean_type_bool(self):
        """Test that the parser can parse BOOL type."""
        query = "BOOL"
        expr = self.helper.parse_single(query, ast.BooleanType)

        self.assertIsInstance(expr, ast.BooleanType)
        self.assertFalse(expr.not_null)

    def test_boolean_type_boolean(self):
        """Test that the parser can parse BOOLEAN type."""
        query = "BOOLEAN"
        expr = self.helper.parse_single(query, ast.BooleanType)

        self.assertIsInstance(expr, ast.BooleanType)
        self.assertFalse(expr.not_null)

    def test_boolean_type_with_not_null(self):
        """Test that the parser can parse boolean type with NOT NULL."""
        query = "BOOLEAN NOT NULL"
        expr = self.helper.parse_single(query, ast.BooleanType)

        self.assertIsInstance(expr, ast.BooleanType)
        self.assertTrue(expr.not_null)


class TestCharacterStringType(unittest.TestCase):
    """Test suite for CharacterStringType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_character_string_type_string(self):
        """Test that the parser can parse STRING type."""
        query = "STRING"
        expr = self.helper.parse_single(query, ast.CharacterStringType)

        self.assertIsInstance(expr, ast.CharacterStringType)

    def test_character_string_type_string_with_length(self):
        """Test that the parser can parse STRING type with length."""
        query = "STRING(100)"
        expr = self.helper.parse_single(query, ast.CharacterStringType)

        self.assertIsInstance(expr, ast.CharacterStringType)

    def test_character_string_type_char(self):
        """Test that the parser can parse CHAR type."""
        query = "CHAR"
        expr = self.helper.parse_single(query, ast.CharacterStringType)

        self.assertIsInstance(expr, ast.CharacterStringType)

    def test_character_string_type_char_with_length(self):
        """Test that the parser can parse CHAR type with fixed length."""
        query = "CHAR(10)"
        expr = self.helper.parse_single(query, ast.CharacterStringType)

        self.assertIsInstance(expr, ast.CharacterStringType)

    def test_character_string_type_varchar(self):
        """Test that the parser can parse VARCHAR type."""
        query = "VARCHAR(255)"
        expr = self.helper.parse_single(query, ast.CharacterStringType)

        self.assertIsInstance(expr, ast.CharacterStringType)

    def test_character_string_type_with_not_null(self):
        """Test that the parser can parse character string type with NOT NULL."""
        query = "STRING NOT NULL"
        expr = self.helper.parse_single(query, ast.CharacterStringType)

        self.assertIsInstance(expr, ast.CharacterStringType)


class TestNumericType(unittest.TestCase):
    """Test suite for NumericType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_numeric_type_integer(self):
        """Test that the parser can parse INTEGER type."""
        query = "INTEGER"
        expr = self.helper.parse_single(query, ast.NumericType)

        self.assertIsInstance(expr, ast.NumericType)

    def test_numeric_type_double(self):
        """Test that the parser can parse DOUBLE type."""
        query = "DOUBLE"
        expr = self.helper.parse_single(query, ast.NumericType)

        self.assertIsInstance(expr, ast.NumericType)


class TestPathValueType(unittest.TestCase):
    """Test suite for PathValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_path_value_type(self):
        """Test that the parser can parse PATH type."""
        query = "PATH"
        expr = self.helper.parse_single(query, ast.PathValueType)

        self.assertIsInstance(expr, ast.PathValueType)
        self.assertFalse(expr.not_null)

    def test_path_value_type_with_not_null(self):
        """Test that the parser can parse PATH type with NOT NULL."""
        query = "PATH NOT NULL"
        expr = self.helper.parse_single(query, ast.PathValueType)

        self.assertIsInstance(expr, ast.PathValueType)
        self.assertTrue(expr.not_null)


class TestListValueType(unittest.TestCase):
    """Test suite for ListValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_list_value_type_with_angle_brackets(self):
        """Test that the parser can parse LIST type with angle brackets."""
        query = "LIST<INTEGER>"
        expr = self.helper.parse_single(query, ast.ListValueType)

        self.assertIsInstance(expr, ast.ListValueType)

    def test_list_value_type_with_array_synonym(self):
        """Test that the parser can parse ARRAY type synonym."""
        query = "ARRAY<STRING>"
        expr = self.helper.parse_single(query, ast.ListValueType)

        self.assertIsInstance(expr, ast.ListValueType)

    def test_list_value_type_with_max_length(self):
        """Test that the parser can parse LIST type with max length."""
        query = "LIST<INTEGER>[100]"
        expr = self.helper.parse_single(query, ast.ListValueType)

        self.assertIsInstance(expr, ast.ListValueType)

    def test_list_value_type_with_not_null(self):
        """Test that the parser can parse LIST type with NOT NULL."""
        query = "LIST<INTEGER> NOT NULL"
        expr = self.helper.parse_single(query, ast.ListValueType)

        self.assertIsInstance(expr, ast.ListValueType)


class TestPostfixListValueType(unittest.TestCase):
    """Test suite for postfix <list value type>: <value type> <list value type name>."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_postfix_int_list(self):
        """Test INT LIST parses as postfix list value type."""
        result = self.helper.parse_single("INT LIST", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertIsInstance(result.body, ast.ListValueType._ValueTypeListValueTypeName)
        self.assertFalse(result.body.list_value_type_name.group)

    def test_postfix_string_array(self):
        """Test STRING ARRAY uses the ARRAY synonym."""
        result = self.helper.parse_single("STRING ARRAY", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertIsInstance(result.body, ast.ListValueType._ValueTypeListValueTypeName)

    def test_postfix_with_max_length(self):
        """Test INTEGER LIST[100] sets max_length."""
        result = self.helper.parse_single("INTEGER LIST[100]", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertIsNotNone(result.max_length)
        self.assertEqual(result.max_length.value, 100)

    def test_postfix_with_not_null(self):
        """Test INTEGER LIST NOT NULL sets not_null."""
        result = self.helper.parse_single("INTEGER LIST NOT NULL", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertTrue(result.not_null)

    def test_postfix_group_list(self):
        """Test STRING GROUP LIST sets group=True."""
        result = self.helper.parse_single("STRING GROUP LIST", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertTrue(result.body.list_value_type_name.group)

    def test_postfix_group_list_max_length(self):
        """Test STRING GROUP LIST[10] with group and max_length."""
        result = self.helper.parse_single("STRING GROUP LIST[10]", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertTrue(result.body.list_value_type_name.group)
        self.assertIsNotNone(result.max_length)
        self.assertEqual(result.max_length.value, 10)

    def test_postfix_all_options(self):
        """Test INTEGER GROUP LIST[5] NOT NULL with all options."""
        result = self.helper.parse_single("INTEGER GROUP LIST[5] NOT NULL", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertTrue(result.body.list_value_type_name.group)
        self.assertEqual(result.max_length.value, 5)
        self.assertTrue(result.not_null)

    def test_postfix_nested(self):
        """Test INT LIST LIST produces nested ListValueType."""
        result = self.helper.parse_single("INT LIST LIST", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        inner = result.body.value_type
        self.assertIsInstance(inner, ast.ListValueType)

    def test_postfix_boolean_list(self):
        """Test BOOLEAN LIST parses correctly."""
        result = self.helper.parse_single("BOOLEAN LIST", ast.ValueType)
        self.assertIsInstance(result, ast.ListValueType)
        self.assertIsInstance(result.body.value_type, ast.BooleanType)

    def test_postfix_round_trip(self):
        """Test postfix list types round-trip through generate and reparse."""
        for query in ["INT LIST", "STRING GROUP LIST[10]", "BOOLEAN LIST NOT NULL"]:
            ast1 = self.helper.parse_single(query, ast.ValueType)
            generated = ast1.to_gql()
            ast2 = self.helper.parse_single(generated, ast.ValueType)
            self.assertEqual(ast1, ast2, f"Round-trip failed for: {query}")


class TestRecordType(unittest.TestCase):
    """Test suite for RecordType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_record_type_any(self):
        """Test that the parser can parse ANY RECORD type."""
        query = "ANY RECORD"
        expr = self.helper.parse_single(query, ast.RecordType)

        self.assertIsInstance(expr, ast.RecordType)

    def test_record_type_simple(self):
        """Test that the parser can parse RECORD type."""
        query = "RECORD"
        expr = self.helper.parse_single(query, ast.RecordType)

        self.assertIsInstance(expr, ast.RecordType)

    def test_record_type_with_not_null(self):
        """Test that the parser can parse RECORD type with NOT NULL."""
        query = "RECORD NOT NULL"
        expr = self.helper.parse_single(query, ast.RecordType)

        self.assertIsInstance(expr, ast.RecordType)


class TestImmaterialValueType(unittest.TestCase):
    """Test suite for ImmaterialValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_immaterial_value_type_null(self):
        """Test that the parser can parse NULL type."""
        query = "NULL"
        expr = self.helper.parse_single(query, ast.ImmaterialValueType)

        self.assertIsInstance(expr, ast.NullType)

    def test_immaterial_value_type_empty(self):
        """Test that the parser can parse NOTHING type."""
        query = "NOTHING"
        expr = self.helper.parse_single(query, ast.ImmaterialValueType)

        self.assertIsInstance(expr, ast.EmptyType)


class TestConstructedValueType(unittest.TestCase):
    """Test suite for ConstructedValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_constructed_value_type_path(self):
        """Test that the parser can parse path constructed value type."""
        query = "PATH"
        expr = self.helper.parse_single(query, ast.ConstructedValueType)

        self.assertIsInstance(expr, ast.PathValueType)

    def test_constructed_value_type_list(self):
        """Test that the parser can parse list constructed value type."""
        query = "LIST<INTEGER>"
        expr = self.helper.parse_single(query, ast.ConstructedValueType)

        self.assertIsInstance(expr, ast.ListValueType)

    def test_constructed_value_type_record(self):
        """Test that the parser can parse record constructed value type."""
        query = "RECORD"
        expr = self.helper.parse_single(query, ast.ConstructedValueType)

        self.assertIsInstance(expr, ast.RecordType)


class TestStringTypeValidation(unittest.TestCase):
    """Test that _String and _Bytes reject min_length without max_length."""

    def test_string_min_without_max_raises(self):
        """STRING with min_length but no max_length should raise ValueError."""
        with pytest.raises(ValidationError):
            ast.CharacterStringType._String(
                min_length=ast.UnsignedInteger(value=1),
                max_length=None,
            )

    def test_string_min_with_max_ok(self):
        """STRING with both min_length and max_length should be valid."""
        s = ast.CharacterStringType._String(
            min_length=ast.UnsignedInteger(value=1),
            max_length=ast.UnsignedInteger(value=100),
        )
        self.assertIsNotNone(s.min_length)
        self.assertIsNotNone(s.max_length)

    def test_string_no_lengths_ok(self):
        """STRING with no lengths should be valid."""
        s = ast.CharacterStringType._String(min_length=None, max_length=None)
        self.assertIsNone(s.min_length)
        self.assertIsNone(s.max_length)

    def test_bytes_min_without_max_raises(self):
        """BYTES with min_length but no max_length should raise ValueError."""
        with pytest.raises(ValidationError):
            ast.ByteStringType._Bytes(
                min_length=ast.UnsignedInteger(value=1),
                max_length=None,
            )

    def test_bytes_min_with_max_ok(self):
        """BYTES with both min_length and max_length should be valid."""
        b = ast.ByteStringType._Bytes(
            min_length=ast.UnsignedInteger(value=1),
            max_length=ast.UnsignedInteger(value=100),
        )
        self.assertIsNotNone(b.min_length)
        self.assertIsNotNone(b.max_length)
