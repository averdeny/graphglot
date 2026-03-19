from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.SessionSetSchemaClause)
def parse_session_set_schema_clause(parser: Parser) -> ast.SessionSetSchemaClause:
    (
        _,
        schema_reference,
    ) = parser.seq(
        TokenType.SCHEMA,
        parser.get_parser(ast.SchemaReference),
    )
    return ast.SessionSetSchemaClause(
        schema_reference=schema_reference,
    )


@parses(ast.SessionSetGraphClause)
def parse_session_set_graph_clause(parser: Parser) -> ast.SessionSetGraphClause:
    (
        _,
        graph_expression,
    ) = parser.seq(
        # Assumption here is both PROPERTY and PROPERTY GRAPH mean the same
        TokenType.GRAPH,
        parser.get_parser(ast.GraphExpression),
    )
    return ast.SessionSetGraphClause(
        graph_expression=graph_expression,
    )


@parses(ast.SessionSetTimeZoneClause)
def parse_session_set_time_zone_clause(parser: Parser) -> ast.SessionSetTimeZoneClause:
    (
        _,
        _,
        set_time_zone_value,
    ) = parser.seq(
        TokenType.TIME,
        TokenType.ZONE,
        parser.get_parser(ast.SetTimeZoneValue),
    )
    return ast.SessionSetTimeZoneClause(
        set_time_zone_value=set_time_zone_value,
    )


@parses(ast.SessionSetParameterClause)
def parse_session_set_parameter_clause(parser: Parser) -> ast.SessionSetParameterClause:
    candidates_session_set_parameter_clause = (
        parser.get_parser(ast.SessionSetGraphParameterClause),
        parser.get_parser(ast.SessionSetBindingTableParameterClause),
        parser.get_parser(ast.SessionSetValueParameterClause),
    )
    (result,) = parser.seq(candidates_session_set_parameter_clause)
    return result


@parses(ast.HavingClause)
def parse_having_clause(parser: Parser) -> ast.HavingClause:
    (
        _,
        search_condition,
    ) = parser.seq(
        TokenType.HAVING,
        parser.get_parser(ast.SearchCondition),
    )
    return ast.HavingClause(
        search_condition=search_condition,
    )


@parses(ast.VariableScopeClause)
def parse_variable_scope_clause(parser: Parser) -> ast.VariableScopeClause:
    (
        _,
        binding_variable_reference_list,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.opt(parser.get_parser(ast.BindingVariableReferenceList)),
        TokenType.RIGHT_PAREN,
    )
    return ast.VariableScopeClause(
        binding_variable_reference_list=binding_variable_reference_list,
    )


@parses(ast.AtSchemaClause)
def parse_at_schema_clause(parser: Parser) -> ast.AtSchemaClause:
    (
        _,
        schema_reference,
    ) = parser.seq(
        TokenType.AT,
        parser.get_parser(ast.SchemaReference),
    )
    return ast.AtSchemaClause(
        schema_reference=schema_reference,
    )


@parses(ast.UseGraphClause)
def parse_use_graph_clause(parser: Parser) -> ast.UseGraphClause:
    (
        _,
        graph_expression,
    ) = parser.seq(
        TokenType.USE,
        parser.get_parser(ast.GraphExpression),
    )
    return ast.UseGraphClause(
        graph_expression=graph_expression,
    )


@parses(ast.GraphPatternYieldClause)
def parse_graph_pattern_yield_clause(parser: Parser) -> ast.GraphPatternYieldClause:
    (
        _,
        graph_pattern_yield_item_list,
    ) = parser.seq(
        TokenType.YIELD,
        parser.get_parser(ast.GraphPatternYieldItemList),
    )
    return ast.GraphPatternYieldClause(
        graph_pattern_yield_item_list=graph_pattern_yield_item_list,
    )


@parses(ast.KeepClause)
def parse_keep_clause(parser: Parser) -> ast.KeepClause:
    (
        _,
        path_pattern_prefix,
    ) = parser.seq(
        TokenType.KEEP,
        parser.get_parser(ast.PathPatternPrefix),
    )

    return ast.KeepClause(
        path_pattern_prefix=path_pattern_prefix,
    )


@parses(ast.GraphPatternWhereClause)
def parse_graph_pattern_where_clause(parser: Parser) -> ast.GraphPatternWhereClause:
    (
        _,
        search_condition,
    ) = parser.seq(
        TokenType.WHERE,
        parser.get_parser(ast.SearchCondition),
    )
    return ast.GraphPatternWhereClause(
        search_condition=search_condition,
    )


@parses(ast.ParenthesizedPathPatternWhereClause)
def parse_parenthesized_path_pattern_where_clause(
    parser: Parser,
) -> ast.ParenthesizedPathPatternWhereClause:
    (
        _,
        search_condition,
    ) = parser.seq(
        TokenType.WHERE,
        parser.get_parser(ast.SearchCondition),
    )
    return ast.ParenthesizedPathPatternWhereClause(
        search_condition=search_condition,
    )


@parses(ast.WhereClause)
def parse_where_clause(parser: Parser) -> ast.WhereClause:
    (
        _,
        search_condition,
    ) = parser.seq(
        TokenType.WHERE,
        parser.get_parser(ast.SearchCondition),
    )
    return ast.WhereClause(
        search_condition=search_condition,
    )


@parses(ast.YieldClause)
def parse_yield_clause(parser: Parser) -> ast.YieldClause:
    (
        _,
        yield_item_list,
    ) = parser.seq(
        TokenType.YIELD,
        parser.get_parser(ast.YieldItemList),
    )
    return ast.YieldClause(
        yield_item_list=yield_item_list,
    )


@parses(ast.GroupByClause)
def parse_group_by_clause(parser: Parser) -> ast.GroupByClause:
    (
        _,
        grouping_element_list,
    ) = parser.seq(
        TokenType.GROUP_BY,
        parser.get_parser(ast.GroupingElementList),
    )
    return ast.GroupByClause(
        grouping_element_list=grouping_element_list,
    )


@parses(ast.OrderByClause)
def parse_order_by_clause(parser: Parser) -> ast.OrderByClause:
    (
        _,
        sort_specification_list,
    ) = parser.seq(
        TokenType.ORDER_BY,
        parser.get_parser(ast.SortSpecificationList),
    )
    return ast.OrderByClause(
        sort_specification_list=sort_specification_list,
    )


@parses(ast.LimitClause)
def parse_limit_clause(parser: Parser) -> ast.LimitClause:
    (
        _,
        non_negative_integer_specification,
    ) = parser.seq(
        TokenType.LIMIT,
        parser.get_parser(ast.NonNegativeIntegerSpecification),
    )
    return ast.LimitClause(
        non_negative_integer_specification=non_negative_integer_specification,
    )


@parses(ast.OffsetClause)
def parse_offset_clause(parser: Parser) -> ast.OffsetClause:
    (
        _,
        non_negative_integer_specification,
    ) = parser.seq(
        TokenType.OFFSET,
        parser.get_parser(ast.NonNegativeIntegerSpecification),
    )
    return ast.OffsetClause(
        non_negative_integer_specification=non_negative_integer_specification,
    )


@parses(ast.SimpleWhenClause)
def parse_simple_when_clause(parser: Parser) -> ast.SimpleWhenClause:
    (
        _,
        when_operand_list,
        _,
        result,
    ) = parser.seq(
        TokenType.WHEN,
        parser.get_parser(ast.WhenOperandList),
        TokenType.THEN,
        parser.get_parser(ast.Result),
    )
    return ast.SimpleWhenClause(
        when_operand_list=when_operand_list,
        result=result,
    )


@parses(ast.SearchedWhenClause)
def parse_searched_when_clause(parser: Parser) -> ast.SearchedWhenClause:
    (
        _,
        search_condition,
        _,
        result,
    ) = parser.seq(
        TokenType.WHEN,
        parser.get_parser(ast.SearchCondition),
        TokenType.THEN,
        parser.get_parser(ast.Result),
    )
    return ast.SearchedWhenClause(
        search_condition=search_condition,
        result=result,
    )


@parses(ast.ElseClause)
def parse_else_clause(parser: Parser) -> ast.ElseClause:
    (
        _,
        result,
    ) = parser.seq(
        TokenType.ELSE,
        parser.get_parser(ast.Result),
    )
    return ast.ElseClause(
        result=result,
    )


@parses(ast.SessionSetGraphParameterClause)
def parse_session_set_graph_parameter_clause(parser: Parser) -> ast.SessionSetGraphParameterClause:
    (
        _,
        session_set_parameter_name,
        opt_typed_graph_initializer,
    ) = parser.seq(
        TokenType.GRAPH,
        parser.get_parser(ast.SessionSetParameterName),
        parser.get_parser(ast.OptTypedGraphInitializer),
    )
    return ast.SessionSetGraphParameterClause(
        session_set_parameter_name=session_set_parameter_name,
        opt_typed_graph_initializer=opt_typed_graph_initializer,
    )


@parses(ast.SessionSetBindingTableParameterClause)
def parse_session_set_binding_table_parameter_clause(
    parser: Parser,
) -> ast.SessionSetBindingTableParameterClause:
    (
        _,
        session_set_parameter_name,
        opt_typed_binding_table_initializer,
    ) = parser.seq(
        TokenType.TABLE,
        parser.get_parser(ast.SessionSetParameterName),
        parser.get_parser(ast.OptTypedBindingTableInitializer),
    )
    return ast.SessionSetBindingTableParameterClause(
        session_set_parameter_name=session_set_parameter_name,
        opt_typed_binding_table_initializer=opt_typed_binding_table_initializer,
    )


@parses(ast.SessionSetValueParameterClause)
def parse_session_set_value_parameter_clause(parser: Parser) -> ast.SessionSetValueParameterClause:
    (
        _,
        session_set_parameter_name,
        opt_typed_value_initializer,
    ) = parser.seq(
        TokenType.VALUE,
        parser.get_parser(ast.SessionSetParameterName),
        parser.get_parser(ast.OptTypedValueInitializer),
    )
    return ast.SessionSetValueParameterClause(
        session_set_parameter_name=session_set_parameter_name,
        opt_typed_value_initializer=opt_typed_value_initializer,
    )


@parses(ast.ElementPatternWhereClause)
def parse_element_pattern_where_clause(parser: Parser) -> ast.ElementPatternWhereClause:
    (
        _,
        search_condition,
    ) = parser.seq(
        TokenType.WHERE,
        parser.get_parser(ast.SearchCondition),
    )
    return ast.ElementPatternWhereClause(
        search_condition=search_condition,
    )
