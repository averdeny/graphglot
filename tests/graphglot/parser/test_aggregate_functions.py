"""Tests for aggregate function parsing."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestAggregateFunctions(unittest.TestCase):
    """Test suite for aggregate function parsers."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_count_star(self):
        query = "COUNT(*)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)

    def test_general_set_function_sum(self):
        query = "SUM(n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.GeneralSetFunction,
        )

    def test_max(self):
        query = "MAX(n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.GeneralSetFunction,
        )

    def test_min(self):
        query = "MIN(n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.GeneralSetFunction,
        )

    def test_collect_list(self):
        query = "COLLECT_LIST(n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.GeneralSetFunction,
        )

    def test_stddev_samp(self):
        query = "STDDEV_SAMP(n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.GeneralSetFunction,
        )

    def test_stddev_pop(self):
        query = "STDDEV_POP(n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.GeneralSetFunction,
        )

    def test_general_set_function_avg_distinct(self):
        query = "AVG(DISTINCT n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)

    def test_binary_set_function_percentile_cont(self):
        query = "PERCENTILE_CONT(0.5, n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.BinarySetFunction,
        )

    def test_binary_set_function_percentile_disc(self):
        query = "PERCENTILE_DISC(0.5, n.age)"
        expr = self.helper.parse_single(query, ast.AggregateFunction)
        self.assertIsInstance(expr, ast.AggregateFunction)
        self.assertIsInstance(
            expr.aggregate_function,
            ast.BinarySetFunction,
        )
