"""Type rules for resolving ambiguous value expressions.

At parse time, some expressions are syntactically ambiguous:
- ``a || b`` could be string, list, or path concatenation
- ``a + b`` could be numeric, duration, or temporal arithmetic
- ``ABS(x)`` could be numeric or duration absolute value

These rules resolve the ambiguity based on operand types when possible,
or produce a union type when not.
"""

from __future__ import annotations

from graphglot.ast import expressions as ast
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType, TypeKind


@type_rule(ast.ConcatenationValueExpression)
def type_concatenation_value_expression(annotator, expr):
    """Resolve ``a || b`` based on operand types.

    Only resolves to a concrete type when all concrete (non-unknown) operands
    agree on the same kind.  Mixed types (e.g. path || string) stay unknown.
    """
    for operand in expr.operands:
        annotator.annotate_child(operand)

    operand_types = [op._resolved_type for op in expr.operands if op._resolved_type is not None]

    concat_kinds = {TypeKind.STRING, TypeKind.BYTE_STRING, TypeKind.PATH, TypeKind.LIST}
    concrete_kinds = {ot.kind for ot in operand_types if ot.kind in concat_kinds}

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

    base_type = expr.base._resolved_type if expr.base._resolved_type else GqlType.unknown()

    # No operators — just a wrapped bare value; pass through its type directly
    if not expr.steps:
        return base_type

    if base_type.is_numeric:
        return base_type if base_type.kind != TypeKind.NUMERIC else GqlType.numeric()
    if base_type.kind == TypeKind.DURATION:
        return GqlType.duration()
    if base_type.is_temporal:
        return base_type

    # Check step operands (_SignedTerm has no type rule, so read from its inner term)
    for step in expr.steps:
        step_type = step.term._resolved_type if step.term._resolved_type else GqlType.unknown()
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
    base_type = expr.base._resolved_type if expr.base._resolved_type else GqlType.unknown()
    if not expr.steps:
        return base_type
    if base_type.is_numeric:
        return base_type
    if base_type.kind == TypeKind.DURATION:
        return GqlType.duration()
    return GqlType.unknown()


@type_rule(ast.ArithmeticFactor)
def type_arithmetic_factor(annotator, expr):
    """Resolve arithmetic factor (sign + primary in ambiguous context)."""
    annotator.annotate_children(expr)
    inner = (
        expr.arithmetic_primary._resolved_type
        if expr.arithmetic_primary._resolved_type
        else GqlType.unknown()
    )
    return inner


@type_rule(ast.ArithmeticAbsoluteValueFunction)
def type_arithmetic_absolute_value_function(annotator, expr):
    """Resolve ``ABS(x)`` based on argument type."""
    annotator.annotate_children(expr)
    arg_type = (
        expr.arithmetic_value_expression._resolved_type
        if expr.arithmetic_value_expression._resolved_type
        else GqlType.unknown()
    )

    if arg_type.is_numeric:
        return GqlType.numeric()
    if arg_type.kind == TypeKind.DURATION:
        return GqlType.duration()
    if arg_type.is_unknown:
        return GqlType.union(GqlType.numeric(), GqlType.duration())
    return GqlType.unknown()
