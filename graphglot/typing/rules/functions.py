"""Type rules for built-in functions."""

from __future__ import annotations

from graphglot.ast import expressions as ast, functions as f
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType

# ---------------------------------------------------------------------------
# Aggregate functions
# ---------------------------------------------------------------------------


@type_rule(ast.AggregateFunction)
def type_aggregate_function(annotator, expr):
    annotator.annotate_children(expr)
    agg = expr.aggregate_function
    if isinstance(agg, ast.AggregateFunction._CountAsterisk):
        return GqlType.integer()
    if isinstance(agg, ast.GeneralSetFunction):
        return agg._resolved_type or GqlType.unknown()
    if isinstance(agg, ast.BinarySetFunction):
        return agg._resolved_type or GqlType.unknown()
    return GqlType.unknown()


@type_rule(ast.GeneralSetFunction)
def type_general_set_function(annotator, expr):
    annotator.annotate_children(expr)
    fn_type = expr.general_set_function_type.general_set_function_type
    if isinstance(fn_type, ast.GeneralSetFunctionType._Count):
        return GqlType.integer()
    if isinstance(fn_type, ast.GeneralSetFunctionType._Avg):
        return GqlType.numeric()
    if isinstance(fn_type, ast.GeneralSetFunctionType._Sum):
        # SUM returns the same type as its argument
        arg_type = expr.value_expression._resolved_type
        if arg_type and arg_type.is_numeric:
            return arg_type
        return GqlType.numeric()
    if isinstance(fn_type, ast.GeneralSetFunctionType._Max | ast.GeneralSetFunctionType._Min):
        arg_type = expr.value_expression._resolved_type
        if arg_type and not arg_type.is_unknown:
            return arg_type
        return GqlType.unknown()
    if isinstance(fn_type, ast.GeneralSetFunctionType._CollectList):
        arg_type = expr.value_expression._resolved_type
        return GqlType.list_(arg_type)
    if isinstance(
        fn_type,
        ast.GeneralSetFunctionType._StddevSamp | ast.GeneralSetFunctionType._StddevPop,
    ):
        return GqlType.float_()
    return GqlType.unknown()


@type_rule(ast.BinarySetFunction)
def type_binary_set_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.numeric()


# ---------------------------------------------------------------------------
# Numeric functions
# ---------------------------------------------------------------------------


@type_rule(
    ast.AbsoluteValueExpression,
    ast.ModulusExpression,
)
def type_numeric_value_function_numeric(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.numeric()


@type_rule(ast.FloorFunction, ast.CeilingFunction)
def type_floor_ceiling(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.integer()


@type_rule(ast.SquareRoot)
def type_square_root(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.float_()


@type_rule(ast.PowerFunction)
def type_power_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.float_()


@type_rule(ast.TrigonometricFunction)
def type_trigonometric_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.float_()


@type_rule(ast.GeneralLogarithmFunction, ast.CommonLogarithm, ast.NaturalLogarithm)
def type_logarithm_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.float_()


@type_rule(ast.ExponentialFunction)
def type_exponential_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.float_()


@type_rule(ast.CardinalityExpression)
def type_cardinality_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.integer()


@type_rule(ast.PathLengthExpression)
def type_path_length_expression(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.integer()


# ---------------------------------------------------------------------------
# String functions
# ---------------------------------------------------------------------------


@type_rule(ast.SubstringFunction)
def type_substring_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.string()


@type_rule(ast.Fold)
def type_fold(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.string()


# ---------------------------------------------------------------------------
# Temporal functions
# ---------------------------------------------------------------------------


@type_rule(ast.DateFunction)
def type_date_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.date()


@type_rule(ast.TimeFunction)
def type_time_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.time()


@type_rule(ast.LocaltimeFunction)
def type_localtime_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.local_time()


@type_rule(ast.DatetimeFunction)
def type_datetime_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.datetime_()


@type_rule(ast.LocaldatetimeFunction)
def type_localdatetime_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.local_datetime()


@type_rule(ast.DurationFunction)
def type_duration_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.duration()


# ---------------------------------------------------------------------------
# Element functions
# ---------------------------------------------------------------------------


@type_rule(ast.ElementIdFunction)
def type_element_id_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.string()


@type_rule(f.Size)
def type_size_function(annotator, expr):
    """size(expr) always returns integer; argument type drives resolution."""
    annotator.annotate_children(expr)
    return GqlType.integer()


@type_rule(ast.ElementsFunction)
def type_elements_function(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.list_(GqlType.union(GqlType.node(), GqlType.edge()))
