"""Tests for identifier parsing functionality."""

import unittest

import pytest

from graphglot import ast
from graphglot.dialect.base import Dialect
from graphglot.error import ParseError
from graphglot.lexer.lexer import Lexer
from graphglot.lexer.token import TokenType

from .helpers import ParserTestHelper


class TestIdentifier(unittest.TestCase):
    """Test suite for identifier parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_simple_identifier(self):
        """Test that the parser can parse a simple identifier."""
        query = "n"
        expr = self.helper.parse_single(query, ast.Identifier)

        self.assertIsInstance(expr, ast.Identifier)
        self.assertEqual(expr.name, "n")

    def test_identifier_from_non_reserved_word(self):
        """Non-reserved words can be used as identifiers per GQL §21.3 SR18."""
        query = "edge"
        expr = self.helper.parse_single(query, ast.Identifier)

        self.assertIsInstance(expr, ast.Identifier)
        self.assertEqual(expr.name, "edge")

    def test_all_non_reserved_words_as_identifiers(self):
        """Every non-reserved word should parse as a valid identifier."""
        for token_type in Dialect.NON_RESERVED_WORDS:
            word = token_type.name.lower()
            with self.subTest(word=word):
                expr = self.helper.parse_single(word, ast.Identifier)
                self.assertIsInstance(expr, ast.Identifier)

    def test_non_reserved_word_in_match_pattern(self):
        """Non-reserved word as node variable in a full query."""
        query = "MATCH (edge) RETURN edge"
        result = Dialect().parse(query)
        self.assertTrue(len(result) > 0)

    def test_reserved_word_as_identifier_fails(self):
        """Reserved words should NOT parse as identifiers."""
        with self.assertRaises(ParseError):
            self.helper.parse_single("MATCH", ast.Identifier)

    def test_backtick_quoted_reserved_word_tokenizes_as_var(self):
        """Backtick-quoted reserved words should tokenize as VAR per §21.3."""
        tokens = [t for t in Lexer().tokenize("`MATCH`") if t.token_type != TokenType.EOF]
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].token_type, TokenType.VAR)
        self.assertEqual(tokens[0].text, "MATCH")

    def test_backtick_quoted_reserved_word_in_query(self):
        """Backtick-quoted reserved words should parse as identifiers in full queries."""
        result = Dialect().parse("MATCH (`MATCH`) RETURN `MATCH`")
        self.assertTrue(len(result) > 0)

    @pytest.mark.xfail(reason="TABLE excluded from NON_RESERVED_WORDS due to parse ambiguity")
    def test_table_as_identifier_in_match(self):
        """TABLE is non-reserved per §21.3 but ambiguous with TABLE { ... } syntax."""
        result = Dialect().parse("MATCH (table) RETURN table")
        self.assertTrue(len(result) > 0)

    @pytest.mark.xfail(reason="TYPE excluded from NON_RESERVED_WORDS due to parse ambiguity")
    def test_type_as_identifier_in_match(self):
        """TYPE is non-reserved per §21.3 but ambiguous with GRAPH/NODE/EDGE TYPE DDL."""
        result = Dialect().parse("MATCH (type) RETURN type")
        self.assertTrue(len(result) > 0)
