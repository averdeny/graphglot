"""Parser for macro AST nodes (@name and @name(args...))."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.ast.macros import MacroCall, MacroVar
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(MacroCall, MacroVar)
def parse_macro(parser: Parser) -> MacroCall | MacroVar:
    """Parse @name or @name(args...) into MacroCall/MacroVar."""
    parser._expect(TokenType.COMMERCIAL_AT)
    # Accept any word-like token (VAR or keyword used as identifier)
    if parser._curr and parser._curr.text.isidentifier():
        name_token = parser._curr
        parser._advance()
    else:
        name_token = parser._expect(TokenType.VAR)

    # @name(...) -> MacroCall
    if parser._match(TokenType.LEFT_PAREN):
        parser._advance()
        args: list[ast.Expression] = []
        if not parser._match(TokenType.RIGHT_PAREN):
            args.append(parser.get_parser(ast.ValueExpression)(parser))
            while parser._match(TokenType.COMMA):
                parser._advance()
                args.append(parser.get_parser(ast.ValueExpression)(parser))
        parser._expect(TokenType.RIGHT_PAREN)
        return MacroCall(name=name_token.text, arguments=args)

    # @name -> MacroVar
    return MacroVar(name=name_token.text)
