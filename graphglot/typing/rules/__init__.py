"""Type rule registry for type inference."""

from __future__ import annotations

import typing as t

from graphglot.ast.base import Expression
from graphglot.typing.annotator import TypeAnnotator
from graphglot.typing.types import GqlType

TypeRuleFn = t.Callable[[TypeAnnotator, Expression], GqlType]

TYPE_RULE_REGISTRY: dict[type, TypeRuleFn] = {}


def type_rule(*expr_types: type) -> t.Callable[[TypeRuleFn], TypeRuleFn]:
    """Register a function as the type rule for one or more AST node types."""

    def decorator(fn: TypeRuleFn) -> TypeRuleFn:
        for expr_type in expr_types:
            TYPE_RULE_REGISTRY[expr_type] = fn
        return fn

    return decorator


def _ensure_rules_loaded() -> None:
    """Import all rule submodules so their ``@type_rule`` decorators run."""
    from graphglot.typing.rules import (  # noqa: F401
        cast,
        functions,
        literals,
        operators,
        resolution,
        statements,
        variables,
    )


_ensure_rules_loaded()
