"""Type rules for resolving ambiguous value expressions (plausibility layer).

At parse time, some expressions are syntactically ambiguous:
- ``a || b`` could be string, list, or path concatenation
- ``a + b`` could be numeric, duration, or temporal arithmetic
- ``ABS(x)`` could be numeric or duration absolute value

These rules resolve the ambiguity based on operand types when possible,
or produce a union type when not.  If any operand has a concrete type
outside the operation's allowlist, the expression bails to ``unknown()``
so the ambiguous node is preserved (not transformed into a concrete GQL
type that would hide the error).

This is layer 1 of two-layer operand type validation.  Layer 2 (the
``type-mismatch`` structural rule) catches operands that are individually
plausible but incompatible with each other.  See ``Dialect.validate``
for the full picture.
"""

from __future__ import annotations

from graphglot.ast import expressions as ast
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType, TypeKind

_ARITHMETIC_KINDS = frozenset(
    {
        TypeKind.INT,
        TypeKind.FLOAT,
        TypeKind.DECIMAL,
        TypeKind.NUMERIC,
        TypeKind.DATE,
        TypeKind.TIME,
        TypeKind.DATETIME,
        TypeKind.LOCAL_DATETIME,
        TypeKind.LOCAL_TIME,
        TypeKind.DURATION,
    }
)

_CONCAT_KINDS = frozenset({TypeKind.STRING, TypeKind.BYTE_STRING, TypeKind.PATH, TypeKind.LIST})


def _any_incompatible(types: list[GqlType], allowed: frozenset[TypeKind]) -> bool:
    """True when any type in *types* is concrete and outside *allowed* kinds.

    Unknown, union, error, ANY, NULL and PROPERTY_VALUE are never treated as
    incompatible — they could still be valid once resolved.
    """
    for tp in types:
        if tp.is_unknown or tp.is_union or tp.is_error:
            continue
        if tp.kind in (TypeKind.ANY, TypeKind.NULL, TypeKind.PROPERTY_VALUE):
            continue
        if tp.kind not in allowed:
            return True
    return False


def _resolve_type(expr: ast.Expression) -> GqlType:
    return expr._resolved_type if expr._resolved_type else GqlType.unknown()


@type_rule(ast.ConcatenationValueExpression)
def type_concatenation_value_expression(annotator, expr):
    """Resolve ``a || b`` based on operand types.

    Only resolves to a concrete type when all concrete (non-unknown) operands
    agree on the same kind.  Mixed types (e.g. path || string) stay unknown.
    """
    for operand in expr.operands:
        annotator.annotate_child(operand)

    operand_types = [_resolve_type(op) for op in expr.operands]

    if _any_incompatible(operand_types, _CONCAT_KINDS):
        return GqlType.unknown()

    concrete_kinds = {ot.kind for ot in operand_types if ot.kind in _CONCAT_KINDS}

    if len(concrete_kinds) == 1:
        kind = next(iter(concrete_kinds))
        if kind == TypeKind.STRING:
            return GqlType.string()
        if kind == TypeKind.BYTE_STRING:
            return GqlType.byte_string()
        if kind == TypeKind.PATH:
            return GqlType.path()
        if kind == TypeKind.LIST:
            return GqlType.list_()

    # No concrete concat-compatible types — return union of possibilities
    if not concrete_kinds:
        return GqlType.union(
            GqlType.string(), GqlType.byte_string(), GqlType.list_(), GqlType.path()
        )

    # Mixed concrete types — cannot resolve
    return GqlType.unknown()


@type_rule(ast.ArithmeticValueExpression)
def type_arithmetic_value_expression(annotator, expr):
    """Resolve ``a + b`` based on operand types."""
    annotator.annotate_children(expr)

    base_type = _resolve_type(expr.base)

    # No operators — just a wrapped bare value; pass through its type directly
    if not expr.steps:
        return base_type

    step_types = [_resolve_type(step.term) for step in expr.steps]

    all_types = [base_type, *step_types]

    # Cypher list arithmetic: list + list (concat), list - list (difference).
    # Only fires when every concrete operand is LIST (unknowns are permissive).
    if not _any_incompatible(all_types, frozenset({TypeKind.LIST})) and any(
        t.kind == TypeKind.LIST for t in all_types
    ):
        return GqlType.list_()

    if _any_incompatible(all_types, _ARITHMETIC_KINDS):
        return GqlType.unknown()

    if base_type.is_numeric:
        return base_type if base_type.kind != TypeKind.NUMERIC else GqlType.numeric()
    if base_type.kind == TypeKind.DURATION:
        return GqlType.duration()
    if base_type.is_temporal:
        return base_type

    # Infer from step operands when base is unknown
    for step_type in step_types:
        if step_type.is_numeric:
            return GqlType.numeric()
        if step_type.kind == TypeKind.DURATION:
            return GqlType.duration()
        if step_type.is_temporal:
            return step_type

    if base_type.is_unknown:
        return GqlType.union(
            GqlType.numeric(),
            GqlType.duration(),
            GqlType.date(),
            GqlType.time(),
            GqlType.datetime_(),
            GqlType.local_datetime(),
            GqlType.local_time(),
        )

    return GqlType.unknown()


@type_rule(ast.ArithmeticTerm)
def type_arithmetic_term(annotator, expr):
    """Resolve arithmetic term (multiply/divide in ambiguous context)."""
    annotator.annotate_children(expr)
    base_type = _resolve_type(expr.base)
    if not expr.steps:
        return base_type
    factor_types = [_resolve_type(step.factor) for step in expr.steps]
    if _any_incompatible([base_type, *factor_types], _ARITHMETIC_KINDS):
        return GqlType.unknown()
    if base_type.is_numeric:
        return base_type
    if base_type.kind == TypeKind.DURATION:
        return GqlType.duration()
    return GqlType.unknown()


@type_rule(ast.ArithmeticFactor)
def type_arithmetic_factor(annotator, expr):
    """Resolve arithmetic factor (sign + primary in ambiguous context)."""
    annotator.annotate_children(expr)
    return _resolve_type(expr.arithmetic_primary)


@type_rule(ast.ArithmeticAbsoluteValueFunction)
def type_arithmetic_absolute_value_function(annotator, expr):
    """Resolve ``ABS(x)`` based on argument type."""
    annotator.annotate_children(expr)
    arg_type = _resolve_type(expr.arithmetic_value_expression)

    if arg_type.is_numeric:
        return GqlType.numeric()
    if arg_type.kind == TypeKind.DURATION:
        return GqlType.duration()
    if arg_type.is_unknown:
        return GqlType.union(GqlType.numeric(), GqlType.duration())
    return GqlType.unknown()
