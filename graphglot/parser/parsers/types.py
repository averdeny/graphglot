from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses, token_parser

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.OpenGraphType)
def parse_open_graph_type(parser: Parser) -> ast.OpenGraphType:
    (
        typed,
        _,
        graph,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Typed)),
        TokenType.ANY,
        parser.opt(TokenType.GRAPH),
    )
    return ast.OpenGraphType(
        typed=typed,
        graph=bool(graph),
    )


@parses(ast.OfGraphType)
def parse_of_graph_type(parser: Parser) -> ast.OfGraphType:
    def _parse__typed_graph_type_reference(
        parser: Parser,
    ) -> ast.OfGraphType._TypedGraphTypeReference:
        (
            typed,
            graph_type_reference,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.Typed)),
            parser.get_parser(ast.GraphTypeReference),
        )
        return ast.OfGraphType._TypedGraphTypeReference(
            typed=typed,
            graph_type_reference=graph_type_reference,
        )

    def _parse__typed_graph_nested_graph_type_specification(
        parser: Parser,
    ) -> ast.OfGraphType._TypedGraphNestedGraphTypeSpecification:
        (
            typed,
            graph,
            nested_graph_type_specification,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.Typed)),
            parser.opt(TokenType.GRAPH),
            parser.get_parser(ast.NestedGraphTypeSpecification),
        )
        return ast.OfGraphType._TypedGraphNestedGraphTypeSpecification(
            typed=typed,
            graph=True if graph else False,
            nested_graph_type_specification=nested_graph_type_specification,
        )

    candidates_of_graph_type = (
        parser.get_parser(ast.GraphTypeLikeGraph),
        _parse__typed_graph_type_reference,
        _parse__typed_graph_nested_graph_type_specification,
    )
    (of_graph_type,) = parser.seq(candidates_of_graph_type)
    return ast.OfGraphType(
        of_graph_type=of_graph_type,
    )


@parses(ast.CopyOfGraphType)
def parse_copy_of_graph_type(parser: Parser) -> ast.CopyOfGraphType:
    candidates_copy_of_graph_type = (
        parser.get_parser(ast.GraphTypeReference),
        parser.get_parser(ast.ExternalObjectReference),
    )
    (
        _,
        _,
        copy_of_graph_type,
    ) = parser.seq(
        TokenType.COPY,
        TokenType.OF,
        candidates_copy_of_graph_type,
    )
    return ast.CopyOfGraphType(
        copy_of_graph_type=copy_of_graph_type,
    )


@parses(ast.PropertyType)
def parse_property_type(parser: Parser) -> ast.PropertyType:
    (
        property_name,
        typed,
        property_value_type,
    ) = parser.seq(
        parser.get_parser(ast.PropertyName),
        parser.opt(parser.get_parser(ast.Typed)),
        parser.get_parser(ast.PropertyValueType),
    )
    return ast.PropertyType(
        property_name=property_name,
        typed=typed,
        property_value_type=property_value_type,
    )


@parses(ast.BindingTableType)
def parse_binding_table_type(parser: Parser) -> ast.BindingTableType:
    (
        _,
        field_types_specification,
    ) = parser.seq(
        TokenType.TABLE,
        parser.get_parser(ast.FieldTypesSpecification),
    )
    return ast.BindingTableType(
        field_types_specification=field_types_specification,
    )


@parses(ast.ValueType)
def parse_value_type(parser: Parser) -> ast.ValueType:
    # Token-based lookahead guards to prevent infinite recursion.
    # Without these, DynamicUnionType → ClosedDynamicUnionType → ComponentTypeList → ValueType
    # creates an infinite loop when no PredefinedType matches (e.g. bare DURATION, NUMERIC).
    constructed_leading = {
        TokenType.PATH,
        TokenType.GROUP,
        TokenType.LIST,
        TokenType.ARRAY,
        TokenType.RECORD,
        TokenType.LEFT_BRACE,
    }
    dynamic_union_leading = {
        TokenType.ANY,
        TokenType.PROPERTY,
        TokenType.LEFT_ANGLE_BRACKET,
    }

    candidates: list = [parser.get_parser(ast.PredefinedType)]
    # ANY can start both ConstructedValueType (ANY RECORD) and DynamicUnionType (ANY VALUE),
    # so check each independently.
    if parser._match(constructed_leading | {TokenType.ANY}):
        candidates.append(parser.get_parser(ast.ConstructedValueType))
    if parser._match(dynamic_union_leading):
        candidates.append(parser.get_parser(ast.DynamicUnionType))

    (result,) = parser.seq(tuple(candidates))
    result = t.cast(ast.ValueType, result)

    # Handle postfix <list value type>: <value type> <list value type name>
    # e.g. "INT LIST", "STRING GROUP LIST[10]"
    postfix_leading = {TokenType.LIST, TokenType.GROUP}
    while parser._match(postfix_leading):
        postfix = _try_parse_postfix_list(parser, result)
        if postfix:
            result = postfix
        else:
            break

    return result


def _try_parse_postfix_list(parser: Parser, inner: ast.ValueType) -> ast.ListValueType | None:
    """Try to parse a postfix list suffix and wrap *inner* in a ListValueType."""

    def _parse(parser: Parser) -> ast.ListValueType:
        (list_value_type_name, max_length, not_null) = parser.seq(
            parser.get_parser(ast.ListValueTypeName),
            parser.opt(
                lambda parser: parser.seq(
                    TokenType.LEFT_BRACKET,
                    parser.get_parser(ast.MaxLength),
                    TokenType.RIGHT_BRACKET,
                )[1]
            ),
            parser.opt(parser.get_parser(ast.NotNull)),
        )
        return ast.ListValueType(
            body=ast.ListValueType._ValueTypeListValueTypeName(
                value_type=inner,
                list_value_type_name=list_value_type_name,
            ),
            max_length=max_length,
            not_null=bool(not_null),
        )

    return t.cast(ast.ListValueType | None, parser.try_parse(_parse))


@parses(ast.FieldType)
def parse_field_type(parser: Parser) -> ast.FieldType:
    (
        field_name,
        typed,
        value_type,
    ) = parser.seq(
        parser.get_parser(ast.FieldName),
        parser.opt(parser.get_parser(ast.Typed)),
        parser.get_parser(ast.ValueType),
    )
    return ast.FieldType(
        field_name=field_name,
        typed=typed,
        value_type=value_type,
    )


@parses(ast.GeneralSetFunctionType)
def parse_general_set_function_type(parser: Parser) -> ast.GeneralSetFunctionType:
    _parse__avg = token_parser(TokenType.AVG, ast_type=ast.GeneralSetFunctionType._Avg)
    _parse__count = token_parser(TokenType.COUNT, ast_type=ast.GeneralSetFunctionType._Count)
    _parse__max = token_parser(TokenType.MAX, ast_type=ast.GeneralSetFunctionType._Max)
    _parse__min = token_parser(TokenType.MIN, ast_type=ast.GeneralSetFunctionType._Min)
    _parse__sum = token_parser(TokenType.SUM, ast_type=ast.GeneralSetFunctionType._Sum)
    _parse__collect_list = token_parser(
        TokenType.COLLECT_LIST, ast_type=ast.GeneralSetFunctionType._CollectList
    )
    _parse__stddev_samp = token_parser(
        TokenType.STDDEV_SAMP, ast_type=ast.GeneralSetFunctionType._StddevSamp
    )
    _parse__stddev_pop = token_parser(
        TokenType.STDDEV_POP, ast_type=ast.GeneralSetFunctionType._StddevPop
    )

    candidates_general_set_function_type = (
        _parse__avg,
        _parse__count,
        _parse__max,
        _parse__min,
        _parse__sum,
        _parse__collect_list,
        _parse__stddev_samp,
        _parse__stddev_pop,
    )
    (general_set_function_type,) = parser.seq(candidates_general_set_function_type)
    return ast.GeneralSetFunctionType(
        general_set_function_type=general_set_function_type,
    )


@parses(ast.PredefinedType)
def parse_predefined_type(parser: Parser) -> ast.PredefinedType:
    candidates_predefined_type = (
        parser.get_parser(ast.BooleanType),
        parser.get_parser(ast.CharacterStringType),
        parser.get_parser(ast.ByteStringType),
        parser.get_parser(ast.NumericType),
        parser.get_parser(ast.TemporalType),
        parser.get_parser(ast.ReferenceValueType),
        parser.get_parser(ast.ImmaterialValueType),
    )
    (result,) = parser.seq(candidates_predefined_type)
    return result


@parses(ast.ConstructedValueType)
def parse_constructed_value_type(parser: Parser) -> ast.ConstructedValueType:
    candidates_constructed_value_type = (
        parser.get_parser(ast.PathValueType),
        parser.get_parser(ast.ListValueType),
        parser.get_parser(ast.RecordType),
    )
    (result,) = parser.seq(candidates_constructed_value_type)
    return result


@parses(ast.DynamicUnionType)
def parse_dynamic_union_type(parser: Parser) -> ast.DynamicUnionType:
    candidates_dynamic_union_type = (
        parser.get_parser(ast.OpenDynamicUnionType),
        parser.get_parser(ast.DynamicPropertyValueType),
        parser.get_parser(ast.ClosedDynamicUnionType),
    )
    (result,) = parser.seq(candidates_dynamic_union_type)
    return result


@parses(ast.BooleanType)
def parse_boolean_type(parser: Parser) -> ast.BooleanType:
    (_, not_null) = parser.seq(
        TokenType.BOOL,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.BooleanType(
        not_null=bool(not_null),
    )


def _parse_helper_min_max(parser: Parser) -> tuple[ast.MinLength, ast.MaxLength]:
    """Helper function to parse:"""
    (
        _,
        min_length,
        max_length,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.opt(
            lambda parser: parser.seq(
                parser.get_parser(ast.MinLength),
                TokenType.COMMA,
            )[0]
        ),
        parser.get_parser(ast.MaxLength),
        TokenType.RIGHT_PAREN,
    )
    return min_length, max_length


@parses(ast.CharacterStringType)
def parse_character_string_type(parser: Parser) -> ast.CharacterStringType:
    def _parse__string(parser: Parser) -> ast.CharacterStringType._String:
        (
            _,
            min_max,
        ) = parser.seq(
            TokenType.STRING,
            parser.opt(_parse_helper_min_max),
        )

        return ast.CharacterStringType._String(
            min_length=min_max[0] if min_max else None,
            max_length=min_max[1] if min_max else None,
        )

    def _parse__char(parser: Parser) -> ast.CharacterStringType._Char:
        (
            _,
            fixed_length,
        ) = parser.seq(
            TokenType.CHAR,
            parser.opt(
                lambda parser: parser.seq(
                    TokenType.LEFT_PAREN,
                    parser.get_parser(ast.FixedLength),
                    TokenType.RIGHT_PAREN,
                )[1]
            ),
        )
        return ast.CharacterStringType._Char(
            fixed_length=fixed_length,
        )

    def _parse__varchar(
        parser: Parser,
    ) -> ast.CharacterStringType._Varchar:
        (
            _,
            max_length,
        ) = parser.seq(
            TokenType.VARCHAR,
            parser.opt(
                lambda parser: parser.seq(
                    TokenType.LEFT_PAREN,
                    parser.get_parser(ast.MaxLength),
                    TokenType.RIGHT_PAREN,
                )[1]
            ),
        )
        return ast.CharacterStringType._Varchar(
            max_length=max_length,
        )

    candidates_character_string_type = (
        _parse__string,
        _parse__char,
        _parse__varchar,
    )
    (
        character_string_type,
        not_null,
    ) = parser.seq(
        candidates_character_string_type,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.CharacterStringType(
        character_string_type=character_string_type,
        not_null=bool(not_null),
    )


@parses(ast.ByteStringType)
def parse_byte_string_type(parser: Parser) -> ast.ByteStringType:
    def _parse__bytes(
        parser: Parser,
    ) -> ast.ByteStringType._Bytes:
        (
            _,
            min_max,
        ) = parser.seq(
            TokenType.BYTES,
            parser.opt(_parse_helper_min_max),
        )
        return ast.ByteStringType._Bytes(
            min_length=min_max[0] if min_max else None,
            max_length=min_max[1] if min_max else None,
        )

    def _parse__binary(
        parser: Parser,
    ) -> ast.ByteStringType._Binary:
        (
            _,
            fixed_length,
        ) = parser.seq(
            TokenType.BINARY,
            parser.opt(
                lambda parser: parser.seq(
                    TokenType.LEFT_PAREN,
                    parser.get_parser(ast.FixedLength),
                    TokenType.RIGHT_PAREN,
                )[1]
            ),
        )
        return ast.ByteStringType._Binary(
            fixed_length=fixed_length,
        )

    def _parse__varbinary(
        parser: Parser,
    ) -> ast.ByteStringType._Varbinary:
        (
            _,
            max_length,
        ) = parser.seq(
            TokenType.VARBINARY,
            parser.opt(
                lambda parser: parser.seq(
                    TokenType.LEFT_PAREN,
                    parser.get_parser(ast.MaxLength),
                    TokenType.RIGHT_PAREN,
                )[1]
            ),
        )
        return ast.ByteStringType._Varbinary(
            max_length=max_length,
        )

    candidates_byte_string_type = (
        _parse__bytes,
        _parse__binary,
        _parse__varbinary,
    )
    (byte_string_type, not_null) = parser.seq(
        candidates_byte_string_type, parser.opt(parser.get_parser(ast.NotNull))
    )
    return ast.ByteStringType(
        byte_string_type=byte_string_type,
        not_null=bool(not_null),
    )


@parses(ast.NumericType)
def parse_numeric_type(parser: Parser) -> ast.NumericType:
    candidates_numeric_type = (
        parser.get_parser(ast.ExactNumericType),
        parser.get_parser(ast.ApproximateNumericType),
    )
    (result,) = parser.seq(candidates_numeric_type)
    return result


@parses(ast.TemporalType)
def parse_temporal_type(parser: Parser) -> ast.TemporalType:
    candidates_temporal_type = (
        parser.get_parser(ast.TemporalInstantType),
        parser.get_parser(ast.TemporalDurationType),
    )
    (result,) = parser.seq(candidates_temporal_type)
    return result


@parses(ast.ReferenceValueType)
def parse_reference_value_type(parser: Parser) -> ast.ReferenceValueType:
    candidates_reference_value_type = (
        parser.get_parser(ast.GraphReferenceValueType),
        parser.get_parser(ast.BindingTableReferenceValueType),
        parser.get_parser(ast.NodeReferenceValueType),
        parser.get_parser(ast.EdgeReferenceValueType),
    )
    (result,) = parser.seq(candidates_reference_value_type)
    return result


@parses(ast.ImmaterialValueType)
def parse_immaterial_value_type(parser: Parser) -> ast.ImmaterialValueType:
    candidates_immaterial_value_type = (
        parser.get_parser(ast.NullType),
        parser.get_parser(ast.EmptyType),
    )
    (result,) = parser.seq(candidates_immaterial_value_type)
    return result


@parses(ast.PathValueType)
def parse_path_value_type(parser: Parser) -> ast.PathValueType:
    (
        _,
        not_null,
    ) = parser.seq(
        TokenType.PATH,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.PathValueType(
        not_null=bool(not_null),
    )


@parses(ast.ListValueType)
def parse_list_value_type(parser: Parser) -> ast.ListValueType:
    def _parse_alternative_1(parser: Parser) -> ast.ListValueType._ListValueTypeNameValueType:
        (
            list_value_type_name,
            _,
            value_type,
            _,
        ) = parser.seq(
            parser.get_parser(ast.ListValueTypeName),
            TokenType.LEFT_ANGLE_BRACKET,
            parser.get_parser(ast.ValueType),
            TokenType.RIGHT_ANGLE_BRACKET,
        )
        return ast.ListValueType._ListValueTypeNameValueType(
            list_value_type_name=list_value_type_name,
            value_type=value_type,
        )

    def _parse_alternative_2(parser: Parser) -> ast.ListValueType._ValueTypeListValueTypeName:
        # [ <value type> ] is ignored here because of recursion. Handled in ValueType parser
        (list_value_type_name,) = parser.seq(
            parser.get_parser(ast.ListValueTypeName),
        )
        return ast.ListValueType._ValueTypeListValueTypeName(
            value_type=None,
            list_value_type_name=list_value_type_name,
        )

    candidates_body = (_parse_alternative_1, _parse_alternative_2)
    (
        body,
        max_length,
        not_null,
    ) = parser.seq(
        candidates_body,
        parser.opt(
            lambda parser: parser.seq(
                TokenType.LEFT_BRACKET,
                parser.get_parser(ast.MaxLength),
                TokenType.RIGHT_BRACKET,
            )[1]
        ),
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.ListValueType(
        body=body,
        max_length=max_length,
        not_null=bool(not_null),
    )


@parses(ast.RecordType)
def parse_record_type(parser: Parser) -> ast.RecordType:
    def _parse__any_record_not_null(parser: Parser) -> ast.RecordType._AnyRecordNotNull:
        (
            any,
            _,
            not_null,
        ) = parser.seq(
            parser.opt(TokenType.ANY),
            TokenType.RECORD,
            parser.opt(parser.get_parser(ast.NotNull)),
        )
        return ast.RecordType._AnyRecordNotNull(
            any=bool(any),
            not_null=bool(not_null),
        )

    def _parse__record_field_types_specification_not_null(
        parser: Parser,
    ) -> ast.RecordType._RecordFieldTypesSpecificationNotNull:
        (
            record,
            field_types_specification,
            not_null,
        ) = parser.seq(
            parser.opt(TokenType.RECORD),
            parser.get_parser(ast.FieldTypesSpecification),
            parser.opt(parser.get_parser(ast.NotNull)),
        )
        return ast.RecordType._RecordFieldTypesSpecificationNotNull(
            record=bool(record),
            field_types_specification=field_types_specification,
            not_null=bool(not_null),
        )

    candidates_record_type = (
        _parse__record_field_types_specification_not_null,
        _parse__any_record_not_null,
    )
    (record_type,) = parser.seq(candidates_record_type)
    return ast.RecordType(
        record_type=record_type,
    )


@parses(ast.OpenDynamicUnionType)
def parse_open_dynamic_union_type(parser: Parser) -> ast.OpenDynamicUnionType:
    (
        _,
        _,
        not_null,
    ) = parser.seq(
        TokenType.ANY,
        parser.opt(TokenType.VALUE),
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.OpenDynamicUnionType(
        not_null=bool(not_null),
    )


@parses(ast.DynamicPropertyValueType)
def parse_dynamic_property_value_type(parser: Parser) -> ast.DynamicPropertyValueType:
    (
        any,
        _,
        _,
        not_null,
    ) = parser.seq(
        parser.opt(TokenType.ANY),
        TokenType.PROPERTY,
        TokenType.VALUE,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.DynamicPropertyValueType(
        any=bool(any),
        not_null=bool(not_null),
    )


@parses(ast.ClosedDynamicUnionType)
def parse_closed_dynamic_union_type(parser: Parser) -> ast.ClosedDynamicUnionType:
    def _parse__any_value_left_angle_bracket_component_type_list_right_angle_bracket(
        parser: Parser,
    ) -> ast.ComponentTypeList:
        (
            _,
            component_type_list,
            _,
        ) = parser.seq(
            TokenType.LEFT_ANGLE_BRACKET,
            parser.get_parser(ast.ComponentTypeList),
            TokenType.RIGHT_ANGLE_BRACKET,
        )
        return component_type_list

    candidates_component_type_list = (
        _parse__any_value_left_angle_bracket_component_type_list_right_angle_bracket,
        parser.get_parser(ast.ComponentTypeList),
    )
    (
        any_value,
        component_type_list,
    ) = parser.seq(
        parser.opt(
            lambda parser: parser.seq(
                TokenType.ANY,
                parser.opt(TokenType.VALUE),
            )[0]
        ),
        candidates_component_type_list,
    )

    return ast.ClosedDynamicUnionType(
        any_value=bool(any_value),
        component_type_list=component_type_list,
    )


@parses(ast.ExactNumericType)
def parse_exact_numeric_type(parser: Parser) -> ast.ExactNumericType:
    candidates_exact_numeric_type = (
        parser.get_parser(ast.BinaryExactNumericType),
        parser.get_parser(ast.DecimalExactNumericType),
    )
    (result,) = parser.seq(candidates_exact_numeric_type)
    return result


@parses(ast.ApproximateNumericType)
def parse_approximate_numeric_type(parser: Parser) -> ast.ApproximateNumericType:
    _parse__float16 = token_parser(TokenType.FLOAT16, ast_type=ast.ApproximateNumericType._Float16)
    _parse__float32 = token_parser(TokenType.FLOAT32, ast_type=ast.ApproximateNumericType._Float32)
    _parse__float64 = token_parser(TokenType.FLOAT64, ast_type=ast.ApproximateNumericType._Float64)
    _parse__float128 = token_parser(
        TokenType.FLOAT128, ast_type=ast.ApproximateNumericType._Float128
    )
    _parse__float256 = token_parser(
        TokenType.FLOAT256, ast_type=ast.ApproximateNumericType._Float256
    )

    def _parse__float(parser: Parser) -> ast.ApproximateNumericType._Float:
        (_, precision_scale) = parser.seq(TokenType.FLOAT, parser.opt(_parse__precision_scale))
        return ast.ApproximateNumericType._Float(
            precision_scale=precision_scale,
        )

    def _parse__precision_scale(parser: Parser) -> ast.ApproximateNumericType._PrecisionScale:
        (_, precision, scale, _) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.Precision),
            parser.opt(lambda parser: parser.seq(TokenType.COMMA, parser.get_parser(ast.Scale))[1]),
            TokenType.RIGHT_PAREN,
        )
        return ast.ApproximateNumericType._PrecisionScale(
            precision=precision,
            scale=scale,
        )

    def _parse__real(parser: Parser) -> ast.ApproximateNumericType._Real:
        parser.seq(TokenType.REAL, parser.opt(parser.get_parser(ast.NotNull)))
        return ast.ApproximateNumericType._Real()

    def _parse__double_precision(parser: Parser) -> ast.ApproximateNumericType._DoublePrecision:
        parser.seq(TokenType.DOUBLE, parser.opt(parser.get_parser(ast.NotNull)))
        return ast.ApproximateNumericType._DoublePrecision()

    candidates_approximate_numeric_type = (
        _parse__float16,
        _parse__float32,
        _parse__float64,
        _parse__float128,
        _parse__float256,
        _parse__float,
        _parse__real,
        _parse__double_precision,
    )
    (approximate_numeric_type, not_null) = parser.seq(
        candidates_approximate_numeric_type,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.ApproximateNumericType(
        approximate_numeric_type=approximate_numeric_type,
        not_null=bool(not_null),
    )


@parses(ast.TemporalInstantType)
def parse_temporal_instant_type(parser: Parser) -> ast.TemporalInstantType:
    candidates_temporal_instant_type = (
        parser.get_parser(ast.DatetimeType),
        parser.get_parser(ast.LocaldatetimeType),
        parser.get_parser(ast.DateType),
        parser.get_parser(ast.TimeType),
        parser.get_parser(ast.LocaltimeType),
    )
    (result,) = parser.seq(candidates_temporal_instant_type)
    return result


@parses(ast.TemporalDurationType)
def parse_temporal_duration_type(parser: Parser) -> ast.TemporalDurationType:
    (
        _,
        _,
        temporal_duration_qualifier,
        _,
        not_null,
    ) = parser.seq(
        TokenType.DURATION,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.TemporalDurationQualifier),
        TokenType.RIGHT_PAREN,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.TemporalDurationType(
        temporal_duration_qualifier=temporal_duration_qualifier,
        not_null=bool(not_null),
    )


@parses(ast.GraphReferenceValueType)
def parse_graph_reference_value_type(parser: Parser) -> ast.GraphReferenceValueType:
    candidates_graph_reference_value_type = (
        parser.get_parser(ast.OpenGraphReferenceValueType),
        parser.get_parser(ast.ClosedGraphReferenceValueType),
    )
    (result,) = parser.seq(candidates_graph_reference_value_type)
    return result


@parses(ast.BindingTableReferenceValueType)
def parse_binding_table_reference_value_type(parser: Parser) -> ast.BindingTableReferenceValueType:
    (
        binding_table_type,
        not_null,
    ) = parser.seq(
        parser.get_parser(ast.BindingTableType),
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.BindingTableReferenceValueType(
        binding_table_type=binding_table_type,
        not_null=bool(not_null),
    )


@parses(ast.NodeReferenceValueType)
def parse_node_reference_value_type(parser: Parser) -> ast.NodeReferenceValueType:
    candidates_node_reference_value_type = (
        parser.get_parser(ast.OpenNodeReferenceValueType),
        parser.get_parser(ast.ClosedNodeReferenceValueType),
    )
    (result,) = parser.seq(candidates_node_reference_value_type)
    return result


@parses(ast.EdgeReferenceValueType)
def parse_edge_reference_value_type(parser: Parser) -> ast.EdgeReferenceValueType:
    candidates_edge_reference_value_type = (
        parser.get_parser(ast.OpenEdgeReferenceValueType),
        parser.get_parser(ast.ClosedEdgeReferenceValueType),
    )
    (result,) = parser.seq(candidates_edge_reference_value_type)
    return result


@parses(ast.NullType)
def parse_null_type(parser: Parser) -> ast.NullType:
    parser.seq(TokenType.NULL)
    return ast.NullType()


@parses(ast.EmptyType)
def parse_empty_type(parser: Parser) -> ast.EmptyType:
    def _parse__null_not_null(parser: Parser) -> ast.EmptyType._NullNotNull:
        (not_null,) = parser.seq(
            parser.get_parser(ast.NotNull),
        )
        return ast.EmptyType._NullNotNull(
            not_null=not_null,
        )

    _parse__nothing = token_parser(TokenType.NOTHING, ast_type=ast.EmptyType._Nothing)

    candidates_empty_type = (
        _parse__null_not_null,
        _parse__nothing,
    )
    (empty_type,) = parser.seq(candidates_empty_type)
    return ast.EmptyType(
        empty_type=empty_type,
    )


@parses(ast.BinaryExactNumericType)
def parse_binary_exact_numeric_type(parser: Parser) -> ast.BinaryExactNumericType:
    candidates_binary_exact_numeric_type = (
        parser.get_parser(ast.SignedBinaryExactNumericType),
        parser.get_parser(ast.UnsignedBinaryExactNumericType),
    )
    (result,) = parser.seq(candidates_binary_exact_numeric_type)
    return result


@parses(ast.DecimalExactNumericType)
def parse_decimal_exact_numeric_type(parser: Parser) -> ast.DecimalExactNumericType:
    def _parse__precision_scale(
        parser: Parser,
    ) -> ast.DecimalExactNumericType._PrecisionScale:
        """Parse ( precision [, scale] )."""
        (
            _,
            precision,
            scale,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.Precision),
            parser.opt(lambda parser: parser.seq(TokenType.COMMA, parser.get_parser(ast.Scale))[1]),
            TokenType.RIGHT_PAREN,
        )
        return ast.DecimalExactNumericType._PrecisionScale(
            precision=precision,
            scale=scale,
        )

    def _parse__decimal(parser: Parser) -> ast.DecimalExactNumericType:
        """Parse DECIMAL [ ( precision [, scale] ) ] [NOT NULL]."""
        (_, precision_scale, not_null) = parser.seq(
            TokenType.DECIMAL,
            parser.opt(_parse__precision_scale),
            parser.opt(parser.get_parser(ast.NotNull)),
        )
        return ast.DecimalExactNumericType(
            precision_scale=precision_scale,
            not_null=bool(not_null),
        )

    def _parse__dec(parser: Parser) -> ast.DecimalExactNumericType:
        """Parse DEC [ ( precision [, scale] ) ] [NOT NULL]."""
        (
            _,
            precision_scale,
            not_null,
        ) = parser.seq(
            TokenType.DEC,
            parser.opt(_parse__precision_scale),
            parser.opt(parser.get_parser(ast.NotNull)),
        )
        return ast.DecimalExactNumericType(
            precision_scale=precision_scale,
            not_null=bool(not_null),
        )

    candidates_decimal_exact_numeric_type = (
        _parse__decimal,
        _parse__dec,
    )
    (result,) = parser.seq(candidates_decimal_exact_numeric_type)
    return result


@parses(ast.DatetimeType)
def parse_datetime_type(parser: Parser) -> ast.DatetimeType:
    token_candidates = (
        lambda parser: parser.seq(TokenType.ZONED, TokenType.DATETIME),
        lambda parser: parser.seq(
            TokenType.TIMESTAMP, TokenType.WITH, TokenType.TIME, TokenType.ZONE
        ),
    )
    (
        _,
        not_null,
    ) = parser.seq(
        token_candidates,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.DatetimeType(
        not_null=bool(not_null),
    )


@parses(ast.LocaldatetimeType)
def parse_localdatetime_type(parser: Parser) -> ast.LocaldatetimeType:
    token_candidates = (
        lambda parser: parser.seq(TokenType.LOCAL, TokenType.DATETIME),
        lambda parser: parser.seq(
            TokenType.TIMESTAMP, TokenType.WITHOUT, TokenType.TIME, TokenType.ZONE
        ),
        lambda parser: parser.seq(TokenType.TIMESTAMP),
    )

    (
        _,
        not_null,
    ) = parser.seq(
        token_candidates,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.LocaldatetimeType(
        not_null=bool(not_null),
    )


@parses(ast.DateType)
def parse_date_type(parser: Parser) -> ast.DateType:
    (
        _,
        not_null,
    ) = parser.seq(
        TokenType.DATE,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.DateType(
        not_null=bool(not_null),
    )


@parses(ast.TimeType)
def parse_time_type(parser: Parser) -> ast.TimeType:
    token_candidates = (
        lambda parser: parser.seq(TokenType.ZONED, TokenType.TIME),
        lambda parser: parser.seq(TokenType.TIME, TokenType.WITH, TokenType.TIME, TokenType.ZONE),
    )

    (
        _,
        not_null,
    ) = parser.seq(
        token_candidates,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.TimeType(
        not_null=bool(not_null),
    )


@parses(ast.LocaltimeType)
def parse_localtime_type(parser: Parser) -> ast.LocaltimeType:
    token_candidates = (
        lambda parser: parser.seq(TokenType.LOCAL, TokenType.TIME),
        lambda parser: parser.seq(
            TokenType.TIME, TokenType.WITHOUT, TokenType.TIME, TokenType.ZONE
        ),
    )

    (
        _,
        not_null,
    ) = parser.seq(
        token_candidates,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.LocaltimeType(
        not_null=bool(not_null),
    )


@parses(ast.ClosedGraphReferenceValueType)
def parse_closed_graph_reference_value_type(parser: Parser) -> ast.ClosedGraphReferenceValueType:
    (
        _,
        nested_graph_type_specification,
        not_null,
    ) = parser.seq(
        TokenType.GRAPH,
        parser.get_parser(ast.NestedGraphTypeSpecification),
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.ClosedGraphReferenceValueType(
        nested_graph_type_specification=nested_graph_type_specification,
        not_null=bool(not_null),
    )


@parses(ast.OpenGraphReferenceValueType)
def parse_open_graph_reference_value_type(parser: Parser) -> ast.OpenGraphReferenceValueType:
    (
        any,
        _,
        not_null,
    ) = parser.seq(
        parser.opt(TokenType.ANY),
        TokenType.GRAPH,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.OpenGraphReferenceValueType(
        any=bool(any),
        not_null=bool(not_null),
    )


@parses(ast.ClosedNodeReferenceValueType)
def parse_closed_node_reference_value_type(parser: Parser) -> ast.ClosedNodeReferenceValueType:
    (
        node_type_specification,
        not_null,
    ) = parser.seq(
        parser.get_parser(ast.NodeTypeSpecification),
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.ClosedNodeReferenceValueType(
        node_type_specification=node_type_specification,
        not_null=bool(not_null),
    )


@parses(ast.OpenNodeReferenceValueType)
def parse_open_node_reference_value_type(parser: Parser) -> ast.OpenNodeReferenceValueType:
    (
        any,
        _,
        not_null,
    ) = parser.seq(
        parser.opt(TokenType.ANY),
        TokenType.NODE,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.OpenNodeReferenceValueType(
        any=bool(any),
        not_null=bool(not_null),
    )


@parses(ast.ClosedEdgeReferenceValueType)
def parse_closed_edge_reference_value_type(parser: Parser) -> ast.ClosedEdgeReferenceValueType:
    (
        edge_type_specification,
        not_null,
    ) = parser.seq(
        parser.get_parser(ast.EdgeTypeSpecification),
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.ClosedEdgeReferenceValueType(
        edge_type_specification=edge_type_specification,
        not_null=bool(not_null),
    )


@parses(ast.OpenEdgeReferenceValueType)
def parse_open_edge_reference_value_type(parser: Parser) -> ast.OpenEdgeReferenceValueType:
    (
        any,
        _,
        not_null,
    ) = parser.seq(
        parser.opt(TokenType.ANY),
        TokenType.EDGE,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.OpenEdgeReferenceValueType(
        any=bool(any),
        not_null=bool(not_null),
    )


@parses(ast.SignedBinaryExactNumericType)
def parse_signed_binary_exact_numeric_type(parser: Parser) -> ast.SignedBinaryExactNumericType:
    _parse__int8 = token_parser(TokenType.INT8, ast_type=ast.SignedBinaryExactNumericType._Int8)
    _parse__int16 = token_parser(TokenType.INT16, ast_type=ast.SignedBinaryExactNumericType._Int16)
    _parse__int32 = token_parser(TokenType.INT32, ast_type=ast.SignedBinaryExactNumericType._Int32)
    _parse__int64 = token_parser(TokenType.INT64, ast_type=ast.SignedBinaryExactNumericType._Int64)
    _parse__int128 = token_parser(
        TokenType.INT128, ast_type=ast.SignedBinaryExactNumericType._Int128
    )
    _parse__int256 = token_parser(
        TokenType.INT256, ast_type=ast.SignedBinaryExactNumericType._Int256
    )
    _parse__smallint = token_parser(
        TokenType.SMALLINT, ast_type=ast.SignedBinaryExactNumericType._Smallint
    )

    def _parse__int(parser: Parser) -> ast.SignedBinaryExactNumericType._Int:
        (_, precision) = parser.seq(TokenType.INT, parser.opt(_parse__int_precision))
        return ast.SignedBinaryExactNumericType._Int(
            precision=precision,
        )

    _parse__bigint = token_parser(
        TokenType.BIGINT, ast_type=ast.SignedBinaryExactNumericType._Bigint
    )

    def _parse__int_precision(parser: Parser) -> ast.Precision:
        return parser.seq(
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.Precision),
            TokenType.RIGHT_PAREN,
        )[1]

    candidates_signed_type = (
        _parse__int8,
        _parse__int16,
        _parse__int32,
        _parse__int64,
        _parse__int128,
        _parse__int256,
        _parse__smallint,
        _parse__int,
        _parse__bigint,
    )
    (signed_type, not_null) = parser.seq(
        candidates_signed_type,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.SignedBinaryExactNumericType(
        signed_type=signed_type,
        not_null=bool(not_null),
    )


@parses(ast.UnsignedBinaryExactNumericType)
def parse_unsigned_binary_exact_numeric_type(parser: Parser) -> ast.UnsignedBinaryExactNumericType:
    _parse__uint8 = token_parser(
        TokenType.UINT8, ast_type=ast.UnsignedBinaryExactNumericType._Uint8
    )
    _parse__uint16 = token_parser(
        TokenType.UINT16, ast_type=ast.UnsignedBinaryExactNumericType._Uint16
    )
    _parse__uint32 = token_parser(
        TokenType.UINT32, ast_type=ast.UnsignedBinaryExactNumericType._Uint32
    )
    _parse__uint64 = token_parser(
        TokenType.UINT64, ast_type=ast.UnsignedBinaryExactNumericType._Uint64
    )
    _parse__uint128 = token_parser(
        TokenType.UINT128, ast_type=ast.UnsignedBinaryExactNumericType._Uint128
    )
    _parse__uint256 = token_parser(
        TokenType.UINT256, ast_type=ast.UnsignedBinaryExactNumericType._Uint256
    )
    _parse__usmallint = token_parser(
        TokenType.USMALLINT, ast_type=ast.UnsignedBinaryExactNumericType._Usmallint
    )

    def _parse__uint(parser: Parser) -> ast.UnsignedBinaryExactNumericType._Uint:
        (_, precision) = parser.seq(TokenType.UINT, parser.opt(_parse__uint_precision))
        return ast.UnsignedBinaryExactNumericType._Uint(
            precision=precision,
        )

    _parse__ubigint = token_parser(
        TokenType.UBIGINT, ast_type=ast.UnsignedBinaryExactNumericType._Ubigint
    )

    def _parse__uint_precision(parser: Parser) -> ast.Precision:
        return parser.seq(
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.Precision),
            TokenType.RIGHT_PAREN,
        )[1]

    candidates_unsigned_type = (
        _parse__uint8,
        _parse__uint16,
        _parse__uint32,
        _parse__uint64,
        _parse__uint128,
        _parse__uint256,
        _parse__usmallint,
        _parse__uint,
        _parse__ubigint,
    )

    (unsigned_type, not_null) = parser.seq(
        candidates_unsigned_type,
        parser.opt(parser.get_parser(ast.NotNull)),
    )
    return ast.UnsignedBinaryExactNumericType(
        unsigned_type=unsigned_type,
        not_null=bool(not_null),
    )
