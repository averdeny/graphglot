"""Decorator-based generator registry for AST expression types."""

from __future__ import annotations

import typing as t

from enum import Enum
from types import UnionType

from graphglot.ast.base import Expression

GeneratorKey: t.TypeAlias = type[Expression] | type[Enum] | UnionType
GeneratorFunc: t.TypeAlias = t.Callable[..., t.Any]

_REGISTRY: dict[GeneratorKey, GeneratorFunc] = {}


def generates(*expr_types: GeneratorKey) -> t.Callable[[GeneratorFunc], GeneratorFunc]:
    """Register a generator function for one or more AST expression types.

    Usage::

        @generates(ast.BooleanLiteral)
        def generate_boolean_literal(gen, expr):
            ...

        @generates(ast.TypeA, ast.TypeB)
        def generate_shared(gen, expr):
            ...

    Raises:
        ValueError: If a duplicate registration is detected at import time.
    """

    def decorator(func: GeneratorFunc) -> GeneratorFunc:
        for expr_type in expr_types:
            if expr_type in _REGISTRY:
                name = getattr(expr_type, "__name__", str(expr_type))
                raise ValueError(
                    f"Duplicate generator for {name}: "
                    f"{_REGISTRY[expr_type].__name__} and {func.__name__}"
                )
            _REGISTRY[expr_type] = func
        return func

    return decorator


def get_registry() -> dict[GeneratorKey, GeneratorFunc]:
    """Return a copy of the current generator registry."""
    return dict(_REGISTRY)
