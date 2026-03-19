"""Tests for temporal (date/time/datetime/duration) function parsing."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestTemporalFunctions(unittest.TestCase):
    """Test suite for temporal function parsers."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_date_function_current_date(self):
        query = "CURRENT_DATE"
        expr = self.helper.parse_single(query, ast.DateFunction)
        self.assertIsInstance(expr, ast.DateFunction)

    def test_date_function_date(self):
        query = "DATE('2021-01-01')"
        expr = self.helper.parse_single(query, ast.DateFunction)
        self.assertIsInstance(expr, ast.DateFunction)

    def test_time_function_current_time(self):
        query = "CURRENT_TIME"
        expr = self.helper.parse_single(query, ast.TimeFunction)
        self.assertIsInstance(expr, ast.TimeFunction)

    def test_datetime_function_current_timestamp(self):
        query = "CURRENT_TIMESTAMP"
        expr = self.helper.parse_single(query, ast.DatetimeFunction)
        self.assertIsInstance(expr, ast.DatetimeFunction)

    def test_duration_function(self):
        query = "DURATION( { d: 'PT1H' })"
        expr = self.helper.parse_single(query, ast.DurationFunction)
        self.assertIsInstance(expr, ast.DurationFunction)
