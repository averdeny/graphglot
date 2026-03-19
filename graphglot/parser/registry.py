"""Decorator-based parser registry for AST expression types."""

from __future__ import annotations

import functools
import re
import typing as t

from enum import Enum
from types import UnionType

from graphglot.ast.base import Expression

ParserKey: t.TypeAlias = type[Expression] | type[Enum] | UnionType
ParserFunc: t.TypeAlias = t.Callable[..., t.Any]

_REGISTRY: dict[ParserKey, ParserFunc] = {}


def _humanize(name: str) -> str:
    """Convert CamelCase AST type name to readable form.

    'MatchStatement' → 'match statement', 'BooleanLiteral' → 'boolean literal'
    """
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", name).lower()


def parses(*expr_types: ParserKey) -> t.Callable[[ParserFunc], ParserFunc]:
    """Register a parser function for one or more AST expression types.

    Each registered function is wrapped to automatically capture source span
    information (start/end tokens) on the returned Expression.

    Usage::

        @parses(ast.BooleanLiteral)
        def parse_boolean_literal(parser):
            ...

        @parses(ast.TypeA, ast.TypeB)
        def parse_shared(parser):
            ...

    Raises:
        ValueError: If a duplicate registration is detected at import time.
    """

    def decorator(func: ParserFunc) -> ParserFunc:
        @functools.wraps(func)
        def wrapper(parser):
            start_token = parser._curr
            result = func(parser)
            if isinstance(result, Expression) and start_token is not None:
                result._start_token = start_token
                result._end_token = parser._prev or start_token
            return result

        for expr_type in expr_types:
            if expr_type in _REGISTRY:
                name = getattr(expr_type, "__name__", str(expr_type))
                raise ValueError(
                    f"Duplicate parser for {name}: "
                    f"{_REGISTRY[expr_type].__name__} and {func.__name__}"
                )
            _REGISTRY[expr_type] = wrapper
        # Attach human-readable description from first AST type
        name = getattr(expr_types[0], "__name__", str(expr_types[0]))
        wrapper_with_description = t.cast(t.Any, wrapper)
        wrapper_with_description.__description__ = _humanize(name)
        return wrapper

    return decorator


def token_parser(*tokens, ast_type):
    """Create a parser that matches token(s) and returns a no-arg AST instance."""

    def _parser(parser):
        parser.seq(*tokens)
        return ast_type()

    _parser.__name__ = f"_parse__{ast_type.__name__}"
    _parser.__qualname__ = f"token_parser.<locals>._parse__{ast_type.__name__}"
    return _parser


_modules_loaded = False


def get_registry() -> dict[ParserKey, ParserFunc]:
    """Return a copy of the current parser registry.

    On first call, imports all parser modules to trigger @parses registration.
    """
    global _modules_loaded
    if not _modules_loaded:
        import graphglot.parser.parsers  # noqa: F401

        _modules_loaded = True
    return dict(_REGISTRY)
