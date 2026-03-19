from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses, token_parser

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.Statement)
def parse_statement(parser: Parser) -> ast.Statement:
    candidates_statement = (
        parser.get_parser(ast.CompositeQueryStatement),
        parser.get_parser(ast.LinearCatalogModifyingStatement),
        parser.get_parser(ast.LinearDataModifyingStatement),
    )
    (result,) = parser.seq(candidates_statement)
    return result


@parses(ast.NextStatement)
def parse_next_statement(parser: Parser) -> ast.NextStatement:
    (
        _,
        yield_clause,
        statement,
    ) = parser.seq(
        parser.opt(TokenType.NEXT),
        parser.opt(parser.get_parser(ast.YieldClause)),
        parser.get_parser(ast.Statement),
    )
    return ast.NextStatement(
        yield_clause=yield_clause,
        statement=statement,
    )


@parses(ast.SimpleCatalogModifyingStatement)
def parse_simple_catalog_modifying_statement(parser: Parser) -> ast.SimpleCatalogModifyingStatement:
    candidates_simple_catalog_modifying_statement = (
        parser.get_parser(ast.PrimitiveCatalogModifyingStatement),
        parser.get_parser(ast.CallCatalogModifyingProcedureStatement),
    )
    (result,) = parser.seq(candidates_simple_catalog_modifying_statement)
    return result


@parses(ast.SimpleLinearDataAccessingStatement)
def parse_simple_linear_data_accessing_statement(
    parser: Parser,
) -> ast.SimpleLinearDataAccessingStatement:
    (list_simple_data_accessing_statement,) = parser.seq(
        parser.list_(parser.get_parser(ast.SimpleDataAccessingStatement), None),
    )
    return ast.SimpleLinearDataAccessingStatement(
        list_simple_data_accessing_statement=list_simple_data_accessing_statement,
    )


@parses(ast.SimpleDataAccessingStatement)
def parse_simple_data_accessing_statement(parser: Parser) -> ast.SimpleDataAccessingStatement:
    candidates_simple_data_accessing_statement = (
        parser.get_parser(ast.SimpleQueryStatement),
        parser.get_parser(ast.SimpleDataModifyingStatement),
    )
    (result,) = parser.seq(candidates_simple_data_accessing_statement)
    return result


@parses(ast.LinearQueryStatement)
def parse_linear_query_statement(parser: Parser) -> ast.LinearQueryStatement:
    candidates_linear_query_statement = (
        parser.get_parser(ast.AmbientLinearQueryStatement),
        parser.get_parser(ast.FocusedLinearQueryStatement),
    )
    (result,) = parser.seq(candidates_linear_query_statement)
    return result


@parses(ast.FocusedPrimitiveResultStatement)
def parse_focused_primitive_result_statement(parser: Parser) -> ast.FocusedPrimitiveResultStatement:
    (
        use_graph_clause,
        primitive_result_statement,
    ) = parser.seq(
        parser.get_parser(ast.UseGraphClause),
        parser.get_parser(ast.PrimitiveResultStatement),
    )
    return ast.FocusedPrimitiveResultStatement(
        use_graph_clause=use_graph_clause,
        primitive_result_statement=primitive_result_statement,
    )


@parses(ast.SimpleLinearQueryStatement)
def parse_simple_linear_query_statement(parser: Parser) -> ast.SimpleLinearQueryStatement:
    (list_simple_query_statement,) = parser.seq(
        parser.list_(parser.get_parser(ast.SimpleQueryStatement), None),
    )
    return ast.SimpleLinearQueryStatement(
        list_simple_query_statement=list_simple_query_statement,
    )


@parses(ast.PrimitiveResultStatement)
def parse_primitive_result_statement(parser: Parser) -> ast.PrimitiveResultStatement:
    def _parse__return_statement_order_by_and_page_statement(
        parser: Parser,
    ) -> ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement:
        (
            return_statement,
            order_by_and_page_statement,
        ) = parser.seq(
            parser.get_parser(ast.ReturnStatement),
            parser.opt(parser.get_parser(ast.OrderByAndPageStatement)),
        )
        return ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement(
            return_statement=return_statement,
            order_by_and_page_statement=order_by_and_page_statement,
        )

    _parse__finish = token_parser(TokenType.FINISH, ast_type=ast.PrimitiveResultStatement._Finish)

    candidates_primitive_result_statement = (
        _parse__return_statement_order_by_and_page_statement,
        _parse__finish,
    )
    (primitive_result_statement,) = parser.seq(candidates_primitive_result_statement)
    return ast.PrimitiveResultStatement(
        primitive_result_statement=primitive_result_statement,
    )


@parses(ast.ReturnStatement)
def parse_return_statement(parser: Parser) -> ast.ReturnStatement:
    (
        _,
        return_statement_body,
    ) = parser.seq(
        TokenType.RETURN,
        parser.get_parser(ast.ReturnStatementBody),
    )
    return ast.ReturnStatement(
        return_statement_body=return_statement_body,
    )


@parses(ast.SelectStatement)
def parse_select_statement(parser: Parser) -> ast.SelectStatement:
    def _parse__select_statement_body_with_clauses(
        parser: Parser,
    ) -> ast.SelectStatement._SelectStatementBodyWithClauses:
        (
            select_statement_body,
            where_clause,
            group_by_clause,
            having_clause,
            order_by_clause,
            offset_clause,
            limit_clause,
        ) = parser.seq(
            parser.get_parser(ast.SelectStatementBody),
            parser.opt(parser.get_parser(ast.WhereClause)),
            parser.opt(parser.get_parser(ast.GroupByClause)),
            parser.opt(parser.get_parser(ast.HavingClause)),
            parser.opt(parser.get_parser(ast.OrderByClause)),
            parser.opt(parser.get_parser(ast.OffsetClause)),
            parser.opt(parser.get_parser(ast.LimitClause)),
        )
        return ast.SelectStatement._SelectStatementBodyWithClauses(
            select_statement_body=select_statement_body,
            where_clause=where_clause,
            group_by_clause=group_by_clause,
            having_clause=having_clause,
            order_by_clause=order_by_clause,
            offset_clause=offset_clause,
            limit_clause=limit_clause,
        )

    candidates_projection = (
        parser.get_parser(ast.Asterisk),
        parser.get_parser(ast.SelectItemList),
    )

    (
        _,
        set_quantifier,
        projection,
        body,
    ) = parser.seq(
        TokenType.SELECT,
        parser.opt(parser.get_parser(ast.SetQuantifier)),
        candidates_projection,
        parser.opt(_parse__select_statement_body_with_clauses),
    )
    return ast.SelectStatement(
        set_quantifier=set_quantifier,
        projection=projection,
        body=body,
    )


@parses(ast.CallProcedureStatement)
def parse_call_procedure_statement(parser: Parser) -> ast.CallProcedureStatement:
    (
        optional,
        _,
        procedure_call,
    ) = parser.seq(
        parser.opt(TokenType.OPTIONAL),
        TokenType.CALL,
        parser.get_parser(ast.ProcedureCall),
    )
    return ast.CallProcedureStatement(
        optional=bool(optional),
        procedure_call=procedure_call,
    )


@parses(ast.LinearCatalogModifyingStatement)
def parse_linear_catalog_modifying_statement(parser: Parser) -> ast.LinearCatalogModifyingStatement:
    (list_simple_catalog_modifying_statement,) = parser.seq(
        parser.list_(parser.get_parser(ast.SimpleCatalogModifyingStatement), None),
    )
    return ast.LinearCatalogModifyingStatement(
        list_simple_catalog_modifying_statement=list_simple_catalog_modifying_statement,
    )


@parses(ast.LinearDataModifyingStatement)
def parse_linear_data_modifying_statement(parser: Parser) -> ast.LinearDataModifyingStatement:
    candidates_linear_data_modifying_statement = (
        parser.get_parser(ast.FocusedLinearDataModifyingStatement),
        parser.get_parser(ast.AmbientLinearDataModifyingStatement),
    )
    (result,) = parser.seq(candidates_linear_data_modifying_statement)
    return result


@parses(ast.PrimitiveCatalogModifyingStatement)
def parse_primitive_catalog_modifying_statement(
    parser: Parser,
) -> ast.PrimitiveCatalogModifyingStatement:
    # NOTE: The order of candidates matters. We must try the more specific
    # graph-type variants (create/drop graph type) before the generic
    # graph variants; otherwise statements like
    #   DROP GRAPH TYPE IF EXISTS my_type
    # would be consumed by DropGraphStatement and fail before
    # DropGraphTypeStatement is considered.
    candidates_primitive_catalog_modifying_statement = (
        parser.get_parser(ast.CreateSchemaStatement),
        parser.get_parser(ast.DropSchemaStatement),
        parser.get_parser(ast.CreateGraphStatement),
        parser.get_parser(ast.CreateGraphTypeStatement),
        parser.get_parser(ast.DropGraphTypeStatement),
        parser.get_parser(ast.DropGraphStatement),
    )
    (result,) = parser.seq(candidates_primitive_catalog_modifying_statement)
    return result


@parses(ast.SimpleDataModifyingStatement)
def parse_simple_data_modifying_statement(parser: Parser) -> ast.SimpleDataModifyingStatement:
    candidates_simple_data_modifying_statement = (
        parser.get_parser(ast.PrimitiveDataModifyingStatement),
        parser.get_parser(ast.CallDataModifyingProcedureStatement),
    )
    (result,) = parser.seq(candidates_simple_data_modifying_statement)
    return result


@parses(ast.SimpleQueryStatement)
def parse_simple_query_statement(parser: Parser) -> ast.SimpleQueryStatement:
    candidates_simple_query_statement = (
        parser.get_parser(ast.PrimitiveQueryStatement),
        parser.get_parser(ast.CallQueryStatement),
    )
    (result,) = parser.seq(candidates_simple_query_statement)
    return result


@parses(ast.FocusedLinearQueryStatement)
def parse_focused_linear_query_statement(parser: Parser) -> ast.FocusedLinearQueryStatement:
    def _parse__list_focused_linear_query_statement_part_focused_linear_query_and_primitive_result_statement_part(  # noqa: E501
        parser: Parser,
    ) -> ast.FocusedLinearQueryStatement._ListFocusedLinearQueryStatementPartFocusedLinearQueryAndPrimitiveResultStatementPart:  # noqa: E501
        (
            list_focused_linear_query_statement_part,
            focused_linear_query_and_primitive_result_statement_part,
        ) = parser.seq(
            parser.list_(parser.get_parser(ast.FocusedLinearQueryStatementPart), TokenType.COMMA),
            parser.get_parser(ast.FocusedLinearQueryAndPrimitiveResultStatementPart),
        )
        return ast.FocusedLinearQueryStatement._ListFocusedLinearQueryStatementPartFocusedLinearQueryAndPrimitiveResultStatementPart(  # noqa: E501
            list_focused_linear_query_statement_part=list_focused_linear_query_statement_part,
            focused_linear_query_and_primitive_result_statement_part=focused_linear_query_and_primitive_result_statement_part,
        )

    candidates_focused_linear_query_statement = (
        _parse__list_focused_linear_query_statement_part_focused_linear_query_and_primitive_result_statement_part,
        parser.get_parser(ast.FocusedPrimitiveResultStatement),
        parser.get_parser(ast.FocusedNestedQuerySpecification),
        parser.get_parser(ast.SelectStatement),
    )
    (focused_linear_query_statement,) = parser.seq(candidates_focused_linear_query_statement)
    return ast.FocusedLinearQueryStatement(
        focused_linear_query_statement=focused_linear_query_statement,
    )


@parses(ast.AmbientLinearQueryStatement)
def parse_ambient_linear_query_statement(parser: Parser) -> ast.AmbientLinearQueryStatement:
    def _parse__simple_linear_query_statement_primitive_result_statement(
        parser: Parser,
    ) -> ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement:
        (
            simple_linear_query_statement,
            primitive_result_statement,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.SimpleLinearQueryStatement)),
            parser.get_parser(ast.PrimitiveResultStatement),
        )
        return ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement(
            simple_linear_query_statement=simple_linear_query_statement,
            primitive_result_statement=primitive_result_statement,
        )

    candidates_ambient_linear_query_statement = (
        _parse__simple_linear_query_statement_primitive_result_statement,
        parser.get_parser(ast.NestedQuerySpecification),
        parser.get_parser(ast.MacroCall),
    )
    (ambient_linear_query_statement,) = parser.seq(candidates_ambient_linear_query_statement)
    return ast.AmbientLinearQueryStatement(
        ambient_linear_query_statement=ambient_linear_query_statement,
    )


@parses(ast.FocusedLinearDataModifyingStatement)
def parse_focused_linear_data_modifying_statement(
    parser: Parser,
) -> ast.FocusedLinearDataModifyingStatement:
    candidates_focused_linear_data_modifying_statement = (
        parser.get_parser(ast.FocusedLinearDataModifyingStatementBody),
        parser.get_parser(ast.FocusedNestedDataModifyingProcedureSpecification),
    )
    (result,) = parser.seq(candidates_focused_linear_data_modifying_statement)
    return result


@parses(ast.AmbientLinearDataModifyingStatement)
def parse_ambient_linear_data_modifying_statement(
    parser: Parser,
) -> ast.AmbientLinearDataModifyingStatement:
    candidates_ambient_linear_data_modifying_statement = (
        parser.get_parser(ast.AmbientLinearDataModifyingStatementBody),
        parser.get_parser(ast.NestedDataModifyingProcedureSpecification),
    )
    (result,) = parser.seq(candidates_ambient_linear_data_modifying_statement)
    return result


@parses(ast.CreateSchemaStatement)
def parse_create_schema_statement(parser: Parser) -> ast.CreateSchemaStatement:
    (
        _,
        _,
        if_not_exists,
        catalog_schema_parent_and_name,
    ) = parser.seq(
        TokenType.CREATE,
        TokenType.SCHEMA,
        parser.opt(lambda parser: parser.seq(TokenType.IF, TokenType.NOT, TokenType.EXISTS)),
        parser.get_parser(ast.CatalogSchemaParentAndName),
    )
    return ast.CreateSchemaStatement(
        if_not_exists=bool(if_not_exists),
        catalog_schema_parent_and_name=catalog_schema_parent_and_name,
    )


@parses(ast.DropSchemaStatement)
def parse_drop_schema_statement(parser: Parser) -> ast.DropSchemaStatement:
    (
        _,
        _,
        if_exists,
        catalog_schema_parent_and_name,
    ) = parser.seq(
        TokenType.DROP,
        TokenType.SCHEMA,
        parser.opt(lambda parser: parser.seq(TokenType.IF, TokenType.EXISTS)),
        parser.get_parser(ast.CatalogSchemaParentAndName),
    )
    return ast.DropSchemaStatement(
        if_exists=bool(if_exists),
        catalog_schema_parent_and_name=catalog_schema_parent_and_name,
    )


@parses(ast.CreateGraphStatement)
def parse_create_graph_statement(parser: Parser) -> ast.CreateGraphStatement:
    def _parse_create_mode(parser: Parser) -> ast.CreateGraphStatement.CreateMode:
        candidates = (
            lambda parser: parser.seq(
                TokenType.GRAPH,
                TokenType.IF,
                TokenType.NOT,
                TokenType.EXISTS,
            ),
            lambda parser: parser.seq(TokenType.GRAPH),
            lambda parser: parser.seq(
                TokenType.OR,
                TokenType.REPLACE,
                TokenType.GRAPH,
            ),
        )
        (create_mode_token,) = parser.seq(candidates)

        if len(create_mode_token) == 1:
            return ast.CreateGraphStatement.CreateMode.CREATE_GRAPH
        elif len(create_mode_token) == 4:
            return ast.CreateGraphStatement.CreateMode.CREATE_GRAPH_IF_NOT_EXISTS
        elif len(create_mode_token) == 3:
            return ast.CreateGraphStatement.CreateMode.CREATE_OR_REPLACE_GRAPH
        raise AssertionError(f"Unexpected CREATE GRAPH mode token sequence: {create_mode_token}")

    (
        _,
        create_mode,
        catalog_graph_parent_and_name,
        graph_type,
        graph_source,
    ) = parser.seq(
        TokenType.CREATE,
        _parse_create_mode,
        parser.get_parser(ast.CatalogGraphParentAndName),
        (parser.get_parser(ast.OpenGraphType), parser.get_parser(ast.OfGraphType)),
        parser.opt(parser.get_parser(ast.GraphSource)),
    )
    return ast.CreateGraphStatement(
        create_mode=create_mode,
        catalog_graph_parent_and_name=catalog_graph_parent_and_name,
        graph_type=graph_type,
        graph_source=graph_source,
    )


@parses(ast.DropGraphStatement)
def parse_drop_graph_statement(parser: Parser) -> ast.DropGraphStatement:
    (
        _,
        _,
        if_exists,
        catalog_graph_parent_and_name,
    ) = parser.seq(
        TokenType.DROP,
        TokenType.GRAPH,
        parser.opt(lambda parser: parser.seq(TokenType.IF, TokenType.EXISTS)),
        parser.get_parser(ast.CatalogGraphParentAndName),
    )
    return ast.DropGraphStatement(
        if_exists=bool(if_exists),
        catalog_graph_parent_and_name=catalog_graph_parent_and_name,
    )


@parses(ast.CreateGraphTypeStatement)
def parse_create_graph_type_statement(parser: Parser) -> ast.CreateGraphTypeStatement:
    def _parse_create_mode(parser: Parser) -> ast.CreateGraphTypeStatement.CreateMode:
        candidates = (
            lambda parser: parser.seq(
                TokenType.GRAPH,
                TokenType.TYPE,
                TokenType.IF,
                TokenType.NOT,
                TokenType.EXISTS,
            ),
            lambda parser: parser.seq(
                TokenType.GRAPH,
                TokenType.TYPE,
            ),
            lambda parser: parser.seq(
                TokenType.OR,
                TokenType.REPLACE,
                TokenType.GRAPH,
                TokenType.TYPE,
            ),
        )
        (create_mode_token,) = parser.seq(candidates)
        if len(create_mode_token) == 2:
            return ast.CreateGraphTypeStatement.CreateMode.CREATE_GRAPH_TYPE
        elif len(create_mode_token) == 5:
            return ast.CreateGraphTypeStatement.CreateMode.CREATE_GRAPH_TYPE_IF_NOT_EXISTS
        elif len(create_mode_token) == 4:
            return ast.CreateGraphTypeStatement.CreateMode.CREATE_OR_REPLACE_GRAPH_TYPE
        raise AssertionError(
            f"Unexpected CREATE GRAPH TYPE mode token sequence: {create_mode_token}"
        )

    (
        _,
        create_mode,
        catalog_graph_type_parent_and_name,
        graph_type_source,
    ) = parser.seq(
        TokenType.CREATE,
        _parse_create_mode,
        parser.get_parser(ast.CatalogGraphTypeParentAndName),
        parser.get_parser(ast.GraphTypeSource),
    )
    return ast.CreateGraphTypeStatement(
        create_mode=create_mode,
        catalog_graph_type_parent_and_name=catalog_graph_type_parent_and_name,
        graph_type_source=graph_type_source,
    )


@parses(ast.DropGraphTypeStatement)
def parse_drop_graph_type_statement(parser: Parser) -> ast.DropGraphTypeStatement:
    (
        _,
        _,
        _,
        if_exists,
        catalog_graph_type_parent_and_name,
    ) = parser.seq(
        TokenType.DROP,
        TokenType.GRAPH,
        TokenType.TYPE,
        parser.opt(lambda parser: parser.seq(TokenType.IF, TokenType.EXISTS)),
        parser.get_parser(ast.CatalogGraphTypeParentAndName),
    )
    return ast.DropGraphTypeStatement(
        if_exists=bool(if_exists),
        catalog_graph_type_parent_and_name=catalog_graph_type_parent_and_name,
    )


@parses(ast.PrimitiveDataModifyingStatement)
def parse_primitive_data_modifying_statement(parser: Parser) -> ast.PrimitiveDataModifyingStatement:
    candidates_primitive_data_modifying_statement = (
        parser.get_parser(ast.InsertStatement),
        parser.get_parser(ast.SetStatement),
        parser.get_parser(ast.RemoveStatement),
        parser.get_parser(ast.DeleteStatement),
    )
    (result,) = parser.seq(candidates_primitive_data_modifying_statement)
    return result


@parses(ast.PrimitiveQueryStatement)
def parse_primitive_query_statement(parser: Parser) -> ast.PrimitiveQueryStatement:
    candidates_primitive_query_statement = (
        parser.get_parser(ast.MatchStatement),
        parser.get_parser(ast.LetStatement),
        parser.get_parser(ast.ForStatement),
        parser.get_parser(ast.FilterStatement),
        parser.get_parser(ast.OrderByAndPageStatement),
        parser.get_parser(ast.MacroCall),
    )
    (result,) = parser.seq(candidates_primitive_query_statement)
    return result


@parses(ast.InsertStatement)
def parse_insert_statement(parser: Parser) -> ast.InsertStatement:
    (
        _,
        insert_graph_pattern,
    ) = parser.seq(
        TokenType.INSERT,
        parser.get_parser(ast.InsertGraphPattern),
    )
    return ast.InsertStatement(
        insert_graph_pattern=insert_graph_pattern,
    )


@parses(ast.SetStatement)
def parse_set_statement(parser: Parser) -> ast.SetStatement:
    (
        _,
        set_item_list,
    ) = parser.seq(
        TokenType.SET,
        parser.get_parser(ast.SetItemList),
    )
    return ast.SetStatement(
        set_item_list=set_item_list,
    )


@parses(ast.RemoveStatement)
def parse_remove_statement(parser: Parser) -> ast.RemoveStatement:
    (
        _,
        remove_item_list,
    ) = parser.seq(
        TokenType.REMOVE,
        parser.get_parser(ast.RemoveItemList),
    )
    return ast.RemoveStatement(
        remove_item_list=remove_item_list,
    )


@parses(ast.DeleteStatement)
def parse_delete_statement(parser: Parser) -> ast.DeleteStatement:
    (
        mode_token,
        _,
        delete_item_list,
    ) = parser.seq(
        parser.opt({TokenType.DETACH, TokenType.NODETACH}),
        TokenType.DELETE,
        parser.get_parser(ast.DeleteItemList),
    )

    if not mode_token:
        mode = ast.DeleteStatement.Mode.NODETACH
    else:
        match mode_token.token_type:
            case TokenType.DETACH:
                mode = ast.DeleteStatement.Mode.DETACH
            case TokenType.NODETACH:
                mode = ast.DeleteStatement.Mode.NODETACH

    return ast.DeleteStatement(
        mode=mode,
        delete_item_list=delete_item_list,
    )


@parses(ast.MatchStatement)
def parse_match_statement(parser: Parser) -> ast.MatchStatement:
    candidates_match_statement = (
        parser.get_parser(ast.SimpleMatchStatement),
        parser.get_parser(ast.OptionalMatchStatement),
    )
    (result,) = parser.seq(candidates_match_statement)
    return result


@parses(ast.FilterStatement)
def parse_filter_statement(parser: Parser) -> ast.FilterStatement:
    (
        _,
        filter_statement,
    ) = parser.seq(
        TokenType.FILTER,
        (
            parser.get_parser(ast.WhereClause),
            parser.get_parser(ast.SearchCondition),
        ),
    )
    return ast.FilterStatement(
        filter_statement=filter_statement,
    )


@parses(ast.LetStatement)
def parse_let_statement(parser: Parser) -> ast.LetStatement:
    (
        _,
        let_variable_definition_list,
    ) = parser.seq(
        TokenType.LET,
        parser.get_parser(ast.LetVariableDefinitionList),
    )
    return ast.LetStatement(
        let_variable_definition_list=let_variable_definition_list,
    )


@parses(ast.ForStatement)
def parse_for_statement(parser: Parser) -> ast.ForStatement:
    (
        _,
        for_item,
        for_ordinality_or_offset,
    ) = parser.seq(
        TokenType.FOR,
        parser.get_parser(ast.ForItem),
        parser.opt(parser.get_parser(ast.ForOrdinalityOrOffset)),
    )
    return ast.ForStatement(
        for_item=for_item,
        for_ordinality_or_offset=for_ordinality_or_offset,
    )


@parses(ast.OrderByAndPageStatement)
def parse_order_by_and_page_statement(parser: Parser) -> ast.OrderByAndPageStatement:
    def _parse__order_by_clause_offset_clause_limit_clause(
        parser: Parser,
    ) -> ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause:
        (
            order_by_clause,
            offset_clause,
            limit_clause,
        ) = parser.seq(
            parser.get_parser(ast.OrderByClause),
            parser.opt(parser.get_parser(ast.OffsetClause)),
            parser.opt(parser.get_parser(ast.LimitClause)),
        )
        return ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause(
            order_by_clause=order_by_clause,
            offset_clause=offset_clause,
            limit_clause=limit_clause,
        )

    def _parse__offset_clause_limit_clause(
        parser: Parser,
    ) -> ast.OrderByAndPageStatement._OffsetClauseLimitClause:
        (
            offset_clause,
            limit_clause,
        ) = parser.seq(
            parser.get_parser(ast.OffsetClause),
            parser.opt(parser.get_parser(ast.LimitClause)),
        )
        return ast.OrderByAndPageStatement._OffsetClauseLimitClause(
            offset_clause=offset_clause,
            limit_clause=limit_clause,
        )

    candidates_order_by_and_page_statement = (
        _parse__order_by_clause_offset_clause_limit_clause,
        _parse__offset_clause_limit_clause,
        parser.get_parser(ast.LimitClause),
    )
    (order_by_and_page_statement,) = parser.seq(candidates_order_by_and_page_statement)
    return ast.OrderByAndPageStatement(
        order_by_and_page_statement=order_by_and_page_statement,
    )


@parses(ast.SimpleMatchStatement)
def parse_simple_match_statement(parser: Parser) -> ast.SimpleMatchStatement:
    (
        _,
        graph_pattern_binding_table,
    ) = parser.seq(
        TokenType.MATCH,
        parser.get_parser(ast.GraphPatternBindingTable),
    )
    return ast.SimpleMatchStatement(
        graph_pattern_binding_table=graph_pattern_binding_table,
    )


@parses(ast.OptionalMatchStatement)
def parse_optional_match_statement(parser: Parser) -> ast.OptionalMatchStatement:
    (
        _,
        optional_operand,
    ) = parser.seq(
        TokenType.OPTIONAL,
        parser.get_parser(ast.OptionalOperand),
    )
    return ast.OptionalMatchStatement(
        optional_operand=optional_operand,
    )
