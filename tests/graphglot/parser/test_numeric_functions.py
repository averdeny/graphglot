"""Tests for numeric value function parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestNumericFunctions(unittest.TestCase):
    """Test suite for numeric value function parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_length_expression(self):
        """Test that the parser can parse CHAR_LENGTH expression."""
        query = 'CHAR_LENGTH("Hello" || "World")'
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.LengthExpression)

    def test_cardinality_expression(self):
        """Test that the parser can parse CARDINALITY expression."""
        query = "CARDINALITY(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.CardinalityExpression)

    def test_absolute_value_expression(self):
        """Test that the parser can parse ABS expression."""
        query = "ABS(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.AbsoluteValueExpression)

    def test_modulus_expression(self):
        """Test that the parser can parse MOD expression."""
        query = "MOD(p, 2)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.ModulusExpression)

    def test_trigonometric_function(self):
        """Test that the parser can parse trigonometric function."""
        query = "SIN(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.TrigonometricFunction)

    def test_general_logarithm_function(self):
        """Test that the parser can parse general logarithm function."""
        query = "LOG(p, 10)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.GeneralLogarithmFunction)

    def test_common_logarithm(self):
        """Test that the parser can parse common logarithm."""
        query = "LOG10(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.CommonLogarithm)

    def test_natural_logarithm(self):
        """Test that the parser can parse natural logarithm."""
        query = "LN(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.NaturalLogarithm)

    def test_exponential_function(self):
        """Test that the parser can parse exponential function."""
        query = "EXP(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.ExponentialFunction)

    def test_power_function(self):
        """Test that the parser can parse POWER function."""
        query = "POWER(p, 2)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.PowerFunction)

    def test_square_root_expression(self):
        """Test that the parser can parse SQRT expression."""
        query = "SQRT(4)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.SquareRoot)

    def test_floor_function(self):
        """Test that the parser can parse FLOOR function."""
        query = "FLOOR(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.FloorFunction)

    def test_ceiling_function(self):
        """Test that the parser can parse CEILING function."""
        query = "CEILING(p)"
        expr = self.helper.parse_single(query, ast.NumericValueFunction)

        self.assertIsInstance(expr, ast.CeilingFunction)
