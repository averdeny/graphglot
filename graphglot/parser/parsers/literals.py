from __future__ import annotations

import typing as t

from decimal import Decimal

from graphglot import ast
from graphglot.error import ParseError, ValidationError
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses, token_parser

_INT64_MAX = 9223372036854775807  # 2^63 - 1

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.BooleanLiteral)
def parse_boolean_literal(parser: Parser) -> ast.BooleanLiteral:
    candidates_boolean_literal = (
        lambda parser: parser.seq(TokenType.TRUE),
        lambda parser: parser.seq(TokenType.FALSE),
        lambda parser: parser.seq(TokenType.UNKNOWN),
    )
    (token,) = parser.seq(candidates_boolean_literal)

    if token[0].token_type == TokenType.TRUE:
        value = True
    elif token[0].token_type == TokenType.FALSE:
        value = False
    elif token[0].token_type == TokenType.UNKNOWN:
        value = None

    return ast.BooleanLiteral(value=value)


@parses(ast.CharacterStringLiteral)
def parse_character_string_literal(parser: Parser) -> ast.CharacterStringLiteral:
    (value,) = parser.seq(TokenType.STRING)
    return ast.CharacterStringLiteral(
        value=value.text,
    )


@parses(ast.ByteStringLiteral)
def parse_byte_string_literal(parser: Parser) -> ast.ByteStringLiteral:
    (value,) = parser.seq(TokenType.BYTE_STRING)
    return ast.ByteStringLiteral(
        value=value.text,
    )


@parses(ast.UnsignedNumericLiteral)
def parse_unsigned_numeric_literal(parser: Parser) -> ast.UnsignedNumericLiteral:
    (number,) = parser.seq(TokenType.NUMBER)

    # Strip numeric suffix (M for exact, f/d for approximate) before conversion.
    # Skip stripping for hex literals (0x...) where f/d are valid hex digits.
    number_text = number.text
    is_hex = number_text.startswith(("0x", "0X"))
    is_numeric = number_text and (number_text[0].isdigit() or number_text[0] == ".")
    if not is_hex and is_numeric and number_text[-1].lower() in ("m", "f", "d"):
        number_text = number_text[:-1]
    value: Decimal | int
    if is_numeric and ("." in number_text or (not is_hex and "e" in number_text.lower())):
        value = Decimal(number_text)
        # Check IEEE 754 double precision overflow
        if value.is_finite():
            try:
                f = float(value)
                if f == float("inf") or f == float("-inf"):
                    raise ValidationError(
                        f"Floating point literal {number_text} exceeds maximum value"
                    )
            except (OverflowError, ValueError) as err:
                raise ValidationError(
                    f"Floating point literal {number_text} exceeds maximum value"
                ) from err
    elif is_numeric:
        value = int(number_text, 0)
        # Allow up to 2^63 so that -2^63 (INT64_MIN) can be parsed.
        # The ArithmeticFactor check rejects positive 2^63.
        if value > _INT64_MAX + 1:
            raise ValidationError(
                f"Integer literal {number_text} exceeds maximum value {_INT64_MAX}"
            )
    else:
        raise ParseError(f"Expected numeric literal, got {number_text!r}")

    return ast.UnsignedNumericLiteral(
        value=value,
    )


@parses(ast.TemporalLiteral)
def parse_temporal_literal(parser: Parser) -> ast.TemporalLiteral:
    candidates_temporal_literal = (
        parser.get_parser(ast.DateLiteral),
        parser.get_parser(ast.TimeLiteral),
        parser.get_parser(ast.DatetimeLiteral),
        parser.get_parser(ast.SqlDatetimeLiteral),
    )
    (result,) = parser.seq(candidates_temporal_literal)
    return result


@parses(ast.DurationLiteral)
def parse_duration_literal(parser: Parser) -> ast.DurationLiteral:
    def _parse__duration_duration_string(
        parser: Parser,
    ) -> ast.DurationLiteral._DurationDurationString:
        (
            _,
            duration_string,
        ) = parser.seq(
            TokenType.DURATION,
            parser.get_parser(ast.DurationString),
        )
        return ast.DurationLiteral._DurationDurationString(
            duration_string=duration_string,
        )

    candidates_duration_literal = (
        _parse__duration_duration_string,
        parser.get_parser(ast.SqlIntervalLiteral),
    )
    (duration_literal,) = parser.seq(candidates_duration_literal)
    return ast.DurationLiteral(
        duration_literal=duration_literal,
    )


@parses(ast.SqlIntervalLiteral)
def parse_sql_interval_literal(parser: Parser) -> ast.SqlIntervalLiteral:
    datetime_field_tokens = {
        TokenType.YEAR,
        TokenType.MONTH,
        TokenType.DAY,
        TokenType.HOUR,
        TokenType.MINUTE,
        TokenType.SECOND,
    }

    token_to_field = {
        TokenType.YEAR: ast.SqlIntervalLiteral.DatetimeField.YEAR,
        TokenType.MONTH: ast.SqlIntervalLiteral.DatetimeField.MONTH,
        TokenType.DAY: ast.SqlIntervalLiteral.DatetimeField.DAY,
        TokenType.HOUR: ast.SqlIntervalLiteral.DatetimeField.HOUR,
        TokenType.MINUTE: ast.SqlIntervalLiteral.DatetimeField.MINUTE,
        TokenType.SECOND: ast.SqlIntervalLiteral.DatetimeField.SECOND,
    }

    def _parse_to_field(parser: Parser) -> ast.SqlIntervalLiteral.DatetimeField:
        (_, end_token) = parser.seq(TokenType.TO, datetime_field_tokens)
        return token_to_field[end_token.token_type]

    (
        _,
        sign,
        interval_string,
        start_token,
        end_field,
    ) = parser.seq(
        TokenType.INTERVAL,
        parser.opt(parser.get_parser(ast.Sign)),
        parser.get_parser(ast.CharacterStringLiteral),
        datetime_field_tokens,
        parser.opt(_parse_to_field),
    )

    return ast.SqlIntervalLiteral(
        sign=sign,
        interval_string=interval_string,
        start_field=token_to_field[start_token.token_type],
        end_field=end_field,
    )


@parses(ast.Literal)
def parse_literal(parser: Parser) -> ast.Literal:
    candidates_literal = (
        parser.get_parser(ast.SignedNumericLiteral),
        parser.get_parser(ast.GeneralLiteral),
    )
    (result,) = parser.seq(candidates_literal)
    return result


parse_null_literal = parses(ast.NullLiteral)(token_parser(TokenType.NULL, ast_type=ast.NullLiteral))


@parses(ast.DateLiteral)
def parse_date_literal(parser: Parser) -> ast.DateLiteral:
    (
        _,
        date_string,
    ) = parser.seq(
        TokenType.DATE,
        parser.get_parser(ast.DateString),
    )
    return ast.DateLiteral(
        date_string=date_string,
    )


@parses(ast.TimeLiteral)
def parse_time_literal(parser: Parser) -> ast.TimeLiteral:
    (
        _,
        time_string,
    ) = parser.seq(
        TokenType.TIME,
        parser.get_parser(ast.TimeString),
    )
    return ast.TimeLiteral(
        time_string=time_string,
    )


@parses(ast.DatetimeLiteral)
def parse_datetime_literal(parser: Parser) -> ast.DatetimeLiteral:
    (
        kind_token,
        datetime_string,
    ) = parser.seq(
        {TokenType.DATETIME, TokenType.TIMESTAMP},
        parser.get_parser(ast.DatetimeString),
    )

    match kind_token.token_type:
        case TokenType.DATETIME:
            kind = ast.DatetimeLiteral.Kind.DATETIME
        case TokenType.TIMESTAMP:
            kind = ast.DatetimeLiteral.Kind.TIMESTAMP

    return ast.DatetimeLiteral(
        kind=kind,
        datetime_string=datetime_string,
    )


@parses(ast.SqlDatetimeLiteral)
def parse_sql_datetime_literal(parser: Parser) -> ast.SqlDatetimeLiteral:
    """
    Note: In practice this is unreachable because DateLiteral, TimeLiteral,
    and DatetimeLiteral are tried first in parse_temporal_literal.
    """
    (
        kind_token,
        datetime_string,
    ) = parser.seq(
        {TokenType.DATE, TokenType.TIME, TokenType.TIMESTAMP},
        parser.get_parser(ast.CharacterStringLiteral),
    )

    match kind_token.token_type:
        case TokenType.DATE:
            kind = ast.SqlDatetimeLiteral.Kind.DATE
        case TokenType.TIME:
            kind = ast.SqlDatetimeLiteral.Kind.TIME
        case TokenType.TIMESTAMP:
            kind = ast.SqlDatetimeLiteral.Kind.TIMESTAMP

    return ast.SqlDatetimeLiteral(
        kind=kind,
        datetime_string=datetime_string,
    )


@parses(ast.SignedNumericLiteral)
def parse_signed_numeric_literal(parser: Parser) -> ast.SignedNumericLiteral:
    (
        sign,
        unsigned_numeric_literal,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Sign)),
        parser.get_parser(ast.UnsignedNumericLiteral),
    )
    return ast.SignedNumericLiteral(
        sign=sign or ast.Sign.PLUS_SIGN,
        unsigned_numeric_literal=unsigned_numeric_literal,
    )


@parses(ast.GeneralLiteral)
def parse_general_literal(parser: Parser) -> ast.GeneralLiteral:
    candidates_general_literal = (
        parser.get_parser(ast.BooleanLiteral),
        parser.get_parser(ast.CharacterStringLiteral),
        parser.get_parser(ast.ByteStringLiteral),
        parser.get_parser(ast.TemporalLiteral),
        parser.get_parser(ast.DurationLiteral),
        parser.get_parser(ast.NullLiteral),
        parser.get_parser(ast.ListValueConstructorByEnumeration),
        parser.get_parser(ast.RecordConstructor),
    )
    (result,) = parser.seq(candidates_general_literal)
    return result


@parses(ast.UnsignedLiteral)
def parse_unsigned_literal(parser: Parser) -> ast.UnsignedLiteral:
    candidates_unsigned_literal = (
        parser.get_parser(ast.UnsignedNumericLiteral),
        parser.get_parser(ast.GeneralLiteral),
    )
    (result,) = parser.seq(candidates_unsigned_literal)
    return result
