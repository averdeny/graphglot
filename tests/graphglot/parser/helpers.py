"""Helper utilities for parser tests."""

from graphglot import ast
from graphglot.lexer import Lexer
from graphglot.parser import Parser


class ParserTestHelper:
    """Helper class for parser tests with common utilities."""

    def __init__(self):
        """Initialize parser test helper."""
        self.lexer = Lexer()
        self.parser = Parser()

    def parse(self, query: str, expr_type: type[ast.Expression] | None = None):
        """
        Parse a query into AST expressions.

        Args:
            query: The query string to parse
            expr_type: Optional AST expression type to parse directly.
                      If None, uses full GQL program parsing.

        Returns:
            List of parsed AST expressions
        """
        tokens = self.lexer.tokenize(query)
        if expr_type is None:
            return self.parser.parse(raw_tokens=tokens, query=query)
        else:
            return self.parser._parse(
                raw_tokens=tokens,
                query=query,
                parse_method=self.parser.PARSERS[expr_type],
            )

    def parse_single(self, query: str, expr_type: type[ast.Expression]):
        """
        Parse a query and return the first expression.

        Args:
            query: The query string to parse
            expr_type: AST expression type to parse

        Returns:
            The first parsed AST expression
        """
        results = self.parse(query, expr_type)
        return results[0] if results else None
