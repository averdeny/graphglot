"""Property-based fuzz tests for lexer and parser.

Uses hypothesis to generate random/semi-random inputs and verify
no unhandled exceptions or hangs occur.

Strategies are derived from the Lexer's actual KEYWORDS and SINGLE_TOKENS
so they stay in sync as the lexer evolves.
"""

import pytest

from hypothesis import HealthCheck, given, settings, strategies as st

from graphglot.error import GraphGlotError
from graphglot.lexer.lexer import Lexer
from graphglot.parser import Parser

pytestmark = pytest.mark.fuzz

# ---------------------------------------------------------------------------
# Strategies — derived from the real lexer constants
# ---------------------------------------------------------------------------

# All keywords recognised by the lexer (includes multi-word like "ORDER BY")
_GQL_KEYWORDS = sorted(k for k in Lexer.KEYWORDS if k[0].isalpha())

# Multi-char operators from KEYWORDS (e.g. "->", "<>", "||")
_GQL_MULTI_OPERATORS = sorted(k for k in Lexer.KEYWORDS if not k[0].isalpha())

# Single-char tokens from SINGLE_TOKENS (e.g. "(", ")", ";")
_GQL_SINGLE_OPERATORS = sorted(Lexer.SINGLE_TOKENS.keys())

# Sample literals and identifiers to make fragments more realistic
_LITERALS = ["42", "3.14", "0", "-1", "'hello'", "'it''s'", "TRUE", "FALSE", "NULL"]
_IDENTIFIERS = ["n", "m", "r", "x", "y", "label", "prop", "age", "name"]

_ALL_FRAGMENTS = (
    _GQL_KEYWORDS + _GQL_MULTI_OPERATORS + _GQL_SINGLE_OPERATORS + _LITERALS + _IDENTIFIERS
)

gql_fragments = st.lists(
    st.sampled_from(_ALL_FRAGMENTS),
    min_size=1,
    max_size=20,
).map(" ".join)


# ---------------------------------------------------------------------------
# Allowed exceptions — the goal is to catch *unhandled* crashes, not parse errors
# ---------------------------------------------------------------------------

_ALLOWED_EXCEPTIONS = (GraphGlotError, RecursionError, OverflowError)

_lexer = Lexer()
_parser = Parser()


def _lex(query: str) -> list:
    """Tokenize a query, allowing expected errors."""
    return _lexer.tokenize(query)


def _lex_and_parse(query: str) -> None:
    """Lex and parse a query, allowing expected errors."""
    tokens = _lexer.tokenize(query)
    _parser.parse(tokens, query)


# ---------------------------------------------------------------------------
# Lexer fuzz tests
# ---------------------------------------------------------------------------


class TestLexerFuzz:
    """Fuzz the lexer with random inputs."""

    @given(text=st.text(min_size=0, max_size=500))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_unicode(self, text: str) -> None:
        """Lexer should not crash on arbitrary unicode input."""
        try:
            _lex(text)
        except _ALLOWED_EXCEPTIONS:
            pass

    @given(
        text=st.text(st.characters(categories=("L", "N", "P", "S", "Z")), min_size=0, max_size=300)
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_ascii_text(self, text: str) -> None:
        """Lexer should not crash on ASCII-ish text."""
        try:
            _lex(text)
        except _ALLOWED_EXCEPTIONS:
            pass

    @given(text=gql_fragments)
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_gql_fragments(self, text: str) -> None:
        """Lexer should not crash on random GQL-like fragments."""
        try:
            _lex(text)
        except _ALLOWED_EXCEPTIONS:
            pass


# ---------------------------------------------------------------------------
# Parser fuzz tests
# ---------------------------------------------------------------------------


class TestParserFuzz:
    """Fuzz the parser with random inputs."""

    @given(text=st.text(min_size=1, max_size=200))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_unicode(self, text: str) -> None:
        """Parser should not crash on arbitrary unicode input."""
        try:
            _lex_and_parse(text)
        except _ALLOWED_EXCEPTIONS:
            pass

    @given(text=gql_fragments)
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_gql_fragments(self, text: str) -> None:
        """Parser should not crash on random GQL-like fragments."""
        try:
            _lex_and_parse(text)
        except _ALLOWED_EXCEPTIONS:
            pass

    @given(depth=st.integers(min_value=10, max_value=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_deeply_nested_parens(self, depth: int) -> None:
        """Parser should handle deeply nested parentheses without crashing."""
        text = "RETURN " + "(" * depth + "1" + ")" * depth
        try:
            _lex_and_parse(text)
        except _ALLOWED_EXCEPTIONS:
            pass

    @given(length=st.integers(min_value=100, max_value=5000))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_long_identifiers(self, length: int) -> None:
        """Parser should handle very long identifiers without crashing."""
        ident = "a" * length
        try:
            _lex_and_parse(f"MATCH ({ident}) RETURN {ident}")
        except _ALLOWED_EXCEPTIONS:
            pass
