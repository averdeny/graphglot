"""Tests for lexer-level feature toggles for numeric literals."""

import pytest

from graphglot import features as F
from graphglot.dialect import Dialect
from graphglot.error import FeatureError, TokenError
from graphglot.features import ALL_FEATURES, Feature
from graphglot.lexer import Lexer

# Test cases for numeric literal feature toggles.
# Each entry contains: (feature_id, query, expected_token_text)
TEST_CASES = [
    # GL01: Hexadecimal literals
    pytest.param(
        F.GL01,
        "0x1A2B",
        "0x1A2B",
        id="GL01_hex_lowercase_prefix",
    ),
    pytest.param(
        F.GL01,
        "0X1a2b",
        "0X1a2b",
        id="GL01_hex_uppercase_prefix",
    ),
    pytest.param(
        F.GL01,
        "0xDEADBEEF",
        "0xDEADBEEF",
        id="GL01_hex_long",
    ),
    # GL02: Octal literals
    pytest.param(
        F.GL02,
        "0o755",
        "0o755",
        id="GL02_octal_lowercase_prefix",
    ),
    pytest.param(
        F.GL02,
        "0O777",
        "0O777",
        id="GL02_octal_uppercase_prefix",
    ),
    # GL03: Binary literals
    pytest.param(
        F.GL03,
        "0b1010",
        "0b1010",
        id="GL03_binary_lowercase_prefix",
    ),
    pytest.param(
        F.GL03,
        "0B1111",
        "0B1111",
        id="GL03_binary_uppercase_prefix",
    ),
    # GL04: Exact number in common notation without suffix
    pytest.param(
        F.GL04,
        "3.14",
        "3.14",
        id="GL04_decimal_without_suffix",
    ),
    pytest.param(
        F.GL04,
        "0.5",
        "0.5",
        id="GL04_decimal_leading_zero",
    ),
    pytest.param(
        F.GL04,
        "123.456789",
        "123.456789",
        id="GL04_decimal_long",
    ),
    pytest.param(
        F.GL04,
        "3.",
        "3.",
        id="GL04_decimal_trailing_dot",
    ),
    pytest.param(
        F.GL04,
        ".14",
        ".14",
        id="GL04_decimal_leading_dot",
    ),
    # GL05: Exact number with suffix
    pytest.param(
        F.GL05,
        "123m",
        "123m",
        id="GL05_integer_with_suffix",
    ),
    pytest.param(
        F.GL05,
        "123M",
        "123M",
        id="GL05_integer_with_uppercase_suffix",
    ),
    pytest.param(
        F.GL05,
        "3.14m",
        "3.14m",
        id="GL05_decimal_with_suffix",
    ),
    # GL06: Exact number in scientific notation with suffix
    pytest.param(
        F.GL06,
        "1.23e10m",
        "1.23e10m",
        id="GL06_scientific_with_suffix",
    ),
    pytest.param(
        F.GL06,
        "1.23E10m",
        "1.23E10m",
        id="GL06_scientific_uppercase_e_with_suffix",
    ),
    pytest.param(
        F.GL06,
        "5e-3m",
        "5e-3m",
        id="GL06_scientific_negative_exponent_with_suffix",
    ),
    # GL07: Approximate number in common notation or decimal integer with suffix
    pytest.param(
        F.GL07,
        "3.14f",
        "3.14f",
        id="GL07_decimal_with_float_suffix",
    ),
    pytest.param(
        F.GL07,
        "123f",
        "123f",
        id="GL07_integer_with_float_suffix",
    ),
    pytest.param(
        F.GL07,
        "3.14d",
        "3.14d",
        id="GL07_decimal_with_double_suffix",
    ),
    pytest.param(
        F.GL07,
        "123d",
        "123d",
        id="GL07_integer_with_double_suffix",
    ),
    # GL08: Approximate number in scientific notation with suffix
    pytest.param(
        F.GL08,
        "1.23e10f",
        "1.23e10f",
        id="GL08_scientific_with_float_suffix",
    ),
    pytest.param(
        F.GL08,
        "1.23e10d",
        "1.23e10d",
        id="GL08_scientific_with_double_suffix",
    ),
    pytest.param(
        F.GL08,
        "5E-3f",
        "5E-3f",
        id="GL08_scientific_negative_exponent_with_float_suffix",
    ),
    # GL09: Optional float number suffix
    pytest.param(
        F.GL09,
        "3.14f",
        "3.14f",
        id="GL09_float_suffix_lowercase",
    ),
    pytest.param(
        F.GL09,
        "3.14F",
        "3.14F",
        id="GL09_float_suffix_uppercase",
    ),
    pytest.param(
        F.GL09,
        "1e5f",
        "1e5f",
        id="GL09_scientific_float_suffix",
    ),
    # GL10: Optional double number suffix
    pytest.param(
        F.GL10,
        "3.14d",
        "3.14d",
        id="GL10_double_suffix_lowercase",
    ),
    pytest.param(
        F.GL10,
        "3.14D",
        "3.14D",
        id="GL10_double_suffix_uppercase",
    ),
    pytest.param(
        F.GL10,
        "1e5d",
        "1e5d",
        id="GL10_scientific_double_suffix",
    ),
    # GL11: Opt-out character escaping (no escape)
    pytest.param(
        F.GL11,
        "@'hello'",
        "hello",
        id="GL11_no_escape_single_quote",
    ),
    pytest.param(
        F.GL11,
        '@"hello"',
        "hello",
        id="GL11_no_escape_double_quote",
    ),
]


def build_dialect_without_feature(feature: Feature) -> Dialect:
    """Return a Dialect instance with a specific feature disabled."""
    supported = ALL_FEATURES - {feature}

    class RestrictedDialect(Dialect):
        SUPPORTED_FEATURES = supported

    return RestrictedDialect()


@pytest.fixture(scope="module")
def full_dialect() -> Dialect:
    """Shared full dialect instance."""
    return Dialect()


@pytest.mark.parametrize(("feature", "query", "expected_text"), TEST_CASES)
def test_supported_feature_tokenizes_successfully(
    full_dialect: Dialect, feature: Feature, query: str, expected_text: str
):
    """Verify that queries tokenize successfully when the feature is supported."""
    tokens = full_dialect.tokenize(query)
    assert len(tokens) == 1
    assert tokens[0].text == expected_text


@pytest.mark.parametrize(("feature", "query", "expected_text"), TEST_CASES)
def test_unsupported_feature_raises_error(feature: Feature, query: str, expected_text: str):
    """Verify that queries fail when the required feature is not supported."""
    dialect = build_dialect_without_feature(feature)

    with pytest.raises(FeatureError) as exc:
        dialect.tokenize(query)

    message = str(exc.value)
    assert str(feature) in message
    assert "not supported" in message


class TestFeatureTracking:
    """Tests for feature tracking via get_required_features()."""

    def test_require_feature_tracks_features(self):
        """Verify get_required_features() returns features used."""
        lexer = Lexer()
        lexer.tokenize("0x1A + 3.14")
        features = lexer.get_required_features()
        assert F.GL01 in features  # hex
        assert F.GL04 in features  # decimal without suffix

    def test_required_features_reset_on_new_tokenize(self):
        """Required features are reset when tokenizing a new query."""
        lexer = Lexer()
        lexer.tokenize("0x1A")
        assert F.GL01 in lexer.get_required_features()

        lexer.tokenize("42")
        assert F.GL01 not in lexer.get_required_features()


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_hex_empty_after_prefix(self):
        """0x alone without digits fails."""
        dialect = Dialect()
        with pytest.raises(TokenError) as exc:
            dialect.tokenize("0x")
        assert "Invalid hexadecimal literal" in str(exc.value)

    def test_octal_empty_after_prefix(self):
        """0o alone without digits fails."""
        dialect = Dialect()
        with pytest.raises(TokenError) as exc:
            dialect.tokenize("0o")
        assert "Invalid octal literal" in str(exc.value)

    def test_binary_empty_after_prefix(self):
        """0b alone without digits fails."""
        dialect = Dialect()
        with pytest.raises(TokenError) as exc:
            dialect.tokenize("0b")
        assert "Invalid binary literal" in str(exc.value)

    def test_octal_invalid_digit(self):
        """Octal literals with invalid digits (8, 9) fail."""
        dialect = Dialect()
        with pytest.raises(TokenError) as exc:
            dialect.tokenize("0o89")
        assert "Invalid octal literal" in str(exc.value)

    def test_binary_no_valid_digit_after_prefix(self):
        """Binary literals with no valid digit after prefix fail."""
        dialect = Dialect()
        with pytest.raises(TokenError) as exc:
            dialect.tokenize("0b2")
        assert "Invalid binary literal" in str(exc.value)

    def test_binary_partial_valid(self):
        """Binary literals stop scanning at non-binary digits.

        0b123 tokenizes as 0b1 followed by 23 (two separate tokens).
        This is not an error - just like how 0b1+2 would tokenize.
        """
        dialect = Dialect()
        tokens = dialect.tokenize("0b123")
        assert len(tokens) == 2
        assert tokens[0].text == "0b1"
        assert tokens[1].text == "23"

    def test_zero_alone_is_valid(self):
        """A single 0 is a valid integer."""
        dialect = Dialect()
        tokens = dialect.tokenize("0")
        assert tokens[0].text == "0"

    def test_integer_without_suffix_always_allowed(self):
        """Plain integers like 42 should always work regardless of feature flags."""
        dialect = build_dialect_without_feature(F.GL04)
        tokens = dialect.tokenize("42")
        assert tokens[0].text == "42"

    def test_scientific_without_suffix_always_allowed(self):
        """Scientific notation without suffix like 1.23e10 should always work."""
        dialect = build_dialect_without_feature(F.GL06)
        tokens = dialect.tokenize("1.23e10")
        assert tokens[0].text == "1.23e10"

    def test_no_escape_single_quote_doubling_not_collapsed(self):
        """@'it''s' tokenizes as STRING 'it' + STRING 's' (doubling NOT collapsed)."""
        dialect = Dialect()
        tokens = dialect.tokenize("@'it''s'")
        assert len(tokens) == 2
        assert tokens[0].text == "it"
        assert tokens[1].text == "s"

    def test_no_escape_double_quote_doubling_not_collapsed(self):
        """@"hello""there" tokenizes as STRING 'hello' + STRING 'there'."""
        dialect = Dialect()
        tokens = dialect.tokenize('@"hello""there"')
        assert len(tokens) == 2
        assert tokens[0].text == "hello"
        assert tokens[1].text == "there"

    def test_no_escape_vs_normal_escape(self):
        """Normal strings collapse delimiter doubling; @-prefixed strings don't."""
        dialect = Dialect()
        # Normal: '' is an escape for a literal single quote
        normal = dialect.tokenize("'it''s'")
        assert len(normal) == 1
        assert normal[0].text == "it's"

        # No-escape: '' terminates and starts a new string
        no_esc = dialect.tokenize("@'it''s'")
        assert len(no_esc) == 2
        assert no_esc[0].text == "it"
        assert no_esc[1].text == "s"

    def test_at_alone_is_commercial_at(self):
        """@ alone (not followed by quote) still tokenizes as COMMERCIAL_AT."""
        from graphglot.lexer.token import TokenType

        dialect = Dialect()
        tokens = dialect.tokenize("@ x")
        assert tokens[0].token_type == TokenType.COMMERCIAL_AT
