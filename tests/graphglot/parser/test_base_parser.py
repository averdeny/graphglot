"""Tests for base parser functionality."""

import unittest

from graphglot import ast
from graphglot.parser import Parser

from .helpers import ParserTestHelper


class TestBaseParser(unittest.TestCase):
    """Test suite for base parser functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_parser_initialization(self):
        """Test that parser can be initialized."""
        parser = Parser()
        self.assertIsNotNone(parser)

    def test_parser_reset(self):
        """Test that parser reset clears state."""
        parser = Parser()
        parser.reset()
        self.assertEqual(parser.query, "")
        self.assertEqual(len(parser.errors), 0)
        self.assertEqual(len(parser._tokens), 0)
        self.assertEqual(parser._index, 0)

    def test_parser_has_parsers_registry(self):
        """Test that parser has a PARSERS registry."""
        self.assertIsNotNone(Parser.PARSERS)
        self.assertIsInstance(Parser.PARSERS, dict)
        self.assertGreater(len(Parser.PARSERS), 0)

    def test_parser_registry_contains_key_types(self):
        """Test that parser registry contains expected key AST types."""
        expected_types = [
            ast.GqlProgram,
            ast.SessionSetCommand,
            ast.SessionResetCommand,
            ast.EndTransactionCommand,
            ast.SimpleLinearQueryStatement,
            ast.ValueExpressionPrimary,
        ]
        for expr_type in expected_types:
            self.assertIn(expr_type, Parser.PARSERS, f"{expr_type} not in PARSERS registry")
