from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses, token_parser

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.GqlProgram)
def parse_gql_program(parser: Parser) -> ast.GqlProgram:
    def _parse__program_activity_session_close_command(
        parser: Parser,
    ) -> ast.GqlProgram._ProgramActivitySessionCloseCommand:
        (
            program_activity,
            session_close_command,
        ) = parser.seq(
            parser.get_parser(ast.ProgramActivity),
            parser.opt(parser.get_parser(ast.SessionCloseCommand)),
        )
        return ast.GqlProgram._ProgramActivitySessionCloseCommand(
            program_activity=program_activity,
            session_close_command=session_close_command,
        )

    candidates_gql_program = (
        _parse__program_activity_session_close_command,
        parser.get_parser(ast.SessionCloseCommand),
    )
    (gql_program,) = parser.seq(candidates_gql_program)
    return ast.GqlProgram(
        gql_program=gql_program,
    )


@parses(ast.ProgramActivity)
def parse_program_activity(parser: Parser) -> ast.ProgramActivity:
    candidates_program_activity = (
        parser.get_parser(ast.SessionActivity),
        parser.get_parser(ast.TransactionActivity),
        parser.get_parser(ast.MacroCall),
    )
    (result,) = parser.seq(candidates_program_activity)
    return result


@parses(ast.SessionSetParameterName)
def parse_session_set_parameter_name(parser: Parser) -> ast.SessionSetParameterName:
    (
        if_not_exists,
        session_parameter_specification,
    ) = parser.seq(
        parser.opt(lambda parser: parser.seq(TokenType.IF, TokenType.NOT, TokenType.EXISTS)),
        parser.get_parser(ast.SessionParameterSpecification),
    )
    return ast.SessionSetParameterName(
        if_not_exists=bool(if_not_exists),
        session_parameter_specification=session_parameter_specification,
    )


@parses(ast.SessionResetArguments)
def parse_session_reset_arguments(parser: Parser) -> ast.SessionResetArguments:
    def _parse__all_parameters(parser: Parser) -> ast.SessionResetArguments._AllParameters:
        (
            all,
            _,
        ) = parser.seq(
            parser.opt(TokenType.ALL),
            TokenType.PARAMETERS,
        )
        return ast.SessionResetArguments._AllParameters(
            all=True if all else False,
        )

    def _parse__all_characteristics(
        parser: Parser,
    ) -> ast.SessionResetArguments._AllCharacteristics:
        (
            all,
            _,
        ) = parser.seq(
            parser.opt(TokenType.ALL),
            TokenType.CHARACTERISTICS,
        )
        return ast.SessionResetArguments._AllCharacteristics(
            all=True if all else False,
        )

    def _parse__schema(parser: Parser) -> ast.SessionResetArguments._Schema:
        (_,) = parser.seq(TokenType.SCHEMA)

        return ast.SessionResetArguments._Schema()

    def _parse__graph(parser: Parser) -> ast.SessionResetArguments._Graph:
        (_,) = parser.seq(TokenType.GRAPH)
        return ast.SessionResetArguments._Graph()

    def _parse__time_zone(parser: Parser) -> ast.SessionResetArguments._TimeZone:
        (_, _) = parser.seq(TokenType.TIME, TokenType.ZONE)
        return ast.SessionResetArguments._TimeZone()

    def _parse__parameter_session_parameter_specification(
        parser: Parser,
    ) -> ast.SessionResetArguments._ParameterSessionParameterSpecification:
        (
            parameter,
            session_parameter_specification,
        ) = parser.seq(
            parser.opt(TokenType.PARAMETER),
            parser.get_parser(ast.SessionParameterSpecification),
        )
        return ast.SessionResetArguments._ParameterSessionParameterSpecification(
            parameter=True if parameter else False,
            session_parameter_specification=session_parameter_specification,
        )

    candidates_session_reset_arguments = (
        _parse__all_parameters,
        _parse__all_characteristics,
        _parse__schema,
        _parse__graph,
        _parse__time_zone,
        _parse__parameter_session_parameter_specification,
    )
    (session_reset_arguments,) = parser.seq(candidates_session_reset_arguments)
    return ast.SessionResetArguments(
        session_reset_arguments=session_reset_arguments,
    )


@parses(ast.TransactionCharacteristics)
def parse_transaction_characteristics(parser: Parser) -> ast.TransactionCharacteristics:
    def _parse__transaction_mode(parser: Parser) -> ast.TransactionCharacteristics.TransactionMode:
        (_, mode_token) = parser.seq(
            TokenType.READ,
            {
                TokenType.ONLY,
                TokenType.WRITE,
            },
        )
        match mode_token.token_type:
            case TokenType.ONLY:
                return ast.TransactionCharacteristics.TransactionMode.READ_ONLY
            case TokenType.WRITE:
                return ast.TransactionCharacteristics.TransactionMode.READ_WRITE
        raise AssertionError(f"Unexpected transaction mode token: {mode_token.token_type}")

    (list_transaction_mode,) = parser.seq(
        parser.list_(_parse__transaction_mode, TokenType.COMMA),
    )
    return ast.TransactionCharacteristics(
        list_transaction_mode=list_transaction_mode,
    )


@parses(ast.NestedProcedureSpecification)
def parse_nested_procedure_specification(parser: Parser) -> ast.NestedProcedureSpecification:
    (
        _,
        procedure_specification,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.get_parser(ast.ProcedureSpecification),
        TokenType.RIGHT_BRACE,
    )
    return ast.NestedProcedureSpecification(
        procedure_specification=procedure_specification,
    )


@parses(ast.ProcedureSpecification)
def parse_procedure_specification(parser: Parser) -> ast.ProcedureSpecification:
    candidates_procedure_specification = (
        parser.get_parser(ast.CatalogModifyingProcedureSpecification),
        parser.get_parser(ast.DataModifyingProcedureSpecification),
        parser.get_parser(ast.QuerySpecification),
    )
    (result,) = parser.seq(candidates_procedure_specification)
    return result


@parses(ast.NestedQuerySpecification)
def parse_nested_query_specification(parser: Parser) -> ast.NestedQuerySpecification:
    (
        _,
        query_specification,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.get_parser(ast.QuerySpecification),
        TokenType.RIGHT_BRACE,
    )
    return ast.NestedQuerySpecification(
        query_specification=query_specification,
    )


@parses(ast.ProcedureBody)
def parse_procedure_body(parser: Parser) -> ast.ProcedureBody:
    (
        at_schema_clause,
        binding_variable_definition_block,
        statement_block,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.AtSchemaClause)),
        parser.opt(parser.get_parser(ast.BindingVariableDefinitionBlock)),
        parser.get_parser(ast.StatementBlock),
    )
    return ast.ProcedureBody(
        at_schema_clause=at_schema_clause,
        binding_variable_definition_block=binding_variable_definition_block,
        statement_block=statement_block,
    )


@parses(ast.BindingVariableDefinitionBlock)
def parse_binding_variable_definition_block(parser: Parser) -> ast.BindingVariableDefinitionBlock:
    (list_binding_variable_definition,) = parser.seq(
        parser.list_(parser.get_parser(ast.BindingVariableDefinition), None),
    )
    return ast.BindingVariableDefinitionBlock(
        list_binding_variable_definition=list_binding_variable_definition,
    )


@parses(ast.BindingVariableDefinition)
def parse_binding_variable_definition(parser: Parser) -> ast.BindingVariableDefinition:
    candidates_binding_variable_definition = (
        parser.get_parser(ast.GraphVariableDefinition),
        parser.get_parser(ast.BindingTableVariableDefinition),
        parser.get_parser(ast.ValueVariableDefinition),
    )
    (result,) = parser.seq(candidates_binding_variable_definition)
    return result


@parses(ast.StatementBlock)
def parse_statement_block(parser: Parser) -> ast.StatementBlock:
    def _parser_next_statement_list(parser: Parser) -> list[ast.NextStatement]:
        (next_statement_list,) = parser.seq(
            parser.list_(
                parser.get_parser(ast.NextStatement),
                None,
            ),
        )
        return next_statement_list

    (
        statement,
        list_next_statement,
    ) = parser.seq(
        parser.get_parser(ast.Statement),
        parser.opt(_parser_next_statement_list),
    )
    return ast.StatementBlock(
        statement=statement,
        list_next_statement=list_next_statement or None,
    )


@parses(ast.OptTypedGraphInitializer)
def parse_opt_typed_graph_initializer(parser: Parser) -> ast.OptTypedGraphInitializer:
    def _parse__typed_graph_reference_value_type(
        parser: Parser,
    ) -> ast.OptTypedGraphInitializer._TypedGraphReferenceValueType:
        (
            typed,
            graph_reference_value_type,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.Typed)),
            parser.get_parser(ast.GraphReferenceValueType),
        )
        return ast.OptTypedGraphInitializer._TypedGraphReferenceValueType(
            typed=typed,
            graph_reference_value_type=graph_reference_value_type,
        )

    # Optimization: Skip type parsing if the current token is '=' (EQUALS_OPERATOR)
    # since that indicates the graph initializer starts immediately.
    # This avoids deep recursion through type parsing when no type is present.
    typed_graph_reference_value_type: (
        ast.OptTypedGraphInitializer._TypedGraphReferenceValueType | None
    ) = None
    if not parser._curr or parser._curr.token_type != TokenType.EQUALS_OPERATOR:
        parsed_typed_graph_reference_value_type = parser.try_parse(
            _parse__typed_graph_reference_value_type,
        )
        typed_graph_reference_value_type = t.cast(
            ast.OptTypedGraphInitializer._TypedGraphReferenceValueType | None,
            parsed_typed_graph_reference_value_type,
        )

    (graph_initializer,) = parser.seq(
        parser.get_parser(ast.GraphInitializer),
    )
    return ast.OptTypedGraphInitializer(
        typed_graph_reference_value_type=typed_graph_reference_value_type,
        graph_initializer=graph_initializer,
    )


@parses(ast.GraphInitializer)
def parse_graph_initializer(parser: Parser) -> ast.GraphInitializer:
    (
        _,
        graph_expression,
    ) = parser.seq(
        TokenType.EQUALS_OPERATOR,
        parser.get_parser(ast.GraphExpression),
    )
    return ast.GraphInitializer(
        graph_expression=graph_expression,
    )


@parses(ast.OptTypedBindingTableInitializer)
def parse_opt_typed_binding_table_initializer(
    parser: Parser,
) -> ast.OptTypedBindingTableInitializer:
    def _parse__typed_binding_table_reference_value_type(
        parser: Parser,
    ) -> ast.OptTypedBindingTableInitializer._TypedBindingTableReferenceValueType:
        (
            typed,
            binding_table_reference_value_type,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.Typed)),
            parser.get_parser(ast.BindingTableReferenceValueType),
        )
        return ast.OptTypedBindingTableInitializer._TypedBindingTableReferenceValueType(
            typed=typed,
            binding_table_reference_value_type=binding_table_reference_value_type,
        )

    # Optimization: Skip type parsing if the current token is '=' (EQUALS_OPERATOR)
    # since that indicates the binding table initializer starts immediately.
    # This avoids deep recursion through type parsing when no type is present.
    typed_binding_table_reference_value_type: (
        ast.OptTypedBindingTableInitializer._TypedBindingTableReferenceValueType | None
    ) = None
    if not parser._curr or parser._curr.token_type != TokenType.EQUALS_OPERATOR:
        parsed_typed_binding_table_reference_value_type = parser.try_parse(
            _parse__typed_binding_table_reference_value_type,
        )
        typed_binding_table_reference_value_type = t.cast(
            ast.OptTypedBindingTableInitializer._TypedBindingTableReferenceValueType | None,
            parsed_typed_binding_table_reference_value_type,
        )

    (binding_table_initializer,) = parser.seq(
        parser.get_parser(ast.BindingTableInitializer),
    )
    return ast.OptTypedBindingTableInitializer(
        typed_binding_table_reference_value_type=typed_binding_table_reference_value_type,
        binding_table_initializer=binding_table_initializer,
    )


@parses(ast.BindingTableInitializer)
def parse_binding_table_initializer(parser: Parser) -> ast.BindingTableInitializer:
    (
        _,
        binding_table_expression,
    ) = parser.seq(
        TokenType.EQUALS_OPERATOR,
        parser.get_parser(ast.BindingTableExpression),
    )
    return ast.BindingTableInitializer(
        binding_table_expression=binding_table_expression,
    )


@parses(ast.OptTypedValueInitializer)
def parse_opt_typed_value_initializer(parser: Parser) -> ast.OptTypedValueInitializer:
    def _parse__typed_value_type(parser: Parser) -> ast.OptTypedValueInitializer._TypedValueType:
        (
            typed,
            value_type,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.Typed)),
            parser.get_parser(ast.ValueType),
        )
        return ast.OptTypedValueInitializer._TypedValueType(
            typed=typed,
            value_type=value_type,
        )

    # Optimization: Skip type parsing if the current token is '=' (EQUALS_OPERATOR)
    # since that indicates the value initializer starts immediately.
    # This avoids deep recursion through type parsing when no type is present.
    typed_value_type: ast.OptTypedValueInitializer._TypedValueType | None = None
    if not parser._curr or parser._curr.token_type != TokenType.EQUALS_OPERATOR:
        parsed_typed_value_type = parser.try_parse(_parse__typed_value_type)
        typed_value_type = t.cast(
            ast.OptTypedValueInitializer._TypedValueType | None,
            parsed_typed_value_type,
        )

    (value_initializer,) = parser.seq(
        parser.get_parser(ast.ValueInitializer),
    )
    return ast.OptTypedValueInitializer(
        typed_value_type=typed_value_type,
        value_initializer=value_initializer,
    )


@parses(ast.ValueInitializer)
def parse_value_initializer(parser: Parser) -> ast.ValueInitializer:
    (
        _,
        value_expression,
    ) = parser.seq(
        TokenType.EQUALS_OPERATOR,
        parser.get_parser(ast.ValueExpression),
    )
    return ast.ValueInitializer(
        value_expression=value_expression,
    )


@parses(ast.GraphTypeLikeGraph)
def parse_graph_type_like_graph(parser: Parser) -> ast.GraphTypeLikeGraph:
    (
        _,
        graph_expression,
    ) = parser.seq(
        TokenType.LIKE,
        parser.get_parser(ast.GraphExpression),
    )
    return ast.GraphTypeLikeGraph(
        graph_expression=graph_expression,
    )


@parses(ast.GraphSource)
def parse_graph_source(parser: Parser) -> ast.GraphSource:
    (
        _,
        _,
        _,
        graph_expression,
    ) = parser.seq(
        TokenType.AS,
        TokenType.COPY,
        TokenType.OF,
        parser.get_parser(ast.GraphExpression),
    )
    return ast.GraphSource(
        graph_expression=graph_expression,
    )


@parses(ast.GraphTypeSource)
def parse_graph_type_source(parser: Parser) -> ast.GraphTypeSource:
    def _parse__as_copy_of_graph_type(parser: Parser) -> ast.GraphTypeSource._AsCopyOfGraphType:
        (
            as_,
            copy_of_graph_type,
        ) = parser.seq(
            parser.opt(TokenType.AS),
            parser.get_parser(ast.CopyOfGraphType),
        )
        return ast.GraphTypeSource._AsCopyOfGraphType(
            as_=bool(as_),
            copy_of_graph_type=copy_of_graph_type,
        )

    def _parse__as_nested_graph_type_specification(
        parser: Parser,
    ) -> ast.GraphTypeSource._AsNestedGraphTypeSpecification:
        (
            as_,
            nested_graph_type_specification,
        ) = parser.seq(
            parser.opt(TokenType.AS),
            parser.get_parser(ast.NestedGraphTypeSpecification),
        )
        return ast.GraphTypeSource._AsNestedGraphTypeSpecification(
            as_=bool(as_),
            nested_graph_type_specification=nested_graph_type_specification,
        )

    candidates_graph_type_source = (
        _parse__as_copy_of_graph_type,
        parser.get_parser(ast.GraphTypeLikeGraph),
        _parse__as_nested_graph_type_specification,
    )
    (graph_type_source,) = parser.seq(candidates_graph_type_source)
    return ast.GraphTypeSource(
        graph_type_source=graph_type_source,
    )


@parses(ast.SetItemList)
def parse_set_item_list(parser: Parser) -> ast.SetItemList:
    (list_set_item,) = parser.seq(
        parser.list_(parser.get_parser(ast.SetItem), TokenType.COMMA),
    )
    return ast.SetItemList(
        list_set_item=list_set_item,
    )


@parses(ast.SetItem)
def parse_set_item(parser: Parser) -> ast.SetItem:
    candidates_set_item = (
        parser.get_parser(ast.SetPropertyItem),
        parser.get_parser(ast.SetAllPropertiesItem),
        parser.get_parser(ast.SetLabelItem),
    )
    (result,) = parser.seq(candidates_set_item)
    return result


@parses(ast.RemoveItemList)
def parse_remove_item_list(parser: Parser) -> ast.RemoveItemList:
    (list_remove_item,) = parser.seq(
        parser.list_(parser.get_parser(ast.RemoveItem), TokenType.COMMA),
    )
    return ast.RemoveItemList(
        list_remove_item=list_remove_item,
    )


@parses(ast.RemoveItem)
def parse_remove_item(parser: Parser) -> ast.RemoveItem:
    candidates_remove_item = (
        parser.get_parser(ast.RemovePropertyItem),
        parser.get_parser(ast.RemoveLabelItem),
    )
    (result,) = parser.seq(candidates_remove_item)
    return result


@parses(ast.DeleteItemList)
def parse_delete_item_list(parser: Parser) -> ast.DeleteItemList:
    (list_delete_item,) = parser.seq(
        parser.list_(parser.get_parser(ast.DeleteItem), TokenType.COMMA),
    )
    return ast.DeleteItemList(
        list_delete_item=list_delete_item,
    )


@parses(ast.QueryConjunction)
def parse_query_conjunction(parser: Parser) -> ast.QueryConjunction:
    def _parse__otherwise(parser: Parser) -> ast.QueryConjunction._Otherwise:
        parser.seq(TokenType.OTHERWISE)

        return ast.QueryConjunction._Otherwise()

    candidates_query_conjunction = (
        parser.get_parser(ast.SetOperator),
        _parse__otherwise,
    )
    (query_conjunction,) = parser.seq(candidates_query_conjunction)
    return ast.QueryConjunction(
        query_conjunction=query_conjunction,
    )


@parses(ast.SetOperator)
def parse_set_operator(parser: Parser) -> ast.SetOperator:
    token_options = {
        TokenType.UNION,
        TokenType.EXCEPT,
        TokenType.INTERSECT,
    }

    (
        matched_token,
        set_quantifier,
    ) = parser.seq(
        token_options,
        parser.opt(parser.get_parser(ast.SetQuantifier)),
    )

    match matched_token.token_type:
        case TokenType.UNION:
            set_operator_type = ast.SetOperator.SetOperatorType.UNION
        case TokenType.EXCEPT:
            set_operator_type = ast.SetOperator.SetOperatorType.EXCEPT
        case TokenType.INTERSECT:
            set_operator_type = ast.SetOperator.SetOperatorType.INTERSECT

    return ast.SetOperator(
        set_operator_type=set_operator_type,
        set_quantifier=set_quantifier,
    )


@parses(ast.FocusedLinearQueryStatementPart)
def parse_focused_linear_query_statement_part(
    parser: Parser,
) -> ast.FocusedLinearQueryStatementPart:
    (
        use_graph_clause,
        simple_linear_query_statement,
    ) = parser.seq(
        parser.get_parser(ast.UseGraphClause),
        parser.get_parser(ast.SimpleLinearQueryStatement),
    )
    return ast.FocusedLinearQueryStatementPart(
        use_graph_clause=use_graph_clause,
        simple_linear_query_statement=simple_linear_query_statement,
    )


@parses(ast.FocusedLinearQueryAndPrimitiveResultStatementPart)
def parse_focused_linear_query_and_primitive_result_statement_part(
    parser: Parser,
) -> ast.FocusedLinearQueryAndPrimitiveResultStatementPart:
    (
        use_graph_clause,
        simple_linear_query_statement,
        primitive_result_statement,
    ) = parser.seq(
        parser.get_parser(ast.UseGraphClause),
        parser.get_parser(ast.SimpleLinearQueryStatement),
        parser.get_parser(ast.PrimitiveResultStatement),
    )
    return ast.FocusedLinearQueryAndPrimitiveResultStatementPart(
        use_graph_clause=use_graph_clause,
        simple_linear_query_statement=simple_linear_query_statement,
        primitive_result_statement=primitive_result_statement,
    )


@parses(ast.FocusedNestedQuerySpecification)
def parse_focused_nested_query_specification(parser: Parser) -> ast.FocusedNestedQuerySpecification:
    (
        use_graph_clause,
        nested_query_specification,
    ) = parser.seq(
        parser.get_parser(ast.UseGraphClause),
        parser.get_parser(ast.NestedQuerySpecification),
    )
    return ast.FocusedNestedQuerySpecification(
        use_graph_clause=use_graph_clause,
        nested_query_specification=nested_query_specification,
    )


@parses(ast.OptionalOperand)
def parse_optional_operand(parser: Parser) -> ast.OptionalOperand:
    def _parse__match_statement_block(parser: Parser) -> ast.MatchStatementBlock:
        candidates = (
            lambda parser: parser.seq(
                TokenType.LEFT_BRACE,
                parser.get_parser(ast.MatchStatementBlock),
                TokenType.RIGHT_BRACE,
            )[1],
            lambda parser: parser.seq(
                TokenType.LEFT_PAREN,
                parser.get_parser(ast.MatchStatementBlock),
                TokenType.RIGHT_PAREN,
            )[1],
        )

        (match_statement_block,) = parser.seq(candidates)
        return match_statement_block

    candidates_optional_operand = (
        parser.get_parser(ast.SimpleMatchStatement),
        _parse__match_statement_block,
    )
    (optional_operand,) = parser.seq(candidates_optional_operand)
    return ast.OptionalOperand(
        optional_operand=optional_operand,
    )


@parses(ast.MatchStatementBlock)
def parse_match_statement_block(parser: Parser) -> ast.MatchStatementBlock:
    (list_match_statement,) = parser.seq(
        parser.list_(parser.get_parser(ast.MatchStatement), None),
    )
    return ast.MatchStatementBlock(
        list_match_statement=list_match_statement,
    )


@parses(ast.LetVariableDefinitionList)
def parse_let_variable_definition_list(parser: Parser) -> ast.LetVariableDefinitionList:
    (list_let_variable_definition,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.LetVariableDefinition),
            TokenType.COMMA,
        ),
    )
    return ast.LetVariableDefinitionList(
        list_let_variable_definition=list_let_variable_definition,
    )


@parses(ast.LetVariableDefinition)
def parse_let_variable_definition(parser: Parser) -> ast.LetVariableDefinition:
    def _parse__binding_variable_value_expression(
        parser: Parser,
    ) -> ast.LetVariableDefinition._BindingVariableValueExpression:
        (
            binding_variable,
            _,
            value_expression,
        ) = parser.seq(
            parser.get_parser(ast.BindingVariable),
            TokenType.EQUALS_OPERATOR,
            parser.get_parser(ast.ValueExpression),
        )
        return ast.LetVariableDefinition._BindingVariableValueExpression(
            binding_variable=binding_variable,
            value_expression=value_expression,
        )

    candidates_let_variable_definition = (
        parser.get_parser(ast.ValueVariableDefinition),
        _parse__binding_variable_value_expression,
    )
    (let_variable_definition,) = parser.seq(candidates_let_variable_definition)
    return ast.LetVariableDefinition(
        let_variable_definition=let_variable_definition,
    )


@parses(ast.ForItem)
def parse_for_item(parser: Parser) -> ast.ForItem:
    (
        for_item_alias,
        for_item_source,
    ) = parser.seq(
        parser.get_parser(ast.ForItemAlias),
        parser.get_parser(ast.ForItemSource),
    )
    return ast.ForItem(
        for_item_alias=for_item_alias,
        for_item_source=for_item_source,
    )


@parses(ast.ForItemAlias)
def parse_for_item_alias(parser: Parser) -> ast.ForItemAlias:
    (
        binding_variable,
        _,
    ) = parser.seq(
        parser.get_parser(ast.BindingVariable),
        TokenType.IN,
    )
    return ast.ForItemAlias(
        binding_variable=binding_variable,
    )


@parses(ast.ForOrdinalityOrOffset)
def parse_for_ordinality_or_offset(parser: Parser) -> ast.ForOrdinalityOrOffset:
    token_options_set = {
        TokenType.WITH_ORDINALITY,
        TokenType.WITH_OFFSET,
    }

    (
        mode_token,
        binding_variable,
    ) = parser.seq(
        token_options_set,
        parser.get_parser(ast.BindingVariable),
    )

    match mode_token.token_type:
        case TokenType.WITH_ORDINALITY:
            mode = ast.ForOrdinalityOrOffset.Mode.ORDINALITY
        case TokenType.WITH_OFFSET:
            mode = ast.ForOrdinalityOrOffset.Mode.OFFSET

    return ast.ForOrdinalityOrOffset(
        mode=mode,
        binding_variable=binding_variable,
    )


@parses(ast.ReturnStatementBody)
def parse_return_statement_body(parser: Parser) -> ast.ReturnStatementBody:
    def _parse__set_quantifier_asterisk_group_by_clause(
        parser: Parser,
    ) -> ast.ReturnStatementBody._SetQuantifierAsteriskGroupByClause:
        (
            set_quantifier,
            asterisk,
            group_by_clause,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.SetQuantifier)),
            parser.get_parser(ast.Asterisk),
            parser.opt(parser.get_parser(ast.GroupByClause)),
        )
        return ast.ReturnStatementBody._SetQuantifierAsteriskGroupByClause(
            set_quantifier=set_quantifier,
            asterisk=asterisk,
            group_by_clause=group_by_clause,
        )

    def _parse__set_quantifier_return_item_list_group_by_clause(
        parser: Parser,
    ) -> ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause:
        (
            set_quantifier,
            return_item_list,
            group_by_clause,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.SetQuantifier)),
            parser.get_parser(ast.ReturnItemList),
            parser.opt(parser.get_parser(ast.GroupByClause)),
        )
        return ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause(
            set_quantifier=set_quantifier,
            return_item_list=return_item_list,
            group_by_clause=group_by_clause,
        )

    _parse__no_bindings = token_parser(
        TokenType.NO, TokenType.BINDINGS, ast_type=ast.ReturnStatementBody._NoBindings
    )

    candidates_return_statement_body = (
        _parse__set_quantifier_asterisk_group_by_clause,
        _parse__set_quantifier_return_item_list_group_by_clause,
        _parse__no_bindings,
    )
    (return_statement_body,) = parser.seq(candidates_return_statement_body)
    return ast.ReturnStatementBody(
        return_statement_body=return_statement_body,
    )


@parses(ast.ReturnItemList)
def parse_return_item_list(parser: Parser) -> ast.ReturnItemList:
    (list_return_item,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.ReturnItem),
            TokenType.COMMA,
        ),
    )
    return ast.ReturnItemList(
        list_return_item=list_return_item,
    )


@parses(ast.ReturnItem)
def parse_return_item(parser: Parser) -> ast.ReturnItem:
    (
        aggregating_value_expression,
        return_item_alias,
    ) = parser.seq(
        parser.get_parser(ast.AggregatingValueExpression),
        parser.opt(parser.get_parser(ast.ReturnItemAlias)),
    )
    return ast.ReturnItem(
        aggregating_value_expression=aggregating_value_expression,
        return_item_alias=return_item_alias,
    )


@parses(ast.ReturnItemAlias)
def parse_return_item_alias(parser: Parser) -> ast.ReturnItemAlias:
    (
        _,
        identifier,
    ) = parser.seq(
        TokenType.AS,
        parser.get_parser(ast.Identifier),
    )
    return ast.ReturnItemAlias(
        identifier=identifier,
    )


@parses(ast.SelectItemList)
def parse_select_item_list(parser: Parser) -> ast.SelectItemList:
    (list_select_item,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.SelectItem),
            TokenType.COMMA,
        ),
    )
    return ast.SelectItemList(
        list_select_item=list_select_item,
    )


@parses(ast.SelectItem)
def parse_select_item(parser: Parser) -> ast.SelectItem:
    (
        aggregating_value_expression,
        select_item_alias,
    ) = parser.seq(
        parser.get_parser(ast.AggregatingValueExpression),
        parser.opt(parser.get_parser(ast.SelectItemAlias)),
    )
    return ast.SelectItem(
        aggregating_value_expression=aggregating_value_expression,
        select_item_alias=select_item_alias,
    )


@parses(ast.SelectItemAlias)
def parse_select_item_alias(parser: Parser) -> ast.SelectItemAlias:
    (
        _,
        identifier,
    ) = parser.seq(
        TokenType.AS,
        parser.get_parser(ast.Identifier),
    )
    return ast.SelectItemAlias(
        identifier=identifier,
    )


@parses(ast.SelectStatementBody)
def parse_select_statement_body(parser: Parser) -> ast.SelectStatementBody:
    candidates_select_statement_body = (
        parser.get_parser(ast.SelectGraphMatchList),
        parser.get_parser(ast.SelectQuerySpecification),
    )
    (
        _,
        select_statement_body,
    ) = parser.seq(
        TokenType.FROM,
        candidates_select_statement_body,
    )
    return ast.SelectStatementBody(
        select_statement_body=select_statement_body,
    )


@parses(ast.SelectGraphMatchList)
def parse_select_graph_match_list(parser: Parser) -> ast.SelectGraphMatchList:
    (list_select_graph_match,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.SelectGraphMatch),
            TokenType.COMMA,
        ),
    )
    return ast.SelectGraphMatchList(
        list_select_graph_match=list_select_graph_match,
    )


@parses(ast.SelectGraphMatch)
def parse_select_graph_match(parser: Parser) -> ast.SelectGraphMatch:
    (
        graph_expression,
        match_statement,
    ) = parser.seq(
        parser.get_parser(ast.GraphExpression),
        parser.get_parser(ast.MatchStatement),
    )
    return ast.SelectGraphMatch(
        graph_expression=graph_expression,
        match_statement=match_statement,
    )


@parses(ast.SelectQuerySpecification)
def parse_select_query_specification(parser: Parser) -> ast.SelectQuerySpecification:
    def _parse__graph_expression_nested_query_specification(
        parser: Parser,
    ) -> ast.SelectQuerySpecification._GraphExpressionNestedQuerySpecification:
        (
            graph_expression,
            nested_query_specification,
        ) = parser.seq(
            parser.get_parser(ast.GraphExpression),
            parser.get_parser(ast.NestedQuerySpecification),
        )
        return ast.SelectQuerySpecification._GraphExpressionNestedQuerySpecification(
            graph_expression=graph_expression,
            nested_query_specification=nested_query_specification,
        )

    candidates_select_query_specification = (
        parser.get_parser(ast.NestedQuerySpecification),
        _parse__graph_expression_nested_query_specification,
    )
    (select_query_specification,) = parser.seq(candidates_select_query_specification)
    return ast.SelectQuerySpecification(
        select_query_specification=select_query_specification,
    )


@parses(ast.ProcedureCall)
def parse_procedure_call(parser: Parser) -> ast.ProcedureCall:
    candidates_procedure_call = (
        parser.get_parser(ast.InlineProcedureCall),
        parser.get_parser(ast.NamedProcedureCall),
    )
    (result,) = parser.seq(candidates_procedure_call)
    return result


@parses(ast.BindingVariableReference)
def parse_binding_variable_reference(parser: Parser) -> ast.BindingVariableReference:
    (ident,) = parser.seq(parser.get_parser(ast.Identifier))
    return ast.BindingVariableReference(binding_variable=ident)


@parses(ast.PropertyName)
def parse_property_name(parser: Parser) -> ast.PropertyName:
    (ident,) = parser.seq(parser.get_parser(ast.Identifier))
    return ast.PropertyName(identifier=ident)


@parses(ast.BindingVariableReferenceList)
def parse_binding_variable_reference_list(parser: Parser) -> ast.BindingVariableReferenceList:
    (list_binding_variable_reference,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.BindingVariableReference),
            TokenType.COMMA,
        ),
    )
    return ast.BindingVariableReferenceList(
        list_binding_variable_reference=list_binding_variable_reference,
    )


@parses(ast.ProcedureArgumentList)
def parse_procedure_argument_list(parser: Parser) -> ast.ProcedureArgumentList:
    (list_procedure_argument,) = parser.seq(
        parser.list_(parser.get_parser(ast.ProcedureArgument), TokenType.COMMA),
    )
    return ast.ProcedureArgumentList(
        list_procedure_argument=list_procedure_argument,
    )


@parses(ast.GraphPatternBindingTable)
def parse_graph_pattern_binding_table(parser: Parser) -> ast.GraphPatternBindingTable:
    (
        graph_pattern,
        graph_pattern_yield_clause,
    ) = parser.seq(
        parser.get_parser(ast.GraphPattern),
        parser.opt(parser.get_parser(ast.GraphPatternYieldClause)),
    )
    return ast.GraphPatternBindingTable(
        graph_pattern=graph_pattern,
        graph_pattern_yield_clause=graph_pattern_yield_clause,
    )


@parses(ast.GraphPatternYieldItemList)
def parse_graph_pattern_yield_item_list(parser: Parser) -> ast.GraphPatternYieldItemList:
    _parse__no_bindings = token_parser(
        TokenType.NO, TokenType.BINDINGS, ast_type=ast.GraphPatternYieldItemList._NoBindings
    )

    candidates_graph_pattern_yield_item_list = (
        lambda parser: parser.seq(
            parser.list_(parser.get_parser(ast.GraphPatternYieldItem), TokenType.COMMA)
        )[0],
        _parse__no_bindings,
    )
    (graph_pattern_yield_item_list,) = parser.seq(candidates_graph_pattern_yield_item_list)
    return ast.GraphPatternYieldItemList(
        graph_pattern_yield_item_list=graph_pattern_yield_item_list,
    )


def parse_graph_pattern_yield_item(parser: Parser) -> ast.GraphPatternYieldItem:
    candidates_graph_pattern_yield_item = (
        parser.get_parser(ast.ElementVariableReference),
        parser.get_parser(ast.PathVariableReference),
    )
    (result,) = parser.seq(candidates_graph_pattern_yield_item)
    return result


@parses(ast.MatchMode)
def parse_match_mode(parser: Parser) -> ast.MatchMode:
    candidates_match_mode = (
        parser.get_parser(ast.RepeatableElementsMatchMode),
        parser.get_parser(ast.DifferentEdgesMatchMode),
    )
    (result,) = parser.seq(candidates_match_mode)
    return result


@parses(ast.PathPatternList)
def parse_path_pattern_list(parser: Parser) -> ast.PathPatternList:
    (list_path_pattern,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.PathPattern),
            TokenType.COMMA,
        ),
    )
    return ast.PathPatternList(
        list_path_pattern=list_path_pattern,
    )


@parses(ast.PathVariableDeclaration)
def parse_path_variable_declaration(parser: Parser) -> ast.PathVariableDeclaration:
    (
        path_variable,
        _,
    ) = parser.seq(
        parser.get_parser(ast.PathVariable),
        TokenType.EQUALS_OPERATOR,
    )
    return ast.PathVariableDeclaration(
        path_variable=path_variable,
    )


@parses(ast.InsertPathPatternList)
def parse_insert_path_pattern_list(parser: Parser) -> ast.InsertPathPatternList:
    (list_insert_path_pattern,) = parser.seq(
        parser.list_(parser.get_parser(ast.InsertPathPattern), TokenType.COMMA),
    )
    return ast.InsertPathPatternList(
        list_insert_path_pattern=list_insert_path_pattern,
    )


@parses(ast.InsertElementPatternFiller)
def parse_insert_element_pattern_filler(parser: Parser) -> ast.InsertElementPatternFiller:
    def _parse__element_variable_declaration_label_and_property_set_specification(
        parser: Parser,
    ) -> ast.InsertElementPatternFiller._ElementVariableDeclarationLabelAndPropertySetSpecification:
        (
            element_variable_declaration,
            label_and_property_set_specification,
        ) = parser.seq(
            parser.get_parser(ast.ElementVariableDeclaration),
            parser.get_parser(ast.LabelAndPropertySetSpecification),
        )
        return ast.InsertElementPatternFiller._ElementVariableDeclarationLabelAndPropertySetSpecification(  # noqa: E501
            element_variable_declaration=element_variable_declaration,
            label_and_property_set_specification=label_and_property_set_specification,
        )

    candidates_insert_element_pattern_filler = (
        _parse__element_variable_declaration_label_and_property_set_specification,  # Important to have this first # noqa: E501
        parser.get_parser(ast.ElementVariableDeclaration),
        parser.get_parser(ast.LabelAndPropertySetSpecification),
    )
    (insert_element_pattern_filler,) = parser.seq(candidates_insert_element_pattern_filler)
    return ast.InsertElementPatternFiller(
        insert_element_pattern_filler=insert_element_pattern_filler,
    )


@parses(ast.LabelAndPropertySetSpecification)
def parse_label_and_property_set_specification(
    parser: Parser,
) -> ast.LabelAndPropertySetSpecification:
    def _parse__label_set_specification_element_property_specification(
        parser: Parser,
    ) -> ast.LabelAndPropertySetSpecification._LabelSetSpecificationElementPropertySpecification:
        (
            _,
            label_set_specification,
            element_property_specification,
        ) = parser.seq(
            {TokenType.IS, TokenType.COLON},
            parser.get_parser(ast.LabelSetSpecification),
            parser.get_parser(ast.ElementPropertySpecification),
        )
        return (
            ast.LabelAndPropertySetSpecification._LabelSetSpecificationElementPropertySpecification(
                label_set_specification=label_set_specification,
                element_property_specification=element_property_specification,
            )
        )

    candidates_label_and_property_set_specification = (
        _parse__label_set_specification_element_property_specification,
        lambda parser: parser.seq(
            {TokenType.IS, TokenType.COLON}, parser.get_parser(ast.LabelSetSpecification)
        )[1],
        parser.get_parser(ast.ElementPropertySpecification),
    )
    (label_and_property_set_specification,) = parser.seq(
        candidates_label_and_property_set_specification
    )
    return ast.LabelAndPropertySetSpecification(
        label_and_property_set_specification=label_and_property_set_specification,
    )


@parses(ast.PathPatternPrefix)
def parse_path_pattern_prefix(parser: Parser) -> ast.PathPatternPrefix:
    candidates_path_pattern_prefix = (
        parser.get_parser(ast.PathModePrefix),
        parser.get_parser(ast.PathSearchPrefix),
    )
    (result,) = parser.seq(candidates_path_pattern_prefix)
    return result


@parses(ast.PathMode)
def parse_path_mode(parser: Parser) -> ast.PathMode:
    token_set = {TokenType.WALK, TokenType.TRAIL, TokenType.SIMPLE, TokenType.ACYCLIC}
    (token,) = parser.seq(token_set)

    match token.token_type:
        case TokenType.WALK:
            mode = ast.PathMode.Mode.WALK
        case TokenType.TRAIL:
            mode = ast.PathMode.Mode.TRAIL
        case TokenType.SIMPLE:
            mode = ast.PathMode.Mode.SIMPLE
        case TokenType.ACYCLIC:
            mode = ast.PathMode.Mode.ACYCLIC

    return ast.PathMode(mode=mode)


@parses(ast.ElementPatternFiller)
def parse_element_pattern_filler(parser: Parser) -> ast.ElementPatternFiller:
    (
        element_variable_declaration,
        is_label_expression,
        element_pattern_predicate,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.ElementVariableDeclaration)),
        parser.opt(parser.get_parser(ast.IsLabelExpression)),
        parser.opt(parser.get_parser(ast.ElementPatternPredicate)),
    )
    return ast.ElementPatternFiller(
        element_variable_declaration=element_variable_declaration,
        is_label_expression=is_label_expression,
        element_pattern_predicate=element_pattern_predicate,
    )


@parses(ast.ElementVariableDeclaration)
def parse_element_variable_declaration(parser: Parser) -> ast.ElementVariableDeclaration:
    (
        temp,
        element_variable,
    ) = parser.seq(
        parser.opt(TokenType.TEMP),
        parser.get_parser(ast.ElementVariable),
    )
    return ast.ElementVariableDeclaration(
        temp=bool(temp),
        element_variable=element_variable,
    )


@parses(ast.PropertyKeyValuePairList)
def parse_property_key_value_pair_list(parser: Parser) -> ast.PropertyKeyValuePairList:
    (list_property_key_value_pair,) = parser.seq(
        parser.list_(parser.get_parser(ast.PropertyKeyValuePair), TokenType.COMMA),
    )
    return ast.PropertyKeyValuePairList(
        list_property_key_value_pair=list_property_key_value_pair,
    )


@parses(ast.PropertyKeyValuePair)
def parse_property_key_value_pair(parser: Parser) -> ast.PropertyKeyValuePair:
    (
        property_name,
        _,
        value_expression,
    ) = parser.seq(
        parser.get_parser(ast.PropertyName),
        TokenType.COLON,
        parser.get_parser(ast.ValueExpression),
    )
    return ast.PropertyKeyValuePair(
        property_name=property_name,
        value_expression=value_expression,
    )


@parses(ast.SubpathVariableDeclaration)
def parse_subpath_variable_declaration(parser: Parser) -> ast.SubpathVariableDeclaration:
    (
        subpath_variable,
        _,
    ) = parser.seq(
        parser.get_parser(ast.SubpathVariable),
        TokenType.EQUALS_OPERATOR,
    )
    return ast.SubpathVariableDeclaration(
        subpath_variable=subpath_variable,
    )


@parses(ast.GraphPatternQuantifier)
def parse_graph_pattern_quantifier(parser: Parser) -> ast.GraphPatternQuantifier:
    def parser_quantifier_asterisk(parser):
        # <asterisk> is equivalent to: {0,}
        parser.seq(TokenType.ASTERISK)
        return ast.GeneralQuantifier(
            lower_bound=ast.UnsignedInteger(value=0),
            upper_bound=None,
        )

    def parser_quantifier_plus_sign(parser):
        # <plus sign> is equivalent to: {1,}
        parser.seq(TokenType.PLUS_SIGN)
        return ast.GeneralQuantifier(
            lower_bound=ast.UnsignedInteger(value=1),
            upper_bound=None,
        )

    candidates_graph_pattern_quantifier = (
        parser_quantifier_asterisk,
        parser_quantifier_plus_sign,
        parser.get_parser(ast.FixedQuantifier),
        parser.get_parser(ast.GeneralQuantifier),
    )
    (result,) = parser.seq(candidates_graph_pattern_quantifier)
    return result


@parses(ast.SimplifiedContents)
def parse_simplified_contents(parser: Parser) -> ast.SimplifiedContents:
    # Parse the first simplified term unconditionally, then decide if we are in a
    # union / multiset alternation or just a single term, analogously to
    # parse_path_pattern_expression.
    (first_term,) = parser.seq(parser.get_parser(ast.SimplifiedTerm))

    if parser._match(TokenType.MULTISET_ALTERNATION_OPERATOR):
        (
            _,
            remaining_terms,
        ) = parser.seq(
            TokenType.MULTISET_ALTERNATION_OPERATOR,
            parser.list_(
                parser.get_parser(ast.SimplifiedTerm),
                TokenType.MULTISET_ALTERNATION_OPERATOR,
            ),
        )
        return ast.SimplifiedMultisetAlternation(
            list_simplified_terms=[first_term, *remaining_terms],
        )

    if parser._match(TokenType.VERTICAL_BAR):
        (
            _,
            remaining_terms,
        ) = parser.seq(
            TokenType.VERTICAL_BAR,
            parser.list_(
                parser.get_parser(ast.SimplifiedTerm),
                TokenType.VERTICAL_BAR,
            ),
        )
        return ast.SimplifiedPathUnion(
            list_simplified_term=[first_term, *remaining_terms],
        )

    # Just a single simplified term
    return first_term


@parses(ast.YieldItemList)
def parse_yield_item_list(parser: Parser) -> ast.YieldItemList:
    (list_yield_item,) = parser.seq(
        parser.list_(parser.get_parser(ast.YieldItem), TokenType.COMMA),
    )
    return ast.YieldItemList(
        list_yield_item=list_yield_item,
    )


@parses(ast.YieldItem)
def parse_yield_item(parser: Parser) -> ast.YieldItem:
    (
        yield_item_name,
        yield_item_alias,
    ) = parser.seq(
        parser.get_parser(ast.YieldItemName),
        parser.opt(parser.get_parser(ast.YieldItemAlias)),
    )
    return ast.YieldItem(
        yield_item_name=yield_item_name,
        yield_item_alias=yield_item_alias,
    )


@parses(ast.YieldItemAlias)
def parse_yield_item_alias(parser: Parser) -> ast.YieldItemAlias:
    (
        _,
        binding_variable,
    ) = parser.seq(
        TokenType.AS,
        parser.get_parser(ast.BindingVariable),
    )
    return ast.YieldItemAlias(
        binding_variable=binding_variable,
    )


@parses(ast.GroupingElementList)
def parse_grouping_element_list(parser: Parser) -> ast.GroupingElementList:
    def _parse_grouping_element_list(parser: Parser) -> list[ast.GroupingElement]:
        (grouping_element_list,) = parser.seq(
            parser.list_(parser.get_parser(ast.GroupingElement), TokenType.COMMA),
        )
        return grouping_element_list

    candidates_grouping_element_list = (
        _parse_grouping_element_list,
        parser.get_parser(ast.EmptyGroupingSet),
    )
    (grouping_element_list,) = parser.seq(candidates_grouping_element_list)
    return ast.GroupingElementList(
        grouping_element_list=grouping_element_list,
    )


@parses(ast.EmptyGroupingSet)
def parse_empty_grouping_set(parser: Parser) -> ast.EmptyGroupingSet:
    parser.seq(
        TokenType.LEFT_PAREN,
        TokenType.RIGHT_PAREN,
    )
    return ast.EmptyGroupingSet()


@parses(ast.SortSpecificationList)
def parse_sort_specification_list(parser: Parser) -> ast.SortSpecificationList:
    (list_sort_specification,) = parser.seq(
        parser.list_(parser.get_parser(ast.SortSpecification), TokenType.COMMA),
    )
    return ast.SortSpecificationList(
        list_sort_specification=list_sort_specification,
    )


@parses(ast.SortSpecification)
def parse_sort_specification(parser: Parser) -> ast.SortSpecification:
    (
        sort_key,
        ordering_specification,
        null_ordering,
    ) = parser.seq(
        parser.get_parser(ast.SortKey),
        parser.opt(parser.get_parser(ast.OrderingSpecification)),
        parser.opt(parser.get_parser(ast.NullOrdering)),
    )
    return ast.SortSpecification(
        sort_key=sort_key,
        ordering_specification=ordering_specification,
        null_ordering=null_ordering,
    )


@parses(ast.OrderingSpecification)
def parse_ordering_specification(parser: Parser) -> ast.OrderingSpecification:
    (token,) = parser.seq({TokenType.ASC, TokenType.DESC})

    match token.token_type:
        case TokenType.ASC:
            order = ast.OrderingSpecification.Order.ASC
        case TokenType.DESC:
            order = ast.OrderingSpecification.Order.DESC

    return ast.OrderingSpecification(ordering_specification=order)


@parses(ast.NullOrdering)
def parse_null_ordering(parser: Parser) -> ast.NullOrdering:
    def _parse__null_ordering(parser: Parser) -> ast.NullOrdering.Order:
        (token,) = parser.seq({TokenType.NULLS_FIRST, TokenType.NULLS_LAST})

        match token.token_type:
            case TokenType.NULLS_FIRST:
                return ast.NullOrdering.Order.NULLS_FIRST
            case TokenType.NULLS_LAST:
                return ast.NullOrdering.Order.NULLS_LAST
        raise AssertionError(f"Unexpected null ordering token: {token.token_type}")

    (null_ordering,) = parser.seq(_parse__null_ordering)
    return ast.NullOrdering(
        null_ordering=null_ordering,
    )


@parses(ast.SchemaReference)
def parse_schema_reference(parser: Parser) -> ast.SchemaReference:
    candidates_schema_reference = (
        parser.get_parser(ast.AbsoluteCatalogSchemaReference),
        parser.get_parser(ast.RelativeCatalogSchemaReference),
        parser.get_parser(ast.ReferenceParameterSpecification),
    )
    (result,) = parser.seq(candidates_schema_reference)
    return result


@parses(ast.CatalogSchemaParentAndName)
def parse_catalog_schema_parent_and_name(parser: Parser) -> ast.CatalogSchemaParentAndName:
    (
        absolute_directory_path,
        schema_name,
    ) = parser.seq(
        parser.get_parser(ast.AbsoluteDirectoryPath),
        parser.get_parser(ast.SchemaName),
    )
    return ast.CatalogSchemaParentAndName(
        absolute_directory_path=absolute_directory_path,
        schema_name=schema_name,
    )


@parses(ast.PredefinedSchemaReference)
def parse_predefined_schema_reference(parser: Parser) -> ast.PredefinedSchemaReference:
    _parse__home_schema = token_parser(
        TokenType.HOME_SCHEMA, ast_type=ast.PredefinedSchemaReference._HomeSchema
    )
    _parse__current_schema = token_parser(
        TokenType.CURRENT_SCHEMA, ast_type=ast.PredefinedSchemaReference._CurrentSchema
    )
    _parse__period = token_parser(TokenType.PERIOD, ast_type=ast.PredefinedSchemaReference._Period)

    candidates_predefined_schema_reference = (
        _parse__home_schema,
        _parse__current_schema,
        _parse__period,
    )
    (predefined_schema_reference,) = parser.seq(candidates_predefined_schema_reference)
    return ast.PredefinedSchemaReference(
        predefined_schema_reference=predefined_schema_reference,
    )


@parses(ast.AbsoluteDirectoryPath)
def parse_absolute_directory_path(parser: Parser) -> ast.AbsoluteDirectoryPath:
    (
        _,
        simple_directory_path,
    ) = parser.seq(
        TokenType.SOLIDUS,
        parser.opt(parser.get_parser(ast.SimpleDirectoryPath)),
    )
    return ast.AbsoluteDirectoryPath(
        simple_directory_path=simple_directory_path,
    )


@parses(ast.RelativeDirectoryPath)
def parse_relative_directory_path(parser: Parser) -> ast.RelativeDirectoryPath:
    def _parser_optional_inner(parser):
        return parser.seq(
            parser.list_(part=TokenType.SOLIDUS, separator=TokenType.DOUBLE_PERIOD, min_items=0),
            parser.opt(parser.get_parser(ast.SimpleDirectoryPath)),
        )

    (
        _,
        optional_inner,
    ) = parser.seq(
        TokenType.DOUBLE_PERIOD,
        parser.opt(_parser_optional_inner),
    )

    if optional_inner is None:
        list_elements = 0
        simple_directory_path = None
    else:
        list_, simple_directory_path = optional_inner
        list_elements = len(list_) - 1 if list_ else 0

    return ast.RelativeDirectoryPath(
        up_levels=1 + list_elements,
        simple_directory_path=simple_directory_path,
    )


@parses(ast.SimpleDirectoryPath)
def parse_simple_directory_path(parser: Parser) -> ast.SimpleDirectoryPath:
    (raw_items,) = parser.seq(
        parser.list_(
            lambda parser: parser.seq(parser.get_parser(ast.DirectoryName), TokenType.SOLIDUS),
            None,
        ),
    )

    # Each element from the list parser is [DirectoryName, SOLIDUS]; we only keep the DirectoryName.
    items = [pair[0] for pair in raw_items]

    return ast.SimpleDirectoryPath(
        items=items,
    )


@parses(ast.CatalogGraphParentAndName)
def parse_catalog_graph_parent_and_name(parser: Parser) -> ast.CatalogGraphParentAndName:
    (
        catalog_object_parent_reference,
        graph_name,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.CatalogObjectParentReference)),
        parser.get_parser(ast.GraphName),
    )
    return ast.CatalogGraphParentAndName(
        catalog_object_parent_reference=catalog_object_parent_reference,
        graph_name=graph_name,
    )


@parses(ast.HomeGraph)
def parse_home_graph(parser: Parser) -> ast.HomeGraph:
    parser.seq(TokenType.HOME_GRAPH)
    return ast.HomeGraph()


@parses(ast.GraphTypeReference)
def parse_graph_type_reference(parser: Parser) -> ast.GraphTypeReference:
    candidates_graph_type_reference = (
        parser.get_parser(ast.CatalogGraphTypeParentAndName),
        parser.get_parser(ast.ReferenceParameterSpecification),
    )
    (result,) = parser.seq(candidates_graph_type_reference)
    return result


@parses(ast.CatalogBindingTableParentAndName)
def parse_catalog_binding_table_parent_and_name(
    parser: Parser,
) -> ast.CatalogBindingTableParentAndName:
    (
        catalog_object_parent_reference,
        binding_table_name,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.CatalogObjectParentReference)),
        parser.get_parser(ast.BindingTableName),
    )
    return ast.CatalogBindingTableParentAndName(
        catalog_object_parent_reference=catalog_object_parent_reference,
        binding_table_name=binding_table_name,
    )


@parses(ast.ProcedureReference)
def parse_procedure_reference(parser: Parser) -> ast.ProcedureReference:
    candidates_procedure_reference = (
        parser.get_parser(ast.CatalogProcedureParentAndName),
        parser.get_parser(ast.ReferenceParameterSpecification),
    )
    (result,) = parser.seq(candidates_procedure_reference)
    return result


@parses(ast.CatalogObjectParentReference)
def parse_catalog_object_parent_reference(parser: Parser) -> ast.CatalogObjectParentReference:
    def _parser_list_object_name(parser: Parser) -> list[ast.ObjectName] | None:
        (list_expr,) = parser.seq(
            parser.list_(
                lambda parser: parser.seq(parser.get_parser(ast.ObjectName), TokenType.PERIOD),
                None,
            )
        )

        return [object_name for object_name, _ in list_expr] if list_expr else None

    def _parse__schema_reference_solidus_list_object_name(
        parser: Parser,
    ) -> ast.CatalogObjectParentReference._SchemaReferenceSolidusListObjectName:
        (
            schema_reference,
            solidus,
            list_object_name,
        ) = parser.seq(
            parser.get_parser(ast.SchemaReference),
            parser.opt(TokenType.SOLIDUS),
            parser.opt(_parser_list_object_name),
        )

        return ast.CatalogObjectParentReference._SchemaReferenceSolidusListObjectName(
            schema_reference=schema_reference,
            solidus=bool(solidus),
            list_object_name=list_object_name,
        )

    candidates_catalog_object_parent_reference = (
        _parser_list_object_name,
        _parse__schema_reference_solidus_list_object_name,
    )
    (catalog_object_parent_reference,) = parser.seq(candidates_catalog_object_parent_reference)

    return ast.CatalogObjectParentReference(
        catalog_object_parent_reference=catalog_object_parent_reference,
    )


@parses(ast.ExternalObjectReference)
def parse_external_object_reference(parser: Parser) -> ast.ExternalObjectReference:
    """
    Per the spec, an external object reference is a URI (a character string
    literal containing a colon). URI validation is done by the AST class.
    """
    (uri,) = parser.seq(parser.get_parser(ast.CharacterStringLiteral))
    return ast.ExternalObjectReference(uri=uri)


@parses(ast.NestedGraphTypeSpecification)
def parse_nested_graph_type_specification(parser: Parser) -> ast.NestedGraphTypeSpecification:
    (
        _,
        graph_type_specification_body,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.get_parser(ast.GraphTypeSpecificationBody),
        TokenType.RIGHT_BRACE,
    )
    return ast.NestedGraphTypeSpecification(
        graph_type_specification_body=graph_type_specification_body,
    )


@parses(ast.ElementTypeList)
def parse_element_type_list(parser: Parser) -> ast.ElementTypeList:
    (list_element_type_specification,) = parser.seq(
        parser.list_(parser.get_parser(ast.ElementTypeSpecification), TokenType.COMMA),
    )
    return ast.ElementTypeList(
        list_element_type_specification=list_element_type_specification,
    )


@parses(ast.ElementTypeSpecification)
def parse_element_type_specification(parser: Parser) -> ast.ElementTypeSpecification:
    # NOTE: EdgeTypeSpecification must be tried before NodeTypeSpecification because
    # edge type patterns like (a)-[:Knows]->(b) start with a node pattern (a) that would
    # be incorrectly consumed by NodeTypeSpecification if tried first.
    candidates_element_type_specification = (
        parser.get_parser(ast.EdgeTypeSpecification),
        parser.get_parser(ast.NodeTypeSpecification),
    )
    (result,) = parser.seq(candidates_element_type_specification)
    return result


@parses(ast.NodeTypePhraseFiller)
def parse_node_type_phrase_filler(parser: Parser) -> ast.NodeTypePhraseFiller:
    def _parse__node_type_name_node_type_filler(
        parser: Parser,
    ) -> ast.NodeTypePhraseFiller._NodeTypeNameNodeTypeFiller:
        (
            node_type_name,
            node_type_filler,
        ) = parser.seq(
            parser.get_parser(ast.NodeTypeName),
            parser.opt(parser.get_parser(ast.NodeTypeFiller)),
        )
        return ast.NodeTypePhraseFiller._NodeTypeNameNodeTypeFiller(
            node_type_name=node_type_name,
            node_type_filler=node_type_filler,
        )

    candidates_node_type_phrase_filler = (
        _parse__node_type_name_node_type_filler,
        parser.get_parser(ast.NodeTypeFiller),
    )
    (node_type_phrase_filler,) = parser.seq(candidates_node_type_phrase_filler)
    return ast.NodeTypePhraseFiller(
        node_type_phrase_filler=node_type_phrase_filler,
    )


@parses(ast.NodeTypeFiller)
def parse_node_type_filler(parser: Parser) -> ast.NodeTypeFiller:
    def _parse__node_type_key_label_set_node_type_implied_content(
        parser: Parser,
    ) -> ast.NodeTypeFiller._NodeTypeKeyLabelSetNodeTypeImpliedContent:
        (
            node_type_key_label_set,
            node_type_implied_content,
        ) = parser.seq(
            parser.get_parser(ast.NodeTypeKeyLabelSet),
            parser.opt(parser.get_parser(ast.NodeTypeImpliedContent)),
        )
        return ast.NodeTypeFiller._NodeTypeKeyLabelSetNodeTypeImpliedContent(
            node_type_key_label_set=node_type_key_label_set,
            node_type_implied_content=node_type_implied_content,
        )

    candidates_node_type_filler = (
        _parse__node_type_key_label_set_node_type_implied_content,
        parser.get_parser(ast.NodeTypeImpliedContent),
    )
    (node_type_filler,) = parser.seq(candidates_node_type_filler)
    return ast.NodeTypeFiller(
        node_type_filler=node_type_filler,
    )


@parses(ast.NodeTypeImpliedContent)
def parse_node_type_implied_content(parser: Parser) -> ast.NodeTypeImpliedContent:
    def _parse__node_type_label_set_node_type_property_types(
        parser: Parser,
    ) -> ast.NodeTypeImpliedContent._NodeTypeLabelSetNodeTypePropertyTypes:
        (
            node_type_label_set,
            node_type_property_types,
        ) = parser.seq(
            parser.get_parser(ast.NodeTypeLabelSet),
            parser.get_parser(ast.NodeTypePropertyTypes),
        )
        return ast.NodeTypeImpliedContent._NodeTypeLabelSetNodeTypePropertyTypes(
            node_type_label_set=node_type_label_set,
            node_type_property_types=node_type_property_types,
        )

    candidates_node_type_implied_content = (
        _parse__node_type_label_set_node_type_property_types,  # Order here matters
        parser.get_parser(ast.NodeTypeLabelSet),
        parser.get_parser(ast.NodeTypePropertyTypes),
    )
    (node_type_implied_content,) = parser.seq(candidates_node_type_implied_content)
    return ast.NodeTypeImpliedContent(
        node_type_implied_content=node_type_implied_content,
    )


@parses(ast.NodeTypeKeyLabelSet)
def parse_node_type_key_label_set(parser: Parser) -> ast.NodeTypeKeyLabelSet:
    (
        label_set_phrase,
        _,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.LabelSetPhrase)),
        {TokenType.IMPLIES, TokenType.RIGHT_DOUBLE_ARROW},
    )
    return ast.NodeTypeKeyLabelSet(
        label_set_phrase=label_set_phrase,
    )


@parses(ast.EdgeTypePhraseFiller)
def parse_edge_type_phrase_filler(parser: Parser) -> ast.EdgeTypePhraseFiller:
    def _parse__edge_type_name_edge_type_filler(
        parser: Parser,
    ) -> ast.EdgeTypePhraseFiller._EdgeTypeNameEdgeTypeFiller:
        (
            edge_type_name,
            edge_type_filler,
        ) = parser.seq(
            parser.get_parser(ast.EdgeTypeName),
            parser.opt(parser.get_parser(ast.EdgeTypeFiller)),
        )
        return ast.EdgeTypePhraseFiller._EdgeTypeNameEdgeTypeFiller(
            edge_type_name=edge_type_name,
            edge_type_filler=edge_type_filler,
        )

    candidates_edge_type_phrase_filler = (
        _parse__edge_type_name_edge_type_filler,
        parser.get_parser(ast.EdgeTypeFiller),
    )
    (edge_type_phrase_filler,) = parser.seq(candidates_edge_type_phrase_filler)
    return ast.EdgeTypePhraseFiller(
        edge_type_phrase_filler=edge_type_phrase_filler,
    )


@parses(ast.EdgeTypeFiller)
def parse_edge_type_filler(parser: Parser) -> ast.EdgeTypeFiller:
    def _parse__edge_type_key_label_set_edge_type_implied_content(
        parser: Parser,
    ) -> ast.EdgeTypeFiller._EdgeTypeKeyLabelSetEdgeTypeImpliedContent:
        (
            edge_type_key_label_set,
            edge_type_implied_content,
        ) = parser.seq(
            parser.get_parser(ast.EdgeTypeKeyLabelSet),
            parser.opt(parser.get_parser(ast.EdgeTypeImpliedContent)),
        )
        return ast.EdgeTypeFiller._EdgeTypeKeyLabelSetEdgeTypeImpliedContent(
            edge_type_key_label_set=edge_type_key_label_set,
            edge_type_implied_content=edge_type_implied_content,
        )

    candidates_edge_type_filler = (
        _parse__edge_type_key_label_set_edge_type_implied_content,
        parser.get_parser(ast.EdgeTypeImpliedContent),
    )
    (edge_type_filler,) = parser.seq(candidates_edge_type_filler)
    return ast.EdgeTypeFiller(
        edge_type_filler=edge_type_filler,
    )


@parses(ast.EdgeTypeImpliedContent)
def parse_edge_type_implied_content(parser: Parser) -> ast.EdgeTypeImpliedContent:
    def _parse__edge_type_label_set_edge_type_property_types(
        parser: Parser,
    ) -> ast.EdgeTypeImpliedContent._EdgeTypeLabelSetEdgeTypePropertyTypes:
        (
            edge_type_label_set,
            edge_type_property_types,
        ) = parser.seq(
            parser.get_parser(ast.EdgeTypeLabelSet),
            parser.get_parser(ast.EdgeTypePropertyTypes),
        )
        return ast.EdgeTypeImpliedContent._EdgeTypeLabelSetEdgeTypePropertyTypes(
            edge_type_label_set=edge_type_label_set,
            edge_type_property_types=edge_type_property_types,
        )

    candidates_edge_type_implied_content = (
        parser.get_parser(ast.EdgeTypeLabelSet),
        parser.get_parser(ast.EdgeTypePropertyTypes),
        _parse__edge_type_label_set_edge_type_property_types,
    )
    (edge_type_implied_content,) = parser.seq(candidates_edge_type_implied_content)
    return ast.EdgeTypeImpliedContent(
        edge_type_implied_content=edge_type_implied_content,
    )


@parses(ast.EdgeTypeKeyLabelSet)
def parse_edge_type_key_label_set(parser: Parser) -> ast.EdgeTypeKeyLabelSet:
    (
        label_set_phrase,
        _,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.LabelSetPhrase)),
        {TokenType.IMPLIES, TokenType.RIGHT_DOUBLE_ARROW},
    )
    return ast.EdgeTypeKeyLabelSet(
        label_set_phrase=label_set_phrase,
    )


@parses(ast.EdgeTypePatternDirected)
def parse_edge_type_pattern_directed(parser: Parser) -> ast.EdgeTypePatternDirected:
    candidates_edge_type_pattern_directed = (
        parser.get_parser(ast.EdgeTypePatternPointingRight),
        parser.get_parser(ast.EdgeTypePatternPointingLeft),
    )
    (result,) = parser.seq(candidates_edge_type_pattern_directed)
    return result


@parses(ast.EdgeTypePatternUndirected)
def parse_edge_type_pattern_undirected(parser: Parser) -> ast.EdgeTypePatternUndirected:
    (
        source_node_type_reference,
        arc_type_undirected,
        destination_node_type_reference,
    ) = parser.seq(
        parser.get_parser(ast.SourceNodeTypeReference),
        parser.get_parser(ast.ArcTypeUndirected),
        parser.get_parser(ast.DestinationNodeTypeReference),
    )
    return ast.EdgeTypePatternUndirected(
        source_node_type_reference=source_node_type_reference,
        arc_type_undirected=arc_type_undirected,
        destination_node_type_reference=destination_node_type_reference,
    )


@parses(ast.ArcTypePointingRight)
def parse_arc_type_pointing_right(parser: Parser) -> ast.ArcTypePointingRight:
    (
        _,
        edge_type_filler,
        _,
    ) = parser.seq(
        TokenType.MINUS_LEFT_BRACKET,
        parser.get_parser(ast.EdgeTypeFiller),
        TokenType.BRACKET_RIGHT_ARROW,
    )
    return ast.ArcTypePointingRight(
        edge_type_filler=edge_type_filler,
    )


@parses(ast.ArcTypePointingLeft)
def parse_arc_type_pointing_left(parser: Parser) -> ast.ArcTypePointingLeft:
    (
        _,
        edge_type_filler,
        _,
    ) = parser.seq(
        TokenType.LEFT_ARROW_BRACKET,
        parser.get_parser(ast.EdgeTypeFiller),
        TokenType.RIGHT_BRACKET_MINUS,
    )
    return ast.ArcTypePointingLeft(
        edge_type_filler=edge_type_filler,
    )


@parses(ast.ArcTypeUndirected)
def parse_arc_type_undirected(parser: Parser) -> ast.ArcTypeUndirected:
    (
        _,
        edge_type_filler,
        _,
    ) = parser.seq(
        TokenType.TILDE_LEFT_BRACKET,
        parser.get_parser(ast.EdgeTypeFiller),
        TokenType.RIGHT_BRACKET_TILDE,
    )
    return ast.ArcTypeUndirected(
        edge_type_filler=edge_type_filler,
    )


@parses(ast.SourceNodeTypeReference)
def parse_source_node_type_reference(parser: Parser) -> ast.SourceNodeTypeReference:
    def _parse__left_paren_source_node_type_alias_right_paren(
        parser: Parser,
    ) -> ast.SourceNodeTypeReference._LeftParenSourceNodeTypeAliasRightParen:
        (
            _,
            source_node_type_alias,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.SourceNodeTypeAlias),
            TokenType.RIGHT_PAREN,
        )
        return ast.SourceNodeTypeReference._LeftParenSourceNodeTypeAliasRightParen(
            source_node_type_alias=source_node_type_alias,
        )

    def _parse__left_paren_node_type_filler_right_paren(
        parser: Parser,
    ) -> ast.SourceNodeTypeReference._LeftParenNodeTypeFillerRightParen:
        (
            _,
            node_type_filler,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.opt(parser.get_parser(ast.NodeTypeFiller)),
            TokenType.RIGHT_PAREN,
        )
        return ast.SourceNodeTypeReference._LeftParenNodeTypeFillerRightParen(
            node_type_filler=node_type_filler,
        )

    candidates_source_node_type_reference = (
        _parse__left_paren_source_node_type_alias_right_paren,
        _parse__left_paren_node_type_filler_right_paren,
    )
    (source_node_type_reference,) = parser.seq(candidates_source_node_type_reference)
    return ast.SourceNodeTypeReference(
        source_node_type_reference=source_node_type_reference,
    )


@parses(ast.DestinationNodeTypeReference)
def parse_destination_node_type_reference(parser: Parser) -> ast.DestinationNodeTypeReference:
    def _parse__left_paren_destination_node_type_alias_right_paren(
        parser: Parser,
    ) -> ast.DestinationNodeTypeReference._LeftParenDestinationNodeTypeAliasRightParen:
        (
            _,
            destination_node_type_alias,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.DestinationNodeTypeAlias),
            TokenType.RIGHT_PAREN,
        )
        return ast.DestinationNodeTypeReference._LeftParenDestinationNodeTypeAliasRightParen(
            destination_node_type_alias=destination_node_type_alias,
        )

    def _parse__left_paren_node_type_filler_right_paren(
        parser: Parser,
    ) -> ast.DestinationNodeTypeReference._LeftParenNodeTypeFillerRightParen:
        (
            _,
            node_type_filler,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.opt(parser.get_parser(ast.NodeTypeFiller)),
            TokenType.RIGHT_PAREN,
        )
        return ast.DestinationNodeTypeReference._LeftParenNodeTypeFillerRightParen(
            node_type_filler=node_type_filler,
        )

    candidates_destination_node_type_reference = (
        _parse__left_paren_destination_node_type_alias_right_paren,
        _parse__left_paren_node_type_filler_right_paren,
    )
    (destination_node_type_reference,) = parser.seq(candidates_destination_node_type_reference)
    return ast.DestinationNodeTypeReference(
        destination_node_type_reference=destination_node_type_reference,
    )


@parses(ast.EdgeKind)
def parse_edge_kind(parser: Parser) -> ast.EdgeKind:
    (token,) = parser.seq({TokenType.DIRECTED, TokenType.UNDIRECTED})
    match token.token_type:
        case TokenType.DIRECTED:
            return ast.EdgeKind.DIRECTED
        case TokenType.UNDIRECTED:
            return ast.EdgeKind.UNDIRECTED
    raise AssertionError(f"Unexpected edge kind token: {token.token_type}")


@parses(ast.EndpointPairPhrase)
def parse_endpoint_pair_phrase(parser: Parser) -> ast.EndpointPairPhrase:
    (
        _,
        endpoint_pair,
    ) = parser.seq(
        TokenType.CONNECTING,
        parser.get_parser(ast.EndpointPair),
    )
    return ast.EndpointPairPhrase(
        endpoint_pair=endpoint_pair,
    )


@parses(ast.EndpointPair)
def parse_endpoint_pair(parser: Parser) -> ast.EndpointPair:
    candidates_endpoint_pair = (
        parser.get_parser(ast.EndpointPairDirected),
        parser.get_parser(ast.EndpointPairUndirected),
    )
    (result,) = parser.seq(candidates_endpoint_pair)
    return result


@parses(ast.ConnectorPointingRight)
def parse_connector_pointing_right(parser: Parser) -> ast.ConnectorPointingRight:
    parser.seq(
        {
            TokenType.TO,
            TokenType.RIGHT_ARROW,
        }
    )
    return ast.ConnectorPointingRight()


@parses(ast.ConnectorUndirected)
def parse_connector_undirected(parser: Parser) -> ast.ConnectorUndirected:
    parser.seq({TokenType.TO, TokenType.TILDE})
    return ast.ConnectorUndirected()


@parses(ast.LabelSetPhrase)
def parse_label_set_phrase(parser: Parser) -> ast.LabelSetPhrase:
    def _parse__label_label_name(parser: Parser) -> ast.LabelSetPhrase._LabelLabelName:
        (
            _,
            label_name,
        ) = parser.seq(
            TokenType.LABEL,
            parser.get_parser(ast.LabelName),
        )
        return ast.LabelSetPhrase._LabelLabelName(
            label_name=label_name,
        )

    def _parse__labels_label_set_specification(
        parser: Parser,
    ) -> ast.LabelSetPhrase._LabelsLabelSetSpecification:
        (
            _,
            label_set_specification,
        ) = parser.seq(
            TokenType.LABELS,
            parser.get_parser(ast.LabelSetSpecification),
        )
        return ast.LabelSetPhrase._LabelsLabelSetSpecification(
            label_set_specification=label_set_specification,
        )

    def _parse__is_or_colon_label_set_specification(
        parser: Parser,
    ) -> ast.LabelSetPhrase._IsOrColonLabelSetSpecification:
        (
            _,
            label_set_specification,
        ) = parser.seq(
            {TokenType.IS, TokenType.COLON},
            parser.get_parser(ast.LabelSetSpecification),
        )
        return ast.LabelSetPhrase._IsOrColonLabelSetSpecification(
            label_set_specification=label_set_specification,
        )

    candidates_label_set_phrase = (
        _parse__label_label_name,
        _parse__labels_label_set_specification,
        _parse__is_or_colon_label_set_specification,
    )
    (label_set_phrase,) = parser.seq(candidates_label_set_phrase)
    return ast.LabelSetPhrase(
        label_set_phrase=label_set_phrase,
    )


@parses(ast.LabelSetSpecification)
def parse_label_set_specification(parser: Parser) -> ast.LabelSetSpecification:
    (list_label_name,) = parser.seq(
        parser.list_(parser.get_parser(ast.LabelName), TokenType.AMPERSAND),
    )
    return ast.LabelSetSpecification(
        list_label_name=list_label_name,
    )


@parses(ast.PropertyTypesSpecification)
def parse_property_types_specification(parser: Parser) -> ast.PropertyTypesSpecification:
    (
        _,
        property_type_list,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.opt(parser.get_parser(ast.PropertyTypeList)),
        TokenType.RIGHT_BRACE,
    )
    return ast.PropertyTypesSpecification(
        property_type_list=property_type_list,
    )


@parses(ast.PropertyTypeList)
def parse_property_type_list(parser: Parser) -> ast.PropertyTypeList:
    (list_property_type,) = parser.seq(
        parser.list_(parser.get_parser(ast.PropertyType), TokenType.COMMA),
    )
    return ast.PropertyTypeList(
        list_property_type=list_property_type,
    )


@parses(ast.Typed)
def parse_typed(parser: Parser) -> ast.Typed:
    parser.seq({TokenType.DOUBLE_COLON, TokenType.TYPED})
    return ast.Typed()


@parses(ast.TemporalDurationQualifier)
def parse_temporal_duration_qualifier(parser: Parser) -> ast.TemporalDurationQualifier:
    _parse__year_to_month = token_parser(
        TokenType.YEAR,
        TokenType.TO,
        TokenType.MONTH,
        ast_type=ast.TemporalDurationQualifier._YearToMonth,
    )
    _parse__day_to_second = token_parser(
        TokenType.DAY,
        TokenType.TO,
        TokenType.SECOND,
        ast_type=ast.TemporalDurationQualifier._DayToSecond,
    )

    candidates_temporal_duration_qualifier = (
        _parse__year_to_month,
        _parse__day_to_second,
    )
    (temporal_duration_qualifier,) = parser.seq(candidates_temporal_duration_qualifier)
    return ast.TemporalDurationQualifier(
        temporal_duration_qualifier=temporal_duration_qualifier,
    )


@parses(ast.ListValueTypeName)
def parse_list_value_type_name(parser: Parser) -> ast.ListValueTypeName:
    (
        group,
        _,
    ) = parser.seq(
        parser.opt(TokenType.GROUP),
        TokenType.LIST,
    )
    return ast.ListValueTypeName(
        group=bool(group),
    )


@parses(ast.FieldTypesSpecification)
def parse_field_types_specification(parser: Parser) -> ast.FieldTypesSpecification:
    (
        _,
        field_type_list,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.opt(parser.get_parser(ast.FieldTypeList)),
        TokenType.RIGHT_BRACE,
    )
    return ast.FieldTypesSpecification(
        field_type_list=field_type_list,
    )


@parses(ast.FieldTypeList)
def parse_field_type_list(parser: Parser) -> ast.FieldTypeList:
    (list_field_type,) = parser.seq(
        parser.list_(parser.get_parser(ast.FieldType), TokenType.COMMA),
    )
    return ast.FieldTypeList(
        list_field_type=list_field_type,
    )


@parses(ast.ComponentTypeList)
def parse_component_type_list(parser: Parser) -> ast.ComponentTypeList:
    (list_component_type,) = parser.seq(
        parser.list_(parser.get_parser(ast.ComponentType), TokenType.VERTICAL_BAR),
    )
    return ast.ComponentTypeList(
        list_component_type=list_component_type,
    )


@parses(ast.NotNull)
def parse_not_null(parser: Parser) -> ast.NotNull:
    parser.seq(
        TokenType.NOT,
        TokenType.NULL,
    )
    return ast.NotNull()


@parses(ast.IsLabeledOrColon)
def parse_is_labeled_or_colon(parser: Parser) -> ast.IsLabeledOrColon:
    def _parse__is_not_labeled(parser: Parser) -> ast.IsLabeledOrColon._IsNotLabeled:
        (
            _,
            not_,
            _,
        ) = parser.seq(
            TokenType.IS,
            TokenType.NOT,
            TokenType.LABELED,
        )
        return ast.IsLabeledOrColon._IsNotLabeled(
            not_=bool(not_),
        )

    _parse__colon = token_parser(TokenType.COLON, ast_type=ast.IsLabeledOrColon._Colon)

    candidates_is_labeled_or_colon = (
        _parse__is_not_labeled,
        _parse__colon,
    )
    (is_labeled_or_colon,) = parser.seq(candidates_is_labeled_or_colon)
    return ast.IsLabeledOrColon(
        is_labeled_or_colon=is_labeled_or_colon,
    )


@parses(ast.ValueExpressionPrimary)
def parse_value_expression_primary(parser: Parser) -> ast.ValueExpressionPrimary:
    candidates_value_expression_primary = (
        parser.get_parser(ast.ParenthesizedValueExpression),
        parser.get_parser(ast.NonParenthesizedValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates_value_expression_primary)
    return result


@parses(ast.ValueSpecification)
def parse_value_specification(parser: Parser) -> ast.ValueSpecification:
    candidates_value_specification = (
        parser.get_parser(ast.Literal),
        parser.get_parser(ast.GeneralValueSpecification),
    )
    (result,) = parser.seq(candidates_value_specification)
    return result


@parses(ast.UnsignedValueSpecification)
def parse_unsigned_value_specification(parser: Parser) -> ast.UnsignedValueSpecification:
    candidates_unsigned_value_specification = (
        parser.get_parser(ast.GeneralValueSpecification),
        parser.get_parser(ast.UnsignedLiteral),
    )
    (result,) = parser.seq(candidates_unsigned_value_specification)
    return result


@parses(ast.NonNegativeIntegerSpecification)
def parse_non_negative_integer_specification(parser: Parser) -> ast.NonNegativeIntegerSpecification:
    candidates_non_negative_integer_specification = (
        parser.get_parser(ast.UnsignedInteger),
        parser.get_parser(ast.DynamicParameterSpecification),
    )
    (result,) = parser.seq(candidates_non_negative_integer_specification)
    return result


def parse_case_operand(parser: Parser) -> ast.CaseOperand:
    candidates_case_operand = (
        parser.get_parser(ast.ElementVariableReference),
        parser.get_parser(ast.NonParenthesizedValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates_case_operand)
    return result


@parses(ast.WhenOperandList)
def parse_when_operand_list(parser: Parser) -> ast.WhenOperandList:
    (list_when_operand,) = parser.seq(
        parser.list_(parser.get_parser(ast.WhenOperand), TokenType.COMMA),
    )
    return ast.WhenOperandList(
        list_when_operand=list_when_operand,
    )


@parses(ast.WhenOperand)
def parse_when_operand(parser: Parser) -> ast.WhenOperand:
    candidates_when_operand = (
        parser.get_parser(ast.NonParenthesizedValueExpressionPrimary),
        parser.get_parser(ast.ComparisonPredicatePart2),
        parser.get_parser(ast.NullPredicatePart2),
        parser.get_parser(ast.ValueTypePredicatePart2),
        parser.get_parser(ast.NormalizedPredicatePart2),
        parser.get_parser(ast.DirectedPredicatePart2),
        parser.get_parser(ast.LabeledPredicatePart2),
        parser.get_parser(ast.SourcePredicatePart2),
        parser.get_parser(ast.DestinationPredicatePart2),
    )
    (result,) = parser.seq(candidates_when_operand)
    return result


def parse_result(parser: Parser) -> ast.Result:
    candidates_result = (
        parser.get_parser(ast.ResultExpression),
        parser.get_parser(ast.NullLiteral),
    )
    (result,) = parser.seq(candidates_result)
    return result


@parses(ast.CastSpecification)
def parse_cast_specification(parser: Parser) -> ast.CastSpecification:
    (
        _,
        _,
        cast_operand,
        _,
        cast_target,
        _,
    ) = parser.seq(
        TokenType.CAST,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.CastOperand),
        TokenType.AS,
        parser.get_parser(ast.CastTarget),
        TokenType.RIGHT_PAREN,
    )
    return ast.CastSpecification(
        cast_operand=cast_operand,
        cast_target=cast_target,
    )


@parses(ast.CastOperand)
def parse_cast_operand(parser: Parser) -> ast.CastOperand:
    candidates_cast_operand = (
        parser.get_parser(ast.ValueExpression),
        parser.get_parser(ast.NullLiteral),
    )
    (result,) = parser.seq(candidates_cast_operand)
    return result


@parses(ast.AggregateFunction)
def parse_aggregate_function(parser: Parser) -> ast.AggregateFunction:
    def _parse__count_asterisk(
        parser: Parser,
    ) -> ast.AggregateFunction._CountAsterisk:
        parser.seq(
            TokenType.COUNT,
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.Asterisk),
            TokenType.RIGHT_PAREN,
        )
        return ast.AggregateFunction._CountAsterisk()

    candidates_aggregate_function = (
        _parse__count_asterisk,
        parser.get_parser(ast.GeneralSetFunction),
        parser.get_parser(ast.BinarySetFunction),
    )
    (aggregate_function,) = parser.seq(candidates_aggregate_function)
    return ast.AggregateFunction(
        aggregate_function=aggregate_function,
    )


@parses(ast.GeneralSetFunction)
def parse_general_set_function(parser: Parser) -> ast.GeneralSetFunction:
    (
        general_set_function_type,
        _,
        set_quantifier,
        value_expression,
        _,
    ) = parser.seq(
        parser.get_parser(ast.GeneralSetFunctionType),
        TokenType.LEFT_PAREN,
        parser.opt(parser.get_parser(ast.SetQuantifier)),
        parser.get_parser(ast.ValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.GeneralSetFunction(
        general_set_function_type=general_set_function_type,
        set_quantifier=set_quantifier,
        value_expression=value_expression,
    )


@parses(ast.BinarySetFunction)
def parse_binary_set_function(parser: Parser) -> ast.BinarySetFunction:
    (
        token,
        _,
        dependent_value_expression,
        _,
        independent_value_expression,
        _,
    ) = parser.seq(
        {TokenType.PERCENTILE_CONT, TokenType.PERCENTILE_DISC},
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.DependentValueExpression),
        TokenType.COMMA,
        parser.get_parser(ast.IndependentValueExpression),
        TokenType.RIGHT_PAREN,
    )
    match token.token_type:
        case TokenType.PERCENTILE_CONT:
            binary_set_function_type = ast.BinarySetFunction.BinarySetFunctionType.PERCENTILE_CONT
        case TokenType.PERCENTILE_DISC:
            binary_set_function_type = ast.BinarySetFunction.BinarySetFunctionType.PERCENTILE_DISC

    return ast.BinarySetFunction(
        binary_set_function_type=binary_set_function_type,
        dependent_value_expression=dependent_value_expression,
        independent_value_expression=independent_value_expression,
    )


@parses(ast.SetQuantifier)
def parse_set_quantifier(parser: Parser) -> ast.SetQuantifier:
    (token,) = parser.seq({TokenType.DISTINCT, TokenType.ALL})

    match token.token_type:
        case TokenType.DISTINCT:
            quantifier = ast.SetQuantifier.Quantifier.DISTINCT
        case TokenType.ALL:
            quantifier = ast.SetQuantifier.Quantifier.ALL

    return ast.SetQuantifier(set_quantifier=quantifier)


@parses(ast.ElementIdFunction)
def parse_element_id_function(parser: Parser) -> ast.ElementIdFunction:
    (_, _, element_variable_reference, _) = parser.seq(
        TokenType.ELEMENT_ID,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ElementVariableReference),
        TokenType.RIGHT_PAREN,
    )
    return ast.ElementIdFunction(
        element_variable_reference=element_variable_reference,
    )


@parses(ast.PropertyReference)
def parse_property_reference(parser: Parser) -> ast.PropertyReference:
    (
        property_source,
        _,
        property_name,
    ) = parser.seq(
        parser.get_parser(ast._PropertySourceExceptPropertyReference),
        TokenType.PERIOD,
        parser.list_(parser.get_parser(ast.PropertyName), TokenType.PERIOD),
    )
    return ast.PropertyReference(
        property_source=property_source,
        property_name=property_name,
    )


@parses(ast.PathValueConstructorByEnumeration)
def parse_path_value_constructor_by_enumeration(
    parser: Parser,
) -> ast.PathValueConstructorByEnumeration:
    (_, _, path_element_list, _) = parser.seq(
        TokenType.PATH,
        TokenType.LEFT_BRACKET,
        parser.get_parser(ast.PathElementList),
        TokenType.RIGHT_BRACKET,
    )
    return ast.PathValueConstructorByEnumeration(
        path_element_list=path_element_list,
    )


@parses(ast.PathElementList)
def parse_path_element_list(parser: Parser) -> ast.PathElementList:
    (
        path_element_list_start,
        list_path_element_list_step,
    ) = parser.seq(
        parser.get_parser(ast.PathElementListStart),
        parser.opt(
            lambda parser: parser.seq(
                parser.list_(parser.get_parser(ast.PathElementListStep), None)
            )
        ),
    )
    return ast.PathElementList(
        path_element_list_start=path_element_list_start,
        list_path_element_list_step=list_path_element_list_step,
    )


@parses(ast.PathElementListStep)
def parse_path_element_list_step(parser: Parser) -> ast.PathElementListStep:
    (
        _,
        edge_reference_value_expression,
        _,
        node_reference_value_expression,
    ) = parser.seq(
        TokenType.COMMA,
        parser.get_parser(ast.EdgeReferenceValueExpression),
        TokenType.COMMA,
        parser.get_parser(ast.NodeReferenceValueExpression),
    )
    return ast.PathElementListStep(
        edge_reference_value_expression=edge_reference_value_expression,
        node_reference_value_expression=node_reference_value_expression,
    )


@parses(ast.ListValueFunction)
def parse_list_value_function(parser: Parser) -> ast.ListValueFunction:
    candidates_list_value_function = (
        parser.get_parser(ast.TrimListFunction),
        parser.get_parser(ast.ElementsFunction),
    )
    (result,) = parser.seq(candidates_list_value_function)
    return result


@parses(ast.ListValueConstructorByEnumeration)
def parse_list_value_constructor_by_enumeration(
    parser: Parser,
) -> ast.ListValueConstructorByEnumeration:
    (
        list_value_type_name,
        _,
        list_element_list,
        _,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.ListValueTypeName)),
        TokenType.LEFT_BRACKET,
        parser.opt(parser.get_parser(ast.ListElementList)),
        TokenType.RIGHT_BRACKET,
    )
    return ast.ListValueConstructorByEnumeration(
        list_value_type_name=list_value_type_name,
        list_element_list=list_element_list,
    )


@parses(ast.ListElementList)
def parse_list_element_list(parser: Parser) -> ast.ListElementList:
    def _parse_list_element(parser: Parser) -> ast.ValueExpression:
        # Fast-path: when the current token is `[`, this is a nested list literal.
        # Directly parse as ListValueConstructorByEnumeration wrapped in
        # ListValueExpression to avoid the deep ValueExpression → CommonValueExpression
        # → ListValueExpression → ListPrimary → VEP → ... call chain (~50 frames
        # saved per nesting level, preventing RecursionError on deeply nested lists).
        if parser._match(TokenType.LEFT_BRACKET):
            inner = parser.get_parser(ast.ListValueConstructorByEnumeration)(parser)
            return ast.ListValueExpression(list_list_primary=[inner])
        return parser.get_parser(ast.ListElement)(parser)

    (list_list_element,) = parser.seq(
        parser.list_(_parse_list_element, TokenType.COMMA),
    )
    return ast.ListElementList(
        list_list_element=list_list_element,
    )


@parses(ast.FieldsSpecification)
def parse_fields_specification(parser: Parser) -> ast.FieldsSpecification:
    (
        _,
        field_list,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.opt(parser.get_parser(ast.FieldList)),
        TokenType.RIGHT_BRACE,
    )
    return ast.FieldsSpecification(
        field_list=field_list,
    )


@parses(ast.FieldList)
def parse_field_list(parser: Parser) -> ast.FieldList:
    (list_field,) = parser.seq(
        parser.list_(parser.get_parser(ast.Field), TokenType.COMMA),
    )
    return ast.FieldList(
        list_field=list_field,
    )


@parses(ast.Field)
def parse_field(parser: Parser) -> ast.Field:
    (
        field_name,
        _,
        value_expression,
    ) = parser.seq(
        parser.get_parser(ast.FieldName),
        TokenType.COLON,
        parser.get_parser(ast.ValueExpression),
    )
    return ast.Field(
        field_name=field_name,
        value_expression=value_expression,
    )


@parses(ast.BooleanTerm)
def parse_boolean_term(parser: Parser) -> ast.BooleanTerm:
    (list_boolean_factor,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.BooleanFactor),
            TokenType.AND,
        ),
    )
    return ast.BooleanTerm(
        list_boolean_factor=list_boolean_factor,
    )


@parses(ast.BooleanFactor)
def parse_boolean_factor(parser: Parser) -> ast.BooleanFactor:
    (
        not_,
        boolean_test,
    ) = parser.seq(
        parser.opt(TokenType.NOT),
        parser.get_parser(ast.BooleanTest),
    )
    return ast.BooleanFactor(
        not_=bool(not_),
        boolean_test=boolean_test,
    )


@parses(ast.BooleanTest)
def parse_boolean_test(parser: Parser) -> ast.BooleanTest:
    def _parse__is_not_truth_value(parser: Parser) -> ast.BooleanTest._IsNotTruthValue:
        (
            _,
            not_,
            truth_value,
        ) = parser.seq(
            TokenType.IS,
            parser.opt(TokenType.NOT),
            parser.get_parser(ast.TruthValue),
        )
        return ast.BooleanTest._IsNotTruthValue(
            not_=bool(not_),
            truth_value=truth_value,
        )

    (
        boolean_primary,
        truth_value,
    ) = parser.seq(
        parser.get_parser(ast.BooleanPrimary),
        parser.opt(_parse__is_not_truth_value),
    )
    return ast.BooleanTest(
        boolean_primary=boolean_primary,
        truth_value=truth_value,
    )


@parses(ast.TruthValue)
def parse_truth_value(parser: Parser) -> ast.TruthValue:
    _parse__true = token_parser(TokenType.TRUE, ast_type=ast.TruthValue._True)
    _parse__false = token_parser(TokenType.FALSE, ast_type=ast.TruthValue._False)
    _parse__unknown = token_parser(TokenType.UNKNOWN, ast_type=ast.TruthValue._Unknown)

    candidates_truth_value = (
        _parse__true,
        _parse__false,
        _parse__unknown,
    )
    (truth_value,) = parser.seq(candidates_truth_value)
    return ast.TruthValue(
        truth_value=truth_value,
    )


@parses(ast.BooleanPrimary)
def parse_boolean_primary(parser: Parser) -> ast.BooleanPrimary:
    candidates_boolean_primary = (
        parser.get_parser(ast.Predicate),
        parser.get_parser(ast.BooleanPredicand),
    )
    (result,) = parser.seq(candidates_boolean_primary)
    return result


@parses(ast.MultiplicativeOperator)
def parse_multiplicative_operator(parser: Parser) -> ast.MultiplicativeOperator:
    (token,) = parser.seq({TokenType.ASTERISK, TokenType.SOLIDUS})
    match token.token_type:
        case TokenType.ASTERISK:
            return ast.MultiplicativeOperator.MULTIPLY
        case TokenType.SOLIDUS:
            return ast.MultiplicativeOperator.DIVIDE
    raise AssertionError(f"Unexpected multiplicative operator token: {token.token_type}")


@parses(ast.Term)
def parse_term(parser: Parser) -> ast.Term:
    def _parser__mul_step(parser: Parser) -> ast.Term._MultiplicativeFactor:
        (operator, factor) = parser.seq(
            parser.get_parser(ast.MultiplicativeOperator), parser.get_parser(ast.Factor)
        )
        return ast.Term._MultiplicativeFactor(operator=operator, factor=factor)

    (
        base,
        steps,
    ) = parser.seq(
        parser.get_parser(ast.Factor), parser.list_(_parser__mul_step, None, min_items=0)
    )
    return ast.Term(
        base=base,
        steps=steps or None,
    )


@parses(ast.Factor)
def parse_factor(parser: Parser) -> ast.Factor:
    (
        sign,
        numeric_primary,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Sign)),
        parser.get_parser(ast.NumericPrimary),
    )
    return ast.Factor(
        sign=sign or ast.Sign.PLUS_SIGN,
        numeric_primary=numeric_primary,
    )


@parses(ast.NumericValueFunction)
def parse_numeric_value_function(parser: Parser) -> ast.NumericValueFunction:
    candidates_numeric_value_function = (
        parser.get_parser(ast.LengthExpression),
        parser.get_parser(ast.CardinalityExpression),
        parser.get_parser(ast.AbsoluteValueExpression),
        parser.get_parser(ast.ModulusExpression),
        parser.get_parser(ast.TrigonometricFunction),
        parser.get_parser(ast.GeneralLogarithmFunction),
        parser.get_parser(ast.CommonLogarithm),
        parser.get_parser(ast.NaturalLogarithm),
        parser.get_parser(ast.ExponentialFunction),
        parser.get_parser(ast.PowerFunction),
        parser.get_parser(ast.SquareRoot),
        parser.get_parser(ast.FloorFunction),
        parser.get_parser(ast.CeilingFunction),
    )
    (result,) = parser.seq(candidates_numeric_value_function)
    return result


@parses(ast.TrigonometricFunctionName)
def parse_trigonometric_function_name(parser: Parser) -> ast.TrigonometricFunctionName:
    _parse__sin = token_parser(TokenType.SIN, ast_type=ast.TrigonometricFunctionName._Sin)
    _parse__cos = token_parser(TokenType.COS, ast_type=ast.TrigonometricFunctionName._Cos)
    _parse__tan = token_parser(TokenType.TAN, ast_type=ast.TrigonometricFunctionName._Tan)
    _parse__cot = token_parser(TokenType.COT, ast_type=ast.TrigonometricFunctionName._Cot)
    _parse__sinh = token_parser(TokenType.SINH, ast_type=ast.TrigonometricFunctionName._Sinh)
    _parse__cosh = token_parser(TokenType.COSH, ast_type=ast.TrigonometricFunctionName._Cosh)
    _parse__tanh = token_parser(TokenType.TANH, ast_type=ast.TrigonometricFunctionName._Tanh)
    _parse__asin = token_parser(TokenType.ASIN, ast_type=ast.TrigonometricFunctionName._Asin)
    _parse__acos = token_parser(TokenType.ACOS, ast_type=ast.TrigonometricFunctionName._Acos)
    _parse__atan = token_parser(TokenType.ATAN, ast_type=ast.TrigonometricFunctionName._Atan)
    _parse__degrees = token_parser(
        TokenType.DEGREES, ast_type=ast.TrigonometricFunctionName._Degrees
    )
    _parse__radians = token_parser(
        TokenType.RADIANS, ast_type=ast.TrigonometricFunctionName._Radians
    )

    candidates_trigonometric_function_name = (
        _parse__sin,
        _parse__cos,
        _parse__tan,
        _parse__cot,
        _parse__sinh,
        _parse__cosh,
        _parse__tanh,
        _parse__asin,
        _parse__acos,
        _parse__atan,
        _parse__degrees,
        _parse__radians,
    )
    (trigonometric_function_name,) = parser.seq(candidates_trigonometric_function_name)
    return ast.TrigonometricFunctionName(
        trigonometric_function_name=trigonometric_function_name,
    )


@parses(ast.CharacterStringFunction)
def parse_character_string_function(parser: Parser) -> ast.CharacterStringFunction:
    candidates_character_string_function = (
        parser.get_parser(ast.SubstringFunction),
        parser.get_parser(ast.Fold),
        parser.get_parser(ast.TrimFunction),
        parser.get_parser(ast.NormalizeFunction),
    )
    (result,) = parser.seq(candidates_character_string_function)
    return result


@parses(ast.TrimOperands)
def parse_trim_operands(parser: Parser) -> ast.TrimOperands:
    def _parse__trim_specification_trim_character_string_from(
        parser: Parser,
    ) -> ast.TrimOperands._TrimSpecificationTrimCharacterStringFrom:
        (
            trim_specification,
            trim_character_string,
            _,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.TrimSpecification)),
            parser.opt(parser.get_parser(ast.TrimCharacterString)),
            TokenType.FROM,
        )
        return ast.TrimOperands._TrimSpecificationTrimCharacterStringFrom(
            trim_specification=trim_specification,
            trim_character_string=trim_character_string,
        )

    (
        trim_specification_trim_character_string_from,
        trim_source,
    ) = parser.seq(
        parser.opt(_parse__trim_specification_trim_character_string_from),
        parser.get_parser(ast.TrimSource),
    )
    return ast.TrimOperands(
        trim_specification_trim_character_string_from=trim_specification_trim_character_string_from,
        trim_source=trim_source,
    )


@parses(ast.TrimSpecification)
def parse_trim_specification(parser: Parser) -> ast.TrimSpecification:
    _parse__leading = token_parser(TokenType.LEADING, ast_type=ast.TrimSpecification._Leading)
    _parse__trailing = token_parser(TokenType.TRAILING, ast_type=ast.TrimSpecification._Trailing)
    _parse__both = token_parser(TokenType.BOTH, ast_type=ast.TrimSpecification._Both)

    candidates_trim_specification = (
        _parse__leading,
        _parse__trailing,
        _parse__both,
    )
    (trim_specification,) = parser.seq(candidates_trim_specification)
    return ast.TrimSpecification(
        trim_specification=trim_specification,
    )


@parses(ast.NormalForm)
def parse_normal_form(parser: Parser) -> ast.NormalForm:
    _parse__nfc = token_parser(TokenType.NFC, ast_type=ast.NormalForm._Nfc)
    _parse__nfd = token_parser(TokenType.NFD, ast_type=ast.NormalForm._Nfd)
    _parse__nfkc = token_parser(TokenType.NFKC, ast_type=ast.NormalForm._Nfkc)
    _parse__nfkd = token_parser(TokenType.NFKD, ast_type=ast.NormalForm._Nfkd)

    candidates_normal_form = (
        _parse__nfc,
        _parse__nfd,
        _parse__nfkc,
        _parse__nfkd,
    )
    (normal_form,) = parser.seq(candidates_normal_form)
    return ast.NormalForm(
        normal_form=normal_form,
    )


@parses(ast.ByteStringFunction)
def parse_byte_string_function(parser: Parser) -> ast.ByteStringFunction:
    candidates_byte_string_function = (
        parser.get_parser(ast.ByteStringSubstringFunction),
        parser.get_parser(ast.ByteStringTrimFunction),
    )
    (result,) = parser.seq(candidates_byte_string_function)
    return result


@parses(ast.ByteStringTrimOperands)
def parse_byte_string_trim_operands(parser: Parser) -> ast.ByteStringTrimOperands:
    def _parse__trim_specification_trim_byte_string_from(
        parser: Parser,
    ) -> ast.ByteStringTrimOperands._TrimSpecificationTrimByteStringFrom:
        (
            trim_specification,
            trim_byte_string,
            _,
        ) = parser.seq(
            parser.opt(parser.get_parser(ast.TrimSpecification)),
            parser.opt(parser.get_parser(ast.TrimByteString)),
            TokenType.FROM,
        )
        return ast.ByteStringTrimOperands._TrimSpecificationTrimByteStringFrom(
            trim_specification=trim_specification,
            trim_byte_string=trim_byte_string,
        )

    (
        trim_specification_trim_byte_string_from,
        byte_string_trim_source,
    ) = parser.seq(
        parser.opt(_parse__trim_specification_trim_byte_string_from),
        parser.get_parser(ast.ByteStringTrimSource),
    )
    return ast.ByteStringTrimOperands(
        trim_specification_trim_byte_string_from=trim_specification_trim_byte_string_from,
        byte_string_trim_source=byte_string_trim_source,
    )


@parses(ast.DatetimeValueFunction)
def parse_datetime_value_function(parser: Parser) -> ast.DatetimeValueFunction:
    candidates_datetime_value_function = (
        parser.get_parser(ast.DateFunction),
        parser.get_parser(ast.TimeFunction),
        parser.get_parser(ast.DatetimeFunction),
        parser.get_parser(ast.LocaltimeFunction),
        parser.get_parser(ast.LocaldatetimeFunction),
    )
    (result,) = parser.seq(candidates_datetime_value_function)
    return result


def parse_date_function_parameters(parser: Parser) -> ast.DateFunctionParameters:
    candidates_date_function_parameters = (
        parser.get_parser(ast.DateString),
        parser.get_parser(ast.RecordConstructor),
    )
    (result,) = parser.seq(candidates_date_function_parameters)
    return result


def parse_time_function_parameters(parser: Parser) -> ast.TimeFunctionParameters:
    candidates_time_function_parameters = (
        parser.get_parser(ast.TimeString),
        parser.get_parser(ast.RecordConstructor),
    )
    (result,) = parser.seq(candidates_time_function_parameters)
    return result


def parse_datetime_function_parameters(parser: Parser) -> ast.DatetimeFunctionParameters:
    candidates_datetime_function_parameters = (
        parser.get_parser(ast.DatetimeString),
        parser.get_parser(ast.RecordConstructor),
    )
    (result,) = parser.seq(candidates_datetime_function_parameters)
    return result


@parses(ast.DatetimeSubtractionParameters)
def parse_datetime_subtraction_parameters(parser: Parser) -> ast.DatetimeSubtractionParameters:
    (
        datetime_value_expression_1,
        _,
        datetime_value_expression_2,
    ) = parser.seq(
        parser.get_parser(ast.DatetimeValueExpression1),
        TokenType.COMMA,
        parser.get_parser(ast.DatetimeValueExpression2),
    )
    return ast.DatetimeSubtractionParameters(
        datetime_value_expression_1=datetime_value_expression_1,
        datetime_value_expression_2=datetime_value_expression_2,
    )


@parses(ast.DurationFactor)
def parse_duration_factor(parser: Parser) -> ast.DurationFactor:
    (
        sign,
        duration_primary,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Sign)),
        parser.get_parser(ast.DurationPrimary),
    )
    return ast.DurationFactor(
        sign=sign or ast.Sign.PLUS_SIGN,
        duration_primary=duration_primary,
    )


@parses(ast.DurationValueFunction)
def parse_duration_value_function(parser: Parser) -> ast.DurationValueFunction:
    candidates_duration_value_function = (
        parser.get_parser(ast.DurationFunction),
        parser.get_parser(ast.DurationAbsoluteValueFunction),
    )
    (result,) = parser.seq(candidates_duration_value_function)
    return result


@parses(ast.DurationFunctionParameters)
def parse_duration_function_parameters(parser: Parser) -> ast.DurationFunctionParameters:
    candidates_duration_function_parameters = (
        parser.get_parser(ast.DurationString),
        parser.get_parser(ast.RecordConstructor),
    )
    (result,) = parser.seq(candidates_duration_function_parameters)
    return result


def parse_graph_name(parser: Parser) -> ast.GraphName:
    candidates_graph_name = (
        parser.get_parser(ast.Identifier),
        parser.get_parser(ast.DelimitedGraphName),
    )
    (result,) = parser.seq(candidates_graph_name)
    return result


@parses(ast.BindingTableName)
def parse_binding_table_name(parser: Parser) -> ast.BindingTableName:
    candidates_binding_table_name = (
        parser.get_parser(ast.Identifier),
        parser.get_parser(ast.DelimitedBindingTableName),
    )
    (result,) = parser.seq(candidates_binding_table_name)
    return result


@parses(ast.GraphPatternVariable)
def parse_graph_pattern_variable(parser: Parser) -> ast.GraphPatternVariable:
    candidates_graph_pattern_variable = (
        parser.get_parser(ast.ElementVariable),
        parser.get_parser(ast.PathOrSubpathVariable),
    )
    (result,) = parser.seq(candidates_graph_pattern_variable)
    return result


@parses(ast.Sign)
def parse_sign(parser: Parser) -> ast.Sign:
    (token,) = parser.seq({TokenType.PLUS_SIGN, TokenType.MINUS_SIGN})
    match token.token_type:
        case TokenType.PLUS_SIGN:
            return ast.Sign.PLUS_SIGN
        case TokenType.MINUS_SIGN:
            return ast.Sign.MINUS_SIGN
    raise AssertionError(f"Unexpected sign token: {token.token_type}")


@parses(ast.Mantissa)
def parse_mantissa(parser: Parser) -> ast.Mantissa:
    candidates_mantissa = (
        parser.get_parser(ast.UnsignedNumericLiteral),
        parser.get_parser(ast.UnsignedInteger),
    )
    (result,) = parser.seq(candidates_mantissa)
    return result


@parses(ast.SignedDecimalInteger)
def parse_signed_decimal_integer(parser: Parser) -> ast.SignedDecimalInteger:
    (
        sign,
        unsigned_integer,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Sign)),
        parser.get_parser(ast.UnsignedInteger),
    )
    return ast.SignedDecimalInteger(
        sign=sign or ast.Sign.PLUS_SIGN,
        unsigned_integer=unsigned_integer,
    )


@parses(ast.Iso8601YearsAndMonths)
def parse_iso8601_years_and_months(parser: Parser) -> ast.Iso8601YearsAndMonths:
    (
        iso8601_years,
        iso8601_months,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Iso8601Years)),
        parser.opt(parser.get_parser(ast.Iso8601Months)),
    )
    return ast.Iso8601YearsAndMonths(
        iso8601_years=iso8601_years,
        iso8601_months=iso8601_months,
    )


@parses(ast.Iso8601Years)
def parse_iso8601_years(parser: Parser) -> ast.Iso8601Years:
    (iso8601_sint,) = parser.seq(
        parser.get_parser(ast.Iso8601Sint),
    )
    return ast.Iso8601Years(
        iso8601_sint=iso8601_sint,
    )


@parses(ast.Iso8601Months)
def parse_iso8601_months(parser: Parser) -> ast.Iso8601Months:
    (iso8601_sint,) = parser.seq(
        parser.get_parser(ast.Iso8601Sint),
    )
    return ast.Iso8601Months(
        iso8601_sint=iso8601_sint,
    )


@parses(ast.Iso8601DaysAndTime)
def parse_iso8601_days_and_time(parser: Parser) -> ast.Iso8601DaysAndTime:
    (
        iso8601_days,
        iso8601_hours,
        iso8601_minutes,
        iso8601_seconds,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Iso8601Days)),
        parser.opt(parser.get_parser(ast.Iso8601Hours)),
        parser.opt(parser.get_parser(ast.Iso8601Minutes)),
        parser.opt(parser.get_parser(ast.Iso8601Seconds)),
    )
    return ast.Iso8601DaysAndTime(
        iso8601_days=iso8601_days,
        iso8601_hours=iso8601_hours,
        iso8601_minutes=iso8601_minutes,
        iso8601_seconds=iso8601_seconds,
    )


@parses(ast.Iso8601Days)
def parse_iso8601_days(parser: Parser) -> ast.Iso8601Days:
    (iso8601_sint,) = parser.seq(
        parser.get_parser(ast.Iso8601Sint),
    )
    return ast.Iso8601Days(
        iso8601_sint=iso8601_sint,
    )


@parses(ast.Iso8601Hours)
def parse_iso8601_hours(parser: Parser) -> ast.Iso8601Hours:
    (iso8601_sint,) = parser.seq(
        parser.get_parser(ast.Iso8601Sint),
    )
    return ast.Iso8601Hours(
        iso8601_sint=iso8601_sint,
    )


@parses(ast.Iso8601Minutes)
def parse_iso8601_minutes(parser: Parser) -> ast.Iso8601Minutes:
    (iso8601_sint,) = parser.seq(
        parser.get_parser(ast.Iso8601Sint),
    )
    return ast.Iso8601Minutes(
        iso8601_sint=iso8601_sint,
    )


@parses(ast.Iso8601Seconds)
def parse_iso8601_seconds(parser: Parser) -> ast.Iso8601Seconds:
    (
        iso8601_sint,
        iso8601_uint,
    ) = parser.seq(
        parser.get_parser(ast.Iso8601Sint),
        parser.opt(parser.get_parser(ast.Iso8601Uint)),
    )
    return ast.Iso8601Seconds(
        iso8601_sint=iso8601_sint,
        iso8601_uint=iso8601_uint,
    )


@parses(ast.Iso8601Sint)
def parse_iso8601_sint(parser: Parser) -> ast.Iso8601Sint:
    (
        minus_sign,
        unsigned_integer,
    ) = parser.seq(
        parser.opt(TokenType.MINUS_SIGN),
        parser.get_parser(ast.UnsignedInteger),
    )
    return ast.Iso8601Sint(
        minus_sign=bool(minus_sign),
        unsigned_integer=unsigned_integer,
    )


@parses(ast.Identifier)
def parse_identifier(parser: Parser) -> ast.Identifier | ast.Expression:
    # Macros can appear in any identifier position (variables, labels, properties).
    # The macro-aware Expression.__init__ ensures the parent node accepts the
    # result even though it's not a strict Identifier subclass.
    if parser._match(TokenType.COMMERCIAL_AT):
        return parser.get_parser(ast.MacroCall)(parser)
    non_reserved_words = parser.dialect.NON_RESERVED_WORDS
    (token,) = parser.seq({TokenType.VAR} | non_reserved_words)
    return ast.Identifier(
        name=token.text,
    )


@parses(ast.SubstitutedParameterReference)
def parse_substituted_parameter_reference(parser: Parser) -> ast.SubstitutedParameterReference:
    (
        _,
        parameter_name,
    ) = parser.seq(
        TokenType.DOUBLE_DOLLAR_SIGN,
        parser.get_parser(ast.ParameterName),
    )
    return ast.SubstitutedParameterReference(
        parameter_name=parameter_name,
    )


@parses(ast.GeneralParameterReference)
def parse_general_parameter_reference(parser: Parser) -> ast.GeneralParameterReference:
    (
        _,
        parameter_name,
    ) = parser.seq(
        TokenType.DOLLAR_SIGN,
        parser.get_parser(ast.ParameterName),
    )
    return ast.GeneralParameterReference(
        parameter_name=parameter_name,
    )


@parses(ast.Solidus)
def parse_solidus(parser: Parser) -> ast.Solidus:
    parser.seq(TokenType.SOLIDUS)
    return ast.Solidus()


@parses(ast.SessionActivity)
def parse_session_activity(parser: Parser) -> ast.SessionActivity:
    def _parse__list_session_set_command_list_session_reset_command(
        parser: Parser,
    ) -> ast.SessionActivity._ListSessionSetCommandListSessionResetCommand:
        (
            list_session_set_command,
            list_session_reset_command,
        ) = parser.seq(
            parser.list_(parser.get_parser(ast.SessionSetCommand), None),
            parser.opt(
                lambda p: parser.seq(parser.list_(parser.get_parser(ast.SessionResetCommand), None))
            ),
        )
        return ast.SessionActivity._ListSessionSetCommandListSessionResetCommand(
            list_session_set_command=list_session_set_command,
            list_session_reset_command=list_session_reset_command,
        )

    def _parse__list_session_reset_command(parser: Parser) -> list[ast.SessionResetCommand]:
        (session_activity,) = parser.seq(
            parser.list_(parser.get_parser(ast.SessionResetCommand), None)
        )
        return session_activity

    candidates_session_activity = (
        _parse__list_session_set_command_list_session_reset_command,
        _parse__list_session_reset_command,
    )
    (session_activity,) = parser.seq(candidates_session_activity)
    return ast.SessionActivity(
        session_activity=session_activity,
    )


@parses(ast.TransactionActivity)
def parse_transaction_activity(parser: Parser) -> ast.TransactionActivity:
    def _parse__start_transaction_command_procedure_specification_end_transaction_command(
        parser: Parser,
    ) -> (
        ast.TransactionActivity._StartTransactionCommandProcedureSpecificationEndTransactionCommand
    ):
        (
            start_transaction_command,
            procedure_specification_end_transaction_command,
        ) = parser.seq(
            parser.get_parser(ast.StartTransactionCommand),
            parser.opt(_parse__procedure_specification_end_transaction_command),
        )
        return ast.TransactionActivity._StartTransactionCommandProcedureSpecificationEndTransactionCommand(  # noqa: E501
            start_transaction_command=start_transaction_command,
            procedure_specification_end_transaction_command=procedure_specification_end_transaction_command,
        )

    def _parse__procedure_specification_end_transaction_command(
        parser: Parser,
    ) -> ast.TransactionActivity._ProcedureSpecificationEndTransactionCommand:
        (
            procedure_specification,
            end_transaction_command,
        ) = parser.seq(
            parser.get_parser(ast.ProcedureSpecification),
            parser.opt(parser.get_parser(ast.EndTransactionCommand)),
        )
        return ast.TransactionActivity._ProcedureSpecificationEndTransactionCommand(
            procedure_specification=procedure_specification,
            end_transaction_command=end_transaction_command,
        )

    candidates_transaction_activity = (
        parser.get_parser(ast.EndTransactionCommand),
        _parse__start_transaction_command_procedure_specification_end_transaction_command,
        _parse__procedure_specification_end_transaction_command,
    )
    (transaction_activity,) = parser.seq(candidates_transaction_activity)
    return ast.TransactionActivity(
        transaction_activity=transaction_activity,
    )


@parses(ast.GraphVariableDefinition)
def parse_graph_variable_definition(parser: Parser) -> ast.GraphVariableDefinition:
    (
        _,
        binding_variable,
        opt_typed_graph_initializer,
    ) = parser.seq(
        TokenType.GRAPH,
        parser.get_parser(ast.BindingVariable),
        parser.get_parser(ast.OptTypedGraphInitializer),
    )
    return ast.GraphVariableDefinition(
        binding_variable=binding_variable,
        opt_typed_graph_initializer=opt_typed_graph_initializer,
    )


@parses(ast.BindingTableVariableDefinition)
def parse_binding_table_variable_definition(parser: Parser) -> ast.BindingTableVariableDefinition:
    (
        _,  # [ BINDING ] TABLE
        binding_variable,
        opt_typed_binding_table_initializer,
    ) = parser.seq(
        TokenType.TABLE,
        parser.get_parser(ast.BindingVariable),
        parser.get_parser(ast.OptTypedBindingTableInitializer),
    )
    return ast.BindingTableVariableDefinition(
        binding_variable=binding_variable,
        opt_typed_binding_table_initializer=opt_typed_binding_table_initializer,
    )


@parses(ast.ValueVariableDefinition)
def parse_value_variable_definition(parser: Parser) -> ast.ValueVariableDefinition:
    (
        _,
        binding_variable,
        opt_typed_value_initializer,
    ) = parser.seq(
        TokenType.VALUE,
        parser.get_parser(ast.BindingVariable),
        parser.get_parser(ast.OptTypedValueInitializer),
    )
    return ast.ValueVariableDefinition(
        binding_variable=binding_variable,
        opt_typed_value_initializer=opt_typed_value_initializer,
    )


@parses(ast.CurrentGraph)
def parse_current_graph(parser: Parser) -> ast.CurrentGraph:
    parser.seq(TokenType.CURRENT_GRAPH)
    return ast.CurrentGraph()


@parses(ast.GraphReference)
def parse_graph_reference(parser: Parser) -> ast.GraphReference:
    def _parse__catalog_object_parent_reference_graph_name(
        parser: Parser,
    ) -> ast.GraphReference._CatalogObjectParentReferenceGraphName:
        (
            catalog_object_parent_reference,
            graph_name,
        ) = parser.seq(
            parser.get_parser(ast.CatalogObjectParentReference),
            parser.get_parser(ast.GraphName),
        )
        return ast.GraphReference._CatalogObjectParentReferenceGraphName(
            catalog_object_parent_reference=catalog_object_parent_reference,
            graph_name=graph_name,
        )

    # NOTE: ReferenceParameterSpecification must be tried first because $$ is a distinctive
    # token that won't be confused with other candidates. If tried last, the parser may
    # incorrectly route $$param through CatalogObjectParentReference which fails validation.
    candidates_graph_reference = (
        parser.get_parser(ast.ReferenceParameterSpecification),
        _parse__catalog_object_parent_reference_graph_name,
        parser.get_parser(ast.DelimitedGraphName),
        parser.get_parser(ast.HomeGraph),
    )
    (graph_reference,) = parser.seq(candidates_graph_reference)
    return ast.GraphReference(
        graph_reference=graph_reference,
    )


@parses(ast.ObjectExpressionPrimary)
def parse_object_expression_primary(parser: Parser) -> ast.ObjectExpressionPrimary:
    def _parse__variable_value_expression_primary(
        parser: Parser,
    ) -> ast.ObjectExpressionPrimary._VariableValueExpressionPrimary:
        (value_expression_primary,) = parser.seq(
            parser.get_parser(ast.ValueExpressionPrimary),
        )
        return ast.ObjectExpressionPrimary._VariableValueExpressionPrimary(
            value_expression_primary=value_expression_primary,
        )

    candidates_object_expression_primary = (
        _parse__variable_value_expression_primary,
        parser.get_parser(ast.ParenthesizedValueExpression),
        parser.get_parser(ast.NonParenthesizedValueExpressionPrimarySpecialCase),
    )
    (object_expression_primary,) = parser.seq(candidates_object_expression_primary)
    return ast.ObjectExpressionPrimary(
        object_expression_primary=object_expression_primary,
    )


@parses(ast.BindingTableReference)
def parse_binding_table_reference(parser: Parser) -> ast.BindingTableReference:
    def _parse__catalog_object_parent_reference_binding_table_name(
        parser: Parser,
    ) -> ast.BindingTableReference._CatalogObjectParentReferenceBindingTableName:
        (
            catalog_object_parent_reference,
            binding_table_name,
        ) = parser.seq(
            parser.get_parser(ast.CatalogObjectParentReference),
            parser.get_parser(ast.BindingTableName),
        )
        return ast.BindingTableReference._CatalogObjectParentReferenceBindingTableName(
            catalog_object_parent_reference=catalog_object_parent_reference,
            binding_table_name=binding_table_name,
        )

    candidates_binding_table_reference = (
        _parse__catalog_object_parent_reference_binding_table_name,
        parser.get_parser(ast.DelimitedBindingTableName),
        parser.get_parser(ast.ReferenceParameterSpecification),
    )
    (binding_table_reference,) = parser.seq(candidates_binding_table_reference)
    return ast.BindingTableReference(
        binding_table_reference=binding_table_reference,
    )


@parses(ast.SetPropertyItem)
def parse_set_property_item(parser: Parser) -> ast.SetPropertyItem:
    (
        binding_variable_reference,
        _,
        property_name,
        _,
        value_expression,
    ) = parser.seq(
        parser.get_parser(ast.BindingVariableReference),
        TokenType.PERIOD,
        parser.get_parser(ast.PropertyName),
        TokenType.EQUALS_OPERATOR,
        parser.get_parser(ast.ValueExpression),
    )
    return ast.SetPropertyItem(
        binding_variable_reference=binding_variable_reference,
        property_name=property_name,
        value_expression=value_expression,
    )


@parses(ast.SetAllPropertiesItem)
def parse_set_all_properties_item(parser: Parser) -> ast.SetAllPropertiesItem:
    (
        binding_variable_reference,
        _,
        _,
        property_key_value_pair_list,
        _,
    ) = parser.seq(
        parser.get_parser(ast.BindingVariableReference),
        TokenType.EQUALS_OPERATOR,
        TokenType.LEFT_BRACE,
        parser.opt(parser.get_parser(ast.PropertyKeyValuePairList)),
        TokenType.RIGHT_BRACE,
    )
    return ast.SetAllPropertiesItem(
        binding_variable_reference=binding_variable_reference,
        property_key_value_pair_list=property_key_value_pair_list,
    )


@parses(ast.SetLabelItem)
def parse_set_label_item(parser: Parser) -> ast.SetLabelItem:
    (
        binding_variable_reference,
        _,
        label_name,
    ) = parser.seq(
        parser.get_parser(ast.BindingVariableReference),
        {TokenType.IS, TokenType.COLON},
        parser.get_parser(ast.LabelName),
    )
    return ast.SetLabelItem(
        binding_variable_reference=binding_variable_reference,
        label_name=label_name,
    )


@parses(ast.RemovePropertyItem)
def parse_remove_property_item(parser: Parser) -> ast.RemovePropertyItem:
    (
        binding_variable_reference,
        _,
        property_name,
    ) = parser.seq(
        parser.get_parser(ast.BindingVariableReference),
        TokenType.PERIOD,
        parser.get_parser(ast.PropertyName),
    )
    return ast.RemovePropertyItem(
        binding_variable_reference=binding_variable_reference,
        property_name=property_name,
    )


@parses(ast.RemoveLabelItem)
def parse_remove_label_item(parser: Parser) -> ast.RemoveLabelItem:
    (
        binding_variable_reference,
        _,
        label_name,
    ) = parser.seq(
        parser.get_parser(ast.BindingVariableReference),
        {TokenType.IS, TokenType.COLON},
        parser.get_parser(ast.LabelName),
    )
    return ast.RemoveLabelItem(
        binding_variable_reference=binding_variable_reference,
        label_name=label_name,
    )


@parses(ast.InlineProcedureCall)
def parse_inline_procedure_call(parser: Parser) -> ast.InlineProcedureCall:
    (
        variable_scope_clause,
        nested_procedure_specification,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.VariableScopeClause)),
        parser.get_parser(ast.NestedProcedureSpecification),
    )
    return ast.InlineProcedureCall(
        variable_scope_clause=variable_scope_clause,
        nested_procedure_specification=nested_procedure_specification,
    )


@parses(ast.NamedProcedureCall)
def parse_named_procedure_call(parser: Parser) -> ast.NamedProcedureCall:
    (
        procedure_reference,
        _,
        procedure_argument_list,
        _,
        yield_clause,
    ) = parser.seq(
        parser.get_parser(ast.ProcedureReference),
        TokenType.LEFT_PAREN,
        parser.opt(parser.get_parser(ast.ProcedureArgumentList)),
        TokenType.RIGHT_PAREN,
        parser.opt(parser.get_parser(ast.YieldClause)),
    )
    return ast.NamedProcedureCall(
        procedure_reference=procedure_reference,
        procedure_argument_list=procedure_argument_list,
        yield_clause=yield_clause,
    )


@parses(ast.RepeatableElementsMatchMode)
def parse_repeatable_elements_match_mode(parser: Parser) -> ast.RepeatableElementsMatchMode:
    def _parser_element_bindings_or_elements(
        parser: Parser,
    ) -> ast.RepeatableElementsMatchMode.Mode:
        candidates = (
            lambda parser: parser.seq(TokenType.ELEMENT, TokenType.BINDINGS),
            lambda parser: parser.seq(TokenType.ELEMENT),
            lambda parser: parser.seq(TokenType.ELEMENTS),
        )

        (result,) = parser.seq(candidates)

        if len(result) == 1:
            match result[0].token_type:
                case TokenType.ELEMENT:
                    return ast.RepeatableElementsMatchMode.Mode.ELEMENT
                case TokenType.ELEMENTS:
                    return ast.RepeatableElementsMatchMode.Mode.ELEMENTS
        elif len(result) == 2:
            expected = [TokenType.ELEMENT, TokenType.BINDINGS]
            if [token.token_type for token in result] == expected:
                return ast.RepeatableElementsMatchMode.Mode.ELEMENT_BINDINGS
        raise AssertionError(f"Unexpected repeatable mode token sequence: {result}")

    (
        _,
        mode,
    ) = parser.seq(
        TokenType.REPEATABLE,
        _parser_element_bindings_or_elements,
    )
    return ast.RepeatableElementsMatchMode(mode=mode)


@parses(ast.DifferentEdgesMatchMode)
def parse_different_edges_match_mode(parser: Parser) -> ast.DifferentEdgesMatchMode:
    def _parser_mode(parser: Parser) -> ast.DifferentEdgesMatchMode.Mode:
        candidates = (
            lambda parser: parser.seq(TokenType.EDGE, TokenType.BINDINGS),
            lambda parser: parser.seq(TokenType.EDGE),
            lambda parser: parser.seq(TokenType.EDGES),
        )

        (result,) = parser.seq(candidates)

        if len(result) == 1:
            match result[0].token_type:
                case TokenType.EDGE:
                    return ast.DifferentEdgesMatchMode.Mode.EDGE
                case TokenType.EDGES:
                    return ast.DifferentEdgesMatchMode.Mode.EDGES
        elif len(result) == 2:
            expected = [TokenType.EDGE, TokenType.BINDINGS]
            if [token.token_type for token in result] == expected:
                return ast.DifferentEdgesMatchMode.Mode.EDGE_BINDINGS
        raise ValueError("Invalid different edges match mode")

    (
        _,
        mode,
    ) = parser.seq(
        TokenType.DIFFERENT,
        _parser_mode,
    )
    return ast.DifferentEdgesMatchMode(
        mode=mode,
    )


@parses(ast.InsertEdgePointingLeft)
def parse_insert_edge_pointing_left(parser: Parser) -> ast.InsertEdgePointingLeft:
    (_, insert_element_pattern_filler, _) = parser.seq(
        TokenType.LEFT_ARROW_BRACKET,
        parser.opt(parser.get_parser(ast.InsertElementPatternFiller)),
        TokenType.RIGHT_BRACKET_MINUS,
    )
    return ast.InsertEdgePointingLeft(
        insert_element_pattern_filler=insert_element_pattern_filler,
    )


@parses(ast.InsertEdgePointingRight)
def parse_insert_edge_pointing_right(parser: Parser) -> ast.InsertEdgePointingRight:
    (
        _,
        insert_element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.MINUS_LEFT_BRACKET,
        parser.opt(parser.get_parser(ast.InsertElementPatternFiller)),
        TokenType.BRACKET_RIGHT_ARROW,
    )
    return ast.InsertEdgePointingRight(
        insert_element_pattern_filler=insert_element_pattern_filler,
    )


@parses(ast.InsertEdgeUndirected)
def parse_insert_edge_undirected(parser: Parser) -> ast.InsertEdgeUndirected:
    (
        _,
        insert_element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.TILDE_LEFT_BRACKET,
        parser.opt(parser.get_parser(ast.InsertElementPatternFiller)),
        TokenType.RIGHT_BRACKET_TILDE,
    )
    return ast.InsertEdgeUndirected(
        insert_element_pattern_filler=insert_element_pattern_filler,
    )


@parses(ast.PathModePrefix)
def parse_path_mode_prefix(parser: Parser) -> ast.PathModePrefix:
    (
        path_mode,
        path_or_paths,
    ) = parser.seq(
        parser.get_parser(ast.PathMode),
        parser.opt(parser.get_parser(ast.PathOrPaths)),
    )
    return ast.PathModePrefix(
        path_mode=path_mode,
        path_or_paths=path_or_paths,
    )


@parses(ast.PathSearchPrefix)
def parse_path_search_prefix(parser: Parser) -> ast.PathSearchPrefix:
    # Order matters: ShortestPathSearch must come before AnyPathSearch and AllPathSearch
    # because it has longer prefixes (e.g., "ANY SHORTEST" vs "ANY", "ALL SHORTEST" vs "ALL")
    candidates_path_search_prefix = (
        parser.get_parser(ast.ShortestPathSearch),
        parser.get_parser(ast.AllPathSearch),
        parser.get_parser(ast.AnyPathSearch),
    )
    (result,) = parser.seq(candidates_path_search_prefix)
    return result


@parses(ast.PathMultisetAlternation)
def parse_path_multiset_alternation(parser: Parser) -> ast.PathMultisetAlternation:
    (list_path_term,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.PathTerm),
            TokenType.MULTISET_ALTERNATION_OPERATOR,
            min_items=2,
        ),
    )
    return ast.PathMultisetAlternation(list_path_term=list_path_term)


@parses(ast.PathPatternUnion)
def parse_path_pattern_union(parser: Parser) -> ast.PathPatternUnion:
    (list_path_term,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.PathTerm),
            TokenType.VERTICAL_BAR,
            min_items=2,
        ),
    )
    return ast.PathPatternUnion(
        list_path_term=list_path_term,
    )


@parses(ast.PathTerm)
def parse_path_term(parser: Parser) -> ast.PathTerm:
    (factors,) = parser.seq(
        parser.list_(parser.get_parser(ast.PathFactor), None),
    )
    return ast.PathTerm(factors=factors)


@parses(ast.ElementPropertySpecification)
def parse_element_property_specification(parser: Parser) -> ast.ElementPropertySpecification:
    (
        _,
        property_key_value_pair_list,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.get_parser(ast.PropertyKeyValuePairList),
        TokenType.RIGHT_BRACE,
    )
    return ast.ElementPropertySpecification(
        property_key_value_pair_list=property_key_value_pair_list,
    )


@parses(ast.LabelTerm)
def parse_label_term(parser: Parser) -> ast.LabelTerm:
    (label_factors,) = parser.seq(
        parser.list_(parser.get_parser(ast.LabelFactor), TokenType.AMPERSAND),
    )
    return ast.LabelTerm(label_factors=label_factors)


@parses(ast.FixedQuantifier)
def parse_fixed_quantifier(parser: Parser) -> ast.FixedQuantifier:
    (
        _,
        unsigned_integer,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.get_parser(ast.UnsignedInteger),
        TokenType.RIGHT_BRACE,
    )
    return ast.FixedQuantifier(
        unsigned_integer=unsigned_integer,
    )


@parses(ast.GeneralQuantifier)
def parse_general_quantifier(parser: Parser) -> ast.GeneralQuantifier:
    (
        _,
        lower_bound,
        _,
        upper_bound,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.opt(parser.get_parser(ast.LowerBound)),
        TokenType.COMMA,
        parser.opt(parser.get_parser(ast.UpperBound)),
        TokenType.RIGHT_BRACE,
    )
    return ast.GeneralQuantifier(
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )


@parses(ast.Asterisk)
def parse_asterisk(parser: Parser) -> ast.Asterisk:
    parser.seq(TokenType.ASTERISK)
    return ast.Asterisk()


@parses(ast.SimplifiedPathUnion)
def parse_simplified_path_union(parser: Parser) -> ast.SimplifiedPathUnion:
    (list_simplified_term,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.SimplifiedTerm),
            TokenType.VERTICAL_BAR,
            min_items=2,
        ),
    )
    return ast.SimplifiedPathUnion(
        list_simplified_term=list_simplified_term,
    )


@parses(ast.SimplifiedMultisetAlternation)
def parse_simplified_multiset_alternation(parser: Parser) -> ast.SimplifiedMultisetAlternation:
    (list_simplified_terms,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.SimplifiedTerm),
            TokenType.MULTISET_ALTERNATION_OPERATOR,
            min_items=2,
        ),
    )
    return ast.SimplifiedMultisetAlternation(list_simplified_terms=list_simplified_terms)


@parses(ast.SimplifiedTerm)
def parse_simplified_term(parser: Parser) -> ast.SimplifiedTerm:
    candidates_simplified_term = (
        parser.get_parser(ast.SimplifiedFactorLow),
        parser.get_parser(ast.SimplifiedConcatenation),
    )
    (result,) = parser.seq(candidates_simplified_term)
    return result


@parses(ast.AbsoluteCatalogSchemaReference)
def parse_absolute_catalog_schema_reference(parser: Parser) -> ast.AbsoluteCatalogSchemaReference:
    def _parse__absolute_directory_path_schema_name(
        parser: Parser,
    ) -> ast.AbsoluteCatalogSchemaReference._AbsoluteDirectoryPathSchemaName:
        (
            absolute_directory_path,
            schema_name,
        ) = parser.seq(
            parser.get_parser(ast.AbsoluteDirectoryPath),
            parser.get_parser(ast.SchemaName),
        )
        return ast.AbsoluteCatalogSchemaReference._AbsoluteDirectoryPathSchemaName(
            absolute_directory_path=absolute_directory_path,
            schema_name=schema_name,
        )

    candidates_absolute_catalog_schema_reference = (
        _parse__absolute_directory_path_schema_name,
        parser.get_parser(ast.Solidus),  # Order is important here
    )
    (absolute_catalog_schema_reference,) = parser.seq(candidates_absolute_catalog_schema_reference)
    return ast.AbsoluteCatalogSchemaReference(
        absolute_catalog_schema_reference=absolute_catalog_schema_reference,
    )


@parses(ast.RelativeCatalogSchemaReference)
def parse_relative_catalog_schema_reference(parser: Parser) -> ast.RelativeCatalogSchemaReference:
    def _parse__relative_directory_path_schema_name(
        parser: Parser,
    ) -> ast.RelativeCatalogSchemaReference._RelativeDirectoryPathSchemaName:
        (
            relative_directory_path,
            schema_name,
        ) = parser.seq(
            parser.get_parser(ast.RelativeDirectoryPath),
            parser.get_parser(ast.SchemaName),
        )
        return ast.RelativeCatalogSchemaReference._RelativeDirectoryPathSchemaName(
            relative_directory_path=relative_directory_path,
            schema_name=schema_name,
        )

    candidates_relative_catalog_schema_reference = (
        parser.get_parser(ast.PredefinedSchemaReference),
        _parse__relative_directory_path_schema_name,
    )
    (relative_catalog_schema_reference,) = parser.seq(candidates_relative_catalog_schema_reference)
    return ast.RelativeCatalogSchemaReference(
        relative_catalog_schema_reference=relative_catalog_schema_reference,
    )


@parses(ast.CatalogGraphTypeParentAndName)
def parse_catalog_graph_type_parent_and_name(parser: Parser) -> ast.CatalogGraphTypeParentAndName:
    (
        catalog_object_parent_reference,
        graph_type_name,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.CatalogObjectParentReference)),
        parser.get_parser(ast.GraphTypeName),
    )
    return ast.CatalogGraphTypeParentAndName(
        catalog_object_parent_reference=catalog_object_parent_reference,
        graph_type_name=graph_type_name,
    )


@parses(ast.CatalogProcedureParentAndName)
def parse_catalog_procedure_parent_and_name(parser: Parser) -> ast.CatalogProcedureParentAndName:
    candidates = (
        lambda parser: parser.seq(
            parser.get_parser(ast.CatalogObjectParentReference),
            parser.get_parser(ast.ProcedureName),
        ),
        parser.get_parser(ast.ProcedureName),
    )

    (result,) = parser.seq(candidates)
    if isinstance(result, ast.ProcedureName):
        return ast.CatalogProcedureParentAndName(
            catalog_object_parent_reference=None,
            procedure_name=result,
        )
    else:
        (catalog_object_parent_reference, procedure_name) = result
        return ast.CatalogProcedureParentAndName(
            catalog_object_parent_reference=catalog_object_parent_reference,
            procedure_name=procedure_name,
        )


@parses(ast.NodeTypeSpecification)
def parse_node_type_specification(parser: Parser) -> ast.NodeTypeSpecification:
    candidates_node_type_specification = (
        parser.get_parser(ast.NodeTypePattern),
        parser.get_parser(ast.NodeTypePhrase),
    )
    (result,) = parser.seq(candidates_node_type_specification)
    return result


@parses(ast.EdgeTypeSpecification)
def parse_edge_type_specification(parser: Parser) -> ast.EdgeTypeSpecification:
    candidates_edge_type_specification = (
        parser.get_parser(ast.EdgeTypePattern),
        parser.get_parser(ast.EdgeTypePhrase),
    )
    (result,) = parser.seq(candidates_edge_type_specification)
    return result


@parses(ast.EdgeTypePatternPointingRight)
def parse_edge_type_pattern_pointing_right(parser: Parser) -> ast.EdgeTypePatternPointingRight:
    (
        source_node_type_reference,
        arc_type_pointing_right,
        destination_node_type_reference,
    ) = parser.seq(
        parser.get_parser(ast.SourceNodeTypeReference),
        parser.get_parser(ast.ArcTypePointingRight),
        parser.get_parser(ast.DestinationNodeTypeReference),
    )
    return ast.EdgeTypePatternPointingRight(
        source_node_type_reference=source_node_type_reference,
        arc_type_pointing_right=arc_type_pointing_right,
        destination_node_type_reference=destination_node_type_reference,
    )


@parses(ast.EdgeTypePatternPointingLeft)
def parse_edge_type_pattern_pointing_left(parser: Parser) -> ast.EdgeTypePatternPointingLeft:
    (
        destination_node_type_reference,
        arc_type_pointing_left,
        source_node_type_reference,
    ) = parser.seq(
        parser.get_parser(ast.DestinationNodeTypeReference),
        parser.get_parser(ast.ArcTypePointingLeft),
        parser.get_parser(ast.SourceNodeTypeReference),
    )
    return ast.EdgeTypePatternPointingLeft(
        destination_node_type_reference=destination_node_type_reference,
        arc_type_pointing_left=arc_type_pointing_left,
        source_node_type_reference=source_node_type_reference,
    )


@parses(ast.EndpointPairDirected)
def parse_endpoint_pair_directed(parser: Parser) -> ast.EndpointPairDirected:
    candidates_endpoint_pair_directed = (
        parser.get_parser(ast.EndpointPairPointingRight),
        parser.get_parser(ast.EndpointPairPointingLeft),
    )
    (result,) = parser.seq(candidates_endpoint_pair_directed)
    return result


@parses(ast.EndpointPairUndirected)
def parse_endpoint_pair_undirected(parser: Parser) -> ast.EndpointPairUndirected:
    (
        _,
        source_node_type_alias,
        connector_undirected,
        destination_node_type_alias,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.SourceNodeTypeAlias),
        parser.get_parser(ast.ConnectorUndirected),
        parser.get_parser(ast.DestinationNodeTypeAlias),
        TokenType.RIGHT_PAREN,
    )
    return ast.EndpointPairUndirected(
        source_node_type_alias=source_node_type_alias,
        connector_undirected=connector_undirected,
        destination_node_type_alias=destination_node_type_alias,
    )


@parses(ast.GeneralValueSpecification)
def parse_general_value_specification(parser: Parser) -> ast.GeneralValueSpecification:
    _parse__session_user = token_parser(
        TokenType.SESSION_USER, ast_type=ast.GeneralValueSpecification._SessionUser
    )

    candidates_general_value_specification = (
        parser.get_parser(ast.DynamicParameterSpecification),
        _parse__session_user,
    )
    (general_value_specification,) = parser.seq(candidates_general_value_specification)
    return ast.GeneralValueSpecification(
        general_value_specification=general_value_specification,
    )


@parses(ast.UnsignedInteger)
def parse_unsigned_integer(parser: Parser) -> ast.UnsignedInteger:
    import re

    integer_literal_re = re.compile(r"[0-9]+")

    (string_value,) = parser.seq(TokenType.NUMBER)

    token_text = string_value.text

    if not integer_literal_re.fullmatch(token_text):
        parser.raise_error(
            f"Expected integer literal, got non-integer numeric literal: {token_text}"
        )

    # 3. Safe to convert
    try:
        value = int(token_text)
    except ValueError:
        parser.raise_error(f"Invalid integer literal: {token_text}")

    return ast.UnsignedInteger(
        value=value,
    )


@parses(ast.CaseAbbreviation)
def parse_case_abbreviation(parser: Parser) -> ast.CaseAbbreviation:
    def _parse__nullif_left_paren_value_expression_comma_value_expression_right_paren(
        parser: Parser,
    ) -> ast.CaseAbbreviation._NullifLeftParenValueExpressionCommaValueExpressionRightParen:
        (_, _, value_expression_1, _, value_expression_2, _) = parser.seq(
            TokenType.NULLIF,
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.ValueExpression),
            TokenType.COMMA,
            parser.get_parser(ast.ValueExpression),
            TokenType.RIGHT_PAREN,
        )
        return ast.CaseAbbreviation._NullifLeftParenValueExpressionCommaValueExpressionRightParen(
            value_expression_1=value_expression_1,
            value_expression_2=value_expression_2,
        )

    def _parse__coalesce_left_paren_list_value_expression_right_paren(
        parser: Parser,
    ) -> ast.CaseAbbreviation._CoalesceLeftParenListValueExpressionRightParen:
        (
            _,
            _,
            list_value_expression,
            _,
        ) = parser.seq(
            TokenType.COALESCE,
            TokenType.LEFT_PAREN,
            parser.list_(parser.get_parser(ast.ValueExpression), TokenType.COMMA),
            TokenType.RIGHT_PAREN,
        )
        return ast.CaseAbbreviation._CoalesceLeftParenListValueExpressionRightParen(
            list_value_expression=list_value_expression,
        )

    candidates_case_abbreviation = (
        _parse__nullif_left_paren_value_expression_comma_value_expression_right_paren,
        _parse__coalesce_left_paren_list_value_expression_right_paren,
    )
    (case_abbreviation,) = parser.seq(candidates_case_abbreviation)
    return ast.CaseAbbreviation(
        case_abbreviation=case_abbreviation,
    )


@parses(ast.CaseSpecification)
def parse_case_specification(parser: Parser) -> ast.CaseSpecification:
    candidates_case_specification = (
        parser.get_parser(ast.SimpleCase),
        parser.get_parser(ast.SearchedCase),
    )
    (result,) = parser.seq(candidates_case_specification)
    return result


@parses(ast.ComparisonPredicatePart2)
def parse_comparison_predicate_part2(parser: Parser) -> ast.ComparisonPredicatePart2:
    token_set = {
        TokenType.EQUALS_OPERATOR,
        TokenType.NOT_EQUALS_OPERATOR,
        TokenType.LEFT_ANGLE_BRACKET,  # less than operator
        TokenType.RIGHT_ANGLE_BRACKET,  # greater than operator
        TokenType.LESS_THAN_OR_EQUALS_OPERATOR,
        TokenType.GREATER_THAN_OR_EQUALS_OPERATOR,
    }

    (
        comp_op,
        comparison_predicand,
    ) = parser.seq(
        token_set,
        parser.get_parser(ast.ComparisonPredicand),
    )

    match comp_op.token_type:
        case TokenType.EQUALS_OPERATOR:
            comp_op = ast.ComparisonPredicatePart2.CompOp.EQUALS
        case TokenType.NOT_EQUALS_OPERATOR:
            comp_op = ast.ComparisonPredicatePart2.CompOp.NOT_EQUALS
        case TokenType.LEFT_ANGLE_BRACKET:
            comp_op = ast.ComparisonPredicatePart2.CompOp.LESS_THAN
        case TokenType.RIGHT_ANGLE_BRACKET:
            comp_op = ast.ComparisonPredicatePart2.CompOp.GREATER_THAN
        case TokenType.LESS_THAN_OR_EQUALS_OPERATOR:
            comp_op = ast.ComparisonPredicatePart2.CompOp.LESS_THAN_OR_EQUALS
        case TokenType.GREATER_THAN_OR_EQUALS_OPERATOR:
            comp_op = ast.ComparisonPredicatePart2.CompOp.GREATER_THAN_OR_EQUALS

    return ast.ComparisonPredicatePart2(
        comp_op=comp_op,
        comparison_predicand=comparison_predicand,
    )


@parses(ast.NullPredicatePart2)
def parse_null_predicate_part2(parser: Parser) -> ast.NullPredicatePart2:
    (
        _,
        not_,
        _,
    ) = parser.seq(
        TokenType.IS,
        parser.opt(TokenType.NOT),
        TokenType.NULL,
    )
    return ast.NullPredicatePart2(
        not_=bool(not_),
    )


@parses(ast.ValueTypePredicatePart2)
def parse_value_type_predicate_part2(parser: Parser) -> ast.ValueTypePredicatePart2:
    (
        _,
        not_,
        typed,
        value_type,
    ) = parser.seq(
        TokenType.IS,
        parser.opt(TokenType.NOT),
        parser.get_parser(ast.Typed),
        parser.get_parser(ast.ValueType),
    )
    return ast.ValueTypePredicatePart2(
        not_=bool(not_),
        typed=typed,
        value_type=value_type,
    )


@parses(ast.NormalizedPredicatePart2)
def parse_normalized_predicate_part2(parser: Parser) -> ast.NormalizedPredicatePart2:
    (
        _,
        not_,
        normal_form,
        _,
    ) = parser.seq(
        TokenType.IS,
        parser.opt(TokenType.NOT),
        parser.opt(parser.get_parser(ast.NormalForm)),
        TokenType.NORMALIZED,
    )
    return ast.NormalizedPredicatePart2(
        not_=bool(not_),
        normal_form=normal_form,
    )


@parses(ast.DirectedPredicatePart2)
def parse_directed_predicate_part2(parser: Parser) -> ast.DirectedPredicatePart2:
    (
        _,
        not_,
        _,
    ) = parser.seq(
        TokenType.IS,
        parser.opt(TokenType.NOT),
        TokenType.DIRECTED,
    )
    return ast.DirectedPredicatePart2(
        not_=bool(not_),
    )


@parses(ast.LabeledPredicatePart2)
def parse_labeled_predicate_part2(parser: Parser) -> ast.LabeledPredicatePart2:
    (
        is_labeled_or_colon,
        label_expression,
    ) = parser.seq(
        parser.get_parser(ast.IsLabeledOrColon),
        parser.get_parser(ast.LabelExpression),
    )
    return ast.LabeledPredicatePart2(
        is_labeled_or_colon=is_labeled_or_colon,
        label_expression=label_expression,
    )


@parses(ast.SourcePredicatePart2)
def parse_source_predicate_part2(parser: Parser) -> ast.SourcePredicatePart2:
    (
        _,
        not_,
        _,
        _,
        edge_reference,
    ) = parser.seq(
        TokenType.IS,
        parser.opt(TokenType.NOT),
        TokenType.SOURCE,
        TokenType.OF,
        parser.get_parser(ast.EdgeReference),
    )
    return ast.SourcePredicatePart2(
        not_=bool(not_),
        edge_reference=edge_reference,
    )


@parses(ast.DestinationPredicatePart2)
def parse_destination_predicate_part2(parser: Parser) -> ast.DestinationPredicatePart2:
    (
        _,
        not_,
        _,
        _,
        edge_reference,
    ) = parser.seq(
        TokenType.IS,
        parser.opt(TokenType.NOT),
        TokenType.DESTINATION,
        TokenType.OF,
        parser.get_parser(ast.EdgeReference),
    )
    return ast.DestinationPredicatePart2(
        not_=bool(not_),
        edge_reference=edge_reference,
    )


@parses(ast.TrimListFunction)
def parse_trim_list_function(parser: Parser) -> ast.TrimListFunction:
    (
        _,
        _,
        list_value_expression,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.TRIM,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ListValueExpression),
        TokenType.COMMA,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.TrimListFunction(
        list_value_expression=list_value_expression,
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.ElementsFunction)
def parse_elements_function(parser: Parser) -> ast.ElementsFunction:
    (
        _,
        _,
        path_value_expression,
        _,
    ) = parser.seq(
        TokenType.ELEMENTS,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.PathValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ElementsFunction(
        path_value_expression=path_value_expression,
    )


@parses(ast.BooleanPredicand)
def parse_boolean_predicand(parser: Parser) -> ast.BooleanPredicand:
    candidates_boolean_predicand = (
        parser.get_parser(ast.ParenthesizedBooleanValueExpression),
        parser.get_parser(ast.NonParenthesizedValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates_boolean_predicand)
    return result


@parses(ast.TrigonometricFunction)
def parse_trigonometric_function(parser: Parser) -> ast.TrigonometricFunction:
    (
        trigonometric_function_name,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        parser.get_parser(ast.TrigonometricFunctionName),
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.TrigonometricFunction(
        trigonometric_function_name=trigonometric_function_name,
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.GeneralLogarithmFunction)
def parse_general_logarithm_function(parser: Parser) -> ast.GeneralLogarithmFunction:
    (
        _,
        _,
        general_logarithm_base,
        _,
        general_logarithm_argument,
        _,
    ) = parser.seq(
        TokenType.LOG,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.GeneralLogarithmBase),
        TokenType.COMMA,
        parser.get_parser(ast.GeneralLogarithmArgument),
        TokenType.RIGHT_PAREN,
    )
    return ast.GeneralLogarithmFunction(
        general_logarithm_base=general_logarithm_base,
        general_logarithm_argument=general_logarithm_argument,
    )


@parses(ast.CommonLogarithm)
def parse_common_logarithm(parser: Parser) -> ast.CommonLogarithm:
    (
        _,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.LOG10,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.CommonLogarithm(
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.NaturalLogarithm)
def parse_natural_logarithm(parser: Parser) -> ast.NaturalLogarithm:
    (
        _,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.LN,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.NaturalLogarithm(
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.ExponentialFunction)
def parse_exponential_function(parser: Parser) -> ast.ExponentialFunction:
    (
        _,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.EXP,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ExponentialFunction(
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.PowerFunction)
def parse_power_function(parser: Parser) -> ast.PowerFunction:
    (
        _,
        _,
        numeric_value_expression_base,
        _,
        numeric_value_expression_exponent,
        _,
    ) = parser.seq(
        TokenType.POWER,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpressionBase),
        TokenType.COMMA,
        parser.get_parser(ast.NumericValueExpressionExponent),
        TokenType.RIGHT_PAREN,
    )
    return ast.PowerFunction(
        numeric_value_expression_base=numeric_value_expression_base,
        numeric_value_expression_exponent=numeric_value_expression_exponent,
    )


@parses(ast.SquareRoot)
def parse_square_root(parser: Parser) -> ast.SquareRoot:
    (
        _,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.SQRT,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.SquareRoot(
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.FloorFunction)
def parse_floor_function(parser: Parser) -> ast.FloorFunction:
    (
        _,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.FLOOR,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.FloorFunction(
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.CeilingFunction)
def parse_ceiling_function(parser: Parser) -> ast.CeilingFunction:
    (
        _,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.CEIL,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.CeilingFunction(
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.SubstringFunction)
def parse_substring_function(parser: Parser) -> ast.SubstringFunction:
    (token, _, character_string_value_expression, _, string_length, _) = parser.seq(
        {TokenType.LEFT, TokenType.RIGHT},
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.CharacterStringValueExpression),
        TokenType.COMMA,
        parser.get_parser(ast.StringLength),
        TokenType.RIGHT_PAREN,
    )
    match token.token_type:
        case TokenType.LEFT:
            mode = ast.SubstringFunction.Mode.LEFT
        case TokenType.RIGHT:
            mode = ast.SubstringFunction.Mode.RIGHT

    return ast.SubstringFunction(
        mode=mode,
        character_string_value_expression=character_string_value_expression,
        string_length=string_length,
    )


@parses(ast.Fold)
def parse_fold(parser: Parser) -> ast.Fold:
    (
        fold,
        _,
        character_string_value_expression,
        _,
    ) = parser.seq(
        {TokenType.UPPER, TokenType.LOWER},
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.CharacterStringValueExpression),
        TokenType.RIGHT_PAREN,
    )

    match fold.token_type:
        case TokenType.UPPER:
            mode = ast.Fold.Mode.UPPER
        case TokenType.LOWER:
            mode = ast.Fold.Mode.LOWER

    return ast.Fold(
        mode=mode,
        character_string_value_expression=character_string_value_expression,
    )


@parses(ast.TrimFunction)
def parse_trim_function(parser: Parser) -> ast.TrimFunction:
    candidates_trim_function = (
        parser.get_parser(ast.SingleCharacterTrimFunction),
        parser.get_parser(ast.MultiCharacterTrimFunction),
    )
    (result,) = parser.seq(candidates_trim_function)
    return result


@parses(ast.NormalizeFunction)
def parse_normalize_function(parser: Parser) -> ast.NormalizeFunction:
    def _parse_comma_normal_form(parser: Parser) -> ast.NormalForm:
        (
            _,
            normal_form,
        ) = parser.seq(
            TokenType.COMMA,
            parser.get_parser(ast.NormalForm),
        )
        return normal_form

    (
        _,
        _,
        character_string_value_expression,
        normal_form,
        _,
    ) = parser.seq(
        TokenType.NORMALIZE,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.CharacterStringValueExpression),
        parser.opt(_parse_comma_normal_form),
        TokenType.RIGHT_PAREN,
    )
    return ast.NormalizeFunction(
        character_string_value_expression=character_string_value_expression,
        normal_form=normal_form,
    )


@parses(ast.ByteStringSubstringFunction)
def parse_byte_string_substring_function(parser: Parser) -> ast.ByteStringSubstringFunction:
    (
        mode_token,
        _,
        byte_string_value_expression,
        _,
        string_length,
        _,
    ) = parser.seq(
        {TokenType.LEFT, TokenType.RIGHT},
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ByteStringValueExpression),
        TokenType.COMMA,
        parser.get_parser(ast.StringLength),
        TokenType.RIGHT_PAREN,
    )
    match mode_token.token_type:
        case TokenType.LEFT:
            mode = ast.ByteStringSubstringFunction.Mode.LEFT
        case TokenType.RIGHT:
            mode = ast.ByteStringSubstringFunction.Mode.RIGHT

    return ast.ByteStringSubstringFunction(
        mode=mode,
        byte_string_value_expression=byte_string_value_expression,
        string_length=string_length,
    )


@parses(ast.ByteStringTrimFunction)
def parse_byte_string_trim_function(parser: Parser) -> ast.ByteStringTrimFunction:
    (_, _, byte_string_trim_operands, _) = parser.seq(
        TokenType.TRIM,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ByteStringTrimOperands),
        TokenType.RIGHT_PAREN,
    )
    return ast.ByteStringTrimFunction(
        byte_string_trim_operands=byte_string_trim_operands,
    )


@parses(ast.DateFunction)
def parse_date_function(parser: Parser) -> ast.DateFunction:
    _parse__current_date = token_parser(
        TokenType.CURRENT_DATE, ast_type=ast.DateFunction._CurrentDate
    )

    def _parse__date_left_paren_date_function_parameters_right_paren(
        parser: Parser,
    ) -> ast.DateFunction._DateLeftParenDateFunctionParametersRightParen:
        (
            _,
            _,
            date_function_parameters,
            _,
        ) = parser.seq(
            TokenType.DATE,
            TokenType.LEFT_PAREN,
            parser.opt(parser.get_parser(ast.DateFunctionParameters)),
            TokenType.RIGHT_PAREN,
        )
        return ast.DateFunction._DateLeftParenDateFunctionParametersRightParen(
            date_function_parameters=date_function_parameters,
        )

    candidates_date_function = (
        _parse__current_date,
        _parse__date_left_paren_date_function_parameters_right_paren,
    )
    (date_function,) = parser.seq(candidates_date_function)
    return ast.DateFunction(
        date_function=date_function,
    )


@parses(ast.TimeFunction)
def parse_time_function(parser: Parser) -> ast.TimeFunction:
    _parse__current_time = token_parser(
        TokenType.CURRENT_TIME, ast_type=ast.TimeFunction._CurrentTime
    )

    def _parse__zoned_time_left_paren_time_function_parameters_right_paren(
        parser: Parser,
    ) -> ast.TimeFunction._ZonedTimeLeftParenTimeFunctionParametersRightParen:
        (
            _,
            time_function_parameters,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.opt(parser.get_parser(ast.TimeFunctionParameters)),
            TokenType.RIGHT_PAREN,
        )
        return ast.TimeFunction._ZonedTimeLeftParenTimeFunctionParametersRightParen(
            time_function_parameters=time_function_parameters,
        )

    candidates_time_function = (
        _parse__current_time,
        _parse__zoned_time_left_paren_time_function_parameters_right_paren,
    )
    (time_function,) = parser.seq(candidates_time_function)
    return ast.TimeFunction(
        time_function=time_function,
    )


@parses(ast.LocaltimeFunction)
def parse_localtime_function(parser: Parser) -> ast.LocaltimeFunction:
    (time_function_parameters,) = parser.seq(
        parser.opt(parser.get_parser(ast.TimeFunctionParameters)),
    )
    return ast.LocaltimeFunction(
        time_function_parameters=time_function_parameters,
    )


@parses(ast.DatetimeFunction)
def parse_datetime_function(parser: Parser) -> ast.DatetimeFunction:
    _parse__current_timestamp = token_parser(
        TokenType.CURRENT_TIMESTAMP, ast_type=ast.DatetimeFunction._CurrentTimestamp
    )

    def _parse__zoned_datetime_left_paren_datetime_function_parameters_right_paren(
        parser: Parser,
    ) -> ast.DatetimeFunction._ZonedDatetimeLeftParenDatetimeFunctionParametersRightParen:
        (
            _,
            datetime_function_parameters,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.opt(parser.get_parser(ast.DatetimeFunctionParameters)),
            TokenType.RIGHT_PAREN,
        )
        return ast.DatetimeFunction._ZonedDatetimeLeftParenDatetimeFunctionParametersRightParen(
            datetime_function_parameters=datetime_function_parameters,
        )

    candidates_datetime_function = (
        _parse__current_timestamp,
        _parse__zoned_datetime_left_paren_datetime_function_parameters_right_paren,
    )
    (datetime_function,) = parser.seq(candidates_datetime_function)
    return ast.DatetimeFunction(
        datetime_function=datetime_function,
    )


@parses(ast.LocaldatetimeFunction)
def parse_localdatetime_function(parser: Parser) -> ast.LocaldatetimeFunction:
    def _parse__local_timestamp(parser: Parser) -> ast.LocaldatetimeFunction._LocalTimestamp:
        (_,) = parser.seq(TokenType.LOCAL_TIMESTAMP)
        return ast.LocaldatetimeFunction._LocalTimestamp()

    def _parse__local_datetime_left_paren_datetime_function_parameters_right_paren(
        parser: Parser,
    ) -> ast.LocaldatetimeFunction._LocalDatetimeLeftParenDatetimeFunctionParametersRightParen:
        (
            _,
            datetime_function_parameters,
            _,
        ) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.opt(parser.get_parser(ast.DatetimeFunctionParameters)),
            TokenType.RIGHT_PAREN,
        )
        return (
            ast.LocaldatetimeFunction._LocalDatetimeLeftParenDatetimeFunctionParametersRightParen(
                datetime_function_parameters=datetime_function_parameters,
            )
        )

    candidates_localdatetime_function = (
        _parse__local_timestamp,
        _parse__local_datetime_left_paren_datetime_function_parameters_right_paren,
    )
    (localdatetime_function,) = parser.seq(candidates_localdatetime_function)
    return ast.LocaldatetimeFunction(
        localdatetime_function=localdatetime_function,
    )


@parses(ast.DurationFunction)
def parse_duration_function(parser: Parser) -> ast.DurationFunction:
    (
        _,
        _,
        duration_function_parameters,
        _,
    ) = parser.seq(
        TokenType.DURATION,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.DurationFunctionParameters),
        TokenType.RIGHT_PAREN,
    )
    return ast.DurationFunction(
        duration_function_parameters=duration_function_parameters,
    )


@parses(ast.DurationAbsoluteValueFunction)
def parse_duration_absolute_value_function(parser: Parser) -> ast.DurationAbsoluteValueFunction:
    (_, _, duration_value_expression, _) = parser.seq(
        TokenType.ABS,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.DurationValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.DurationAbsoluteValueFunction(
        duration_value_expression=duration_value_expression,
    )


@parses(ast.RecordConstructor)
def parse_record_constructor(parser: Parser) -> ast.RecordConstructor:
    (
        record,
        fields_specification,
    ) = parser.seq(
        parser.opt(TokenType.RECORD),
        parser.get_parser(ast.FieldsSpecification),
    )
    return ast.RecordConstructor(
        record=bool(record),
        fields_specification=fields_specification,
    )


@parses(ast.PathOrSubpathVariable)
def parse_path_or_subpath_variable(parser: Parser) -> ast.PathOrSubpathVariable:
    candidates_path_or_subpath_variable = (
        parser.get_parser(ast.PathVariable),
        parser.get_parser(ast.SubpathVariable),
    )
    (result,) = parser.seq(candidates_path_or_subpath_variable)
    return result


@parses(ast.AllPathSearch)
def parse_all_path_search(parser: Parser) -> ast.AllPathSearch:
    (
        _,
        path_mode,
        path_or_paths,
    ) = parser.seq(
        TokenType.ALL,
        parser.opt(parser.get_parser(ast.PathMode)),
        parser.opt(parser.get_parser(ast.PathOrPaths)),
    )
    return ast.AllPathSearch(
        path_mode=path_mode,
        path_or_paths=path_or_paths,
    )


@parses(ast.AnyPathSearch)
def parse_any_path_search(parser: Parser) -> ast.AnyPathSearch:
    (
        _,
        number_of_paths,
        path_mode,
        path_or_paths,
    ) = parser.seq(
        TokenType.ANY,
        parser.opt(parser.get_parser(ast.NumberOfPaths)),
        parser.opt(parser.get_parser(ast.PathMode)),
        parser.opt(parser.get_parser(ast.PathOrPaths)),
    )
    return ast.AnyPathSearch(
        number_of_paths=number_of_paths,
        path_mode=path_mode,
        path_or_paths=path_or_paths,
    )


@parses(ast.ShortestPathSearch)
def parse_shortest_path_search(parser: Parser) -> ast.ShortestPathSearch:
    candidates_shortest_path_search = (
        parser.get_parser(ast.AllShortestPathSearch),
        parser.get_parser(ast.AnyShortestPathSearch),
        parser.get_parser(
            ast.CountedShortestGroupSearch
        ),  # Needs to go before counted shortest path search bc same prefix
        parser.get_parser(ast.CountedShortestPathSearch),
    )
    (result,) = parser.seq(candidates_shortest_path_search)
    return result


@parses(ast.PathFactor)
def parse_path_factor(parser: Parser) -> ast.PathFactor:
    candidates_path_factor = (
        parser.get_parser(ast.QuantifiedPathPrimary),
        parser.get_parser(ast.QuestionedPathPrimary),
        parser.get_parser(ast.PathPrimary),
    )
    (result,) = parser.seq(candidates_path_factor)
    return result


@parses(ast.LabelFactor)
def parse_label_factor(parser: Parser) -> ast.LabelFactor:
    candidates_label_factor = (
        parser.get_parser(ast.LabelPrimary),
        parser.get_parser(ast.LabelNegation),
    )
    (result,) = parser.seq(candidates_label_factor)
    return result


@parses(ast.SimplifiedConcatenation)
def parse_simplified_concatenation(parser: Parser) -> ast.SimplifiedConcatenation:
    (
        simplified_term,
        simplified_factor_low,
    ) = parser.seq(
        parser.get_parser(ast.SimplifiedTerm),
        parser.get_parser(ast.SimplifiedFactorLow),
    )
    return ast.SimplifiedConcatenation(
        simplified_term=simplified_term,
        simplified_factor_low=simplified_factor_low,
    )


@parses(ast.SimplifiedFactorLow)
def parse_simplified_factor_low(parser: Parser) -> ast.SimplifiedFactorLow:
    candidates_simplified_factor_low = (
        parser.get_parser(ast.SimplifiedFactorHigh),
        parser.get_parser(ast.SimplifiedConjunction),
    )
    (result,) = parser.seq(candidates_simplified_factor_low)
    return result


@parses(ast.NodeTypePhrase)
def parse_node_type_phrase(parser: Parser) -> ast.NodeTypePhrase:
    (
        _,
        type,
        node_type_phrase_filler,
        local_node_type_alias,
    ) = parser.seq(
        TokenType.NODE,
        parser.opt(TokenType.TYPE),
        parser.get_parser(ast.NodeTypePhraseFiller),
        parser.opt(
            lambda parser: parser.seq(TokenType.AS, parser.get_parser(ast.LocalNodeTypeAlias))[1],
        ),
    )
    return ast.NodeTypePhrase(
        type=bool(type),
        node_type_phrase_filler=node_type_phrase_filler,
        local_node_type_alias=local_node_type_alias,
    )


@parses(ast.EdgeTypePhrase)
def parse_edge_type_phrase(parser: Parser) -> ast.EdgeTypePhrase:
    (
        edge_kind,
        _,
        type,
        edge_type_phrase_filler,
        endpoint_pair_phrase,
    ) = parser.seq(
        parser.get_parser(ast.EdgeKind),
        TokenType.EDGE,
        parser.opt(TokenType.TYPE),
        parser.get_parser(ast.EdgeTypePhraseFiller),
        parser.get_parser(ast.EndpointPairPhrase),
    )
    return ast.EdgeTypePhrase(
        edge_kind=edge_kind,
        type=bool(type),
        edge_type_phrase_filler=edge_type_phrase_filler,
        endpoint_pair_phrase=endpoint_pair_phrase,
    )


@parses(ast.EndpointPairPointingRight)
def parse_endpoint_pair_pointing_right(parser: Parser) -> ast.EndpointPairPointingRight:
    (
        _,
        source_node_type_alias,
        connector_pointing_right,
        destination_node_type_alias,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.SourceNodeTypeAlias),
        parser.get_parser(ast.ConnectorPointingRight),
        parser.get_parser(ast.DestinationNodeTypeAlias),
        TokenType.RIGHT_PAREN,
    )
    return ast.EndpointPairPointingRight(
        source_node_type_alias=source_node_type_alias,
        connector_pointing_right=connector_pointing_right,
        destination_node_type_alias=destination_node_type_alias,
    )


@parses(ast.EndpointPairPointingLeft)
def parse_endpoint_pair_pointing_left(parser: Parser) -> ast.EndpointPairPointingLeft:
    (
        _,
        destination_node_type_alias,
        _,
        source_node_type_alias,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.DestinationNodeTypeAlias),
        TokenType.LEFT_ARROW,
        parser.get_parser(ast.SourceNodeTypeAlias),
        TokenType.RIGHT_PAREN,
    )
    return ast.EndpointPairPointingLeft(
        destination_node_type_alias=destination_node_type_alias,
        source_node_type_alias=source_node_type_alias,
    )


@parses(ast.SimpleCase)
def parse_simple_case(parser: Parser) -> ast.SimpleCase:
    (
        _,
        case_operand,
        list_simple_when_clause,
        else_clause,
        _,
    ) = parser.seq(
        TokenType.CASE,
        parser.get_parser(ast.CaseOperand),
        parser.list_(parser.get_parser(ast.SimpleWhenClause), None),
        parser.opt(parser.get_parser(ast.ElseClause)),
        TokenType.END,
    )
    return ast.SimpleCase(
        case_operand=case_operand,
        list_simple_when_clause=list_simple_when_clause,
        else_clause=else_clause,
    )


@parses(ast.SearchedCase)
def parse_searched_case(parser: Parser) -> ast.SearchedCase:
    (
        _,
        list_searched_when_clause,
        else_clause,
        _,
    ) = parser.seq(
        TokenType.CASE,
        parser.list_(parser.get_parser(ast.SearchedWhenClause), None),
        parser.opt(parser.get_parser(ast.ElseClause)),
        TokenType.END,
    )
    return ast.SearchedCase(
        list_searched_when_clause=list_searched_when_clause,
        else_clause=else_clause,
    )


@parses(ast.SingleCharacterTrimFunction)
def parse_single_character_trim_function(parser: Parser) -> ast.SingleCharacterTrimFunction:
    (
        _,
        _,
        trim_operands,
        _,
    ) = parser.seq(
        TokenType.TRIM,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.TrimOperands),
        TokenType.RIGHT_PAREN,
    )
    return ast.SingleCharacterTrimFunction(
        trim_operands=trim_operands,
    )


@parses(ast.MultiCharacterTrimFunction)
def parse_multi_character_trim_function(parser: Parser) -> ast.MultiCharacterTrimFunction:
    def parse_comma_trim_character_string(parser: Parser) -> ast.TrimCharacterString:
        (
            _,
            trim_character_string,
        ) = parser.seq(
            TokenType.COMMA,
            parser.get_parser(ast.TrimCharacterString),
        )
        return trim_character_string

    (token, _, trim_source, trim_character_string, _) = parser.seq(
        {TokenType.BTRIM, TokenType.LTRIM, TokenType.RTRIM},
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.TrimSource),
        parser.opt(parse_comma_trim_character_string),
        TokenType.RIGHT_PAREN,
    )
    match token.token_type:
        case TokenType.BTRIM:
            mode = ast.MultiCharacterTrimFunction.Mode.BTRIM
        case TokenType.LTRIM:
            mode = ast.MultiCharacterTrimFunction.Mode.LTRIM
        case TokenType.RTRIM:
            mode = ast.MultiCharacterTrimFunction.Mode.RTRIM

    return ast.MultiCharacterTrimFunction(
        mode=mode,
        trim_source=trim_source,
        trim_character_string=trim_character_string,
    )


@parses(ast.FocusedLinearDataModifyingStatementBody)
def parse_focused_linear_data_modifying_statement_body(
    parser: Parser,
) -> ast.FocusedLinearDataModifyingStatementBody:
    (
        use_graph_clause,
        simple_linear_data_accessing_statement,
        primitive_result_statement,
    ) = parser.seq(
        parser.get_parser(ast.UseGraphClause),
        parser.get_parser(ast.SimpleLinearDataAccessingStatement),
        parser.opt(parser.get_parser(ast.PrimitiveResultStatement)),
    )
    return ast.FocusedLinearDataModifyingStatementBody(
        use_graph_clause=use_graph_clause,
        simple_linear_data_accessing_statement=simple_linear_data_accessing_statement,
        primitive_result_statement=primitive_result_statement,
    )


@parses(ast.FocusedNestedDataModifyingProcedureSpecification)
def parse_focused_nested_data_modifying_procedure_specification(
    parser: Parser,
) -> ast.FocusedNestedDataModifyingProcedureSpecification:
    (
        use_graph_clause,
        nested_data_modifying_procedure_specification,
    ) = parser.seq(
        parser.get_parser(ast.UseGraphClause),
        parser.get_parser(ast.NestedDataModifyingProcedureSpecification),
    )
    return ast.FocusedNestedDataModifyingProcedureSpecification(
        use_graph_clause=use_graph_clause,
        nested_data_modifying_procedure_specification=nested_data_modifying_procedure_specification,
    )


@parses(ast.NestedDataModifyingProcedureSpecification)
def parse_nested_data_modifying_procedure_specification(
    parser: Parser,
) -> ast.NestedDataModifyingProcedureSpecification:
    (
        _,
        data_modifying_procedure_specification,
        _,
    ) = parser.seq(
        TokenType.LEFT_BRACE,
        parser.get_parser(ast.DataModifyingProcedureSpecification),
        TokenType.RIGHT_BRACE,
    )
    return ast.NestedDataModifyingProcedureSpecification(
        data_modifying_procedure_specification=data_modifying_procedure_specification,
    )


@parses(ast.AmbientLinearDataModifyingStatementBody)
def parse_ambient_linear_data_modifying_statement_body(
    parser: Parser,
) -> ast.AmbientLinearDataModifyingStatementBody:
    (
        simple_linear_data_accessing_statement,
        primitive_result_statement,
    ) = parser.seq(
        parser.get_parser(ast.SimpleLinearDataAccessingStatement),
        parser.opt(parser.get_parser(ast.PrimitiveResultStatement)),
    )
    return ast.AmbientLinearDataModifyingStatementBody(
        simple_linear_data_accessing_statement=simple_linear_data_accessing_statement,
        primitive_result_statement=primitive_result_statement,
    )


@parses(ast.AllShortestPathSearch)
def parse_all_shortest_path_search(parser: Parser) -> ast.AllShortestPathSearch:
    (
        _,
        _,
        path_mode,
        path_or_paths,
    ) = parser.seq(
        TokenType.ALL,
        TokenType.SHORTEST,
        parser.opt(parser.get_parser(ast.PathMode)),
        parser.opt(parser.get_parser(ast.PathOrPaths)),
    )
    return ast.AllShortestPathSearch(
        path_mode=path_mode,
        path_or_paths=path_or_paths,
    )


@parses(ast.AnyShortestPathSearch)
def parse_any_shortest_path_search(parser: Parser) -> ast.AnyShortestPathSearch:
    (
        _,
        _,
        path_mode,
        path_or_paths,
    ) = parser.seq(
        TokenType.ANY,
        TokenType.SHORTEST,
        parser.opt(parser.get_parser(ast.PathMode)),
        parser.opt(parser.get_parser(ast.PathOrPaths)),
    )
    return ast.AnyShortestPathSearch(
        path_mode=path_mode,
        path_or_paths=path_or_paths,
    )


@parses(ast.CountedShortestPathSearch)
def parse_counted_shortest_path_search(parser: Parser) -> ast.CountedShortestPathSearch:
    (
        _,
        number_of_paths,
        path_mode,
        path_or_paths,
    ) = parser.seq(
        TokenType.SHORTEST,
        parser.get_parser(ast.NumberOfPaths),
        parser.opt(parser.get_parser(ast.PathMode)),
        parser.opt(parser.get_parser(ast.PathOrPaths)),
    )
    return ast.CountedShortestPathSearch(
        number_of_paths=number_of_paths,
        path_mode=path_mode,
        path_or_paths=path_or_paths,
    )


@parses(ast.CountedShortestGroupSearch)
def parse_counted_shortest_group_search(parser: Parser) -> ast.CountedShortestGroupSearch:
    (
        _,
        number_of_groups,
        path_mode,
        path_or_paths,
        _,
    ) = parser.seq(
        TokenType.SHORTEST,
        parser.opt(parser.get_parser(ast.NumberOfGroups)),
        parser.opt(parser.get_parser(ast.PathMode)),
        parser.opt(parser.get_parser(ast.PathOrPaths)),
        {TokenType.GROUP, TokenType.GROUPS},
    )

    return ast.CountedShortestGroupSearch(
        number_of_groups=number_of_groups,
        path_mode=path_mode,
        path_or_paths=path_or_paths,
    )


@parses(ast.QuantifiedPathPrimary)
def parse_quantified_path_primary(parser: Parser) -> ast.QuantifiedPathPrimary:
    (
        path_primary,
        graph_pattern_quantifier,
    ) = parser.seq(
        parser.get_parser(ast.PathPrimary),
        parser.get_parser(ast.GraphPatternQuantifier),
    )
    return ast.QuantifiedPathPrimary(
        path_primary=path_primary,
        graph_pattern_quantifier=graph_pattern_quantifier,
    )


@parses(ast.QuestionedPathPrimary)
def parse_questioned_path_primary(parser: Parser) -> ast.QuestionedPathPrimary:
    (
        path_primary,
        _,
    ) = parser.seq(
        parser.get_parser(ast.PathPrimary),
        TokenType.QUESTION_MARK,
    )
    return ast.QuestionedPathPrimary(
        path_primary=path_primary,
    )


@parses(ast.PathPrimary)
def parse_path_primary(parser: Parser) -> ast.PathPrimary:
    candidates_path_primary = (
        parser.get_parser(ast.ElementPattern),
        parser.get_parser(ast.ParenthesizedPathPatternExpression),
        parser.get_parser(ast.SimplifiedPathPatternExpression),
    )
    (result,) = parser.seq(candidates_path_primary)
    return result


@parses(ast.LabelNegation)
def parse_label_negation(parser: Parser) -> ast.LabelNegation:
    (
        _,
        label_primary,
    ) = parser.seq(
        TokenType.EXCLAMATION_MARK,
        parser.get_parser(ast.LabelPrimary),
    )
    return ast.LabelNegation(
        label_primary=label_primary,
    )


@parses(ast.LabelPrimary)
def parse_label_primary(parser: Parser) -> ast.LabelPrimary:
    candidates_label_primary = (
        parser.get_parser(ast.LabelName),
        parser.get_parser(ast.WildcardLabel),
        parser.get_parser(ast.ParenthesizedLabelExpression),
    )
    (result,) = parser.seq(candidates_label_primary)
    return result


@parses(ast.WildcardLabel)
def parse_wildcard_label(parser: Parser) -> ast.WildcardLabel:
    parser.seq(TokenType.PERCENT)
    return ast.WildcardLabel()


@parses(ast.SimplifiedConjunction)
def parse_simplified_conjunction(parser: Parser) -> ast.SimplifiedConjunction:
    (
        simplified_factor_low,
        _,
        simplified_factor_high,
    ) = parser.seq(
        parser.get_parser(ast.SimplifiedFactorLow),
        TokenType.AMPERSAND,
        parser.get_parser(ast.SimplifiedFactorHigh),
    )
    return ast.SimplifiedConjunction(
        simplified_factor_low=simplified_factor_low,
        simplified_factor_high=simplified_factor_high,
    )


@parses(ast.SimplifiedFactorHigh)
def parse_simplified_factor_high(parser: Parser) -> ast.SimplifiedFactorHigh:
    candidates_simplified_factor_high = (
        parser.get_parser(ast.SimplifiedTertiary),
        parser.get_parser(ast.SimplifiedQuantified),
        parser.get_parser(ast.SimplifiedQuestioned),
    )
    (result,) = parser.seq(candidates_simplified_factor_high)
    return result


@parses(ast.SimplifiedQuantified)
def parse_simplified_quantified(parser: Parser) -> ast.SimplifiedQuantified:
    (
        simplified_tertiary,
        graph_pattern_quantifier,
    ) = parser.seq(
        parser.get_parser(ast.SimplifiedTertiary),
        parser.get_parser(ast.GraphPatternQuantifier),
    )
    return ast.SimplifiedQuantified(
        simplified_tertiary=simplified_tertiary,
        graph_pattern_quantifier=graph_pattern_quantifier,
    )


@parses(ast.SimplifiedQuestioned)
def parse_simplified_questioned(parser: Parser) -> ast.SimplifiedQuestioned:
    (simplified_tertiary, _) = parser.seq(
        parser.get_parser(ast.SimplifiedTertiary),
        TokenType.QUESTION_MARK,
    )
    return ast.SimplifiedQuestioned(
        simplified_tertiary=simplified_tertiary,
    )


@parses(ast.SimplifiedTertiary)
def parse_simplified_tertiary(parser: Parser) -> ast.SimplifiedTertiary:
    candidates_simplified_tertiary = (
        parser.get_parser(ast.SimplifiedDirectionOverride),
        parser.get_parser(ast.SimplifiedSecondary),
    )
    (result,) = parser.seq(candidates_simplified_tertiary)
    return result


@parses(ast.PathValueConcatenation)
def parse_path_value_concatenation(parser: Parser) -> ast.PathValueConcatenation:
    (primaries,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.PathValuePrimary),
            TokenType.CONCATENATION_OPERATOR,
            min_items=2,
        ),
    )
    return ast.PathValueConcatenation(
        list_path_value_primary=primaries,
        path_value_expression_1=ast.PathValueExpression(
            list_path_value_primary=primaries[:-1],
        ),
        path_value_primary=primaries[-1],
    )


@parses(ast.DatetimeSubtraction)
def parse_datetime_subtraction(parser: Parser) -> ast.DatetimeSubtraction:
    (
        _,
        _,
        datetime_subtraction_parameters,
        _,
        temporal_duration_qualifier,
    ) = parser.seq(
        TokenType.DURATION_BETWEEN,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.DatetimeSubtractionParameters),
        TokenType.RIGHT_PAREN,
        parser.opt(parser.get_parser(ast.TemporalDurationQualifier)),
    )
    return ast.DatetimeSubtraction(
        datetime_subtraction_parameters=datetime_subtraction_parameters,
        temporal_duration_qualifier=temporal_duration_qualifier,
    )


@parses(ast.DurationTerm)
def parse_duration_term(parser: Parser) -> ast.DurationTerm:
    def _parser__multiplicative_factor(parser: Parser) -> ast.DurationTerm._MultiplicativeFactor:
        (operator, factor) = parser.seq(
            parser.get_parser(ast.MultiplicativeOperator),
            parser.get_parser(ast.Factor),
        )
        return ast.DurationTerm._MultiplicativeFactor(
            operator=operator,
            factor=factor,
        )

    (multiplicative_term, duration_factor, list_multiplicative_factors) = parser.seq(
        parser.opt(
            lambda parser: parser.seq(
                TokenType.ASTERISK,
                parser.get_parser(ast.Term),
            )[1],
        ),
        parser.get_parser(ast.DurationFactor),
        parser.list_(_parser__multiplicative_factor, None, min_items=0),
    )
    return ast.DurationTerm(
        multiplicative_term=multiplicative_term,
        base=duration_factor,
        steps=list_multiplicative_factors,
    )


@parses(ast.SimplifiedDefaultingLeft)
def parse_simplified_defaulting_left(parser: Parser) -> ast.SimplifiedDefaultingLeft:
    (_, simplified_contents, _) = parser.seq(
        TokenType.LEFT_MINUS_SLASH,
        parser.get_parser(ast.SimplifiedContents),
        TokenType.SLASH_MINUS,
    )
    return ast.SimplifiedDefaultingLeft(
        simplified_contents=simplified_contents,
    )


@parses(ast.SimplifiedDefaultingUndirected)
def parse_simplified_defaulting_undirected(parser: Parser) -> ast.SimplifiedDefaultingUndirected:
    (
        _,
        simplified_contents,
        _,
    ) = parser.seq(
        TokenType.TILDE_SLASH,
        parser.get_parser(ast.SimplifiedContents),
        TokenType.SLASH_TILDE,
    )
    return ast.SimplifiedDefaultingUndirected(
        simplified_contents=simplified_contents,
    )


@parses(ast.SimplifiedDefaultingRight)
def parse_simplified_defaulting_right(parser: Parser) -> ast.SimplifiedDefaultingRight:
    (
        _,
        simplified_contents,
        _,
    ) = parser.seq(
        TokenType.MINUS_SLASH,
        parser.get_parser(ast.SimplifiedContents),
        TokenType.SLASH_MINUS_RIGHT,
    )
    return ast.SimplifiedDefaultingRight(
        simplified_contents=simplified_contents,
    )


@parses(ast.SimplifiedDefaultingLeftOrUndirected)
def parse_simplified_defaulting_left_or_undirected(
    parser: Parser,
) -> ast.SimplifiedDefaultingLeftOrUndirected:
    (
        _,
        simplified_contents,
        _,
    ) = parser.seq(
        TokenType.LEFT_TILDE_SLASH,
        parser.get_parser(ast.SimplifiedContents),
        TokenType.SLASH_TILDE,
    )
    return ast.SimplifiedDefaultingLeftOrUndirected(
        simplified_contents=simplified_contents,
    )


@parses(ast.SimplifiedDefaultingUndirectedOrRight)
def parse_simplified_defaulting_undirected_or_right(
    parser: Parser,
) -> ast.SimplifiedDefaultingUndirectedOrRight:
    (
        _,
        simplified_contents,
        _,
    ) = parser.seq(
        TokenType.TILDE_SLASH,
        parser.get_parser(ast.SimplifiedContents),
        TokenType.SLASH_TILDE_RIGHT,
    )
    return ast.SimplifiedDefaultingUndirectedOrRight(
        simplified_contents=simplified_contents,
    )


@parses(ast.SimplifiedDefaultingLeftOrRight)
def parse_simplified_defaulting_left_or_right(
    parser: Parser,
) -> ast.SimplifiedDefaultingLeftOrRight:
    (
        _,
        simplified_contents,
        _,
    ) = parser.seq(
        TokenType.MINUS_SLASH,
        parser.get_parser(ast.SimplifiedContents),
        TokenType.SLASH_MINUS_RIGHT,
    )
    return ast.SimplifiedDefaultingLeftOrRight(
        simplified_contents=simplified_contents,
    )


@parses(ast.SimplifiedDefaultingAnyDirection)
def parse_simplified_defaulting_any_direction(
    parser: Parser,
) -> ast.SimplifiedDefaultingAnyDirection:
    (
        _,
        simplified_contents,
        _,
    ) = parser.seq(
        TokenType.MINUS_SLASH,
        parser.get_parser(ast.SimplifiedContents),
        TokenType.SLASH_MINUS,
    )
    return ast.SimplifiedDefaultingAnyDirection(
        simplified_contents=simplified_contents,
    )


@parses(ast.SimplifiedDirectionOverride)
def parse_simplified_direction_override(parser: Parser) -> ast.SimplifiedDirectionOverride:
    candidates_simplified_direction_override = (
        parser.get_parser(ast.SimplifiedOverrideLeft),
        parser.get_parser(ast.SimplifiedOverrideUndirected),
        parser.get_parser(ast.SimplifiedOverrideRight),
        parser.get_parser(ast.SimplifiedOverrideLeftOrUndirected),
        parser.get_parser(ast.SimplifiedOverrideUndirectedOrRight),
        parser.get_parser(ast.SimplifiedOverrideLeftOrRight),
        parser.get_parser(ast.SimplifiedOverrideAnyDirection),
    )
    (result,) = parser.seq(candidates_simplified_direction_override)
    return result


@parses(ast.SimplifiedSecondary)
def parse_simplified_secondary(parser: Parser) -> ast.SimplifiedSecondary:
    candidates_simplified_secondary = (
        parser.get_parser(ast.SimplifiedPrimary),
        parser.get_parser(ast.SimplifiedNegation),
    )
    (result,) = parser.seq(candidates_simplified_secondary)
    return result


@parses(ast.SimplifiedOverrideLeft)
def parse_simplified_override_left(parser: Parser) -> ast.SimplifiedOverrideLeft:
    (
        _,
        simplified_secondary,
    ) = parser.seq(
        TokenType.LEFT_ANGLE_BRACKET,
        parser.get_parser(ast.SimplifiedSecondary),
    )
    return ast.SimplifiedOverrideLeft(
        simplified_secondary=simplified_secondary,
    )


@parses(ast.SimplifiedOverrideUndirected)
def parse_simplified_override_undirected(parser: Parser) -> ast.SimplifiedOverrideUndirected:
    (simplified_secondary,) = parser.seq(
        parser.get_parser(ast.SimplifiedSecondary),
    )
    return ast.SimplifiedOverrideUndirected(
        simplified_secondary=simplified_secondary,
    )


@parses(ast.SimplifiedOverrideRight)
def parse_simplified_override_right(parser: Parser) -> ast.SimplifiedOverrideRight:
    (
        simplified_secondary,
        _,
    ) = parser.seq(
        parser.get_parser(ast.SimplifiedSecondary),
        TokenType.RIGHT_ANGLE_BRACKET,
    )
    return ast.SimplifiedOverrideRight(
        simplified_secondary=simplified_secondary,
    )


@parses(ast.SimplifiedOverrideLeftOrUndirected)
def parse_simplified_override_left_or_undirected(
    parser: Parser,
) -> ast.SimplifiedOverrideLeftOrUndirected:
    (
        _,
        simplified_secondary,
    ) = parser.seq(
        TokenType.LEFT_ARROW_TILDE,
        parser.get_parser(ast.SimplifiedSecondary),
    )
    return ast.SimplifiedOverrideLeftOrUndirected(
        simplified_secondary=simplified_secondary,
    )


@parses(ast.SimplifiedOverrideUndirectedOrRight)
def parse_simplified_override_undirected_or_right(
    parser: Parser,
) -> ast.SimplifiedOverrideUndirectedOrRight:
    (
        _,
        simplified_secondary,
        _,
    ) = parser.seq(
        TokenType.TILDE,
        parser.get_parser(ast.SimplifiedSecondary),
        TokenType.RIGHT_ANGLE_BRACKET,
    )
    return ast.SimplifiedOverrideUndirectedOrRight(
        simplified_secondary=simplified_secondary,
    )


@parses(ast.SimplifiedOverrideLeftOrRight)
def parse_simplified_override_left_or_right(parser: Parser) -> ast.SimplifiedOverrideLeftOrRight:
    (
        _,
        simplified_secondary,
        _,
    ) = parser.seq(
        TokenType.LEFT_ANGLE_BRACKET,
        parser.get_parser(ast.SimplifiedSecondary),
        TokenType.RIGHT_ANGLE_BRACKET,
    )
    return ast.SimplifiedOverrideLeftOrRight(simplified_secondary=simplified_secondary)


@parses(ast.SimplifiedOverrideAnyDirection)
def parse_simplified_override_any_direction(parser: Parser) -> ast.SimplifiedOverrideAnyDirection:
    (
        _,
        simplified_secondary,
    ) = parser.seq(
        TokenType.MINUS_SIGN,
        parser.get_parser(ast.SimplifiedSecondary),
    )
    return ast.SimplifiedOverrideAnyDirection(
        simplified_secondary=simplified_secondary,
    )


@parses(ast.SimplifiedNegation)
def parse_simplified_negation(parser: Parser) -> ast.SimplifiedNegation:
    (
        _,
        simplified_primary,
    ) = parser.seq(
        TokenType.EXCLAMATION_MARK,
        parser.get_parser(ast.SimplifiedPrimary),
    )
    return ast.SimplifiedNegation(
        simplified_primary=simplified_primary,
    )


@parses(ast.SimplifiedPrimary)
def parse_simplified_primary(parser: Parser) -> ast.SimplifiedPrimary:
    def _parse__left_paren_simplified_contents_right_paren(
        parser: Parser,
    ) -> ast.SimplifiedPrimary._LeftParenSimplifiedContentsRightParen:
        (_, simplified_contents, _) = parser.seq(
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.SimplifiedContents),
            TokenType.RIGHT_PAREN,
        )
        return ast.SimplifiedPrimary._LeftParenSimplifiedContentsRightParen(
            simplified_contents=simplified_contents,
        )

    candidates_simplified_primary = (
        parser.get_parser(ast.LabelName),
        _parse__left_paren_simplified_contents_right_paren,
    )
    (simplified_primary,) = parser.seq(candidates_simplified_primary)
    return ast.SimplifiedPrimary(
        simplified_primary=simplified_primary,
    )


@parses(ast.FullEdgePointingLeft)
def parse_full_edge_pointing_left(parser: Parser) -> ast.FullEdgePointingLeft:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.LEFT_ARROW_BRACKET,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.RIGHT_BRACKET_MINUS,
    )
    return ast.FullEdgePointingLeft(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.FullEdgeUndirected)
def parse_full_edge_undirected(parser: Parser) -> ast.FullEdgeUndirected:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.TILDE_LEFT_BRACKET,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.RIGHT_BRACKET_TILDE,
    )
    return ast.FullEdgeUndirected(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.FullEdgePointingRight)
def parse_full_edge_pointing_right(parser: Parser) -> ast.FullEdgePointingRight:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.MINUS_LEFT_BRACKET,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.BRACKET_RIGHT_ARROW,
    )
    return ast.FullEdgePointingRight(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.FullEdgeLeftOrUndirected)
def parse_full_edge_left_or_undirected(parser: Parser) -> ast.FullEdgeLeftOrUndirected:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.LEFT_ARROW_TILDE_BRACKET,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.RIGHT_BRACKET_TILDE,
    )
    return ast.FullEdgeLeftOrUndirected(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.FullEdgeUndirectedOrRight)
def parse_full_edge_undirected_or_right(parser: Parser) -> ast.FullEdgeUndirectedOrRight:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.TILDE_LEFT_BRACKET,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.BRACKET_TILDE_RIGHT_ARROW,
    )
    return ast.FullEdgeUndirectedOrRight(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.FullEdgeLeftOrRight)
def parse_full_edge_left_or_right(parser: Parser) -> ast.FullEdgeLeftOrRight:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.LEFT_ARROW_BRACKET,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.BRACKET_RIGHT_ARROW,
    )
    return ast.FullEdgeLeftOrRight(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.FullEdgeAnyDirection)
def parse_full_edge_any_direction(parser: Parser) -> ast.FullEdgeAnyDirection:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.MINUS_LEFT_BRACKET,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.RIGHT_BRACKET_MINUS,
    )
    return ast.FullEdgeAnyDirection(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.NumericPrimary)
def parse_numeric_primary(parser: Parser) -> ast.NumericPrimary:
    candidates_numeric_primary = (
        parser.get_parser(ast.ValueExpressionPrimary),
        parser.get_parser(ast.NumericValueFunction),
    )
    (result,) = parser.seq(candidates_numeric_primary)
    return result


@parses(ast.DatetimePrimary)
def parse_datetime_primary(parser: Parser) -> ast.DatetimePrimary:
    candidates_datetime_primary = (
        parser.get_parser(ast.ValueExpressionPrimary),
        parser.get_parser(ast.DatetimeValueFunction),
    )
    (result,) = parser.seq(candidates_datetime_primary)
    return result


@parses(ast.DurationPrimary)
def parse_duration_primary(parser: Parser) -> ast.DurationPrimary:
    candidates_duration_primary = (
        parser.get_parser(ast.ValueExpressionPrimary),
        parser.get_parser(ast.DurationValueFunction),
    )
    (result,) = parser.seq(candidates_duration_primary)
    return result


@parses(ast.NonParenthesizedValueExpressionPrimarySpecialCase)
def parse_non_parenthesized_value_expression_primary_special_case(
    parser: Parser,
) -> ast.NonParenthesizedValueExpressionPrimarySpecialCase:
    candidates_non_parenthesized_value_expression_primary_special_case = (
        parser.get_parser(ast.MacroCall),
        parser.get_parser(ast.AggregateFunction),
        parser.get_parser(ast.UnsignedValueSpecification),
        parser.get_parser(ast.ListValueConstructorByEnumeration),
        parser.get_parser(ast.RecordConstructor),
        parser.get_parser(ast.PathValueConstructorByEnumeration),
        parser.get_parser(ast.ValueQueryExpression),
        parser.get_parser(ast.CaseExpression),
        parser.get_parser(ast.CastSpecification),
        parser.get_parser(ast.ElementIdFunction),
        parser.get_parser(ast.LetValueExpression),
        parser.get_parser(ast.PropertyReference),
    )
    (result,) = parser.seq(candidates_non_parenthesized_value_expression_primary_special_case)
    return result


@parses(ast.ComparisonPredicand)
def parse_comparison_predicand(parser: Parser) -> ast.ComparisonPredicand:
    candidates_comparison_predicand = (
        parser.get_parser(ast.CommonValueExpression),
        parser.get_parser(ast.BooleanPredicand),
    )
    (result,) = parser.seq(candidates_comparison_predicand)
    return result


@parses(ast.NonParenthesizedValueExpressionPrimary)
def parse_non_parenthesized_value_expression_primary(
    parser: Parser,
) -> ast.NonParenthesizedValueExpressionPrimary:
    candidates_non_parenthesized_value_expression_primary = (
        parser.get_parser(ast.NonParenthesizedValueExpressionPrimarySpecialCase),
        parser.get_parser(ast.BindingVariableReference),
    )
    (result,) = parser.seq(candidates_non_parenthesized_value_expression_primary)
    return result


@parses(ast.LabelName)
def parse_label_name(parser: Parser) -> ast.LabelName:
    candidates_label_name = (parser.get_parser(ast.Identifier),)
    (result,) = parser.seq(candidates_label_name)
    return ast.LabelName(identifier=result)


@parses(ast.ListPrimary)
def parse_list_primary(parser: Parser) -> ast.ListPrimary:
    candidates_list_primary = (
        parser.get_parser(ast.ListValueFunction),
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates_list_primary)
    return result


@parses(ast.ForItemSource)
def parse_for_item_source(parser: Parser) -> ast.ForItemSource:
    # NOTE: Order here is important because of non-reserved words being accepted in Identifier.
    # So we need to put the BindingTableReferenceValueExpression first to avoid ambiguity.
    # Otherwise this would fail: FOR x IN TABLE {MATCH (n:Person) RETURN n}
    candidates_for_item_source = (
        parser.get_parser(ast.BindingTableReferenceValueExpression),
        parser.get_parser(ast.ListValueExpression),
    )
    (result,) = parser.seq(candidates_for_item_source)
    return result


@parses(ast.CardinalityExpressionArgument)
def parse_cardinality_expression_argument(parser: Parser) -> ast.CardinalityExpressionArgument:
    candidates_cardinality_expression_argument = (
        parser.get_parser(ast.BindingTableReferenceValueExpression),
        parser.get_parser(ast.PathValueExpression),
        parser.get_parser(ast.ListValueExpression),
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates_cardinality_expression_argument)
    return result


@parses(ast.CharacterStringPrimary)
def parse_character_string_primary(parser: Parser) -> ast.CharacterStringPrimary:
    candidates_character_string_primary = (
        parser.get_parser(ast.ValueExpressionPrimary),
        parser.get_parser(ast.CharacterStringFunction),
    )
    (result,) = parser.seq(candidates_character_string_primary)
    return result


@parses(ast.ByteStringPrimary)
def parse_byte_string_primary(parser: Parser) -> ast.ByteStringPrimary:
    candidates_byte_string_primary = (
        parser.get_parser(ast.ValueExpressionPrimary),
        parser.get_parser(ast.ByteStringFunction),
    )
    (result,) = parser.seq(candidates_byte_string_primary)
    return result


@parses(ast._PropertySourceExceptPropertyReference)
def parse_property_source_except_property_reference(
    parser: Parser,
) -> ast._PropertySourceExceptPropertyReference:
    candidates = (
        parser.get_parser(ast.ParenthesizedValueExpression),
        parser.get_parser(ast.AggregateFunction),
        parser.get_parser(ast.UnsignedNumericLiteral),
        parser.get_parser(ast.BooleanLiteral),
        parser.get_parser(ast.CharacterStringLiteral),
        parser.get_parser(ast.ByteStringLiteral),
        parser.get_parser(ast.TemporalLiteral),
        parser.get_parser(ast.DurationLiteral),
        parser.get_parser(ast.NullLiteral),
        parser.get_parser(ast.ListValueConstructorByEnumeration),
        parser.get_parser(ast.RecordConstructor),
        parser.get_parser(ast.GeneralValueSpecification),
        parser.get_parser(ast.PathValueConstructorByEnumeration),
        parser.get_parser(ast.ValueQueryExpression),
        parser.get_parser(ast.CaseExpression),
        parser.get_parser(ast.CastSpecification),
        parser.get_parser(ast.ElementIdFunction),
        parser.get_parser(ast.LetValueExpression),
        parser.get_parser(ast.BindingVariableReference),
    )
    (result,) = parser.seq(candidates)
    return result


@parses(ast.PathOrPaths)
def parse_path_or_paths(parser: Parser) -> ast.PathOrPaths:
    (token,) = parser.seq({TokenType.PATHS, TokenType.PATH})

    match token.token_type:
        case TokenType.PATHS:
            mode = ast.PathOrPaths.Mode.PATHS
        case TokenType.PATH:
            mode = ast.PathOrPaths.Mode.PATH

    return ast.PathOrPaths(mode=mode)
