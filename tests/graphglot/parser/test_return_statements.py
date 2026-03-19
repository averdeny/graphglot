"""Tests for RETURN statement parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestReturnStatements(unittest.TestCase):
    """Test suite for RETURN statement parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_return_all(self):
        """Test that the parser can parse a return all statement."""
        query = "RETURN *"
        expr = self.helper.parse_single(query, ast.PrimitiveResultStatement)

        leaves = expr.leaf_list()
        self.assertEqual(len(leaves), 1)
        self.assertIsInstance(leaves[0], ast.Asterisk)

    def test_return_item_list(self):
        """Test that the parser can parse a return item list."""
        query = "RETURN DISTINCT n.name, n.age"
        expr = self.helper.parse_single(query, ast.PrimitiveResultStatement)

        leaves = expr.leaf_list()
        self.assertEqual(len(leaves), 5)
