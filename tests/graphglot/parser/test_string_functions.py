"""Tests for character and byte string function parsing."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestStringFunctions(unittest.TestCase):
    """Test suite for string function parsers."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_substring_function_left(self):
        query = "LEFT('abcdef', 3)"
        expr = self.helper.parse_single(query, ast.SubstringFunction)
        self.assertIsInstance(expr, ast.SubstringFunction)
        self.assertEqual(expr.mode, ast.SubstringFunction.Mode.LEFT)

    def test_substring_function_right(self):
        query = "RIGHT('abcdef', 2)"
        expr = self.helper.parse_single(query, ast.SubstringFunction)
        self.assertIsInstance(expr, ast.SubstringFunction)
        self.assertEqual(expr.mode, ast.SubstringFunction.Mode.RIGHT)

    def test_fold_upper(self):
        query = "UPPER('abc')"
        expr = self.helper.parse_single(query, ast.Fold)
        self.assertIsInstance(expr, ast.Fold)
        self.assertEqual(expr.mode, ast.Fold.Mode.UPPER)

    def test_fold_lower(self):
        query = "LOWER('ABC')"
        expr = self.helper.parse_single(query, ast.Fold)
        self.assertIsInstance(expr, ast.Fold)
        self.assertEqual(expr.mode, ast.Fold.Mode.LOWER)

    def test_single_character_trim_function(self):
        query = "TRIM(LEADING ' ' FROM '  abc  ')"
        expr = self.helper.parse_single(query, ast.SingleCharacterTrimFunction)
        self.assertIsInstance(expr, ast.SingleCharacterTrimFunction)
        self.assertIsInstance(expr.trim_operands, ast.TrimOperands)

    def test_multi_character_trim_function_btrim(self):
        query = "BTRIM('xxabcxx', 'x')"
        expr = self.helper.parse_single(query, ast.MultiCharacterTrimFunction)
        self.assertIsInstance(expr, ast.MultiCharacterTrimFunction)

    def test_normalize_function_with_form(self):
        query = "NORMALIZE('abc' , NFC)"
        expr = self.helper.parse_single(query, ast.NormalizeFunction)
        self.assertIsInstance(expr, ast.NormalizeFunction)
        self.assertIsNotNone(expr.normal_form)

    def test_normalize_function_without_form(self):
        query = "NORMALIZE('abc')"
        expr = self.helper.parse_single(query, ast.NormalizeFunction)
        self.assertIsInstance(expr, ast.NormalizeFunction)
        self.assertIsNone(expr.normal_form)
