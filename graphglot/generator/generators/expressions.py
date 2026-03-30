"""Generator functions for value expressions."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.ast import functions as f
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.NestedQuerySpecification)
def generate_nested_query_specification(
    gen: Generator, expr: ast.NestedQuerySpecification
) -> Fragment:
    return gen.braces(gen.dispatch(expr.query_specification))


@generates(ast.ValueQueryExpression)
def generate_value_query_expression(gen: Generator, expr: ast.ValueQueryExpression) -> Fragment:
    return gen.seq("VALUE", gen.dispatch(expr.nested_query_specification))


@generates(ast.BindingTableReferenceValueExpression)
def generate_binding_table_reference_value_expression(
    gen: Generator, expr: ast.BindingTableReferenceValueExpression
) -> Fragment:
    inner = expr.binding_table_reference_value_expression
    if isinstance(inner, ast.BindingTableReferenceValueExpression._TableBindingTableExpression):
        return gen.seq("TABLE", gen.dispatch(inner.binding_table_expression))
    return gen.dispatch(inner)


@generates(ast.GraphReferenceValueExpression)
def generate_graph_reference_value_expression(
    gen: Generator, expr: ast.GraphReferenceValueExpression
) -> Fragment:
    inner = expr.graph_reference_value_expression
    if isinstance(inner, ast.GraphReferenceValueExpression._GraphGraphExpression):
        return gen.seq("GRAPH", gen.dispatch(inner.graph_expression))
    return gen.dispatch(inner)


@generates(ast.ByteStringValueExpression)
def generate_byte_string_value_expression(
    gen: Generator, expr: ast.ByteStringValueExpression
) -> Fragment:
    return gen.join(
        [gen.dispatch(item) for item in expr.list_byte_string_primary],
        sep=" || ",
    )


@generates(ast.PathValueExpression)
def generate_path_value_expression(gen: Generator, expr: ast.PathValueExpression) -> Fragment:
    return gen.join(
        [gen.dispatch(item) for item in expr.list_path_value_primary],
        sep=" || ",
    )


@generates(ast.ListValueExpression)
def generate_list_value_expression(gen: Generator, expr: ast.ListValueExpression) -> Fragment:
    return gen.join(
        [gen.dispatch(item) for item in expr.list_list_primary],
        sep=" || ",
    )


@generates(ast.CharacterStringValueExpression)
def generate_character_string_value_expression(
    gen: Generator, expr: ast.CharacterStringValueExpression
) -> Fragment:
    return gen.join(
        [gen.dispatch(item) for item in expr.list_character_string_value_expression],
        sep=" || ",
    )


@generates(ast.ConcatenationValueExpression)
def generate_concatenation_value_expression(
    gen: Generator, expr: ast.ConcatenationValueExpression
) -> Fragment:
    return gen.join(
        [gen.dispatch(item) for item in expr.operands],
        sep=" || ",
    )


@generates(ast.BooleanValueExpression)
def generate_boolean_value_expression(gen: Generator, expr: ast.BooleanValueExpression) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.boolean_term)]
    if expr.ops:
        for item in expr.ops:
            if item.operator == ast.BooleanValueExpression.Operator.OR:
                parts.append("OR")
            elif item.operator == ast.BooleanValueExpression.Operator.XOR:
                parts.append("XOR")
            parts.append(gen.dispatch(item.boolean_term))
    return gen.seq(*parts)


@generates(ast.BooleanTerm)
def generate_boolean_term(gen: Generator, expr: ast.BooleanTerm) -> Fragment:
    return gen.join([gen.dispatch(f) for f in expr.list_boolean_factor], sep=" AND ")


@generates(ast.BooleanFactor)
def generate_boolean_factor(gen: Generator, expr: ast.BooleanFactor) -> Fragment:
    if expr.not_:
        return gen.seq("NOT", gen.dispatch(expr.boolean_test))
    return gen.dispatch(expr.boolean_test)


@generates(ast.BooleanTest)
def generate_boolean_test(gen: Generator, expr: ast.BooleanTest) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.boolean_primary)]
    if expr.truth_value:
        is_not = "IS NOT" if expr.truth_value.not_ else "IS"
        truth = gen.dispatch(expr.truth_value.truth_value)
        parts.append(is_not)
        parts.append(truth)
    return gen.seq(*parts)


@generates(ast.TruthValue)
def generate_truth_value(gen: Generator, expr: ast.TruthValue) -> Fragment:
    if isinstance(expr.truth_value, ast.TruthValue._True):
        return Fragment("TRUE")
    elif isinstance(expr.truth_value, ast.TruthValue._False):
        return Fragment("FALSE")
    else:
        return Fragment("UNKNOWN")


@generates(ast.ParenthesizedBooleanValueExpression)
def generate_parenthesized_boolean_value_expression(
    gen: Generator, expr: ast.ParenthesizedBooleanValueExpression
) -> Fragment:
    return gen.parens(gen.dispatch(expr.boolean_value_expression))


@generates(ast.NumericValueExpression)
def generate_numeric_value_expression(gen: Generator, expr: ast.NumericValueExpression) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.base)]
    if expr.steps:
        for item in expr.steps:
            sign = "+" if item.sign == ast.Sign.PLUS_SIGN else "-"
            parts.append(sign)
            parts.append(gen.dispatch(item.term))
    return gen.seq(*parts, sep=" ")


@generates(ast.Term)
def generate_term(gen: Generator, expr: ast.Term) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.base)]
    if expr.steps:
        for step in expr.steps:
            op = "*" if step.operator == ast.MultiplicativeOperator.MULTIPLY else "/"
            parts.append(op)
            parts.append(gen.dispatch(step.factor))
    return gen.seq(*parts, sep=" ")


@generates(ast.Factor)
def generate_factor(gen: Generator, expr: ast.Factor) -> Fragment:
    if expr.sign == ast.Sign.MINUS_SIGN:
        return gen.seq("-", gen.dispatch(expr.numeric_primary), sep="")
    return gen.dispatch(expr.numeric_primary)


@generates(ast.ArithmeticValueExpression)
def generate_arithmetic_value_expression(
    gen: Generator, expr: ast.ArithmeticValueExpression
) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.base)]
    if expr.steps:
        for item in expr.steps:
            sign = "+" if item.sign == ast.Sign.PLUS_SIGN else "-"
            parts.append(sign)
            parts.append(gen.dispatch(item.term))
    return gen.seq(*parts, sep=" ")


@generates(ast.ArithmeticTerm)
def generate_arithmetic_term(gen: Generator, expr: ast.ArithmeticTerm) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.base)]
    if expr.steps:
        for step in expr.steps:
            op = "*" if step.operator == ast.MultiplicativeOperator.MULTIPLY else "/"
            parts.append(op)
            parts.append(gen.dispatch(step.factor))
    return gen.seq(*parts, sep=" ")


@generates(ast.ArithmeticFactor)
def generate_arithmetic_factor(gen: Generator, expr: ast.ArithmeticFactor) -> Fragment:
    if expr.sign == ast.Sign.MINUS_SIGN:
        return gen.seq("-", gen.dispatch(expr.arithmetic_primary), sep="")
    return gen.dispatch(expr.arithmetic_primary)


@generates(ast.ArithmeticAbsoluteValueFunction)
def generate_arithmetic_absolute_value_function(
    gen: Generator, expr: ast.ArithmeticAbsoluteValueFunction
) -> Fragment:
    return gen.seq("ABS", gen.parens(gen.dispatch(expr.arithmetic_value_expression)))


@generates(ast.AbsoluteValueExpression)
def generate_absolute_value_expression(
    gen: Generator, expr: ast.AbsoluteValueExpression
) -> Fragment:
    return gen.seq("ABS", gen.parens(gen.dispatch(expr.numeric_value_expression)))


@generates(ast.DurationAbsoluteValueFunction)
def generate_duration_absolute_value_function(
    gen: Generator, expr: ast.DurationAbsoluteValueFunction
) -> Fragment:
    return gen.seq("ABS", gen.parens(gen.dispatch(expr.duration_value_expression)))


@generates(ast.DatetimeValueExpression)
def generate_datetime_value_expression(
    gen: Generator, expr: ast.DatetimeValueExpression
) -> Fragment:
    base = expr.base
    parts: list[str | Fragment]
    if isinstance(base, ast.DatetimeValueExpression._DurationValueExpressionPlusDatetimePrimary):
        # <duration value expression> <plus sign> <datetime primary>
        parts = [
            gen.dispatch(base.duration_value_expression),
            "+",
            gen.dispatch(base.datetime_primary),
        ]
    else:
        # <datetime primary> with optional steps
        parts = [gen.dispatch(base)]

    if expr.steps:
        for item in expr.steps:
            sign = "+" if item.sign == ast.Sign.PLUS_SIGN else "-"
            parts.append(sign)
            parts.append(gen.dispatch(item.duration_term))

    return gen.seq(*parts, sep=" ")


@generates(ast.DurationValueExpression)
def generate_duration_value_expression(
    gen: Generator, expr: ast.DurationValueExpression
) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.base)]
    if expr.steps:
        for item in expr.steps:
            sign = "+" if item.sign == ast.Sign.PLUS_SIGN else "-"
            parts.append(sign)
            parts.append(gen.dispatch(item.duration_term))
    return gen.seq(*parts, sep=" ")


@generates(ast.DurationTerm)
def generate_duration_term(gen: Generator, expr: ast.DurationTerm) -> Fragment:
    parts: list[str | Fragment] = []

    # Optional leading term with asterisk (term * duration_factor)
    if expr.multiplicative_term is not None:
        parts.append(gen.dispatch(expr.multiplicative_term))
        parts.append("*")

    parts.append(gen.dispatch(expr.base))

    # Optional multiplicative steps (duration_term *|/ factor)
    if expr.steps:
        for step in expr.steps:
            op = "*" if step.operator == ast.MultiplicativeOperator.MULTIPLY else "/"
            parts.append(op)
            parts.append(gen.dispatch(step.factor))

    return gen.seq(*parts, sep=" ")


@generates(ast.DurationFactor)
def generate_duration_factor(gen: Generator, expr: ast.DurationFactor) -> Fragment:
    if expr.sign == ast.Sign.MINUS_SIGN:
        return gen.seq("-", gen.dispatch(expr.duration_primary), sep="")
    return gen.dispatch(expr.duration_primary)


@generates(ast.DatetimeSubtraction)
def generate_datetime_subtraction(gen: Generator, expr: ast.DatetimeSubtraction) -> Fragment:
    params = gen.dispatch(expr.datetime_subtraction_parameters)
    result = gen.seq("DURATION_BETWEEN", gen.parens(params))
    if expr.temporal_duration_qualifier:
        result = gen.seq(result, gen.dispatch(expr.temporal_duration_qualifier))
    return result


@generates(ast.DatetimeSubtractionParameters)
def generate_datetime_subtraction_parameters(
    gen: Generator, expr: ast.DatetimeSubtractionParameters
) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.datetime_value_expression_1),
        ",",
        gen.dispatch(expr.datetime_value_expression_2),
        sep=" ",
    )


@generates(ast.PropertyReference)
def generate_property_reference(gen: Generator, expr: ast.PropertyReference) -> Fragment:
    source = gen.dispatch(expr.property_source)
    names = ".".join(str(gen.dispatch(name)) for name in expr.property_name)
    return Fragment(f"{source}.{names}")


@generates(ast.ParenthesizedValueExpression)
def generate_parenthesized_value_expression(
    gen: Generator, expr: ast.ParenthesizedValueExpression
) -> Fragment:
    return gen.parens(gen.dispatch(expr.value_expression))


@generates(ast.AggregateFunction)
def generate_aggregate_function(gen: Generator, expr: ast.AggregateFunction) -> Fragment:
    inner = expr.aggregate_function
    if isinstance(inner, ast.AggregateFunction._CountAsterisk):
        return Fragment("COUNT(*)")
    else:
        return gen.dispatch(inner)


@generates(ast.GeneralSetFunction)
def generate_general_set_function(gen: Generator, expr: ast.GeneralSetFunction) -> Fragment:
    func_type = gen.dispatch(expr.general_set_function_type)
    parts = []
    if expr.set_quantifier:
        parts.append(gen.dispatch(expr.set_quantifier))
    parts.append(gen.dispatch(expr.value_expression))
    return Fragment(f"{func_type}({gen.seq(*parts)})")


@generates(ast.GeneralSetFunctionType)
def generate_general_set_function_type(
    gen: Generator, expr: ast.GeneralSetFunctionType
) -> Fragment:
    type_map = {
        ast.GeneralSetFunctionType._Avg: "AVG",
        ast.GeneralSetFunctionType._Count: "COUNT",
        ast.GeneralSetFunctionType._Max: "MAX",
        ast.GeneralSetFunctionType._Min: "MIN",
        ast.GeneralSetFunctionType._Sum: "SUM",
        ast.GeneralSetFunctionType._CollectList: "COLLECT_LIST",
        ast.GeneralSetFunctionType._StddevSamp: "STDDEV_SAMP",
        ast.GeneralSetFunctionType._StddevPop: "STDDEV_POP",
    }
    for cls, name in type_map.items():
        if isinstance(expr.general_set_function_type, cls):
            return Fragment(gen.keyword(name))
    return Fragment("COUNT")


@generates(ast.DependentValueExpression)
def generate_dependent_value_expression(
    gen: Generator, expr: ast.DependentValueExpression
) -> Fragment:
    parts = []
    if expr.set_quantifier:
        parts.append(gen.dispatch(expr.set_quantifier))
    parts.append(gen.dispatch(expr.numeric_value_expression))
    return gen.seq(*parts)


@generates(ast.BinarySetFunction)
def generate_binary_set_function(gen: Generator, expr: ast.BinarySetFunction) -> Fragment:
    func_name = expr.binary_set_function_type.name
    return Fragment(
        f"{func_name}({gen.dispatch(expr.dependent_value_expression)}, "
        f"{gen.dispatch(expr.independent_value_expression)})"
    )


@generates(ast.SimpleCase)
def generate_simple_case(gen: Generator, expr: ast.SimpleCase) -> Fragment:
    parts: list[str | Fragment] = ["CASE", gen.dispatch(expr.case_operand)]
    for when in expr.list_simple_when_clause:
        parts.append(gen.dispatch(when))
    if expr.else_clause:
        parts.append(gen.dispatch(expr.else_clause))
    parts.append("END")
    return gen.seq(*parts)


@generates(ast.SearchedCase)
def generate_searched_case(gen: Generator, expr: ast.SearchedCase) -> Fragment:
    parts: list[str | Fragment] = ["CASE"]
    for when in expr.list_searched_when_clause:
        parts.append(gen.dispatch(when))
    if expr.else_clause:
        parts.append(gen.dispatch(expr.else_clause))
    parts.append("END")
    return gen.seq(*parts)


@generates(ast.SimpleWhenClause)
def generate_simple_when_clause(gen: Generator, expr: ast.SimpleWhenClause) -> Fragment:
    return gen.seq("WHEN", gen.dispatch(expr.when_operand_list), "THEN", gen.dispatch(expr.result))


@generates(ast.SearchedWhenClause)
def generate_searched_when_clause(gen: Generator, expr: ast.SearchedWhenClause) -> Fragment:
    return gen.seq("WHEN", gen.dispatch(expr.search_condition), "THEN", gen.dispatch(expr.result))


@generates(ast.WhenOperandList)
def generate_when_operand_list(gen: Generator, expr: ast.WhenOperandList) -> Fragment:
    return gen.join([gen.dispatch(o) for o in expr.list_when_operand], sep=", ")


@generates(ast.ElseClause)
def generate_else_clause(gen: Generator, expr: ast.ElseClause) -> Fragment:
    return gen.seq("ELSE", gen.dispatch(expr.result))


@generates(ast.CaseAbbreviation)
def generate_case_abbreviation(gen: Generator, expr: ast.CaseAbbreviation) -> Fragment:
    inner = expr.case_abbreviation
    if isinstance(
        inner, ast.CaseAbbreviation._NullifLeftParenValueExpressionCommaValueExpressionRightParen
    ):
        return Fragment(
            f"NULLIF({gen.dispatch(inner.value_expression_1)}, "
            f"{gen.dispatch(inner.value_expression_2)})"
        )
    elif isinstance(inner, ast.CaseAbbreviation._CoalesceLeftParenListValueExpressionRightParen):
        args = gen.join([gen.dispatch(v) for v in inner.list_value_expression], sep=", ")
        return Fragment(f"COALESCE({args})")
    else:
        return gen.dispatch(inner)


@generates(ast.ListValueConstructorByEnumeration)
def generate_list_value_constructor_by_enumeration(
    gen: Generator, expr: ast.ListValueConstructorByEnumeration
) -> Fragment:
    elements: str | Fragment
    if expr.list_element_list:
        elements = gen.dispatch(expr.list_element_list)
    else:
        elements = ""
    result = gen.brackets(elements)
    if expr.list_value_type_name:
        return gen.seq(gen.dispatch(expr.list_value_type_name), result, sep="")
    return result


@generates(ast.ListElementList)
def generate_list_element_list(gen: Generator, expr: ast.ListElementList) -> Fragment:
    return gen.join([gen.dispatch(e) for e in expr.list_list_element], sep=", ")


@generates(ast.RecordConstructor)
def generate_record_constructor(gen: Generator, expr: ast.RecordConstructor) -> Fragment:
    parts: list[str | Fragment] = []
    if expr.record:
        parts.append("RECORD")
    parts.append(gen.dispatch(expr.fields_specification))
    return gen.seq(*parts)


@generates(ast.FieldsSpecification)
def generate_fields_specification(gen: Generator, expr: ast.FieldsSpecification) -> Fragment:
    if expr.field_list:
        return gen.braces(gen.dispatch(expr.field_list))
    return Fragment("{}")


@generates(ast.FieldList)
def generate_field_list(gen: Generator, expr: ast.FieldList) -> Fragment:
    return gen.join([gen.dispatch(f) for f in expr.list_field], sep=", ")


@generates(ast.Field)
def generate_field(gen: Generator, expr: ast.Field) -> Fragment:
    return gen.seq(gen.dispatch(expr.field_name), ":", gen.dispatch(expr.value_expression), sep=" ")


# Graph expressions


@generates(ast.ObjectExpressionPrimary)
def generate_object_expression_primary(
    gen: Generator, expr: ast.ObjectExpressionPrimary
) -> Fragment:
    inner = expr.object_expression_primary
    if isinstance(inner, ast.ObjectExpressionPrimary._VariableValueExpressionPrimary):
        return gen.dispatch(inner.value_expression_primary)
    return gen.dispatch(inner)


@generates(ast.GraphReference)
def generate_graph_reference(gen: Generator, expr: ast.GraphReference) -> Fragment:
    inner = expr.graph_reference
    if isinstance(inner, ast.GraphReference._CatalogObjectParentReferenceGraphName):
        return gen.seq(
            gen.dispatch(inner.catalog_object_parent_reference),
            gen.dispatch(inner.graph_name),
            sep=".",
        )
    else:
        return gen.dispatch(inner)


@generates(ast.HomeGraph)
def generate_home_graph(gen: Generator, expr: ast.HomeGraph) -> Fragment:
    return Fragment("HOME_GRAPH")


@generates(ast.CurrentGraph)
def generate_current_graph(gen: Generator, expr: ast.CurrentGraph) -> Fragment:
    return Fragment("CURRENT_GRAPH")


# Value expression primary


@generates(ast.GeneralValueSpecification)
def generate_general_value_specification(
    gen: Generator, expr: ast.GeneralValueSpecification
) -> Fragment:
    return gen.dispatch(expr.general_value_specification)


@generates(ast.SubstitutedParameterReference)
def generate_substituted_parameter_reference(
    gen: Generator, expr: ast.SubstitutedParameterReference
) -> Fragment:
    return Fragment(f"$${gen.dispatch(expr.parameter_name)}")


# Numeric value functions


@generates(ast.ModulusExpression)
def generate_modulus_expression(gen: Generator, expr: ast.ModulusExpression) -> Fragment:
    return Fragment(
        f"MOD({gen.dispatch(expr.numeric_value_expression_dividend)}, "
        f"{gen.dispatch(expr.numeric_value_expression_divisor)})"
    )


@generates(ast.FloorFunction)
def generate_floor_function(gen: Generator, expr: ast.FloorFunction) -> Fragment:
    return Fragment(f"FLOOR({gen.dispatch(expr.numeric_value_expression)})")


@generates(ast.CeilingFunction)
def generate_ceiling_function(gen: Generator, expr: ast.CeilingFunction) -> Fragment:
    return Fragment(f"CEIL({gen.dispatch(expr.numeric_value_expression)})")


@generates(ast.SquareRoot)
def generate_square_root(gen: Generator, expr: ast.SquareRoot) -> Fragment:
    return Fragment(f"SQRT({gen.dispatch(expr.numeric_value_expression)})")


@generates(ast.PowerFunction)
def generate_power_function(gen: Generator, expr: ast.PowerFunction) -> Fragment:
    return Fragment(
        f"POWER({gen.dispatch(expr.numeric_value_expression_base)}, "
        f"{gen.dispatch(expr.numeric_value_expression_exponent)})"
    )


@generates(ast.ExponentialFunction)
def generate_exponential_function(gen: Generator, expr: ast.ExponentialFunction) -> Fragment:
    return Fragment(f"EXP({gen.dispatch(expr.numeric_value_expression)})")


@generates(ast.NaturalLogarithm)
def generate_natural_logarithm(gen: Generator, expr: ast.NaturalLogarithm) -> Fragment:
    return Fragment(f"LN({gen.dispatch(expr.numeric_value_expression)})")


@generates(ast.CommonLogarithm)
def generate_common_logarithm(gen: Generator, expr: ast.CommonLogarithm) -> Fragment:
    return Fragment(f"LOG10({gen.dispatch(expr.numeric_value_expression)})")


@generates(ast.GeneralLogarithmFunction)
def generate_general_logarithm_function(
    gen: Generator, expr: ast.GeneralLogarithmFunction
) -> Fragment:
    return Fragment(
        f"LOG({gen.dispatch(expr.general_logarithm_base)}, "
        f"{gen.dispatch(expr.general_logarithm_argument)})"
    )


@generates(ast.TrigonometricFunction)
def generate_trigonometric_function(gen: Generator, expr: ast.TrigonometricFunction) -> Fragment:
    name = gen.dispatch(expr.trigonometric_function_name)
    return Fragment(f"{name}({gen.dispatch(expr.numeric_value_expression)})")


@generates(ast.TrigonometricFunctionName)
def generate_trigonometric_function_name(
    gen: Generator, expr: ast.TrigonometricFunctionName
) -> Fragment:
    type_map = {
        ast.TrigonometricFunctionName._Sin: "SIN",
        ast.TrigonometricFunctionName._Cos: "COS",
        ast.TrigonometricFunctionName._Tan: "TAN",
        ast.TrigonometricFunctionName._Cot: "COT",
        ast.TrigonometricFunctionName._Sinh: "SINH",
        ast.TrigonometricFunctionName._Cosh: "COSH",
        ast.TrigonometricFunctionName._Tanh: "TANH",
        ast.TrigonometricFunctionName._Asin: "ASIN",
        ast.TrigonometricFunctionName._Acos: "ACOS",
        ast.TrigonometricFunctionName._Atan: "ATAN",
        ast.TrigonometricFunctionName._Degrees: "DEGREES",
        ast.TrigonometricFunctionName._Radians: "RADIANS",
    }
    for cls, name in type_map.items():
        if isinstance(expr.trigonometric_function_name, cls):
            return Fragment(name)
    return Fragment("SIN")


# String functions


@generates(ast.Fold)
def generate_fold(gen: Generator, expr: ast.Fold) -> Fragment:
    name = "UPPER" if expr.mode == ast.Fold.Mode.UPPER else "LOWER"
    return Fragment(f"{name}({gen.dispatch(expr.character_string_value_expression)})")


@generates(ast.SubstringFunction)
def generate_substring_function(gen: Generator, expr: ast.SubstringFunction) -> Fragment:
    name = "LEFT" if expr.mode == ast.SubstringFunction.Mode.LEFT else "RIGHT"
    return Fragment(
        f"{name}({gen.dispatch(expr.character_string_value_expression)}, "
        f"{gen.dispatch(expr.string_length)})"
    )


@generates(ast.SingleCharacterTrimFunction)
def generate_single_character_trim_function(
    gen: Generator, expr: ast.SingleCharacterTrimFunction
) -> Fragment:
    return Fragment(f"TRIM({gen.dispatch(expr.trim_operands)})")


@generates(ast.TrimOperands)
def generate_trim_operands(gen: Generator, expr: ast.TrimOperands) -> Fragment:
    parts: list[str | Fragment] = []
    if expr.trim_specification_trim_character_string_from:
        tsf = expr.trim_specification_trim_character_string_from
        if tsf.trim_specification:
            parts.append(gen.dispatch(tsf.trim_specification))
        if tsf.trim_character_string:
            parts.append(gen.dispatch(tsf.trim_character_string))
        parts.append("FROM")
    parts.append(gen.dispatch(expr.trim_source))
    return gen.seq(*parts)


@generates(ast.TrimSpecification)
def generate_trim_specification(gen: Generator, expr: ast.TrimSpecification) -> Fragment:
    if isinstance(expr.trim_specification, ast.TrimSpecification._Leading):
        return Fragment("LEADING")
    elif isinstance(expr.trim_specification, ast.TrimSpecification._Trailing):
        return Fragment("TRAILING")
    return Fragment("BOTH")


@generates(ast.MultiCharacterTrimFunction)
def generate_multi_character_trim_function(
    gen: Generator, expr: ast.MultiCharacterTrimFunction
) -> Fragment:
    name_map = {
        ast.MultiCharacterTrimFunction.Mode.BTRIM: "BTRIM",
        ast.MultiCharacterTrimFunction.Mode.LTRIM: "LTRIM",
        ast.MultiCharacterTrimFunction.Mode.RTRIM: "RTRIM",
    }
    name = name_map[expr.mode]
    if expr.trim_character_string:
        return Fragment(
            f"{name}({gen.dispatch(expr.trim_source)}, {gen.dispatch(expr.trim_character_string)})"
        )
    return Fragment(f"{name}({gen.dispatch(expr.trim_source)})")


# Length expressions


@generates(ast.ByteLengthExpression)
def generate_byte_length_expression(gen: Generator, expr: ast.ByteLengthExpression) -> Fragment:
    return Fragment(f"BYTE_LENGTH({gen.dispatch(expr.byte_string_value_expression)})")


@generates(ast.CharLengthExpression)
def generate_char_length_expression(gen: Generator, expr: ast.CharLengthExpression) -> Fragment:
    return Fragment(f"CHAR_LENGTH({gen.dispatch(expr.character_string_value_expression)})")


@generates(ast.PathLengthExpression)
def generate_path_length_expression(gen: Generator, expr: ast.PathLengthExpression) -> Fragment:
    kw = gen.keyword("PATH_LENGTH")
    return Fragment(f"{kw}({gen.dispatch(expr.path_value_expression)})")


# Collection functions


@generates(ast.CardinalityExpression)
def generate_cardinality_expression(gen: Generator, expr: ast.CardinalityExpression) -> Fragment:
    inner = expr.cardinality_expression
    if isinstance(
        inner,
        ast.CardinalityExpression._CardinalityLeftParenCardinalityExpressionArgumentRightParen,
    ):
        return Fragment(f"CARDINALITY({gen.dispatch(inner.cardinality_expression_argument)})")
    else:
        return Fragment(f"SIZE({gen.dispatch(inner.list_value_expression)})")


@generates(ast.ElementsFunction)
def generate_elements_function(gen: Generator, expr: ast.ElementsFunction) -> Fragment:
    return Fragment(f"ELEMENTS({gen.dispatch(expr.path_value_expression)})")


# Cast


@generates(ast.CastSpecification)
def generate_cast_specification(gen: Generator, expr: ast.CastSpecification) -> Fragment:
    return Fragment(f"CAST({gen.dispatch(expr.cast_operand)} AS {gen.dispatch(expr.cast_target)})")


# LET value expression


@generates(ast.LetValueExpression)
def generate_let_value_expression(gen: Generator, expr: ast.LetValueExpression) -> Fragment:
    return gen.seq(
        "LET",
        gen.dispatch(expr.let_variable_definition_list),
        "IN",
        gen.dispatch(expr.value_expression),
        "END",
    )


# Element ID function


@generates(ast.ElementIdFunction)
def generate_element_id_function(gen: Generator, expr: ast.ElementIdFunction) -> Fragment:
    kw = gen.keyword("ELEMENT_ID")
    return Fragment(f"{kw}({gen.dispatch(expr.element_variable_reference)})")


# Path value constructor


@generates(ast.PathValueConstructorByEnumeration)
def generate_path_value_constructor_by_enumeration(
    gen: Generator, expr: ast.PathValueConstructorByEnumeration
) -> Fragment:
    return gen.seq("PATH", gen.brackets(gen.dispatch(expr.path_element_list)))


@generates(ast.PathElementList)
def generate_path_element_list(gen: Generator, expr: ast.PathElementList) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.path_element_list_start)]
    if expr.list_path_element_list_step:
        for step in expr.list_path_element_list_step:
            parts.append(",")
            parts.append(gen.dispatch(step.edge_reference_value_expression))
            parts.append(",")
            parts.append(gen.dispatch(step.node_reference_value_expression))
    return gen.seq(*parts)


# Temporal functions


@generates(ast.DateFunction)
def generate_date_function(gen: Generator, expr: ast.DateFunction) -> Fragment:
    if isinstance(expr.date_function, ast.DateFunction._CurrentDate):
        return Fragment("CURRENT_DATE")
    inner = expr.date_function
    if inner.date_function_parameters:
        return Fragment(f"DATE({gen.dispatch(inner.date_function_parameters)})")
    return Fragment("DATE()")


@generates(ast.TimeFunction)
def generate_time_function(gen: Generator, expr: ast.TimeFunction) -> Fragment:
    if isinstance(expr.time_function, ast.TimeFunction._CurrentTime):
        return Fragment("CURRENT_TIME")
    inner = expr.time_function
    if inner.time_function_parameters:
        return Fragment(f"ZONED_TIME({gen.dispatch(inner.time_function_parameters)})")
    return Fragment("ZONED_TIME()")


@generates(ast.DatetimeFunction)
def generate_datetime_function(gen: Generator, expr: ast.DatetimeFunction) -> Fragment:
    if isinstance(expr.datetime_function, ast.DatetimeFunction._CurrentTimestamp):
        return Fragment("CURRENT_TIMESTAMP")
    inner = expr.datetime_function
    if inner.datetime_function_parameters:
        return Fragment(f"ZONED_DATETIME({gen.dispatch(inner.datetime_function_parameters)})")
    return Fragment("ZONED_DATETIME()")


@generates(ast.LocaldatetimeFunction)
def generate_localdatetime_function(gen: Generator, expr: ast.LocaldatetimeFunction) -> Fragment:
    if isinstance(expr.localdatetime_function, ast.LocaldatetimeFunction._LocalTimestamp):
        return Fragment("LOCAL_TIMESTAMP")
    inner = expr.localdatetime_function
    if inner.datetime_function_parameters:
        return Fragment(f"LOCAL DATETIME({gen.dispatch(inner.datetime_function_parameters)})")
    return Fragment("LOCAL DATETIME()")


@generates(ast.LocaltimeFunction)
def generate_localtime_function(gen: Generator, expr: ast.LocaltimeFunction) -> Fragment:
    if expr.time_function_parameters:
        return Fragment(f"LOCAL TIME({gen.dispatch(expr.time_function_parameters)})")
    return Fragment("LOCAL TIME()")


@generates(ast.DurationFunction)
def generate_duration_function(gen: Generator, expr: ast.DurationFunction) -> Fragment:
    if expr.duration_function_parameters:
        return Fragment(f"DURATION({gen.dispatch(expr.duration_function_parameters)})")
    return Fragment("DURATION()")


@generates(ast.TemporalDurationQualifier)
def generate_temporal_duration_qualifier(
    gen: Generator, expr: ast.TemporalDurationQualifier
) -> Fragment:
    if isinstance(expr.temporal_duration_qualifier, ast.TemporalDurationQualifier._YearToMonth):
        return Fragment("YEAR TO MONTH")
    return Fragment("DAY TO SECOND")


@generates(f.Anonymous)
def generate_anonymous(gen: Generator, expr: f.Anonymous) -> Fragment:
    """Generate ``name(arg1, arg2, ...)``."""
    if expr.arguments:
        args = gen.join([gen.dispatch(a) for a in expr.arguments], sep=", ")
        return gen.seq(f"{expr.name}(", args, ")", sep="")
    return Fragment(f"{expr.name}()")
