"""Shared function-call parsing helpers.

Used by both the base CVE parser and Cypher dialect extensions.
"""

from __future__ import annotations

import typing as t

from graphglot import ast, features as F
from graphglot.ast import functions as f
from graphglot.lexer import TokenType

if t.TYPE_CHECKING:
    from graphglot.parser.base import Parser


def parse_func_args(parser: Parser, cls: type[f.Func]) -> f.Func:
    """Parse generic function arguments ``(arg, ...)`` after name has been consumed."""
    parser._expect(TokenType.LEFT_PAREN)
    args: list[ast.ValueExpression] = []
    if not parser._match(TokenType.RIGHT_PAREN):
        args.append(parser.get_parser(ast.ValueExpression)(parser))
        while parser._match(TokenType.COMMA):
            parser._expect(TokenType.COMMA)
            args.append(parser.get_parser(ast.ValueExpression)(parser))
    parser._expect(TokenType.RIGHT_PAREN)
    return cls(arguments=args)


def parse_anonymous_func_args(parser: Parser, name: str) -> f.Anonymous:
    """Parse anonymous function arguments ``(arg, ...)`` after name has been consumed."""
    parser._expect(TokenType.LEFT_PAREN)
    args: list[ast.ValueExpression] = []
    if not parser._match(TokenType.RIGHT_PAREN):
        args.append(parser.get_parser(ast.ValueExpression)(parser))
        while parser._match(TokenType.COMMA):
            parser._expect(TokenType.COMMA)
            args.append(parser.get_parser(ast.ValueExpression)(parser))
    parser._expect(TokenType.RIGHT_PAREN)
    return f.Anonymous(name=name, arguments=args)


def parse_function_call(parser: Parser) -> ast.CommonValueExpression:
    """Parse ``name(args)`` after VAR matched: FUNCTIONS → FUNC_REGISTRY → Anonymous.

    Anonymous results are gated behind ``GG:FN01``.
    """
    name_upper = parser._curr.text.upper()
    func_cls = parser.FUNCTIONS.get(name_upper)
    if func_cls is not None:
        parser._advance()  # consume VAR
        return parse_func_args(parser, func_cls)
    if name_upper in f.FUNC_REGISTRY:
        parser._advance()  # consume VAR
        return parse_func_args(parser, f.FUNC_REGISTRY[name_upper])
    # Unknown function: parse as Anonymous, gate behind GG:FN01
    name = parser._curr.text
    parser._advance()  # consume VAR
    result = parse_anonymous_func_args(parser, name)
    result.require_feature(F.GG_FN01)
    return result


def parse_dotted_function(parser: Parser) -> f.Func:
    """Parse ``ns.func(args)`` or ``ns.sub.func(args)`` after first VAR matched.

    Anonymous results are gated behind ``GG:FN01``.
    """
    parts = [parser._curr.text]
    parser._advance()  # consume first VAR
    while parser._match(TokenType.PERIOD):
        parser._expect(TokenType.PERIOD)
        parts.append(parser._curr.text)
        parser._advance()  # consume next name
    dotted = ".".join(parts)
    func_cls = parser.FUNCTIONS.get(dotted.upper())
    if func_cls is not None:
        return parse_func_args(parser, func_cls)
    result = parse_anonymous_func_args(parser, dotted)
    result.require_feature(F.GG_FN01)
    return result
