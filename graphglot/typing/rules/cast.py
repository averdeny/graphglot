"""Type rules for CAST expressions and AST ValueType → GqlType conversion."""

from __future__ import annotations

from graphglot.ast import expressions as ast
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType, TypeKind


def from_ast_value_type(vt: ast.ValueType) -> GqlType:
    """Convert an AST ValueType to a GqlType."""
    if isinstance(vt, ast.BooleanType):
        return GqlType.boolean()
    if isinstance(vt, ast.CharacterStringType):
        return GqlType.string()
    if isinstance(vt, ast.ByteStringType):
        return GqlType.byte_string()

    # Numeric types
    if isinstance(vt, ast.ApproximateNumericType):
        return GqlType.float_()
    if isinstance(vt, ast.DecimalExactNumericType):
        return GqlType.decimal()
    if isinstance(vt, ast.BinaryExactNumericType):
        return GqlType.integer()
    if isinstance(vt, ast.ExactNumericType):
        return GqlType.numeric()
    if isinstance(vt, ast.NumericType):
        return GqlType.numeric()

    # Temporal types
    if isinstance(vt, ast.DateType):
        return GqlType.date()
    if isinstance(vt, ast.TimeType):
        return GqlType.time()
    if isinstance(vt, ast.DatetimeType):
        return GqlType.datetime_()
    if isinstance(vt, ast.TemporalDurationType):
        return GqlType.duration()
    if isinstance(vt, ast.TemporalType):
        return GqlType(kind=TypeKind.UNKNOWN)

    # Constructed types
    if isinstance(vt, ast.PathValueType):
        return GqlType.path()
    if isinstance(vt, ast.ListValueType):
        return GqlType.list_()
    if isinstance(vt, ast.RecordType):
        return GqlType.record()

    # Reference types
    if isinstance(vt, ast.NodeReferenceValueType):
        return GqlType.node()
    if isinstance(vt, ast.EdgeReferenceValueType):
        return GqlType.edge()

    return GqlType.unknown()


@type_rule(ast.CastSpecification)
def type_cast_specification(annotator, expr):
    annotator.annotate_children(expr)
    return from_ast_value_type(expr.cast_target)
