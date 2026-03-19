"""Type rules for literal AST nodes."""

from __future__ import annotations

from graphglot.ast import expressions as ast
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType, TypeKind


@type_rule(ast.BooleanLiteral)
def type_boolean_literal(annotator, expr):
    return GqlType.boolean()


@type_rule(ast.TruthValue)
def type_truth_value(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.CharacterStringLiteral)
def type_character_string_literal(annotator, expr):
    return GqlType.string()


@type_rule(ast.ByteStringLiteral)
def type_byte_string_literal(annotator, expr):
    return GqlType.byte_string()


@type_rule(ast.UnsignedNumericLiteral)
def type_unsigned_numeric_literal(annotator, expr):
    if isinstance(expr.value, int):
        return GqlType.integer()
    return GqlType.decimal()


@type_rule(ast.SignedNumericLiteral)
def type_signed_numeric_literal(annotator, expr):
    inner = annotator.annotate_child(expr.unsigned_numeric_literal)
    return inner


@type_rule(ast.NullLiteral)
def type_null_literal(annotator, expr):
    return GqlType.null()


@type_rule(ast.DurationLiteral)
def type_duration_literal(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.duration()


@type_rule(ast.TemporalLiteral)
def type_temporal_literal(annotator, expr):
    annotator.annotate_children(expr)
    # TemporalLiteral is a base class; subtypes carry more info
    return GqlType(kind=TypeKind.UNKNOWN)


@type_rule(ast.DateLiteral)
def type_date_literal(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.date()


@type_rule(ast.TimeLiteral)
def type_time_literal(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.time()


@type_rule(ast.DatetimeLiteral)
def type_datetime_literal(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.datetime_()


@type_rule(ast.SqlDatetimeLiteral)
def type_sql_datetime_literal(annotator, expr):
    annotator.annotate_children(expr)
    kind_map = {
        ast.SqlDatetimeLiteral.Kind.DATE: TypeKind.DATE,
        ast.SqlDatetimeLiteral.Kind.TIME: TypeKind.TIME,
        ast.SqlDatetimeLiteral.Kind.TIMESTAMP: TypeKind.DATETIME,
    }
    return GqlType(kind=kind_map.get(expr.kind, TypeKind.UNKNOWN))


@type_rule(ast.ListValueConstructorByEnumeration)
def type_list_constructor(annotator, expr):
    annotator.annotate_children(expr)
    # Try to infer element type from list elements
    if expr.list_element_list is not None:
        elements = expr.list_element_list.list_list_element
        if elements:
            elem_types = [e._resolved_type for e in elements if e._resolved_type]
            if elem_types and all(t == elem_types[0] for t in elem_types):
                return GqlType.list_(elem_types[0])
            if elem_types:
                return GqlType.list_(GqlType.union(*elem_types))
    return GqlType.list_()


@type_rule(ast.RecordConstructor)
def type_record_constructor(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.record()
