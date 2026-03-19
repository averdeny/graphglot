"""Generator functions for literal expressions."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.BooleanLiteral)
def generate_boolean_literal(gen: Generator, expr: ast.BooleanLiteral) -> Fragment:
    if expr.value is True:
        return Fragment("TRUE")
    elif expr.value is False:
        return Fragment("FALSE")
    else:
        return Fragment("UNKNOWN")


@generates(ast.CharacterStringLiteral)
def generate_character_string_literal(gen: Generator, expr: ast.CharacterStringLiteral) -> Fragment:
    value = expr.value or ""
    # Escape single quotes by doubling them
    escaped = value.replace("'", "''")
    return Fragment(f"'{escaped}'")


@generates(ast.ByteStringLiteral)
def generate_byte_string_literal(gen: Generator, expr: ast.ByteStringLiteral) -> Fragment:
    hex_value = expr.value or ""
    return Fragment(f"X'{hex_value}'")


@generates(ast.UnsignedNumericLiteral)
def generate_unsigned_numeric_literal(gen: Generator, expr: ast.UnsignedNumericLiteral) -> Fragment:
    return Fragment(str(expr.value))


@generates(ast.SignedNumericLiteral)
def generate_signed_numeric_literal(gen: Generator, expr: ast.SignedNumericLiteral) -> Fragment:
    sign = "-" if expr.sign == ast.Sign.MINUS_SIGN else ""
    unsigned = gen.dispatch(expr.unsigned_numeric_literal)
    return Fragment(f"{sign}{unsigned}")


@generates(ast.NullLiteral)
def generate_null_literal(gen: Generator, expr: ast.NullLiteral) -> Fragment:
    return Fragment("NULL")


@generates(ast.DateLiteral)
def generate_date_literal(gen: Generator, expr: ast.DateLiteral) -> Fragment:
    date_str = gen.dispatch(expr.date_string)
    return gen.seq("DATE", date_str)


@generates(ast.TimeLiteral)
def generate_time_literal(gen: Generator, expr: ast.TimeLiteral) -> Fragment:
    time_str = gen.dispatch(expr.time_string)
    return gen.seq("TIME", time_str)


@generates(ast.DatetimeLiteral)
def generate_datetime_literal(gen: Generator, expr: ast.DatetimeLiteral) -> Fragment:
    keyword = "DATETIME" if expr.kind == ast.DatetimeLiteral.Kind.DATETIME else "TIMESTAMP"
    datetime_str = gen.dispatch(expr.datetime_string)
    return gen.seq(keyword, datetime_str)


@generates(ast.DurationLiteral)
def generate_duration_literal(gen: Generator, expr: ast.DurationLiteral) -> Fragment:
    inner = expr.duration_literal
    if isinstance(inner, ast.DurationLiteral._DurationDurationString):
        duration_str = gen.dispatch(inner.duration_string)
        return gen.seq("DURATION", duration_str)
    else:
        # SqlIntervalLiteral
        return gen.dispatch(inner)


@generates(ast.SqlIntervalLiteral)
def generate_sql_interval_literal(gen: Generator, expr: ast.SqlIntervalLiteral) -> Fragment:
    parts: list[str | Fragment] = ["INTERVAL"]
    if expr.sign is not None and expr.sign == ast.Sign.MINUS_SIGN:
        parts.append("-")
    parts.append(gen.dispatch(expr.interval_string))
    parts.append(expr.start_field.name)
    if expr.end_field is not None:
        parts.append("TO")
        parts.append(expr.end_field.name)
    return gen.seq(*parts)


@generates(ast.UnsignedInteger)
def generate_unsigned_integer(gen: Generator, expr: ast.UnsignedInteger) -> Fragment:
    return Fragment(str(expr.value))
