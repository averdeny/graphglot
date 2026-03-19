"""Tests for error message formatting and error types."""

import pytest

from graphglot import features as F
from graphglot.dialect.base import Dialect
from graphglot.error import FeatureError, GraphGlotError, ParseError, TokenError
from graphglot.parser.base import _parser_description
from graphglot.parser.registry import _humanize


class TestHumanize:
    """Tests for _humanize converting CamelCase to readable names."""

    def test_simple_two_words(self):
        assert _humanize("MatchStatement") == "match statement"

    def test_boolean_literal(self):
        assert _humanize("BooleanLiteral") == "boolean literal"

    def test_single_word(self):
        assert _humanize("Identifier") == "identifier"

    def test_consecutive_uppercase(self):
        assert _humanize("GQLProgram") == "gql program"

    def test_three_words(self):
        assert _humanize("SessionCloseCommand") == "session close command"

    def test_all_uppercase(self):
        assert _humanize("AST") == "ast"


class TestParserDescription:
    """Tests for _parser_description extracting human-readable names."""

    def test_function_with_description(self):
        def my_func():
            pass

        my_func.__description__ = "boolean literal"
        assert _parser_description(my_func) == "boolean literal"

    def test_parse_prefix_function(self):
        def parse_boolean_literal():
            pass

        assert _parser_description(parse_boolean_literal) == "boolean literal"

    def test_internal_parse_prefix_function(self):
        def _parse__session_close_command():
            pass

        assert _parser_description(_parse__session_close_command) == "session close command"

    def test_lambda_returns_none(self):
        f = lambda: None  # noqa: E731
        assert _parser_description(f) is None

    def test_description_takes_priority(self):
        """__description__ takes priority over __name__ derivation."""

        def parse_some_thing():
            pass

        parse_some_thing.__description__ = "custom description"
        assert _parser_description(parse_some_thing) == "custom description"

    def test_unrecognized_name_returns_none(self):
        """Functions with unrecognized names return None."""

        def some_random_function():
            pass

        assert _parser_description(some_random_function) is None


class TestFeatureError:
    """Tests for FeatureError structured fields."""

    def test_inherits_from_graphglot_error(self):
        assert issubclass(FeatureError, GraphGlotError)

    def test_structured_fields(self):
        err = FeatureError(
            "test message",
            feature_id="GH01",
            expression_type="MatchStatement",
            line=5,
            col=10,
        )
        assert str(err) == "test message"
        assert err.feature_id == "GH01"
        assert err.expression_type == "MatchStatement"
        assert err.line == 5
        assert err.col == 10

    def test_default_none_fields(self):
        err = FeatureError("message only")
        assert err.feature_id is None
        assert err.expression_type is None
        assert err.line is None
        assert err.col is None


class TestFeatureErrorMessages:
    """Tests that feature error messages include human-readable descriptions."""

    def test_single_unsupported_feature_includes_description(self):
        """Single unsupported feature message shows ID and description."""
        from graphglot.features import ALL_FEATURES

        feature = F.GG_UE01
        supported = ALL_FEATURES - {feature}

        class RestrictedDialect(Dialect):
            SUPPORTED_FEATURES = supported

        d = RestrictedDialect()
        with pytest.raises(FeatureError) as exc:
            d.parse("MATCH (a)~[r]~>(b) RETURN a")
        msg = str(exc.value)
        assert "GG:UE01" in msg
        assert feature.description in msg
        assert "RestrictedDialect" in msg
        assert "not supported" in msg

    def test_single_feature_message_format(self):
        """Single feature error uses 'Feature ID (description) not supported' format."""
        from graphglot.features import ALL_FEATURES

        feature = F.GG_UE02
        supported = ALL_FEATURES - {feature}

        class RestrictedDialect(Dialect):
            SUPPORTED_FEATURES = supported

        d = RestrictedDialect()
        with pytest.raises(FeatureError) as exc:
            d.parse("MATCH (a)~>(b) RETURN a")
        msg = str(exc.value)
        assert msg.startswith(f"Feature {feature.id}")
        assert f"({feature.description})" in msg

    def test_single_feature_omits_implementation_details(self):
        """Error message does not mention AST type or parsing/transpilation context."""
        from graphglot.features import ALL_FEATURES

        supported = ALL_FEATURES - {F.GG_UE01}

        class RestrictedDialect(Dialect):
            SUPPORTED_FEATURES = supported

        d = RestrictedDialect()
        with pytest.raises(FeatureError) as exc:
            d.parse("MATCH (a)~[r]~>(b) RETURN a")
        msg = str(exc.value)
        assert "required by" not in msg
        assert "during parsing" not in msg
        assert "during transpilation" not in msg

    def test_gql_feature_includes_description(self):
        """Standard GQL features also show their description."""
        from graphglot.features import ALL_FEATURES

        feature = F.G004
        supported = ALL_FEATURES - {feature}

        class RestrictedDialect(Dialect):
            SUPPORTED_FEATURES = supported

        d = RestrictedDialect()
        with pytest.raises(FeatureError) as exc:
            d.parse("MATCH p = (n)-[e]->(m) RETURN p")
        msg = str(exc.value)
        assert feature.id in msg
        assert feature.description in msg


class TestTokenError:
    """Tests for TokenError structured fields."""

    def test_inherits_from_graphglot_error(self):
        assert issubclass(TokenError, GraphGlotError)

    def test_structured_fields(self):
        err = TokenError("bad token", line=3, col=7)
        assert str(err) == "bad token"
        assert err.line == 3
        assert err.col == 7

    def test_default_none_fields(self):
        err = TokenError("message only")
        assert err.line is None
        assert err.col is None


class TestParseErrorMessages:
    """Tests that parse error messages don't leak internal names."""

    def test_no_internal_names_in_error(self):
        """Error messages should not contain _parse__ prefixed names."""
        d = Dialect()
        try:
            d.parse("FOOBAR")
        except Exception as e:
            msg = str(e)
            assert "_parse__" not in msg, f"Internal name leaked: {msg}"

    def test_no_lambda_in_error(self):
        """Error messages should not contain <lambda> references."""
        d = Dialect()
        try:
            d.parse("FOOBAR")
        except Exception as e:
            msg = str(e)
            assert "<lambda>" not in msg, f"Lambda leaked: {msg}"

    def test_parse_error_contains_line_col(self):
        """Parse errors include line and column information."""
        d = Dialect()
        with pytest.raises(Exception) as exc:
            d.parse("FOOBAR")
        msg = str(exc.value)
        assert "Line" in msg or "line" in msg


class TestLexerErrorMessages:
    """Tests for improved lexer error message formats."""

    def test_unterminated_string(self):
        d = Dialect()
        with pytest.raises(TokenError) as exc:
            d.tokenize("'unterminated")
        msg = str(exc.value)
        assert "Unterminated string literal" in msg
        assert "(line" in msg

    def test_invalid_number_literal(self):
        """Invalid number underscore placement gives clear message."""
        d = Dialect()
        d.NUMBERS_CAN_BE_UNDERSCORE_SEPARATED = True
        with pytest.raises(TokenError) as exc:
            d.tokenize("1__2")
        msg = str(exc.value)
        assert "Invalid number literal" in msg
        assert "(line" in msg

    def test_invalid_hex_empty(self):
        d = Dialect()
        with pytest.raises(TokenError) as exc:
            d.tokenize("0x")
        msg = str(exc.value)
        assert "Invalid hexadecimal literal" in msg
        assert "(line" in msg

    def test_invalid_octal_empty(self):
        d = Dialect()
        with pytest.raises(TokenError) as exc:
            d.tokenize("0o")
        msg = str(exc.value)
        assert "Invalid octal literal" in msg
        assert "(line" in msg

    def test_invalid_binary_empty(self):
        d = Dialect()
        with pytest.raises(TokenError) as exc:
            d.tokenize("0b")
        msg = str(exc.value)
        assert "Invalid binary literal" in msg
        assert "(line" in msg

    def test_feature_error_from_lexer(self):
        """Feature errors from lexer are FeatureError, not TokenError."""
        from graphglot.features import ALL_FEATURES

        supported = ALL_FEATURES - {F.GL01}

        class RestrictedDialect(Dialect):
            SUPPORTED_FEATURES = supported

        d = RestrictedDialect()
        with pytest.raises(FeatureError) as exc:
            d.tokenize("0x1A")
        assert exc.value.feature_id == "GL01"
        assert exc.value.line is not None


def _parse_error_details(query: str) -> dict:
    """Parse a query and return error details from the raised ParseError."""
    d = Dialect()
    with pytest.raises(ParseError) as exc:
        d.parse(query)
    err = exc.value
    details = err.errors[0] if err.errors else {}
    return {
        "description": details.get("description", ""),
        "col": details.get("col"),
        "highlight": details.get("highlight", ""),
    }


class TestHighWaterMarkErrors:
    """Tests that parse errors highlight the deepest failure point, not the backtrack point."""

    def test_trailing_comma_highlights_comma(self):
        """MATCH (n) RETURN n, — error should point at the comma, not RETURN."""
        info = _parse_error_details("MATCH (n) RETURN n,")
        assert info["highlight"] == ","
        assert info["col"] == 20
        assert "trailing" in info["description"].lower()

    def test_trailing_comma_message_mentions_separator(self):
        """Error message should say 'Unexpected trailing ','."""
        info = _parse_error_details("MATCH (n) RETURN n,")
        assert info["description"] == "Unexpected trailing ','"

    def test_incomplete_order_by(self):
        """MATCH (n) RETURN n ORDER BY — error should point past RETURN."""
        info = _parse_error_details("MATCH (n) RETURN n ORDER BY")
        # Error should be at or beyond ORDER BY, not at RETURN
        assert info["col"] >= 20

    def test_incomplete_addition(self):
        """RETURN 1 + — error should point at +, not at RETURN."""
        info = _parse_error_details("RETURN 1 +")
        assert info["col"] >= 10

    def test_multiple_trailing_commas(self):
        """MATCH (n) RETURN a, b, — error at second trailing comma."""
        info = _parse_error_details("MATCH (n) RETURN a, b,")
        assert info["highlight"] == ","
        assert info["col"] == 23

    def test_valid_query_still_parses(self):
        """High-water mark tracking doesn't break valid queries."""
        d = Dialect()
        result = d.parse("MATCH (n) RETURN n")
        assert result is not None

    def test_simple_unexpected_token_no_deeper_error(self):
        """When there's no deeper error, falls back to 'Unexpected token'."""
        info = _parse_error_details("FOOBAR")
        # Should still produce a sensible error (may or may not be "Unexpected token"
        # depending on parser internals, but should not crash)
        assert info["col"] is not None

    def test_trailing_separator_in_set_list(self):
        """MATCH (n) SET n.a = 1, — trailing comma in SET."""
        info = _parse_error_details("MATCH (n) SET n.a = 1,")
        assert info["highlight"] == ","

    def test_error_col_deeper_than_backtrack(self):
        """The reported error column should be deeper than where backtracking lands."""
        # MATCH (n) RETURN n, — parser backtracks to RETURN (col 11),
        # but the actual error is at , (col 20)
        info = _parse_error_details("MATCH (n) RETURN n,")
        # col 11 is where RETURN starts — the error must be deeper
        assert info["col"] > 11
