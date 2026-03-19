"""Type rules for operator expressions."""

from __future__ import annotations

from graphglot.ast import expressions as ast
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType

# ---------------------------------------------------------------------------
# Boolean
# ---------------------------------------------------------------------------


@type_rule(ast.BooleanValueExpression)
def type_boolean_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.BooleanTerm)
def type_boolean_term(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.BooleanFactor)
def type_boolean_factor(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.BooleanTest)
def type_boolean_test(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


# ---------------------------------------------------------------------------
# Comparison / Predicates
# ---------------------------------------------------------------------------


@type_rule(ast.ComparisonPredicate)
def type_comparison_predicate(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.ExistsPredicate)
def type_exists_predicate(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.NullPredicate)
def type_null_predicate(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.NormalizedPredicate)
def type_normalized_predicate(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.DirectedPredicate)
def type_directed_predicate(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.LabeledPredicate)
def type_labeled_predicate(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


@type_rule(ast.SourceDestinationPredicate)
def type_source_destination_predicate(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.boolean()


# ---------------------------------------------------------------------------
# Numeric
# ---------------------------------------------------------------------------


@type_rule(ast.NumericValueExpression)
def type_numeric_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    # Determine specific numeric type from operands
    base_type = expr.base._resolved_type if expr.base._resolved_type else GqlType.unknown()
    if base_type.is_numeric:
        return base_type
    return GqlType.numeric()


@type_rule(ast.Term)
def type_term(annotator, expr):
    annotator.annotate_children(expr)
    base_type = expr.base._resolved_type if expr.base._resolved_type else GqlType.unknown()
    if base_type.is_numeric:
        return base_type
    return GqlType.numeric()


@type_rule(ast.Factor)
def type_factor(annotator, expr):
    annotator.annotate_children(expr)
    inner = expr.numeric_primary._resolved_type if expr.numeric_primary._resolved_type else None
    if inner:
        return inner
    return GqlType.numeric()


# ---------------------------------------------------------------------------
# String
# ---------------------------------------------------------------------------


@type_rule(ast.CharacterStringValueExpression)
def type_character_string_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.string()


@type_rule(ast.ByteStringValueExpression)
def type_byte_string_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.byte_string()


# ---------------------------------------------------------------------------
# Temporal / Duration
# ---------------------------------------------------------------------------


@type_rule(ast.DatetimeValueExpression)
def type_datetime_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    # The base primary determines the datetime kind
    return GqlType.datetime_()


@type_rule(ast.DurationValueExpression)
def type_duration_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.duration()


@type_rule(ast.DurationTerm)
def type_duration_term(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.duration()


# ---------------------------------------------------------------------------
# List / Path
# ---------------------------------------------------------------------------


@type_rule(ast.ListValueExpression)
def type_list_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.list_()


@type_rule(ast.PathValueExpression)
def type_path_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.path()


# ---------------------------------------------------------------------------
# Property reference
# ---------------------------------------------------------------------------


@type_rule(ast.PropertyReference)
def type_property_reference(annotator, expr):
    annotator.annotate_children(expr)
    # Check external context for property types
    source_type = (
        expr.property_source._resolved_type if expr.property_source._resolved_type else None
    )
    if source_type and expr.property_name:
        prop_name = expr.property_name[0].identifier.name if expr.property_name else None
        if prop_name and source_type.labels:
            for label in source_type.labels:
                pt = annotator.external_context.property_types.get((label, prop_name))
                if pt is not None:
                    return pt
    return GqlType.unknown()


# ---------------------------------------------------------------------------
# Parenthesized / Let / Query
# ---------------------------------------------------------------------------


@type_rule(ast.ParenthesizedValueExpression)
def type_parenthesized_value_expression(annotator, expr):
    inner = annotator.annotate_child(expr.value_expression)
    return inner


@type_rule(ast.LetValueExpression)
def type_let_value_expression(annotator, expr):
    annotator.annotate_children(expr)
    return expr.value_expression._resolved_type or GqlType.unknown()


@type_rule(ast.ValueQueryExpression)
def type_value_query_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.unknown()


# ---------------------------------------------------------------------------
# Case expressions
# ---------------------------------------------------------------------------


@type_rule(ast.SimpleCase)
def type_simple_case(annotator, expr):
    annotator.annotate_children(expr)
    # Result type is the union of all THEN/ELSE clause result types
    result_types = []
    for clause in expr.list_simple_when_clause:
        if clause._resolved_type and not clause._resolved_type.is_unknown:
            result_types.append(clause._resolved_type)
    if expr.else_clause and expr.else_clause._resolved_type:
        result_types.append(expr.else_clause._resolved_type)
    if result_types and all(t == result_types[0] for t in result_types):
        return result_types[0]
    if result_types:
        return GqlType.union(*result_types)
    return GqlType.unknown()


@type_rule(ast.SearchedCase)
def type_searched_case(annotator, expr):
    annotator.annotate_children(expr)
    result_types = []
    for clause in expr.list_searched_when_clause:
        if clause._resolved_type and not clause._resolved_type.is_unknown:
            result_types.append(clause._resolved_type)
    if expr.else_clause and expr.else_clause._resolved_type:
        result_types.append(expr.else_clause._resolved_type)
    if result_types and all(t == result_types[0] for t in result_types):
        return result_types[0]
    if result_types:
        return GqlType.union(*result_types)
    return GqlType.unknown()
