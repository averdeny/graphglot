"""
This module contains Abstract Syntax Tree (AST) expressions derived from the
grammar artifacts defined in the ISO/IEC 39075:2024 standard.

This module is best understood alongside the BNF grammar from the standard.
"""

from __future__ import annotations

import typing as t

from decimal import Decimal
from enum import Enum, auto

from graphglot import features as F

if t.TYPE_CHECKING:
    from graphglot.dialect.base import Dialect

from .base import Expression, field, model_validator, nonstandard


class GqlProgram(Expression):
    """AST Expression for <GQL-program>."""

    class _ProgramActivitySessionCloseCommand(Expression):
        """Internal expression."""

        program_activity: ProgramActivity
        session_close_command: SessionCloseCommand | None

    gql_program: _ProgramActivitySessionCloseCommand | SessionCloseCommand


class ProgramActivity(Expression):
    """Semantic marker for <program activity> in the Abstract Syntax Tree (AST)."""

    pass


class EndTransactionCommand(Expression):
    """AST Expression for <end transaction command>."""

    class Mode(Enum):
        ROLLBACK = auto()
        COMMIT = auto()

    mode: Mode

    @model_validator(mode="after")
    def _check_end_transaction_command(self):
        self.require_feature(F.GT01)  # Explicit transaction commands
        return self


class SessionSetCommand(Expression):
    """AST Expression for <session set command>."""

    session_set_command: (
        SessionSetSchemaClause
        | SessionSetGraphClause
        | SessionSetTimeZoneClause
        | SessionSetParameterClause
    )

    @model_validator(mode="after")
    def _check_session_set_command(self):
        self.require_feature(F.GG_SM01)  # Session management: SESSION SET command
        return self


class SessionSetSchemaClause(Expression):
    """AST Expression for <session set schema clause>."""

    schema_reference: SchemaReference


class SessionSetGraphClause(Expression):
    """AST Expression for <session set graph clause>."""

    graph_expression: GraphExpression


class SessionSetTimeZoneClause(Expression):
    """AST Expression for <session set time zone clause>."""

    set_time_zone_value: SetTimeZoneValue

    @model_validator(mode="after")
    def _check_session_set_time_zone_clause(self):
        self.require_feature(F.GS15)  # SESSION SET: set time zone displacement
        return self


class SessionSetParameterClause(Expression):
    """Semantic marker for <session set parameter clause> in the Abstract Syntax Tree (AST)."""

    pass


class SessionSetParameterName(Expression):
    """AST Expression for <session set parameter name>."""

    if_not_exists: bool
    session_parameter_specification: SessionParameterSpecification


class SessionResetCommand(Expression):
    """AST Expression for <session reset command>."""

    session_reset_arguments: SessionResetArguments | None

    @model_validator(mode="after")
    def _check_session_reset_command(self):
        self.require_feature(F.GG_SM02)  # Session management: SESSION RESET command
        args = self.session_reset_arguments
        if args is None:
            # Bare SESSION RESET (no arguments) requires GS04
            self.require_feature(F.GS04)  # SESSION RESET: reset all characteristics
            return self
        inner = args.session_reset_arguments
        if isinstance(inner, SessionResetArguments._AllParameters):
            self.require_feature(F.GS04)  # SESSION RESET: PARAMETERS
            if inner.all:
                self.require_feature(F.GS08)  # SESSION RESET: ALL PARAMETERS
        elif isinstance(inner, SessionResetArguments._AllCharacteristics):
            self.require_feature(F.GS04)  # SESSION RESET: CHARACTERISTICS
        elif isinstance(inner, SessionResetArguments._Schema):
            self.require_feature(F.GS05)  # SESSION RESET: reset session schema
        elif isinstance(inner, SessionResetArguments._Graph):
            self.require_feature(F.GS06)  # SESSION RESET: reset session graph
        elif isinstance(inner, SessionResetArguments._TimeZone):
            self.require_feature(F.GS07)  # SESSION RESET: reset time zone
        elif isinstance(inner, SessionResetArguments._ParameterSessionParameterSpecification):
            self.require_feature(F.GS16)  # SESSION RESET: reset individual parameter
        return self


class SessionResetArguments(Expression):
    """AST Expression for <session reset arguments>."""

    class _AllParameters(Expression):
        """Internal expression."""

        all: bool

    class _AllCharacteristics(Expression):
        """Internal expression."""

        all: bool

    class _Schema(Expression):
        """Internal expression."""

        pass

    class _Graph(Expression):
        """Internal expression."""

        pass

    class _TimeZone(Expression):
        """Internal expression."""

        pass

    class _ParameterSessionParameterSpecification(Expression):
        """Internal expression."""

        parameter: bool
        session_parameter_specification: SessionParameterSpecification

    session_reset_arguments: (
        _AllParameters
        | _AllCharacteristics
        | _Schema
        | _Graph
        | _TimeZone
        | _ParameterSessionParameterSpecification
    )


class SessionCloseCommand(Expression):
    """AST Expression for <session close command>."""

    @model_validator(mode="after")
    def _check_session_close_command(self):
        self.require_feature(F.GG_SM03)  # Session management: SESSION CLOSE command
        return self


class StartTransactionCommand(Expression):
    """AST Expression for <start transaction command>."""

    transaction_characteristics: TransactionCharacteristics | None

    @model_validator(mode="after")
    def _check_start_transaction_command(self):
        self.require_feature(F.GT01)  # Explicit transaction commands
        if self.transaction_characteristics is not None:
            self.require_feature(F.GT02)  # Specified transaction characteristics
        return self


class TransactionCharacteristics(Expression):
    """AST Expression for <transaction characteristics>."""

    class TransactionMode(Enum):
        READ_ONLY = auto()
        READ_WRITE = auto()
        # Additional implementation-defined access modes are possible

    list_transaction_mode: list[TransactionCharacteristics.TransactionMode]


class NestedProcedureSpecification(Expression):
    """AST Expression for <nested procedure specification>."""

    procedure_specification: ProcedureSpecification


class ProcedureSpecification(Expression):
    """Semantic marker for <procedure specification> in the Abstract Syntax Tree (AST)."""

    pass


class NestedQuerySpecification(Expression):
    """AST Expression for <nested query specification>."""

    query_specification: QuerySpecification


class ProcedureBody(ProcedureSpecification):
    """AST Expression for <procedure body>."""

    at_schema_clause: AtSchemaClause | None
    binding_variable_definition_block: BindingVariableDefinitionBlock | None
    statement_block: StatementBlock

    @model_validator(mode="after")
    def _check_procedure_body(self):
        if self.at_schema_clause is not None:
            self.require_feature(F.GP16)  # AT schema clause in procedure body
        if self.binding_variable_definition_block is not None:
            self.require_feature(F.GP17)  # Binding variable definition block
        return self


class BindingVariableDefinitionBlock(Expression):
    """AST Expression for <binding variable definition block>."""

    list_binding_variable_definition: list[BindingVariableDefinition]


class BindingVariableDefinition(Expression):
    """Semantic marker for <binding variable definition> in the Abstract Syntax Tree (AST)."""

    pass


class StatementBlock(Expression):
    """AST Expression for <statement block>."""

    statement: Statement
    list_next_statement: list[NextStatement] | None

    @model_validator(mode="after")
    def _check_statement_block(self):
        if self.list_next_statement:
            statements = [self.statement] + [ns.statement for ns in self.list_next_statement]
            has_catalog = any(isinstance(s, LinearCatalogModifyingStatement) for s in statements)
            has_data = any(
                isinstance(s, LinearDataModifyingStatement | CompositeQueryExpression)
                for s in statements
            )
            if has_catalog and has_data:
                self.require_feature(F.GP18)
        return self


class Statement(Expression):
    """Semantic marker for <statement> in the Abstract Syntax Tree (AST)."""

    pass


class NextStatement(Expression):
    """AST Expression for <next statement>."""

    yield_clause: YieldClause | None
    statement: Statement

    @model_validator(mode="after")
    def _check_next_statement(self):
        self.require_feature(F.GQ20)  # Advanced linear composition with NEXT
        return self


class OptTypedGraphInitializer(Expression):
    """AST Expression for <opt typed graph initializer>."""

    class _TypedGraphReferenceValueType(Expression):
        """Internal expression."""

        typed: Typed | None
        graph_reference_value_type: GraphReferenceValueType

    typed_graph_reference_value_type: _TypedGraphReferenceValueType | None
    graph_initializer: GraphInitializer


class GraphInitializer(Expression):
    """AST Expression for <graph initializer>."""

    graph_expression: GraphExpression


class OptTypedBindingTableInitializer(Expression):
    """AST Expression for <opt typed binding table initializer>."""

    class _TypedBindingTableReferenceValueType(Expression):
        """Internal expression."""

        typed: Typed | None
        binding_table_reference_value_type: BindingTableReferenceValueType

    typed_binding_table_reference_value_type: _TypedBindingTableReferenceValueType | None
    binding_table_initializer: BindingTableInitializer


class BindingTableInitializer(Expression):
    """AST Expression for <binding table initializer>."""

    binding_table_expression: BindingTableExpression


class OptTypedValueInitializer(Expression):
    """AST Expression for <opt typed value initializer>."""

    class _TypedValueType(Expression):
        """Internal expression."""

        typed: Typed | None
        value_type: ValueType

    typed_value_type: _TypedValueType | None
    value_initializer: ValueInitializer


class ValueInitializer(Expression):
    """AST Expression for <value initializer>."""

    value_expression: ValueExpression


class GraphExpression(Expression):
    """Semantic marker for <graph expression> in the Abstract Syntax Tree (AST)."""

    pass


class SimpleCatalogModifyingStatement(Expression):
    """Semantic marker for <simple catalog-modifying statement> in the Abstract Syntax Tree."""

    pass


class OpenGraphType(Expression):
    """AST Expression for <open graph type>."""

    typed: Typed | None
    graph: bool


class OfGraphType(Expression):
    """AST Expression for <of graph type>."""

    class _TypedGraphTypeReference(Expression):
        """Internal expression."""

        typed: Typed | None
        graph_type_reference: GraphTypeReference

    class _TypedGraphNestedGraphTypeSpecification(Expression):
        """Internal expression."""

        typed: Typed | None
        graph: bool
        nested_graph_type_specification: NestedGraphTypeSpecification

    of_graph_type: (
        GraphTypeLikeGraph | _TypedGraphTypeReference | _TypedGraphNestedGraphTypeSpecification
    )


class GraphTypeLikeGraph(Expression):
    """AST Expression for <graph type like graph>."""

    graph_expression: GraphExpression


class GraphSource(Expression):
    """AST Expression for <graph source>."""

    graph_expression: GraphExpression


class GraphTypeSource(Expression):
    """AST Expression for <graph type source>."""

    class _AsCopyOfGraphType(Expression):
        """Internal expression."""

        as_: bool
        copy_of_graph_type: CopyOfGraphType

    class _AsNestedGraphTypeSpecification(Expression):
        """Internal expression."""

        as_: bool
        nested_graph_type_specification: NestedGraphTypeSpecification

    graph_type_source: _AsCopyOfGraphType | GraphTypeLikeGraph | _AsNestedGraphTypeSpecification


class CopyOfGraphType(Expression):
    """AST Expression for <copy of graph type>."""

    copy_of_graph_type: GraphTypeReference | ExternalObjectReference


class SimpleLinearDataAccessingStatement(Expression):
    """AST Expression for <simple linear data-accessing statement>."""

    list_simple_data_accessing_statement: list[SimpleDataAccessingStatement]


class SimpleDataAccessingStatement(Expression):
    """Semantic marker for <simple data-accessing statement> in the Abstract Syntax Tree (AST)."""

    pass


class SetItemList(Expression):
    """AST Expression for <set item list>."""

    list_set_item: list[SetItem]


class SetItem(Expression):
    """Semantic marker for <set item> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_set_item(self):
        if isinstance(self, SetLabelItem):
            self.require_feature(F.GD02)
        return self


class RemoveItemList(Expression):
    """AST Expression for <remove item list>."""

    list_remove_item: list[RemoveItem]


class RemoveItem(Expression):
    """Semantic marker for <remove item> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_remove_item(self):
        if isinstance(self, RemoveLabelItem):
            self.require_feature(F.GD02)
        return self


class DeleteItemList(Expression):
    """AST Expression for <delete item list>."""

    list_delete_item: list[DeleteItem]

    @model_validator(mode="after")
    def _check_delete_item_list(self):
        procedure_body = self.find_first(ProcedureBody)
        if procedure_body is not None:
            self.require_feature(F.GD03)

        for item in self.list_delete_item:
            if not isinstance(item, Identifier):
                self.require_feature(F.GD04)
                break

        return self


class CompositeQueryExpression(Statement):
    """AST Expression for <composite query expression>."""

    class _QueryConjunctionElement(Expression):
        """Internal expression."""

        query_conjunction: QueryConjunction
        composite_query_primary: CompositeQueryPrimary

    left_composite_query_primary: CompositeQueryPrimary
    query_conjunction_elements: list[_QueryConjunctionElement] | None

    @model_validator(mode="after")
    def _check_composite_query_expression(self):
        if self.query_conjunction_elements:
            for element in self.query_conjunction_elements:
                conj = element.query_conjunction.query_conjunction
                if isinstance(conj, QueryConjunction._Otherwise):
                    self.require_feature(F.GQ02)  # Composite query: OTHERWISE
                elif isinstance(conj, SetOperator):
                    op_type = conj.set_operator_type
                    is_all = (
                        conj.set_quantifier is not None
                        and conj.set_quantifier.set_quantifier == SetQuantifier.Quantifier.ALL
                    )
                    if op_type == SetOperator.SetOperatorType.UNION:
                        self.require_feature(F.GQ03)  # Composite query: UNION
                    elif op_type == SetOperator.SetOperatorType.EXCEPT:
                        if is_all:
                            self.require_feature(F.GQ05)  # Composite query: EXCEPT ALL
                        else:
                            self.require_feature(F.GQ04)  # Composite query: EXCEPT DISTINCT
                    elif op_type == SetOperator.SetOperatorType.INTERSECT:
                        if is_all:
                            self.require_feature(F.GQ07)  # Composite query: INTERSECT ALL
                        else:
                            self.require_feature(F.GQ06)  # Composite query: INTERSECT DISTINCT
        return self


class QueryConjunction(Expression):
    """AST Expression for <query conjunction>."""

    class _Otherwise(Expression):
        """Internal expression."""

        pass

    query_conjunction: SetOperator | _Otherwise


class SetOperator(Expression):
    """AST Expression for <set operator>."""

    class SetOperatorType(Enum):
        UNION = auto()
        EXCEPT = auto()
        INTERSECT = auto()

    set_operator_type: SetOperatorType
    set_quantifier: SetQuantifier | None


class LinearQueryStatement(Expression):
    """Semantic marker for <linear query statement> in the Abstract Syntax Tree (AST)."""

    pass


class FocusedLinearQueryStatementPart(Expression):
    """AST Expression for <focused linear query statement part>."""

    use_graph_clause: UseGraphClause
    simple_linear_query_statement: SimpleLinearQueryStatement


class FocusedLinearQueryAndPrimitiveResultStatementPart(Expression):
    """AST Expression for <focused linear query and primitive result statement part>."""

    use_graph_clause: UseGraphClause
    simple_linear_query_statement: SimpleLinearQueryStatement
    primitive_result_statement: PrimitiveResultStatement


class FocusedPrimitiveResultStatement(Expression):
    """AST Expression for <focused primitive result statement>."""

    use_graph_clause: UseGraphClause
    primitive_result_statement: PrimitiveResultStatement


class FocusedNestedQuerySpecification(Expression):
    """AST Expression for <focused nested query specification>."""

    use_graph_clause: UseGraphClause
    nested_query_specification: NestedQuerySpecification


class SimpleLinearQueryStatement(Expression):
    """AST Expression for <simple linear query statement>."""

    list_simple_query_statement: list[SimpleQueryStatement]


class OptionalOperand(Expression):
    """AST Expression for <optional operand>."""

    optional_operand: SimpleMatchStatement | MatchStatementBlock

    @model_validator(mode="after")
    def _check_optional_operand(self):
        if isinstance(self.optional_operand, MatchStatementBlock):
            self.require_feature(F.GQ21)  # OPTIONAL: Multiple MATCH statements
        return self


class MatchStatementBlock(Expression):
    """AST Expression for <match statement block>."""

    list_match_statement: list[MatchStatement]


class LetVariableDefinitionList(Expression):
    """AST Expression for <let variable definition list>."""

    list_let_variable_definition: list[LetVariableDefinition]


class LetVariableDefinition(Expression):
    """AST Expression for <let variable definition>."""

    class _BindingVariableValueExpression(Expression):
        """Internal expression."""

        binding_variable: BindingVariable
        value_expression: ValueExpression

    let_variable_definition: ValueVariableDefinition | _BindingVariableValueExpression


class ForItem(Expression):
    """AST Expression for <for item>."""

    for_item_alias: ForItemAlias
    for_item_source: ForItemSource


class ForItemAlias(Expression):
    """AST Expression for <for item alias>."""

    binding_variable: BindingVariable


class ForOrdinalityOrOffset(Expression):
    """AST Expression for <for ordinality or offset>."""

    class Mode(Enum):
        ORDINALITY = auto()
        OFFSET = auto()

    mode: Mode
    binding_variable: BindingVariable


class PrimitiveResultStatement(Expression):
    """AST Expression for <primitive result statement>."""

    class _ReturnStatementOrderByAndPageStatement(Expression):
        """Internal expression."""

        return_statement: ReturnStatement
        order_by_and_page_statement: OrderByAndPageStatement | None

    class _Finish(Expression):
        """Internal expression."""

        pass

    primitive_result_statement: _ReturnStatementOrderByAndPageStatement | _Finish

    @model_validator(mode="after")
    def _check_primitive_result_statement(self):
        stmt = self.primitive_result_statement
        if not isinstance(stmt, self._ReturnStatementOrderByAndPageStatement):
            return self
        obs = stmt.order_by_and_page_statement
        if obs is None:
            return self
        page = obs.order_by_and_page_statement
        if not isinstance(page, OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause):
            return self

        order_by = page.order_by_clause
        sort_specs = order_by.sort_specification_list.list_sort_specification

        def _extract_simple_binding_variable(sort_key):
            """Extract the Identifier if the sort key is a simple binding variable reference."""
            node = sort_key
            while True:
                children = list(node.children())
                if len(children) == 0:
                    return node if isinstance(node, Identifier) else None
                if len(children) == 1:
                    node = children[0]
                else:
                    return None

        # GQ14: without this feature, sort keys must be simple binding variable references
        for spec in sort_specs:
            if _extract_simple_binding_variable(spec.sort_key) is None:
                self.require_feature(F.GQ14)  # Complex expressions in sort keys
                break

        # GQ16: without this feature, sort keys shall not contain binding variable
        # references that match return item aliases from the preceding return statement
        return_body = stmt.return_statement.return_statement_body.return_statement_body
        if isinstance(return_body, ReturnStatementBody._SetQuantifierReturnItemListGroupByClause):
            alias_names = set()
            for item in return_body.return_item_list.list_return_item:
                if item.return_item_alias is not None:
                    alias_names.add(item.return_item_alias.identifier.name)
            if alias_names:
                for spec in sort_specs:
                    ident = _extract_simple_binding_variable(spec.sort_key)
                    if ident is not None and ident.name in alias_names:
                        self.require_feature(F.GQ16)  # Pre-projection aliases in sort keys
                        break

        return self


class ReturnStatement(Expression):
    """AST Expression for <return statement>."""

    return_statement_body: ReturnStatementBody


class ReturnStatementBody(Expression):
    """AST Expression for <return statement body>."""

    class _SetQuantifierAsteriskGroupByClause(Expression):
        """Internal expression."""

        set_quantifier: SetQuantifier | None
        asterisk: Asterisk
        group_by_clause: GroupByClause | None

    class _SetQuantifierReturnItemListGroupByClause(Expression):
        """Internal expression."""

        set_quantifier: SetQuantifier | None
        return_item_list: ReturnItemList
        group_by_clause: GroupByClause | None

    class _NoBindings(Expression):
        """Internal expression."""

        pass

    return_statement_body: (
        _SetQuantifierAsteriskGroupByClause
        | _SetQuantifierReturnItemListGroupByClause
        | _NoBindings
    )


class ReturnItemList(Expression):
    """AST Expression for <return item list>."""

    list_return_item: list[ReturnItem]


class ReturnItem(Expression):
    """AST Expression for <return item>."""

    aggregating_value_expression: AggregatingValueExpression
    return_item_alias: ReturnItemAlias | None


class ReturnItemAlias(Expression):
    """AST Expression for <return item alias>."""

    identifier: Identifier


class SelectStatement(Expression):
    """AST Expression for <select statement>."""

    class _SelectStatementBodyWithClauses(Expression):
        """Internal expression."""

        select_statement_body: SelectStatementBody
        where_clause: WhereClause | None
        group_by_clause: GroupByClause | None
        having_clause: HavingClause | None
        order_by_clause: OrderByClause | None
        offset_clause: OffsetClause | None
        limit_clause: LimitClause | None

    set_quantifier: SetQuantifier | None
    projection: Asterisk | SelectItemList
    body: _SelectStatementBodyWithClauses | None

    @model_validator(mode="after")
    def _check_select_statement(self):
        self.require_feature(F.GG_SS01)
        return self


class SelectItemList(Expression):
    """AST Expression for <select item list>."""

    list_select_item: list[SelectItem]


class SelectItem(Expression):
    """AST Expression for <select item>."""

    aggregating_value_expression: AggregatingValueExpression
    select_item_alias: SelectItemAlias | None


class SelectItemAlias(Expression):
    """AST Expression for <select item alias>."""

    identifier: Identifier


class HavingClause(Expression):
    """AST Expression for <having clause>."""

    search_condition: SearchCondition


class SelectStatementBody(Expression):
    """AST Expression for <select statement body>."""

    select_statement_body: SelectGraphMatchList | SelectQuerySpecification


class SelectGraphMatchList(Expression):
    """AST Expression for <select graph match list>."""

    list_select_graph_match: list[SelectGraphMatch]


class SelectGraphMatch(Expression):
    """AST Expression for <select graph match>."""

    graph_expression: GraphExpression
    match_statement: MatchStatement


class SelectQuerySpecification(Expression):
    """AST Expression for <select query specification>."""

    class _GraphExpressionNestedQuerySpecification(Expression):
        """Internal expression."""

        graph_expression: GraphExpression
        nested_query_specification: NestedQuerySpecification

    select_query_specification: NestedQuerySpecification | _GraphExpressionNestedQuerySpecification


class SimpleQueryStatement(SimpleDataAccessingStatement):
    """Semantic marker for <simple query statement> in the Abstract Syntax Tree (AST)."""

    pass


class ProcedureCall(Expression):
    """Semantic marker for <procedure call> in the Abstract Syntax Tree (AST)."""

    pass


class VariableScopeClause(Expression):
    """AST Expression for <variable scope clause>."""

    binding_variable_reference_list: BindingVariableReferenceList | None


class BindingVariableReferenceList(Expression):
    """AST Expression for <binding variable reference list>."""

    list_binding_variable_reference: list[BindingVariableReference]


class ProcedureArgumentList(Expression):
    """AST Expression for <procedure argument list>."""

    list_procedure_argument: list[ProcedureArgument]


class AtSchemaClause(Expression):
    """AST Expression for <at schema clause>."""

    schema_reference: SchemaReference

    @model_validator(mode="after")
    def _check_at_schema_clause(self):
        self.require_feature(F.GG_SC01)  # Schema references: AT clause
        return self


class UseGraphClause(Expression):
    """AST Expression for <use graph clause>."""

    graph_expression: GraphExpression

    @model_validator(mode="after")
    def _check_use_graph_clause(self):
        self.require_feature(F.GQ01)  # USE graph clause
        return self


class GraphPatternBindingTable(Expression):
    """AST Expression for <graph pattern binding table>."""

    graph_pattern: GraphPattern
    graph_pattern_yield_clause: GraphPatternYieldClause | None

    @model_validator(mode="after")
    def _check_graph_pattern_binding_table(self):
        if self.graph_pattern_yield_clause is not None:
            self.require_feature(F.GQ19)  # Graph pattern YIELD clause
        return self


class GraphPatternYieldClause(Expression):
    """AST Expression for <graph pattern yield clause>."""

    graph_pattern_yield_item_list: GraphPatternYieldItemList


class GraphPatternYieldItemList(Expression):
    """AST Expression for <graph pattern yield item list>."""

    class _NoBindings(Expression):
        """Internal expression."""

        pass

    graph_pattern_yield_item_list: list[GraphPatternYieldItem] | _NoBindings


class GraphPattern(Expression):
    """AST Expression for <graph pattern>."""

    match_mode: MatchMode | None
    path_pattern_list: PathPatternList
    keep_clause: KeepClause | None
    graph_pattern_where_clause: GraphPatternWhereClause | None

    def effective_match_mode(self, dialect: Dialect) -> type[MatchMode]:
        """Resolve the effective match-mode type under *dialect*.

        Returns the class of the user-written match mode when present,
        otherwise the dialect's implementation-defined default.
        """
        if self.match_mode is not None:
            return type(self.match_mode)
        return dialect.DEFAULT_MATCH_MODE


class MatchMode(Expression):
    """Semantic marker for <match mode> in the Abstract Syntax Tree (AST)."""

    pass


class PathPatternList(Expression):
    """AST Expression for <path pattern list>."""

    list_path_pattern: list[PathPattern]


class PathPattern(Expression):
    """AST Expression for <path pattern>."""

    path_variable_declaration: PathVariableDeclaration | None
    path_pattern_prefix: PathPatternPrefix | None
    path_pattern_expression: PathPatternExpression

    @model_validator(mode="after")
    def _check_path_pattern(self):
        if isinstance(self.path_pattern_prefix, PathSearchPrefix):
            self.require_feature(F.G005)
        return self

    def effective_path_mode(self, dialect: Dialect) -> PathMode.Mode:
        """Resolve the effective path mode under *dialect*.

        Returns the user-written mode — either the one wrapped in a
        ``PathModePrefix`` (``MATCH TRAIL (a)-[r]-(b)``) or the one
        attached to a ``PathSearchPrefix`` variant such as
        ``AllPathSearch`` (``MATCH ALL TRAIL (a)-[r]-(b)``) — and falls
        back to the dialect's implementation-defined default otherwise.
        """
        prefix = self.path_pattern_prefix
        if isinstance(prefix, PathModePrefix):
            return prefix.path_mode.mode
        # PathSearchPrefix is a marker class; its concrete subclasses
        # (AllPathSearch, AnyPathSearch, the four Shortest variants) all
        # carry an optional `path_mode` field.
        inner: PathMode | None = getattr(prefix, "path_mode", None)
        if inner is not None:
            return inner.mode
        return dialect.DEFAULT_PATH_MODE


class PathVariableDeclaration(Expression):
    """AST Expression for <path variable declaration>."""

    path_variable: PathVariable

    @model_validator(mode="after")
    def _check_path_variable_declaration(self):
        self.require_feature(F.G004)
        return self


class KeepClause(Expression):
    """AST Expression for <keep clause>."""

    path_pattern_prefix: PathPatternPrefix

    @model_validator(mode="after")
    def _check_keep_clause(self):
        if isinstance(self.path_pattern_prefix, PathModePrefix):
            self.require_feature(F.G006)
        if isinstance(self.path_pattern_prefix, PathSearchPrefix):
            self.require_feature(F.G007)
        return self


class GraphPatternWhereClause(Expression):
    """AST Expression for <graph pattern where clause>."""

    search_condition: SearchCondition


class InsertPathPatternList(Expression):
    """AST Expression for <insert path pattern list>."""

    list_insert_path_pattern: list[InsertPathPattern]


class InsertPathPattern(Expression):
    """AST Expression for <insert path pattern>."""

    class _InsertEdgePatternInsertNodePattern(Expression):
        """Internal expression."""

        insert_edge_pattern: InsertEdgePattern
        insert_node_pattern: InsertNodePattern

    insert_node_pattern: InsertNodePattern
    list_insert_edge_pattern_insert_node_pattern: list[_InsertEdgePatternInsertNodePattern] | None


class InsertNodePattern(Expression):
    """AST Expression for <insert node pattern>."""

    insert_element_pattern_filler: InsertElementPatternFiller | None


class InsertEdgePattern(Expression):
    """Semantic marker for <insert edge pattern> in the Abstract Syntax Tree (AST)."""

    pass


class InsertElementPatternFiller(Expression):
    """AST Expression for <insert element pattern filler>."""

    class _ElementVariableDeclarationLabelAndPropertySetSpecification(Expression):
        """Internal expression."""

        element_variable_declaration: ElementVariableDeclaration
        label_and_property_set_specification: LabelAndPropertySetSpecification

    insert_element_pattern_filler: (
        _ElementVariableDeclarationLabelAndPropertySetSpecification
        | ElementVariableDeclaration
        | LabelAndPropertySetSpecification
    )


class LabelAndPropertySetSpecification(Expression):
    """AST Expression for <label and property set specification>."""

    class _LabelSetSpecificationElementPropertySpecification(Expression):
        """Internal expression."""

        label_set_specification: LabelSetSpecification
        element_property_specification: ElementPropertySpecification

    label_and_property_set_specification: (
        _LabelSetSpecificationElementPropertySpecification
        | LabelSetSpecification
        | ElementPropertySpecification
    )


class PathPatternPrefix(Expression):
    """Semantic marker for <path pattern prefix> in the Abstract Syntax Tree (AST)."""

    pass


class PathMode(Expression):
    """AST Expression for <path mode>."""

    class Mode(Enum):
        WALK = auto()
        TRAIL = auto()
        SIMPLE = auto()
        ACYCLIC = auto()

    mode: PathMode.Mode

    @model_validator(mode="after")
    def _check_path_mode(self):
        match self.mode:
            case PathMode.Mode.WALK:
                self.require_feature(F.G010)
            case PathMode.Mode.TRAIL:
                self.require_feature(F.G011)
            case PathMode.Mode.SIMPLE:
                self.require_feature(F.G012)
            case PathMode.Mode.ACYCLIC:
                self.require_feature(F.G013)
        return self


class PathPatternExpression(Expression):
    """Semantic marker for <path pattern expression> in the Abstract Syntax Tree (AST)."""

    pass


class ElementPatternFiller(Expression):
    """AST Expression for <element pattern filler>."""

    element_variable_declaration: ElementVariableDeclaration | None
    is_label_expression: IsLabelExpression | None
    element_pattern_predicate: ElementPatternPredicate | None


class ElementVariableDeclaration(Expression):
    """AST Expression for <element variable declaration>."""

    temp: bool
    element_variable: ElementVariable


class IsLabelExpression(Expression):
    """AST Expression for <is label expression>."""

    label_expression: LabelExpression


class ElementPatternPredicate(Expression):
    """Semantic marker for <element pattern predicate> in the Abstract Syntax Tree (AST)."""

    pass


class PropertyKeyValuePairList(Expression):
    """AST Expression for <property key value pair list>."""

    list_property_key_value_pair: list[PropertyKeyValuePair]


class PropertyKeyValuePair(Expression):
    """AST Expression for <property key value pair>."""

    property_name: PropertyName
    value_expression: ValueExpression


class SubpathVariableDeclaration(Expression):
    """AST Expression for <subpath variable declaration>."""

    subpath_variable: SubpathVariable


class ParenthesizedPathPatternWhereClause(Expression):
    """AST Expression for <parenthesized path pattern where clause>."""

    search_condition: SearchCondition


class LabelExpression(Expression):
    """AST Expression for <label expression> and <label disjunction>."""

    label_terms: list[LabelTerm]


class GraphPatternQuantifier(Expression):
    """Semantic marker for <graph pattern quantifier> in the Abstract Syntax Tree (AST)."""

    # Asterisk and Plus sign here are modelled as GeneralQuantifier given the equivalent syntax:
    # * = {0,}
    # + = {1,}

    @model_validator(mode="after")
    def _check_graph_pattern_quantifier(self):
        if isinstance(self, GeneralQuantifier):
            if self.upper_bound is None:
                self.require_feature(F.G061)
        return self


class SimplifiedContents(Expression):
    """Semantic marker for <simplified contents> in the Abstract Syntax Tree (AST)."""

    pass


class WhereClause(Expression):
    """AST Expression for <where clause>."""

    search_condition: SearchCondition


class YieldClause(Expression):
    """AST Expression for <yield clause>."""

    yield_item_list: YieldItemList


class YieldItemList(Expression):
    """AST Expression for <yield item list>."""

    list_yield_item: list[YieldItem]


class YieldItem(Expression):
    """AST Expression for <yield item>."""

    yield_item_name: YieldItemName
    yield_item_alias: YieldItemAlias | None


class YieldItemAlias(Expression):
    """AST Expression for <yield item alias>."""

    binding_variable: BindingVariable


class GroupByClause(Expression):
    """AST Expression for <group by clause>."""

    grouping_element_list: GroupingElementList

    @model_validator(mode="after")
    def _check_group_by_clause(self):
        self.require_feature(F.GQ15)  # GROUP BY clause
        return self


class GroupingElementList(Expression):
    """AST Expression for <grouping element list>."""

    grouping_element_list: list[GroupingElement] | EmptyGroupingSet


class EmptyGroupingSet(Expression):
    """AST Expression for <empty grouping set>."""

    pass


class OrderByClause(Expression):
    """AST Expression for <order by clause>."""

    sort_specification_list: SortSpecificationList


class SortSpecificationList(Expression):
    """AST Expression for <sort specification list>."""

    list_sort_specification: list[SortSpecification]


class SortSpecification(Expression):
    """AST Expression for <sort specification>."""

    sort_key: SortKey
    ordering_specification: OrderingSpecification | None
    null_ordering: NullOrdering | None

    @model_validator(mode="after")
    def _check_sort_specification(self):
        if self.sort_key.find_first(AggregateFunction) is not None:
            self.require_feature(F.GF20)
        return self

    def effective_order_direction(self, dialect: Dialect) -> OrderingSpecification.Order:
        """Resolve the effective sort direction (ASC/DESC) under *dialect*.

        Returns the user-written direction when ``ordering_specification``
        is set, otherwise the dialect's implementation-defined default.
        """
        if self.ordering_specification is not None:
            return self.ordering_specification.ordering_specification
        return dialect.DEFAULT_ORDER_DIRECTION


class OrderingSpecification(Expression):
    """AST Expression for <ordering specification>."""

    class Order(Enum):
        ASC = auto()
        DESC = auto()

    ordering_specification: OrderingSpecification.Order


class NullOrdering(Expression):
    """AST Expression for <null ordering>."""

    class Order(Enum):
        NULLS_FIRST = auto()
        NULLS_LAST = auto()

    null_ordering: NullOrdering.Order

    @model_validator(mode="after")
    def _check_null_ordering(self):
        self.require_feature(F.GA03)
        return self


class LimitClause(Expression):
    """AST Expression for <limit clause>."""

    non_negative_integer_specification: NonNegativeIntegerSpecification


class OffsetClause(Expression):
    """AST Expression for <offset clause>."""

    non_negative_integer_specification: NonNegativeIntegerSpecification


class SchemaReference(Expression):
    """Semantic marker for <schema reference> in the Abstract Syntax Tree (AST)."""

    pass


class CatalogSchemaParentAndName(Expression):
    """AST Expression for <catalog schema parent and name>."""

    absolute_directory_path: AbsoluteDirectoryPath
    schema_name: SchemaName


class PredefinedSchemaReference(Expression):
    """AST Expression for <predefined schema reference>."""

    class _HomeSchema(Expression):
        """Internal expression."""

        @model_validator(mode="after")
        def _check_home_schema(self):
            self.require_feature(F.GG_SC02)  # Schema references: HOME_SCHEMA
            return self

    class _CurrentSchema(Expression):
        """Internal expression."""

        @model_validator(mode="after")
        def _check_current_schema(self):
            self.require_feature(F.GG_SC03)  # Schema references: CURRENT_SCHEMA
            return self

    class _Period(Expression):
        """Internal expression."""

        pass

    predefined_schema_reference: _HomeSchema | _CurrentSchema | _Period


class AbsoluteDirectoryPath(Expression):
    """AST Expression for <absolute directory path>."""

    simple_directory_path: SimpleDirectoryPath | None


class RelativeDirectoryPath(Expression):
    """AST Expression for <relative directory path>."""

    up_levels: int
    simple_directory_path: SimpleDirectoryPath | None


class SimpleDirectoryPath(Expression):
    """AST Expression for <simple directory path>."""

    items: list[DirectoryName]


class CatalogGraphParentAndName(Expression):
    """AST Expression for <catalog graph parent and name>."""

    catalog_object_parent_reference: CatalogObjectParentReference | None
    graph_name: GraphName


class HomeGraph(Expression):
    """AST Expression for <home graph>."""

    pass


class GraphTypeReference(Expression):
    """Semantic marker for <graph type reference> in the Abstract Syntax Tree (AST)."""

    pass


class CatalogBindingTableParentAndName(Expression):
    """AST Expression for <catalog binding table parent and name>."""

    catalog_object_parent_reference: CatalogObjectParentReference | None
    binding_table_name: BindingTableName


class ProcedureReference(Expression):
    """Semantic marker for <procedure reference> in the Abstract Syntax Tree (AST)."""

    pass


class CatalogObjectParentReference(Expression):
    """AST Expression for <catalog object parent reference>."""

    class _SchemaReferenceSolidusListObjectName(Expression):
        """Internal expression."""

        schema_reference: SchemaReference
        solidus: bool
        list_object_name: list[ObjectName] | None

    catalog_object_parent_reference: _SchemaReferenceSolidusListObjectName | list[ObjectName]


class ExternalObjectReference(Expression):
    """AST Expression for <external object reference>."""

    uri: CharacterStringLiteral

    @model_validator(mode="after")
    def _check_external_object_reference(self):
        self.require_feature(F.GH01)
        if ":" not in self.uri.value:
            raise ValueError(
                "External object reference must be a URI with a mandatory scheme (containing ':')"
            )
        return self


class NestedGraphTypeSpecification(Expression):
    """AST Expression for <nested graph type specification>."""

    graph_type_specification_body: GraphTypeSpecificationBody


class ElementTypeList(Expression):
    """AST Expression for <element type list>."""

    list_element_type_specification: list[ElementTypeSpecification]


class ElementTypeSpecification(Expression):
    """Semantic marker for <element type specification> in the Abstract Syntax Tree (AST)."""

    pass


class NodeTypePhraseFiller(Expression):
    """AST Expression for <node type phrase filler>."""

    class _NodeTypeNameNodeTypeFiller(Expression):
        """Internal expression."""

        node_type_name: NodeTypeName
        node_type_filler: NodeTypeFiller | None

    node_type_phrase_filler: _NodeTypeNameNodeTypeFiller | NodeTypeFiller

    @model_validator(mode="after")
    def _check_node_type_phrase_filler(self):
        # GG20: node type specification shall not simply contain a node type name
        if isinstance(
            self.node_type_phrase_filler, NodeTypePhraseFiller._NodeTypeNameNodeTypeFiller
        ):
            if self.node_type_phrase_filler.node_type_filler is None:
                self.require_feature(F.GG20)
        return self


class NodeTypeFiller(Expression):
    """AST Expression for <node type filler>."""

    class _NodeTypeKeyLabelSetNodeTypeImpliedContent(Expression):
        """Internal expression."""

        node_type_key_label_set: NodeTypeKeyLabelSet
        node_type_implied_content: NodeTypeImpliedContent | None

    node_type_filler: _NodeTypeKeyLabelSetNodeTypeImpliedContent | NodeTypeImpliedContent

    @model_validator(mode="after")
    def _check_node_type_filler(self):
        # GG21: node type specification shall not simply contain a node type key label set
        if isinstance(
            self.node_type_filler, NodeTypeFiller._NodeTypeKeyLabelSetNodeTypeImpliedContent
        ):
            if self.node_type_filler.node_type_implied_content is None:
                self.require_feature(F.GG21)
        return self


class NodeTypeImpliedContent(Expression):
    """AST Expression for <node type implied content>."""

    class _NodeTypeLabelSetNodeTypePropertyTypes(Expression):
        """Internal expression."""

        node_type_label_set: NodeTypeLabelSet
        node_type_property_types: NodeTypePropertyTypes

    node_type_implied_content: (
        NodeTypeLabelSet | NodeTypePropertyTypes | _NodeTypeLabelSetNodeTypePropertyTypes
    )


class NodeTypeKeyLabelSet(Expression):
    """AST Expression for <node type key label set>."""

    label_set_phrase: LabelSetPhrase | None


class EdgeTypePhraseFiller(Expression):
    """AST Expression for <edge type phrase filler>."""

    class _EdgeTypeNameEdgeTypeFiller(Expression):
        """Internal expression."""

        edge_type_name: EdgeTypeName
        edge_type_filler: EdgeTypeFiller | None

    edge_type_phrase_filler: _EdgeTypeNameEdgeTypeFiller | EdgeTypeFiller

    @model_validator(mode="after")
    def _check_edge_type_phrase_filler(self):
        # GG20: edge type specification shall not simply contain an edge type name
        if isinstance(
            self.edge_type_phrase_filler, EdgeTypePhraseFiller._EdgeTypeNameEdgeTypeFiller
        ):
            if self.edge_type_phrase_filler.edge_type_filler is None:
                self.require_feature(F.GG20)
        return self


class EdgeTypeFiller(Expression):
    """AST Expression for <edge type filler>."""

    class _EdgeTypeKeyLabelSetEdgeTypeImpliedContent(Expression):
        """Internal expression."""

        edge_type_key_label_set: EdgeTypeKeyLabelSet
        edge_type_implied_content: EdgeTypeImpliedContent | None

    edge_type_filler: _EdgeTypeKeyLabelSetEdgeTypeImpliedContent | EdgeTypeImpliedContent

    @model_validator(mode="after")
    def _check_edge_type_filler(self):
        # GG21: edge type specification shall not simply contain an edge type key label set
        if isinstance(
            self.edge_type_filler, EdgeTypeFiller._EdgeTypeKeyLabelSetEdgeTypeImpliedContent
        ):
            if self.edge_type_filler.edge_type_implied_content is None:
                self.require_feature(F.GG21)
        return self


class EdgeTypeImpliedContent(Expression):
    """AST Expression for <edge type implied content>."""

    class _EdgeTypeLabelSetEdgeTypePropertyTypes(Expression):
        """Internal expression."""

        edge_type_label_set: EdgeTypeLabelSet
        edge_type_property_types: EdgeTypePropertyTypes

    edge_type_implied_content: (
        EdgeTypeLabelSet | EdgeTypePropertyTypes | _EdgeTypeLabelSetEdgeTypePropertyTypes
    )


class EdgeTypeKeyLabelSet(Expression):
    """AST Expression for <edge type key label set>."""

    label_set_phrase: LabelSetPhrase | None


class EdgeTypePatternDirected(Expression):
    """Semantic marker for <edge type pattern directed> in the Abstract Syntax Tree (AST)."""

    pass


class EdgeTypePatternUndirected(Expression):
    """AST Expression for <edge type pattern undirected>."""

    source_node_type_reference: SourceNodeTypeReference
    arc_type_undirected: ArcTypeUndirected
    destination_node_type_reference: DestinationNodeTypeReference

    @model_validator(mode="after")
    def _check_edge_type_pattern_undirected(self):
        self.require_feature(F.GH02)
        return self


class ArcTypePointingRight(Expression):
    """AST Expression for <arc type pointing right>."""

    edge_type_filler: EdgeTypeFiller


class ArcTypePointingLeft(Expression):
    """AST Expression for <arc type pointing left>."""

    edge_type_filler: EdgeTypeFiller


class ArcTypeUndirected(Expression):
    """AST Expression for <arc type undirected>."""

    edge_type_filler: EdgeTypeFiller


class SourceNodeTypeReference(Expression):
    """AST Expression for <source node type reference>."""

    class _LeftParenSourceNodeTypeAliasRightParen(Expression):
        """Internal expression."""

        source_node_type_alias: SourceNodeTypeAlias

    class _LeftParenNodeTypeFillerRightParen(Expression):
        """Internal expression."""

        node_type_filler: NodeTypeFiller | None

    source_node_type_reference: (
        _LeftParenSourceNodeTypeAliasRightParen | _LeftParenNodeTypeFillerRightParen
    )


class DestinationNodeTypeReference(Expression):
    """AST Expression for <destination node type reference>."""

    class _LeftParenDestinationNodeTypeAliasRightParen(Expression):
        """Internal expression."""

        destination_node_type_alias: DestinationNodeTypeAlias

    class _LeftParenNodeTypeFillerRightParen(Expression):
        """Internal expression."""

        node_type_filler: NodeTypeFiller | None

    destination_node_type_reference: (
        _LeftParenDestinationNodeTypeAliasRightParen | _LeftParenNodeTypeFillerRightParen
    )


class EdgeKind(Enum):
    """Enum for <edge kind>."""

    DIRECTED = auto()
    UNDIRECTED = auto()


class EndpointPairPhrase(Expression):
    """AST Expression for <endpoint pair phrase>."""

    endpoint_pair: EndpointPair


class EndpointPair(Expression):
    """Semantic marker for <endpoint pair> in the Abstract Syntax Tree (AST)."""

    pass


class ConnectorPointingRight(Expression):
    """AST Expression for <connector pointing right>."""

    pass


class ConnectorUndirected(Expression):
    """AST Expression for <connector undirected>."""

    pass


class LabelSetPhrase(Expression):
    """AST Expression for <label set phrase>."""

    class _LabelLabelName(Expression):
        """Internal expression."""

        label_name: LabelName

    class _LabelsLabelSetSpecification(Expression):
        """Internal expression."""

        label_set_specification: LabelSetSpecification

    class _IsOrColonLabelSetSpecification(Expression):
        """Internal expression."""

        label_set_specification: LabelSetSpecification

    label_set_phrase: (
        _LabelLabelName | _LabelsLabelSetSpecification | _IsOrColonLabelSetSpecification
    )


class LabelSetSpecification(Expression):
    """AST Expression for <label set specification>."""

    list_label_name: list[LabelName]


class PropertyTypesSpecification(Expression):
    """AST Expression for <property types specification>."""

    property_type_list: PropertyTypeList | None


class PropertyTypeList(Expression):
    """AST Expression for <property type list>."""

    list_property_type: list[PropertyType]


class PropertyType(Expression):
    """AST Expression for <property type>."""

    property_name: PropertyName
    typed: Typed | None
    property_value_type: PropertyValueType

    @model_validator(mode="after")
    def _check_property_type(self):
        if self.property_value_type.find_first(RecordType):
            self.require_feature(F.GV48)  # Nested record types
        return self


class BindingTableType(Expression):
    """AST Expression for <binding table type>."""

    field_types_specification: FieldTypesSpecification


class ValueType(Expression):
    """Semantic marker for <value type> in the Abstract Syntax Tree (AST)."""

    pass


class Typed(Expression):
    """AST Expression for <typed>."""

    pass


class TemporalDurationQualifier(Expression):
    """AST Expression for <temporal duration qualifier>."""

    class _YearToMonth(Expression):
        """Internal expression."""

        pass

    class _DayToSecond(Expression):
        """Internal expression."""

        pass

    temporal_duration_qualifier: _YearToMonth | _DayToSecond


class ListValueTypeName(Expression):
    """AST Expression for <list value type name>."""

    group: bool


class ListValueTypeNameSynonym(Expression):
    """AST Expression for <list value type name synonym>."""

    pass


class FieldTypesSpecification(Expression):
    """AST Expression for <field types specification>."""

    field_type_list: FieldTypeList | None


class FieldTypeList(Expression):
    """AST Expression for <field type list>."""

    list_field_type: list[FieldType]


class ComponentTypeList(Expression):
    """AST Expression for <component type list>."""

    list_component_type: list[ComponentType]


class NotNull(Expression):
    """AST Expression for <not null>."""

    pass


class FieldType(Expression):
    """AST Expression for <field type>."""

    field_name: FieldName
    typed: Typed | None
    value_type: ValueType

    @model_validator(mode="after")
    def _check_field_type(self):
        if self.value_type.find_first(RecordType):
            self.require_feature(F.GV48)  # Nested record types
        return self


class IsLabeledOrColon(Expression):
    """AST Expression for <is labeled or colon>."""

    class _IsNotLabeled(Expression):
        """Internal expression."""

        not_: bool

    class _Colon(Expression):
        """Internal expression."""

        pass

    is_labeled_or_colon: _IsNotLabeled | _Colon


class ValueSpecification(Expression):
    """Semantic marker for <value specification> in the Abstract Syntax Tree (AST)."""

    pass


class NonNegativeIntegerSpecification(Expression):
    """Semantic marker for <non-negative integer specification> in the Abstract Syntax Tree."""

    pass


class LetValueExpression(Expression):
    """AST Expression for <let value expression>."""

    let_variable_definition_list: LetVariableDefinitionList
    value_expression: ValueExpression

    @model_validator(mode="after")
    def _check_let_value_expression(self):
        self.require_feature(F.GE03)
        return self


class ValueQueryExpression(Expression):
    """AST Expression for <value query expression>."""

    nested_query_specification: NestedQuerySpecification

    @model_validator(mode="after")
    def _check_value_query_expression(self):
        self.require_feature(F.GQ18)  # Scalar subqueries
        return self


class CaseExpression(Expression):
    """Semantic marker for <case expression> in the Abstract Syntax Tree (AST)."""

    pass


class SimpleWhenClause(Expression):
    """AST Expression for <simple when clause>."""

    when_operand_list: WhenOperandList
    result: Result


class SearchedWhenClause(Expression):
    """AST Expression for <searched when clause>."""

    search_condition: SearchCondition
    result: Result


class ElseClause(Expression):
    """AST Expression for <else clause>."""

    result: Result


class WhenOperandList(Expression):
    """AST Expression for <when operand list>."""

    list_when_operand: list[WhenOperand]


class CastSpecification(Expression):
    """AST Expression for <cast specification>."""

    cast_operand: CastOperand
    cast_target: CastTarget

    @model_validator(mode="after")
    def _check_cast_specification(self):
        self.require_feature(F.GA05)
        return self


class AggregateFunction(Expression):
    """AST Expression for <aggregate function>."""

    class _CountAsterisk(Expression):
        """Internal expression."""

        pass

    aggregate_function: _CountAsterisk | GeneralSetFunction | BinarySetFunction

    @model_validator(mode="after")
    def _check_aggregate_function(self):
        if isinstance(self.aggregate_function, GeneralSetFunction):
            gsft = self.aggregate_function.general_set_function_type.general_set_function_type
            if isinstance(
                gsft,
                GeneralSetFunctionType._CollectList
                | GeneralSetFunctionType._StddevSamp
                | GeneralSetFunctionType._StddevPop,
            ):
                self.require_feature(F.GF10)
        elif isinstance(self.aggregate_function, BinarySetFunction):
            self.require_feature(F.GF11)
        return self


class GeneralSetFunction(Expression):
    """AST Expression for <general set function>."""

    general_set_function_type: GeneralSetFunctionType
    set_quantifier: SetQuantifier | None
    value_expression: ValueExpression


class BinarySetFunction(Expression):
    """AST Expression for <binary set function>."""

    class BinarySetFunctionType(Enum):
        PERCENTILE_CONT = auto()
        PERCENTILE_DISC = auto()

    binary_set_function_type: BinarySetFunction.BinarySetFunctionType
    dependent_value_expression: DependentValueExpression
    independent_value_expression: IndependentValueExpression


class GeneralSetFunctionType(Expression):
    """AST Expression for <general set function type>."""

    class _Avg(Expression):
        """Internal expression."""

        pass

    class _Count(Expression):
        """Internal expression."""

        pass

    class _Max(Expression):
        """Internal expression."""

        pass

    class _Min(Expression):
        """Internal expression."""

        pass

    class _Sum(Expression):
        """Internal expression."""

        pass

    class _CollectList(Expression):
        """Internal expression."""

        pass

    class _StddevSamp(Expression):
        """Internal expression."""

        pass

    class _StddevPop(Expression):
        """Internal expression."""

        pass

    general_set_function_type: (
        _Avg | _Count | _Max | _Min | _Sum | _CollectList | _StddevSamp | _StddevPop
    )


class SetQuantifier(Expression):
    """AST Expression for <set quantifier>."""

    class Quantifier(Enum):
        DISTINCT = auto()
        ALL = auto()

    set_quantifier: SetQuantifier.Quantifier


class DependentValueExpression(Expression):
    """AST Expression for <dependent value expression>."""

    set_quantifier: SetQuantifier | None
    numeric_value_expression: NumericValueExpression


class ElementIdFunction(Expression):
    """AST Expression for <element_id function>."""

    element_variable_reference: ElementVariableReference

    @model_validator(mode="after")
    def _check_element_id_function(self):
        self.require_feature(F.G100)
        return self


class PropertyReference(Expression):
    """AST Expression for <property reference>."""

    # If we have property_source: PropertySource, there is an infinite recursion loop
    # because PropertySource points to PropertyReference. To overcome this issue we define
    # PropertySourceExceptPropertyReference and allow property name to be a list.

    property_source: _PropertySourceExceptPropertyReference
    property_name: list[PropertyName]


class PathValueConstructorByEnumeration(Expression):
    """AST Expression for <path value constructor by enumeration>."""

    path_element_list: PathElementList

    @model_validator(mode="after")
    def _check_path_value_constructor_by_enumeration(self):
        self.require_feature(F.GE06)
        return self


class PathElementList(Expression):
    """AST Expression for <path element list>."""

    path_element_list_start: PathElementListStart
    list_path_element_list_step: list[PathElementListStep] | None


class PathElementListStep(Expression):
    """AST Expression for <path element list step>."""

    edge_reference_value_expression: EdgeReferenceValueExpression
    node_reference_value_expression: NodeReferenceValueExpression


class ListValueFunction(Expression):
    """Semantic marker for <list value function> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_list_value_function(self):
        self.require_feature(F.GV50)  # List value types
        return self


class ListValueConstructorByEnumeration(Expression):
    """AST Expression for <list value constructor by enumeration>."""

    list_value_type_name: ListValueTypeName | None
    list_element_list: ListElementList | None

    @model_validator(mode="after")
    def _check_list_value_constructor_by_enumeration(self):
        self.require_feature(F.GV50)  # List value types
        return self


class ListElementList(Expression):
    """AST Expression for <list element list>."""

    list_list_element: list[ListElement]


class FieldsSpecification(Expression):
    """AST Expression for <fields specification>."""

    field_list: FieldList | None


class FieldList(Expression):
    """AST Expression for <field list>."""

    list_field: list[Field]


class Field(Expression):
    """AST Expression for <field>."""

    field_name: FieldName
    value_expression: ValueExpression

    @model_validator(mode="after")
    def _check_field(self):
        if self.value_expression.find_first(RecordConstructor):
            self.require_feature(F.GV48)  # Nested record types
        return self


class BooleanTerm(Expression):
    """AST Expression for <boolean term>."""

    list_boolean_factor: list[BooleanFactor]


class BooleanFactor(Expression):
    """AST Expression for <boolean factor>."""

    not_: bool
    boolean_test: BooleanTest


class BooleanTest(Expression):
    """AST Expression for <boolean test>."""

    class _IsNotTruthValue(Expression):
        """Internal expression."""

        not_: bool
        truth_value: TruthValue

    boolean_primary: BooleanPrimary
    truth_value: _IsNotTruthValue | None


class TruthValue(Expression):
    """AST Expression for <truth value>."""

    class _True(Expression):
        """Internal expression."""

        pass

    class _False(Expression):
        """Internal expression."""

        pass

    class _Unknown(Expression):
        """Internal expression."""

        pass

    truth_value: _True | _False | _Unknown


class MultiplicativeOperator(Enum):
    MULTIPLY = "*"
    DIVIDE = "/"


class Term(Expression):
    """AST Expression for <term>."""

    class _MultiplicativeFactor(Expression):
        """Internal expression."""

        operator: MultiplicativeOperator
        factor: Factor

    base: Factor
    steps: list[_MultiplicativeFactor] | None = None


class Sign(Enum):
    PLUS_SIGN = "+"
    MINUS_SIGN = "-"


class Factor(Expression):
    """AST Expression for <factor>."""

    sign: Sign = Sign.PLUS_SIGN
    numeric_primary: NumericPrimary


class NumericValueFunction(Expression):
    """Semantic marker for <numeric value function> in the Abstract Syntax Tree (AST)."""

    pass


class TrigonometricFunctionName(Expression):
    """AST Expression for <trigonometric function name>."""

    class _Sin(Expression):
        """Internal expression."""

        pass

    class _Cos(Expression):
        """Internal expression."""

        pass

    class _Tan(Expression):
        """Internal expression."""

        pass

    class _Cot(Expression):
        """Internal expression."""

        pass

    class _Sinh(Expression):
        """Internal expression."""

        pass

    class _Cosh(Expression):
        """Internal expression."""

        pass

    class _Tanh(Expression):
        """Internal expression."""

        pass

    class _Asin(Expression):
        """Internal expression."""

        pass

    class _Acos(Expression):
        """Internal expression."""

        pass

    class _Atan(Expression):
        """Internal expression."""

        pass

    class _Degrees(Expression):
        """Internal expression."""

        pass

    class _Radians(Expression):
        """Internal expression."""

        pass

    trigonometric_function_name: (
        _Sin
        | _Cos
        | _Tan
        | _Cot
        | _Sinh
        | _Cosh
        | _Tanh
        | _Asin
        | _Acos
        | _Atan
        | _Degrees
        | _Radians
    )


class CharacterStringFunction(Expression):
    """Semantic marker for <character string function> in the Abstract Syntax Tree (AST)."""

    pass


class TrimOperands(Expression):
    """AST Expression for <trim operands>."""

    class _TrimSpecificationTrimCharacterStringFrom(Expression):
        """Internal expression."""

        trim_specification: TrimSpecification | None
        trim_character_string: TrimCharacterString | None

    trim_specification_trim_character_string_from: _TrimSpecificationTrimCharacterStringFrom | None
    trim_source: TrimSource


class TrimSpecification(Expression):
    """AST Expression for <trim specification>."""

    class _Leading(Expression):
        """Internal expression."""

        pass

    class _Trailing(Expression):
        """Internal expression."""

        pass

    class _Both(Expression):
        """Internal expression."""

        pass

    trim_specification: _Leading | _Trailing | _Both


class NormalForm(Expression):
    """AST Expression for <normal form>."""

    class _Nfc(Expression):
        """Internal expression."""

        pass

    class _Nfd(Expression):
        """Internal expression."""

        pass

    class _Nfkc(Expression):
        """Internal expression."""

        pass

    class _Nfkd(Expression):
        """Internal expression."""

        pass

    normal_form: _Nfc | _Nfd | _Nfkc | _Nfkd


class ByteStringFunction(Expression):
    """Semantic marker for <byte string function> in the Abstract Syntax Tree (AST)."""

    pass


class ByteStringTrimOperands(Expression):
    """AST Expression for <byte string trim operands>."""

    class _TrimSpecificationTrimByteStringFrom(Expression):
        """Internal expression."""

        trim_specification: TrimSpecification | None
        trim_byte_string: TrimByteString | None

    trim_specification_trim_byte_string_from: _TrimSpecificationTrimByteStringFrom | None
    byte_string_trim_source: ByteStringTrimSource


class DatetimeValueFunction(Expression):
    """Semantic marker for <datetime value function> in the Abstract Syntax Tree (AST)."""

    pass


class DatetimeSubtractionParameters(Expression):
    """AST Expression for <datetime subtraction parameters>."""

    datetime_value_expression_1: DatetimeValueExpression1
    datetime_value_expression_2: DatetimeValueExpression2


class DurationFactor(Expression):
    """AST Expression for <duration factor>."""

    sign: Sign = Sign.PLUS_SIGN
    duration_primary: DurationPrimary


class DurationValueFunction(Expression):
    """Semantic marker for <duration value function> in the Abstract Syntax Tree (AST)."""

    pass


class BindingTableName(Expression):
    """Semantic marker for <binding table name> in the Abstract Syntax Tree (AST)."""

    pass


class GraphPatternVariable(Expression):
    """Semantic marker for <graph pattern variable> in the Abstract Syntax Tree (AST)."""

    pass


class BooleanLiteral(Expression):
    """AST Expression for <boolean literal>."""

    value: bool | None


class CharacterStringLiteral(Expression):
    """AST Expression for <character string literal>."""

    value: str | None


class ByteStringLiteral(Expression):
    """AST Expression for <byte string literal>."""

    value: str


class UnsignedNumericLiteral(Expression):
    """AST Expression for <unsigned numeric literal>."""

    value: Decimal | int = field(..., ge=0)


class Mantissa(Expression):
    """Semantic marker for <mantissa> in the Abstract Syntax Tree (AST)."""

    pass


class SignedDecimalInteger(Expression):
    """AST Expression for <signed decimal integer>."""

    sign: Sign = Sign.PLUS_SIGN
    unsigned_integer: UnsignedInteger


class TemporalLiteral(Expression):
    """Semantic marker for <temporal literal> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_temporal_literal(self):
        self.require_feature(F.GG_TL01)
        self.require_feature(F.GV39)  # Temporal types: date, local datetime and local time
        return self


class DurationLiteral(Expression):
    """AST Expression for <duration literal>."""

    class _DurationDurationString(Expression):
        """Internal expression."""

        duration_string: DurationString

    duration_literal: _DurationDurationString | SqlIntervalLiteral

    @model_validator(mode="after")
    def _check_duration_literal(self):
        self.require_feature(F.GV41)  # Temporal types: duration support
        return self


class Iso8601YearsAndMonths(Expression):
    """AST Expression for <iso8601 years and months>."""

    iso8601_years: Iso8601Years | None
    iso8601_months: Iso8601Months | None


class Iso8601Years(Expression):
    """AST Expression for <iso8601 years>."""

    iso8601_sint: Iso8601Sint


class Iso8601Months(Expression):
    """AST Expression for <iso8601 months>."""

    iso8601_sint: Iso8601Sint


class Iso8601DaysAndTime(Expression):
    """AST Expression for <iso8601 days and time>."""

    iso8601_days: Iso8601Days | None
    iso8601_hours: Iso8601Hours | None
    iso8601_minutes: Iso8601Minutes | None
    iso8601_seconds: Iso8601Seconds | None


class Iso8601Days(Expression):
    """AST Expression for <iso8601 days>."""

    iso8601_sint: Iso8601Sint


class Iso8601Hours(Expression):
    """AST Expression for <iso8601 hours>."""

    iso8601_sint: Iso8601Sint


class Iso8601Minutes(Expression):
    """AST Expression for <iso8601 minutes>."""

    iso8601_sint: Iso8601Sint


class Iso8601Seconds(Expression):
    """AST Expression for <iso8601 seconds>."""

    iso8601_sint: Iso8601Sint
    iso8601_uint: Iso8601Uint | None


class Iso8601Sint(Expression):
    """AST Expression for <iso8601 sint>."""

    minus_sign: bool
    unsigned_integer: UnsignedInteger


class SqlIntervalLiteral(Expression):
    """AST Expression for <SQL-interval literal>."""

    class DatetimeField(Enum):
        YEAR = auto()
        MONTH = auto()
        DAY = auto()
        HOUR = auto()
        MINUTE = auto()
        SECOND = auto()

    sign: Sign | None
    interval_string: CharacterStringLiteral
    start_field: SqlIntervalLiteral.DatetimeField
    end_field: SqlIntervalLiteral.DatetimeField | None

    @model_validator(mode="after")
    def _check_sql_interval_literal(self):
        self.require_feature(F.GL12)
        return self


class Token(Expression):
    """Semantic marker for <token> in the Abstract Syntax Tree (AST)."""

    pass


class Identifier(Expression):
    """AST Expression for <identifier>."""

    name: str

    @model_validator(mode="after")
    def _check_identifier(self):
        if len(self.name) > 127:
            self.require_feature(F.GB01)
        return self


class SubstitutedParameterReference(Expression):
    """AST Expression for <substituted parameter reference>."""

    parameter_name: ParameterName

    @model_validator(mode="after")
    def _check_substituted_parameter_reference(self):
        self.require_feature(F.GE08)
        return self


class GeneralParameterReference(Expression):
    """AST Expression for <general parameter reference>."""

    parameter_name: ParameterName


class Solidus(Expression):
    """AST Expression for <solidus>."""

    pass


class SessionActivity(ProgramActivity):
    """AST Expression for <session activity>."""

    class _ListSessionSetCommandListSessionResetCommand(Expression):
        """Internal expression."""

        list_session_set_command: list[SessionSetCommand]
        list_session_reset_command: list[SessionResetCommand] | None

    session_activity: list[SessionResetCommand] | _ListSessionSetCommandListSessionResetCommand


class TransactionActivity(ProgramActivity):
    """AST Expression for <transaction activity>."""

    class _StartTransactionCommandProcedureSpecificationEndTransactionCommand(Expression):
        """Internal expression."""

        start_transaction_command: StartTransactionCommand
        procedure_specification_end_transaction_command: (
            TransactionActivity._ProcedureSpecificationEndTransactionCommand | None
        )

    class _ProcedureSpecificationEndTransactionCommand(Expression):
        """Internal expression."""

        procedure_specification: ProcedureSpecification
        end_transaction_command: EndTransactionCommand | None

    transaction_activity: (
        _StartTransactionCommandProcedureSpecificationEndTransactionCommand
        | _ProcedureSpecificationEndTransactionCommand
        | EndTransactionCommand
    )


class SessionSetGraphParameterClause(SessionSetParameterClause):
    """AST Expression for <session set graph parameter clause>."""

    session_set_parameter_name: SessionSetParameterName
    opt_typed_graph_initializer: OptTypedGraphInitializer

    @model_validator(mode="after")
    def _check_session_set_graph_parameter_clause(self):
        self.require_feature(F.GS01)  # SESSION SET: session-local graph parameters
        self.require_feature(F.GS12)  # SESSION SET: graph params from simple expressions
        return self


class SessionSetBindingTableParameterClause(SessionSetParameterClause):
    """AST Expression for <session set binding table parameter clause>."""

    session_set_parameter_name: SessionSetParameterName
    opt_typed_binding_table_initializer: OptTypedBindingTableInitializer

    @model_validator(mode="after")
    def _check_session_set_binding_table_parameter_clause(self):
        self.require_feature(F.GS02)  # SESSION SET: session-local binding table parameters
        init = self.opt_typed_binding_table_initializer.binding_table_initializer
        expr = init.binding_table_expression
        if isinstance(expr, NestedQuerySpecification):
            self.require_feature(F.GS10)  # SESSION SET: binding table params from subqueries
        else:
            self.require_feature(
                "GS13"
            )  # SESSION SET: binding table params from simple expressions
        return self


class SessionSetValueParameterClause(SessionSetParameterClause):
    """AST Expression for <session set value parameter clause>."""

    session_set_parameter_name: SessionSetParameterName
    opt_typed_value_initializer: OptTypedValueInitializer

    @model_validator(mode="after")
    def _check_session_set_value_parameter_clause(self):
        self.require_feature(F.GS03)  # SESSION SET: session-local value parameters
        if self.opt_typed_value_initializer.find_first(ProcedureBody) is not None:
            self.require_feature(F.GS11)  # SESSION SET: value params from subqueries
        else:
            self.require_feature(F.GS14)  # SESSION SET: value params from simple expressions
        return self


CatalogModifyingProcedureSpecification: t.TypeAlias = ProcedureBody

DataModifyingProcedureSpecification: t.TypeAlias = ProcedureBody

QuerySpecification: t.TypeAlias = ProcedureBody


class GraphVariableDefinition(BindingVariableDefinition):
    """AST Expression for <graph variable definition>."""

    binding_variable: BindingVariable
    opt_typed_graph_initializer: OptTypedGraphInitializer

    @model_validator(mode="after")
    def _check_graph_variable_definition(self):
        self.require_feature(F.GP11)  # Procedure-local graph variable definitions

        graph_expr = self.opt_typed_graph_initializer.graph_initializer.graph_expression
        if graph_expr.find_first(NestedQuerySpecification) is not None:
            self.require_feature(F.GP13)  # Based on subqueries
        else:
            self.require_feature(F.GP12)  # Based on simple expressions or references

        return self


class BindingTableVariableDefinition(BindingVariableDefinition):
    """AST Expression for <binding table variable definition>."""

    binding_variable: BindingVariable
    opt_typed_binding_table_initializer: OptTypedBindingTableInitializer

    @model_validator(mode="after")
    def _check_binding_table_variable_definition(self):
        self.require_feature(F.GP08)  # Procedure-local binding table variable definitions

        # Check if the binding table expression contains a subquery (procedure body)
        initializer = self.opt_typed_binding_table_initializer
        if initializer and initializer.binding_table_initializer:
            expr = initializer.binding_table_initializer.binding_table_expression
            # Check if it's a nested query specification (subquery)
            if isinstance(expr, NestedQuerySpecification):
                self.require_feature(F.GP10)  # Based on subqueries
            else:
                self.require_feature(F.GP09)  # Based on simple expressions or references
        return self


class ValueVariableDefinition(BindingVariableDefinition):
    """AST Expression for <value variable definition>."""

    binding_variable: BindingVariable
    opt_typed_value_initializer: OptTypedValueInitializer

    @model_validator(mode="after")
    def _check_value_variable_definition(self):
        self.require_feature(F.GP05)  # Procedure-local value variable definitions

        # Check if the value expression contains a subquery (procedure body)
        initializer = self.opt_typed_value_initializer
        if initializer and initializer.value_initializer:
            # Check if the value expression contains a ProcedureBody (subquery)
            procedure_body = initializer.value_initializer.find_first(ProcedureBody)
            if procedure_body is not None:
                self.require_feature(F.GP07)  # Value variables based on subqueries
            else:
                self.require_feature(F.GP06)  # Value variables based on simple expressions
        return self


class LinearCatalogModifyingStatement(Statement):
    """AST Expression for <linear catalog-modifying statement>."""

    list_simple_catalog_modifying_statement: list[SimpleCatalogModifyingStatement]


class LinearDataModifyingStatement(Statement):
    """Semantic marker for <linear data-modifying statement> in the Abstract Syntax Tree (AST)."""

    pass


class CurrentGraph(GraphExpression):
    """AST Expression for <current graph>."""

    @model_validator(mode="after")
    def _check_current_graph(self):
        self.require_feature(F.GG_GE01)
        return self


class GraphReference(GraphExpression):
    """AST Expression for <graph reference>."""

    class _CatalogObjectParentReferenceGraphName(Expression):
        """Internal expression."""

        catalog_object_parent_reference: CatalogObjectParentReference
        graph_name: GraphName

    graph_reference: (
        _CatalogObjectParentReferenceGraphName
        | DelimitedGraphName
        | HomeGraph
        | ReferenceParameterSpecification
    )


NestedBindingTableQuerySpecification: t.TypeAlias = NestedQuerySpecification


class ObjectExpressionPrimary(GraphExpression):
    """AST Expression for <object expression primary>."""

    class _VariableValueExpressionPrimary(Expression):
        """Internal expression."""

        value_expression_primary: ValueExpressionPrimary

    object_expression_primary: (
        _VariableValueExpressionPrimary
        | ParenthesizedValueExpression
        | NonParenthesizedValueExpressionPrimarySpecialCase
    )


class BindingTableReference(Expression):
    """AST Expression for <binding table reference>."""

    class _CatalogObjectParentReferenceBindingTableName(Expression):
        """Internal expression."""

        catalog_object_parent_reference: CatalogObjectParentReference
        binding_table_name: BindingTableName

    binding_table_reference: (
        _CatalogObjectParentReferenceBindingTableName
        | DelimitedBindingTableName
        | ReferenceParameterSpecification
    )


class PrimitiveCatalogModifyingStatement(SimpleCatalogModifyingStatement):
    """Semantic marker for <primitive catalog-modifying statement> in the Abstract Syntax Tree."""

    pass


class SimpleDataModifyingStatement(SimpleDataAccessingStatement):
    """Semantic marker for <simple data-modifying statement> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_simple_data_modifying_statement(self):
        self.require_feature(F.GD01)
        return self


class CallProcedureStatement(
    SimpleQueryStatement,
    SimpleDataModifyingStatement,
    SimpleCatalogModifyingStatement,
):
    """AST Expression for <call procedure statement>."""

    optional: bool
    procedure_call: ProcedureCall


class SetPropertyItem(SetItem):
    """AST Expression for <set property item>."""

    binding_variable_reference: BindingVariableReference
    property_name: PropertyName
    value_expression: ValueExpression


class SetAllPropertiesItem(SetItem):
    """AST Expression for <set all properties item>."""

    binding_variable_reference: BindingVariableReference
    property_key_value_pair_list: PropertyKeyValuePairList | None


class SetLabelItem(SetItem):
    """AST Expression for <set label item>."""

    binding_variable_reference: BindingVariableReference
    label_name: LabelName


class RemovePropertyItem(RemoveItem):
    """AST Expression for <remove property item>."""

    binding_variable_reference: BindingVariableReference
    property_name: PropertyName


class RemoveLabelItem(RemoveItem):
    """AST Expression for <remove label item>."""

    binding_variable_reference: BindingVariableReference
    label_name: LabelName


CompositeQueryStatement: t.TypeAlias = CompositeQueryExpression

CompositeQueryPrimary: t.TypeAlias = LinearQueryStatement


class FocusedLinearQueryStatement(LinearQueryStatement):
    """AST Expression for <focused linear query statement>."""

    class _ListFocusedLinearQueryStatementPartFocusedLinearQueryAndPrimitiveResultStatementPart(
        Expression
    ):
        """Internal expression."""

        list_focused_linear_query_statement_part: list[FocusedLinearQueryStatementPart] | None
        focused_linear_query_and_primitive_result_statement_part: (
            FocusedLinearQueryAndPrimitiveResultStatementPart
        )

    focused_linear_query_statement: (
        _ListFocusedLinearQueryStatementPartFocusedLinearQueryAndPrimitiveResultStatementPart
        | FocusedPrimitiveResultStatement
        | FocusedNestedQuerySpecification
        | SelectStatement
    )

    @model_validator(mode="after")
    def _check_focused_linear_query_statement(self):
        # GQ01 is required only when a USE clause is actually present;
        # UseGraphClause's own validator handles that.  SelectStatement
        # is routed here by the grammar without any USE clause.
        return self


class AmbientLinearQueryStatement(LinearQueryStatement):
    """AST Expression for <ambient linear query statement>."""

    class _SimpleLinearQueryStatementPrimitiveResultStatement(Expression):
        """Internal expression."""

        simple_linear_query_statement: SimpleLinearQueryStatement | None
        primitive_result_statement: PrimitiveResultStatement

    ambient_linear_query_statement: (
        _SimpleLinearQueryStatementPrimitiveResultStatement | NestedQuerySpecification
    )


CallCatalogModifyingProcedureStatement: t.TypeAlias = CallProcedureStatement


class InlineProcedureCall(ProcedureCall):
    """AST Expression for <inline procedure call>."""

    variable_scope_clause: VariableScopeClause | None
    nested_procedure_specification: NestedProcedureSpecification

    @model_validator(mode="after")
    def _check_inline_procedure_call(self):
        self.require_feature(F.GP01)  # Inline procedure
        if self.variable_scope_clause is None:
            self.require_feature(F.GP02)  # Implicit nested variable scope
        else:
            self.require_feature(F.GP03)  # Explicit nested variable scope
        return self


class NamedProcedureCall(ProcedureCall):
    """AST Expression for <named procedure call>."""

    procedure_reference: ProcedureReference
    procedure_argument_list: ProcedureArgumentList | None
    yield_clause: YieldClause | None

    @model_validator(mode="after")
    def _check_named_procedure_call(self):
        self.require_feature(F.GP04)  # Named procedure calls
        return self


class RepeatableElementsMatchMode(MatchMode):
    """AST Expression for <repeatable elements match mode>."""

    class Mode(Enum):
        ELEMENT = auto()
        ELEMENTS = auto()
        ELEMENT_BINDINGS = auto()

    mode: RepeatableElementsMatchMode.Mode

    @model_validator(mode="after")
    def _check_repeatable_elements_match_mode(self):
        self.require_feature(F.G003)
        return self


class DifferentEdgesMatchMode(MatchMode):
    """AST Expression for <different edges match mode>."""

    class Mode(Enum):
        EDGE = auto()
        EDGES = auto()
        EDGE_BINDINGS = auto()

    mode: DifferentEdgesMatchMode.Mode

    @model_validator(mode="after")
    def _check_different_edges_match_mode(self):
        self.require_feature(F.G002)
        return self


InsertGraphPattern: t.TypeAlias = InsertPathPatternList


class InsertEdgePointingLeft(InsertEdgePattern):
    """AST Expression for <insert edge pointing left>."""

    insert_element_pattern_filler: InsertElementPatternFiller | None


class InsertEdgePointingRight(InsertEdgePattern):
    """AST Expression for <insert edge pointing right>."""

    insert_element_pattern_filler: InsertElementPatternFiller | None


class InsertEdgeUndirected(InsertEdgePattern):
    """AST Expression for <insert edge undirected>."""

    insert_element_pattern_filler: InsertElementPatternFiller | None

    @model_validator(mode="after")
    def _check_insert_edge_undirected(self):
        self.require_feature(F.GH02)
        return self


class PathModePrefix(PathPatternPrefix):
    """AST Expression for <path mode prefix>."""

    path_mode: PathMode
    path_or_paths: PathOrPaths | None


class PathSearchPrefix(PathPatternPrefix):
    """Semantic marker for <path search prefix> in the Abstract Syntax Tree (AST)."""

    pass


class PathMultisetAlternation(PathPatternExpression):
    """AST Expression for <path multiset alternation>."""

    list_path_term: list[PathTerm] = field(..., min_length=2)

    @model_validator(mode="after")
    def _check_path_multiset_alternation(self):
        self.require_feature(F.G030)

        for path_term in self.list_path_term:
            gpq = path_term.find_first(GraphPatternQuantifier)
            if gpq is not None:
                gpq.require_feature(F.G031)
                break
        return self


class PathPatternUnion(PathPatternExpression):
    """AST Expression for <path pattern union>."""

    list_path_term: list[PathTerm] = field(..., min_length=2)

    @model_validator(mode="after")
    def _check_path_pattern_union(self):
        self.require_feature(F.G032)

        for path_term in self.list_path_term:
            gpq = path_term.find_first(GraphPatternQuantifier)
            if gpq is not None:
                gpq.require_feature(F.G033)
                break
        return self


class PathTerm(PathPatternExpression):
    """AST Expression for <path term> and <path concatenation>."""

    factors: list[PathFactor] = field(..., min_length=1)

    @model_validator(mode="after")
    def _check_path_term(self):
        for i, factor in enumerate(self.factors):
            previous_factor = self.factors[i - 1] if i > 0 else None
            next_factor = self.factors[i + 1] if i < len(self.factors) - 1 else None
            condition = isinstance(previous_factor, NodePattern) and isinstance(
                next_factor, NodePattern
            )
            if isinstance(factor, EdgePattern) and not condition:
                #  <edge pattern> shall be immediately preceded and followed by a <node pattern>
                self.require_feature(F.G047)
                break

        saw_node = False
        for factor in self.factors:
            primary = factor
            if isinstance(factor, QuantifiedPathPrimary | QuestionedPathPrimary):
                primary = factor.path_primary
            if isinstance(primary, NodePattern):
                if saw_node:
                    self.require_feature(F.G046)
                    break
                saw_node = True
            elif isinstance(primary, EdgePattern | ParenthesizedPathPatternExpression):
                saw_node = False

        return self


class ElementPatternWhereClause(ElementPatternPredicate):
    """AST Expression for <element pattern where clause>."""

    search_condition: SearchCondition


class ElementPropertySpecification(ElementPatternPredicate):
    """AST Expression for <element property specification>."""

    property_key_value_pair_list: PropertyKeyValuePairList


class LabelTerm(Expression):
    """AST Expression for <label term> and <label conjunction>."""

    label_factors: list[LabelFactor] = field(..., min_length=1)


class FixedQuantifier(GraphPatternQuantifier):
    """AST Expression for <fixed quantifier>."""

    unsigned_integer: UnsignedInteger

    @model_validator(mode="after")
    def _check_fixed_quantifier(self):
        self.require_feature(F.G060)
        return self


class GeneralQuantifier(GraphPatternQuantifier):
    """AST Expression for <general quantifier>."""

    lower_bound: LowerBound | None
    upper_bound: UpperBound | None

    @model_validator(mode="after")
    def _check_general_quantifier(self):
        if self.upper_bound is not None:
            self.require_feature(F.G060)
        return self


class Asterisk(Expression):
    """AST Expression for <asterisk>."""

    pass


class SimplifiedPathUnion(SimplifiedContents):
    """AST Expression for <simplified path union>."""

    list_simplified_term: list[SimplifiedTerm] = field(..., min_length=2)


class SimplifiedMultisetAlternation(SimplifiedContents):
    """AST Expression for <simplified multiset alternation>."""

    list_simplified_terms: list[SimplifiedTerm] = field(..., min_length=2)


class SimplifiedTerm(SimplifiedContents):
    """Semantic marker for <simplified term> in the Abstract Syntax Tree (AST)."""

    pass


class AbsoluteCatalogSchemaReference(SchemaReference):
    """AST Expression for <absolute catalog schema reference>."""

    class _AbsoluteDirectoryPathSchemaName(Expression):
        """Internal expression."""

        absolute_directory_path: AbsoluteDirectoryPath
        schema_name: SchemaName

    absolute_catalog_schema_reference: Solidus | _AbsoluteDirectoryPathSchemaName


class RelativeCatalogSchemaReference(SchemaReference):
    """AST Expression for <relative catalog schema reference>."""

    class _RelativeDirectoryPathSchemaName(Expression):
        """Internal expression."""

        relative_directory_path: RelativeDirectoryPath
        schema_name: SchemaName

    relative_catalog_schema_reference: PredefinedSchemaReference | _RelativeDirectoryPathSchemaName


class CatalogGraphTypeParentAndName(GraphTypeReference):
    """AST Expression for <catalog graph type parent and name>."""

    catalog_object_parent_reference: CatalogObjectParentReference | None
    graph_type_name: GraphTypeName


class CatalogProcedureParentAndName(ProcedureReference):
    """AST Expression for <catalog procedure parent and name>."""

    catalog_object_parent_reference: CatalogObjectParentReference | None
    procedure_name: ProcedureName


GraphTypeSpecificationBody: t.TypeAlias = ElementTypeList


class NodeTypeSpecification(ElementTypeSpecification):
    """Semantic marker for <node type specification> in the Abstract Syntax Tree (AST)."""

    pass


class EdgeTypeSpecification(ElementTypeSpecification):
    """Semantic marker for <edge type specification> in the Abstract Syntax Tree (AST)."""

    pass


class EdgeTypePatternPointingRight(EdgeTypePatternDirected):
    """AST Expression for <edge type pattern pointing right>."""

    source_node_type_reference: SourceNodeTypeReference
    arc_type_pointing_right: ArcTypePointingRight
    destination_node_type_reference: DestinationNodeTypeReference


class EdgeTypePatternPointingLeft(EdgeTypePatternDirected):
    """AST Expression for <edge type pattern pointing left>."""

    destination_node_type_reference: DestinationNodeTypeReference
    arc_type_pointing_left: ArcTypePointingLeft
    source_node_type_reference: SourceNodeTypeReference


class EndpointPairDirected(EndpointPair):
    """Semantic marker for <endpoint pair directed> in the Abstract Syntax Tree (AST)."""

    pass


class EndpointPairUndirected(EndpointPair):
    """AST Expression for <endpoint pair undirected>."""

    source_node_type_alias: SourceNodeTypeAlias
    connector_undirected: ConnectorUndirected
    destination_node_type_alias: DestinationNodeTypeAlias

    @model_validator(mode="after")
    def _check_endpoint_pair_undirected(self):
        self.require_feature(F.GH02)
        return self


NodeTypeLabelSet: t.TypeAlias = LabelSetPhrase

EdgeTypeLabelSet: t.TypeAlias = LabelSetPhrase

NodeTypePropertyTypes: t.TypeAlias = PropertyTypesSpecification

EdgeTypePropertyTypes: t.TypeAlias = PropertyTypesSpecification

PropertyValueType: t.TypeAlias = ValueType


class PredefinedType(ValueType):
    """Semantic marker for <predefined type> in the Abstract Syntax Tree (AST)."""

    pass


class ConstructedValueType(ValueType):
    """Semantic marker for <constructed value type> in the Abstract Syntax Tree (AST)."""

    pass


class DynamicUnionType(ValueType):
    """Semantic marker for <dynamic union type> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_dynamic_union_type(self):
        self.require_feature(F.GV65)
        return self


ComponentType: t.TypeAlias = ValueType

CastTarget: t.TypeAlias = ValueType


class ParenthesizedValueExpression(Expression):
    """AST Expression for <parenthesized value expression>."""

    value_expression: ValueExpression


class Literal(ValueSpecification):
    """Semantic marker for <literal> in the Abstract Syntax Tree (AST)."""

    pass


class GeneralValueSpecification(ValueSpecification):
    """AST Expression for <general value specification>."""

    class _SessionUser(Expression):
        """Internal expression."""

        pass

    general_value_specification: DynamicParameterSpecification | _SessionUser


NumberOfPaths: t.TypeAlias = NonNegativeIntegerSpecification

NumberOfGroups: t.TypeAlias = NonNegativeIntegerSpecification


class UnsignedInteger(NonNegativeIntegerSpecification):
    """AST Expression for <unsigned integer>."""

    value: int = field(..., ge=0)


class CaseAbbreviation(CaseExpression):
    """AST Expression for <case abbreviation>."""

    class _NullifLeftParenValueExpressionCommaValueExpressionRightParen(Expression):
        """Internal expression."""

        value_expression_1: ValueExpression
        value_expression_2: ValueExpression

    class _CoalesceLeftParenListValueExpressionRightParen(Expression):
        """Internal expression."""

        list_value_expression: list[ValueExpression]

    case_abbreviation: (
        _NullifLeftParenValueExpressionCommaValueExpressionRightParen
        | _CoalesceLeftParenListValueExpressionRightParen
    )


class CaseSpecification(CaseExpression):
    """Semantic marker for <case specification> in the Abstract Syntax Tree (AST)."""

    pass


class ComparisonPredicatePart2(Expression):
    """AST Expression for <comparison predicate part 2>."""

    class CompOp(Enum):
        EQUALS = auto()
        NOT_EQUALS = auto()
        LESS_THAN = auto()
        GREATER_THAN = auto()
        LESS_THAN_OR_EQUALS = auto()
        GREATER_THAN_OR_EQUALS = auto()

    comp_op: ComparisonPredicatePart2.CompOp
    comparison_predicand: ComparisonPredicand


class NullPredicatePart2(Expression):
    """AST Expression for <null predicate part 2>."""

    not_: bool


class ValueTypePredicatePart2(Expression):
    """AST Expression for <value type predicate part 2>."""

    not_: bool
    typed: Typed
    value_type: ValueType

    @model_validator(mode="after")
    def _check_value_type_predicate_part2(self):
        self.require_feature(F.GA06)
        return self


class NormalizedPredicatePart2(Expression):
    """AST Expression for <normalized predicate part 2>."""

    not_: bool
    normal_form: NormalForm | None


class DirectedPredicatePart2(Expression):
    """AST Expression for <directed predicate part 2>."""

    not_: bool

    @model_validator(mode="after")
    def _check_directed_predicate_part2(self):
        self.require_feature(F.G110)
        return self


class LabeledPredicatePart2(Expression):
    """AST Expression for <labeled predicate part 2>."""

    is_labeled_or_colon: IsLabeledOrColon
    label_expression: LabelExpression

    @model_validator(mode="after")
    def _check_labeled_predicate_part2(self):
        self.require_feature(F.G111)
        return self


class SourcePredicatePart2(Expression):
    """AST Expression for <source predicate part 2>."""

    not_: bool
    edge_reference: EdgeReference

    @model_validator(mode="after")
    def _check_source_predicate_part2(self):
        self.require_feature(F.G112)
        return self


class DestinationPredicatePart2(Expression):
    """AST Expression for <destination predicate part 2>."""

    not_: bool
    edge_reference: EdgeReference

    @model_validator(mode="after")
    def _check_destination_predicate_part2(self):
        self.require_feature(F.G112)
        return self


class ValueExpression(Expression):
    """Semantic marker for <value expression> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_value_expression(self):
        if isinstance(self, GraphReferenceValueExpression):
            self.require_feature(F.GE01)
        elif isinstance(self, BindingTableReferenceValueExpression):
            self.require_feature(F.GE02)
        return self


class NullLiteral(Expression):
    """AST Expression for <null literal>."""

    pass


PathValueConstructor: t.TypeAlias = PathValueConstructorByEnumeration


class TrimListFunction(ListValueFunction):
    """AST Expression for <trim list function>."""

    list_value_expression: ListValueExpression
    numeric_value_expression: NumericValueExpression


class ElementsFunction(ListValueFunction):
    """AST Expression for <elements function>."""

    path_value_expression: PathValueExpression

    @model_validator(mode="after")
    def _check_elements_function(self):
        self.require_feature(F.GF04)
        return self


ListValueConstructor: t.TypeAlias = ListValueConstructorByEnumeration

ListLiteral: t.TypeAlias = ListValueConstructorByEnumeration


class LengthExpression(NumericValueFunction):
    """Semantic marker for <length expression> in the Abstract Syntax Tree (AST)."""

    pass


class CardinalityExpression(NumericValueFunction):
    """AST Expression for <cardinality expression>."""

    class _CardinalityLeftParenCardinalityExpressionArgumentRightParen(Expression):
        """Internal expression."""

        cardinality_expression_argument: CardinalityExpressionArgument

    class _SizeLeftParenListValueExpressionRightParen(Expression):
        """Internal expression."""

        list_value_expression: ListValueExpression

    cardinality_expression: (
        _CardinalityLeftParenCardinalityExpressionArgumentRightParen
        | _SizeLeftParenListValueExpressionRightParen
    )

    @model_validator(mode="after")
    def _check_cardinality_expression(self):
        if isinstance(
            self.cardinality_expression,
            CardinalityExpression._CardinalityLeftParenCardinalityExpressionArgumentRightParen,
        ):
            self.require_feature(F.GF12)
        elif isinstance(
            self.cardinality_expression,
            CardinalityExpression._SizeLeftParenListValueExpressionRightParen,
        ):
            self.require_feature(F.GF13)
        return self


class AbsoluteValueExpression(NumericValueFunction):
    """AST Expression for <absolute value expression>."""

    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_absolute_value_expression(self):
        self.require_feature(F.GF01)
        return self


class ModulusExpression(NumericValueFunction):
    """AST Expression for <modulus expression>."""

    numeric_value_expression_dividend: NumericValueExpressionDividend
    numeric_value_expression_divisor: NumericValueExpressionDivisor

    @model_validator(mode="after")
    def _check_modulus_expression(self):
        self.require_feature(F.GF01)
        return self


class TrigonometricFunction(NumericValueFunction):
    """AST Expression for <trigonometric function>."""

    trigonometric_function_name: TrigonometricFunctionName
    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_trigonometric_function(self):
        self.require_feature(F.GF02)
        return self


class GeneralLogarithmFunction(NumericValueFunction):
    """AST Expression for <general logarithm function>."""

    general_logarithm_base: GeneralLogarithmBase
    general_logarithm_argument: GeneralLogarithmArgument

    @model_validator(mode="after")
    def _check_general_logarithm_function(self):
        self.require_feature(F.GF03)
        return self


class CommonLogarithm(NumericValueFunction):
    """AST Expression for <common logarithm>."""

    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_common_logarithm(self):
        self.require_feature(F.GF03)
        return self


class NaturalLogarithm(NumericValueFunction):
    """AST Expression for <natural logarithm>."""

    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_natural_logarithm(self):
        self.require_feature(F.GF03)
        return self


class ExponentialFunction(NumericValueFunction):
    """AST Expression for <exponential function>."""

    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_exponential_function(self):
        self.require_feature(F.GF03)
        return self


class PowerFunction(NumericValueFunction):
    """AST Expression for <power function>."""

    numeric_value_expression_base: NumericValueExpressionBase
    numeric_value_expression_exponent: NumericValueExpressionExponent

    @model_validator(mode="after")
    def _check_power_function(self):
        self.require_feature(F.GF03)
        return self


class SquareRoot(NumericValueFunction):
    """AST Expression for <square root>."""

    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_square_root(self):
        self.require_feature(F.GF01)
        return self


class FloorFunction(NumericValueFunction):
    """AST Expression for <floor function>."""

    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_floor_function(self):
        self.require_feature(F.GF01)
        return self


class CeilingFunction(NumericValueFunction):
    """AST Expression for <ceiling function>."""

    numeric_value_expression: NumericValueExpression

    @model_validator(mode="after")
    def _check_ceiling_function(self):
        self.require_feature(F.GF01)
        return self


class SubstringFunction(CharacterStringFunction):
    """AST Expression for <substring function>."""

    class Mode(Enum):
        LEFT = auto()
        RIGHT = auto()

    mode: Mode
    character_string_value_expression: CharacterStringValueExpression
    string_length: StringLength


class Fold(CharacterStringFunction):
    """AST Expression for <fold>."""

    class Mode(Enum):
        UPPER = auto()
        LOWER = auto()

    mode: Mode
    character_string_value_expression: CharacterStringValueExpression


class TrimFunction(CharacterStringFunction):
    """Semantic marker for <trim function> in the Abstract Syntax Tree (AST)."""

    pass


class NormalizeFunction(CharacterStringFunction):
    """AST Expression for <normalize function>."""

    character_string_value_expression: CharacterStringValueExpression
    normal_form: NormalForm | None


class ByteStringSubstringFunction(ByteStringFunction):
    """AST Expression for <byte string substring function>."""

    class Mode(Enum):
        LEFT = auto()
        RIGHT = auto()

    mode: Mode
    byte_string_value_expression: ByteStringValueExpression
    string_length: StringLength


class ByteStringTrimFunction(ByteStringFunction):
    """AST Expression for <byte string trim function>."""

    byte_string_trim_operands: ByteStringTrimOperands

    @model_validator(mode="after")
    def _check_byte_string_trim_function(self):
        self.require_feature(F.GF07)
        return self


class DateFunction(DatetimeValueFunction):
    """AST Expression for <date function>."""

    class _CurrentDate(Expression):
        """Internal expression."""

        pass

    class _DateLeftParenDateFunctionParametersRightParen(Expression):
        """Internal expression."""

        date_function_parameters: DateFunctionParameters | None

    date_function: _CurrentDate | _DateLeftParenDateFunctionParametersRightParen

    @model_validator(mode="after")
    def _check_date_function(self):
        self.require_feature(F.GV39)  # Temporal types: date, local datetime and local time
        return self


class TimeFunction(DatetimeValueFunction):
    """AST Expression for <time function>."""

    class _CurrentTime(Expression):
        """Internal expression."""

        pass

    class _ZonedTimeLeftParenTimeFunctionParametersRightParen(Expression):
        """Internal expression."""

        time_function_parameters: TimeFunctionParameters | None

    time_function: _CurrentTime | _ZonedTimeLeftParenTimeFunctionParametersRightParen

    @model_validator(mode="after")
    def _check_time_function(self):
        self.require_feature(F.GV40)  # Temporal types: zoned datetime and zoned time
        return self


class LocaltimeFunction(DatetimeValueFunction):
    """AST Expression for <localtime function>."""

    time_function_parameters: TimeFunctionParameters | None

    @model_validator(mode="after")
    def _check_localtime_function(self):
        self.require_feature(F.GV39)  # Temporal types: date, local datetime and local time
        return self


class DatetimeFunction(DatetimeValueFunction):
    """AST Expression for <datetime function>."""

    class _CurrentTimestamp(Expression):
        """Internal expression."""

        pass

    class _ZonedDatetimeLeftParenDatetimeFunctionParametersRightParen(Expression):
        """Internal expression."""

        datetime_function_parameters: DatetimeFunctionParameters | None

    datetime_function: (
        _CurrentTimestamp | _ZonedDatetimeLeftParenDatetimeFunctionParametersRightParen
    )

    @model_validator(mode="after")
    def _check_datetime_function(self):
        self.require_feature(F.GV40)  # Temporal types: zoned datetime and zoned time
        return self


class LocaldatetimeFunction(DatetimeValueFunction):
    """AST Expression for <localdatetime function>."""

    class _LocalTimestamp(Expression):
        """Internal expression."""

        pass

    class _LocalDatetimeLeftParenDatetimeFunctionParametersRightParen(Expression):
        """Internal expression."""

        datetime_function_parameters: DatetimeFunctionParameters | None

    localdatetime_function: (
        _LocalTimestamp | _LocalDatetimeLeftParenDatetimeFunctionParametersRightParen
    )

    @model_validator(mode="after")
    def _check_localdatetime_function(self):
        self.require_feature(F.GV39)  # Temporal types: date, local datetime and local time
        return self


class DurationFunction(DurationValueFunction):
    """AST Expression for <duration function>."""

    duration_function_parameters: DurationFunctionParameters | None

    @model_validator(mode="after")
    def _check_duration_function(self):
        if self.duration_function_parameters is None:
            self.require_feature(F.CY_TF02)
        return self


class DurationAbsoluteValueFunction(DurationValueFunction):
    """AST Expression for <duration absolute value function>."""

    duration_value_expression: DurationValueExpression


class RecordConstructor(Expression):
    """AST Expression for <record constructor>."""

    record: bool
    fields_specification: FieldsSpecification

    @model_validator(mode="after")
    def _check_record_constructor(self):
        self.require_feature(F.GV45)  # Record types
        return self


class PathOrSubpathVariable(GraphPatternVariable):
    """Semantic marker for <path or subpath variable> in the Abstract Syntax Tree (AST)."""

    pass


DateString: t.TypeAlias = CharacterStringLiteral

TimeString: t.TypeAlias = CharacterStringLiteral

DatetimeString: t.TypeAlias = CharacterStringLiteral

TimeZoneString: t.TypeAlias = CharacterStringLiteral

DurationString: t.TypeAlias = CharacterStringLiteral


Exponent: t.TypeAlias = SignedDecimalInteger


class DateLiteral(TemporalLiteral):
    """AST Expression for <date literal>."""

    date_string: DateString


class TimeLiteral(TemporalLiteral):
    """AST Expression for <time literal>."""

    time_string: TimeString


class DatetimeLiteral(TemporalLiteral):
    """AST Expression for <datetime literal>."""

    class Kind(Enum):
        DATETIME = auto()
        TIMESTAMP = auto()

    kind: DatetimeLiteral.Kind
    datetime_string: DatetimeString


class SqlDatetimeLiteral(TemporalLiteral):
    """AST Expression for <SQL-datetime literal>."""

    class Kind(Enum):
        DATE = auto()
        TIME = auto()
        TIMESTAMP = auto()

    kind: SqlDatetimeLiteral.Kind
    datetime_string: CharacterStringLiteral

    @model_validator(mode="after")
    def _check_sql_datetime_literal(self):
        self.require_feature(F.GL12)
        return self


LocalNodeTypeAlias: t.TypeAlias = Identifier

SourceNodeTypeAlias: t.TypeAlias = Identifier

DestinationNodeTypeAlias: t.TypeAlias = Identifier

AuthorizationIdentifier: t.TypeAlias = Identifier

ObjectName: t.TypeAlias = Identifier

ObjectNameOrBindingVariable: t.TypeAlias = Identifier

DirectoryName: t.TypeAlias = Identifier

SchemaName: t.TypeAlias = Identifier

DelimitedGraphName: t.TypeAlias = Identifier

GraphTypeName: t.TypeAlias = Identifier

NodeTypeName: t.TypeAlias = Identifier

EdgeTypeName: t.TypeAlias = Identifier

DelimitedBindingTableName: t.TypeAlias = Identifier

ProcedureName: t.TypeAlias = Identifier


class PropertyName(Expression):
    """AST Expression for <property name>."""

    identifier: Identifier


FieldName: t.TypeAlias = Identifier

ParameterName: t.TypeAlias = Identifier

BindingVariable: t.TypeAlias = Identifier

ReferenceParameterSpecification: t.TypeAlias = SubstitutedParameterReference

SessionParameterSpecification: t.TypeAlias = GeneralParameterReference

DynamicParameterSpecification: t.TypeAlias = GeneralParameterReference


class FocusedLinearDataModifyingStatement(LinearDataModifyingStatement):
    """Semantic marker for <focused linear data-modifying statement> in the Abstract Syntax."""

    @model_validator(mode="after")
    def _check_focused_linear_data_modifying_statement(self):
        # GQ01 is required only when a USE clause is actually present;
        # UseGraphClause's own validator handles that.
        return self


class AmbientLinearDataModifyingStatement(LinearDataModifyingStatement):
    """Semantic marker for <ambient linear data-modifying statement> in the Abstract Syntax."""

    pass


class CreateSchemaStatement(PrimitiveCatalogModifyingStatement):
    """AST Expression for <create schema statement>."""

    if_not_exists: bool
    catalog_schema_parent_and_name: CatalogSchemaParentAndName

    @model_validator(mode="after")
    def _check_create_schema_statement(self):
        self.require_feature(F.GC01)

        if self.if_not_exists:
            self.require_feature(F.GC02)

        return self


class DropSchemaStatement(PrimitiveCatalogModifyingStatement):
    """AST Expression for <drop schema statement>."""

    if_exists: bool
    catalog_schema_parent_and_name: CatalogSchemaParentAndName

    @model_validator(mode="after")
    def _check_drop_schema_statement(self):
        self.require_feature(F.GC01)

        if self.if_exists:
            self.require_feature(F.GC02)

        return self


class CreateGraphStatement(PrimitiveCatalogModifyingStatement):
    """AST Expression for <create graph statement>."""

    class CreateMode(Enum):
        CREATE_GRAPH = auto()
        CREATE_GRAPH_IF_NOT_EXISTS = auto()
        CREATE_OR_REPLACE_GRAPH = auto()

    create_mode: CreateMode
    catalog_graph_parent_and_name: CatalogGraphParentAndName
    graph_type: OpenGraphType | OfGraphType
    graph_source: GraphSource | None

    @model_validator(mode="after")
    def _check_create_graph_statement(self):
        self.require_feature(F.GC04)

        if self.create_mode == CreateGraphStatement.CreateMode.CREATE_GRAPH_IF_NOT_EXISTS:
            self.require_feature(F.GC05)

        if isinstance(self.graph_type, OpenGraphType):
            self.require_feature(F.GG01)
        elif isinstance(self.graph_type, OfGraphType):
            self.require_feature(F.GG02)
            if isinstance(
                self.graph_type.of_graph_type,
                OfGraphType._TypedGraphNestedGraphTypeSpecification,
            ):
                self.require_feature(F.GG03)
            elif isinstance(self.graph_type.of_graph_type, GraphTypeLikeGraph):
                self.require_feature(F.GG04)

        if self.graph_source is not None:
            self.require_feature(F.GG05)

        return self


class DropGraphStatement(PrimitiveCatalogModifyingStatement):
    """AST Expression for <drop graph statement>."""

    if_exists: bool
    catalog_graph_parent_and_name: CatalogGraphParentAndName

    @model_validator(mode="after")
    def _check_drop_graph_statement(self):
        self.require_feature(F.GC04)

        if self.if_exists:
            self.require_feature(F.GC05)

        return self


class CreateGraphTypeStatement(PrimitiveCatalogModifyingStatement):
    """AST Expression for <create graph type statement>."""

    class CreateMode(Enum):
        CREATE_GRAPH_TYPE = auto()
        CREATE_GRAPH_TYPE_IF_NOT_EXISTS = auto()
        CREATE_OR_REPLACE_GRAPH_TYPE = auto()

    create_mode: CreateMode
    catalog_graph_type_parent_and_name: CatalogGraphTypeParentAndName
    graph_type_source: GraphTypeSource

    @model_validator(mode="after")
    def _check_create_graph_type_statement(self):
        self.require_feature(F.GG02)

        if self.create_mode == CreateGraphTypeStatement.CreateMode.CREATE_GRAPH_TYPE_IF_NOT_EXISTS:
            self.require_feature(F.GC03)

        return self


class DropGraphTypeStatement(PrimitiveCatalogModifyingStatement):
    """AST Expression for <drop graph type statement>."""

    if_exists: bool
    catalog_graph_type_parent_and_name: CatalogGraphTypeParentAndName

    @model_validator(mode="after")
    def _check_drop_graph_type_statement(self):
        self.require_feature(F.GG02)

        if self.if_exists:
            self.require_feature(F.GC03)

        return self


class PrimitiveDataModifyingStatement(SimpleDataModifyingStatement):
    """Semantic marker for <primitive data-modifying statement> in the Abstract Syntax Tree."""

    pass


CallDataModifyingProcedureStatement: t.TypeAlias = CallProcedureStatement


class PrimitiveQueryStatement(SimpleQueryStatement):
    """Semantic marker for <primitive query statement> in the Abstract Syntax Tree (AST)."""

    pass


CallQueryStatement: t.TypeAlias = CallProcedureStatement


class AllPathSearch(PathSearchPrefix):
    """AST Expression for <all path search>."""

    path_mode: PathMode | None
    path_or_paths: PathOrPaths | None

    @model_validator(mode="after")
    def _check_all_path_search(self):
        self.require_feature(F.G015)
        return self


class PathOrPaths(Expression):
    """AST Expression for <path or paths>."""

    class Mode(Enum):
        PATHS = auto()
        PATH = auto()

    mode: Mode

    @model_validator(mode="after")
    def _check_path_or_paths(self):
        self.require_feature(F.G014)
        return self


class AnyPathSearch(PathSearchPrefix):
    """AST Expression for <any path search>."""

    number_of_paths: NumberOfPaths | None
    path_mode: PathMode | None
    path_or_paths: PathOrPaths | None

    @model_validator(mode="after")
    def _check_any_path_search(self):
        self.require_feature(F.G016)
        return self


class ShortestPathSearch(PathSearchPrefix):
    """Semantic marker for <shortest path search> in the Abstract Syntax Tree (AST)."""

    pass


class PathFactor(Expression):
    """Semantic marker for <path factor> in the Abstract Syntax Tree (AST)."""

    pass


class LabelFactor(Expression):
    """Semantic marker for <label factor> in the Abstract Syntax Tree (AST)."""

    pass


class SimplifiedConcatenation(SimplifiedTerm):
    """AST Expression for <simplified concatenation>."""

    simplified_term: SimplifiedTerm
    simplified_factor_low: SimplifiedFactorLow


class SimplifiedFactorLow(SimplifiedTerm):
    """Semantic marker for <simplified factor low> in the Abstract Syntax Tree (AST)."""

    pass


class NodeTypePattern(NodeTypeSpecification):
    """AST Expression for <node type pattern>."""

    class _TypeNodeTypeName(Expression):
        """Internal expression."""

        type: bool
        node_type_name: NodeTypeName

    node_synonym_type_node_type_name: _TypeNodeTypeName | None
    local_node_type_alias: LocalNodeTypeAlias | None
    node_type_filler: NodeTypeFiller | None


class NodeTypePhrase(NodeTypeSpecification):
    """AST Expression for <node type phrase>."""

    type: bool
    node_type_phrase_filler: NodeTypePhraseFiller
    local_node_type_alias: LocalNodeTypeAlias | None


class EdgeTypePattern(EdgeTypeSpecification):
    """AST Expression for <edge type pattern>."""

    class _EdgeTypePatternPrefix(Expression):
        """Internal expression."""

        edge_kind: EdgeKind | None
        type_: bool
        edge_type_name: EdgeTypeName

    prefix: _EdgeTypePatternPrefix | None
    edge_type_pattern: EdgeTypePatternDirected | EdgeTypePatternUndirected


class EdgeTypePhrase(EdgeTypeSpecification):
    """AST Expression for <edge type phrase>."""

    edge_kind: EdgeKind
    type: bool
    edge_type_phrase_filler: EdgeTypePhraseFiller
    endpoint_pair_phrase: EndpointPairPhrase

    @model_validator(mode="after")
    def _check_edge_type_phrase(self):
        if self.edge_kind == EdgeKind.UNDIRECTED:
            self.require_feature(F.GH02)
        return self


class EndpointPairPointingRight(EndpointPairDirected):
    """AST Expression for <endpoint pair pointing right>."""

    source_node_type_alias: SourceNodeTypeAlias
    connector_pointing_right: ConnectorPointingRight
    destination_node_type_alias: DestinationNodeTypeAlias


class EndpointPairPointingLeft(EndpointPairDirected):
    """AST Expression for <endpoint pair pointing left>."""

    destination_node_type_alias: DestinationNodeTypeAlias
    source_node_type_alias: SourceNodeTypeAlias


class BooleanType(PredefinedType):
    """AST Expression for <boolean type>."""

    not_null: bool

    @model_validator(mode="after")
    def _check_boolean_type(self):
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class CharacterStringType(PredefinedType):
    """AST Expression for <character string type>."""

    class _String(Expression):
        """Internal expression."""

        min_length: MinLength | None
        max_length: MaxLength | None

        @model_validator(mode="after")
        def _check_min_requires_max(self):
            if self.min_length is not None and self.max_length is None:
                raise ValueError("min_length requires max_length")
            return self

    class _Char(Expression):
        """Internal expression."""

        fixed_length: FixedLength | None

    class _Varchar(Expression):
        """Internal expression."""

        max_length: MaxLength | None

    character_string_type: _String | _Char | _Varchar
    not_null: bool

    @model_validator(mode="after")
    def _check_character_string_type(self):
        match self.character_string_type:
            case CharacterStringType._String(min_length=ml, max_length=mxl):
                if ml is not None:
                    self.require_feature(F.GV30)  # Specified character string minimum length
                if mxl is not None:
                    self.require_feature(F.GV31)  # Specified character string maximum length
            case CharacterStringType._Varchar(max_length=ml) if ml is not None:
                self.require_feature(F.GV31)  # Specified character string maximum length
            case CharacterStringType._Char(fixed_length=fl) if fl is not None:
                self.require_feature(F.GV32)  # Specified character string fixed length
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class ByteStringType(PredefinedType):
    """AST Expression for <byte string type>."""

    class _Bytes(Expression):
        """Internal expression."""

        min_length: MinLength | None
        max_length: MaxLength | None

        @model_validator(mode="after")
        def _check_min_requires_max(self):
            if self.min_length is not None and self.max_length is None:
                raise ValueError("min_length requires max_length")
            return self

    class _Binary(Expression):
        """Internal expression."""

        fixed_length: FixedLength | None

    class _Varbinary(Expression):
        """Internal expression."""

        max_length: MaxLength | None

    byte_string_type: _Bytes | _Binary | _Varbinary
    not_null: bool

    @model_validator(mode="after")
    def _check_byte_string_type(self):
        self.require_feature(F.GV35)  # Byte string types
        match self.byte_string_type:
            case ByteStringType._Bytes(min_length=ml, max_length=mxl):
                if ml is not None:
                    self.require_feature(F.GV36)  # Specified byte string minimum length
                if mxl is not None:
                    self.require_feature(F.GV37)  # Specified byte string maximum length
            case ByteStringType._Varbinary(max_length=ml) if ml is not None:
                self.require_feature(F.GV37)  # Specified byte string maximum length
            case ByteStringType._Binary(fixed_length=fl) if fl is not None:
                self.require_feature(F.GV38)  # Specified byte string fixed length
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class NumericType(PredefinedType):
    """Semantic marker for <numeric type> in the Abstract Syntax Tree (AST)."""

    pass


class TemporalType(PredefinedType):
    """Semantic marker for <temporal type> in the Abstract Syntax Tree (AST)."""

    pass


class ReferenceValueType(PredefinedType):
    """Semantic marker for <reference value type> in the Abstract Syntax Tree (AST)."""

    pass


class ImmaterialValueType(PredefinedType):
    """Semantic marker for <immaterial value type> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_immaterial_value_type(self):
        self.require_feature(F.GV70)
        return self


class PathValueType(ConstructedValueType):
    """AST Expression for <path value type>."""

    not_null: bool

    @model_validator(mode="after")
    def _check_path_value_type(self):
        self.require_feature(F.GV55)  # Path value types
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class ListValueType(ConstructedValueType):
    """AST Expression for <list value type>."""

    class _ListValueTypeNameValueType(Expression):
        """Internal expression."""

        list_value_type_name: ListValueTypeName
        value_type: ValueType

    class _ValueTypeListValueTypeName(Expression):
        """Internal expression."""

        value_type: ValueType | None
        list_value_type_name: ListValueTypeName

    body: _ListValueTypeNameValueType | _ValueTypeListValueTypeName
    max_length: MaxLength | None
    not_null: bool

    @model_validator(mode="after")
    def _check_list_value_type(self):
        self.require_feature(F.GV50)  # List value types
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class RecordType(ConstructedValueType):
    """AST Expression for <record type>."""

    class _AnyRecordNotNull(Expression):
        """Internal expression."""

        any: bool
        not_null: bool

    class _RecordFieldTypesSpecificationNotNull(Expression):
        """Internal expression."""

        record: bool
        field_types_specification: FieldTypesSpecification
        not_null: bool

    record_type: _AnyRecordNotNull | _RecordFieldTypesSpecificationNotNull

    @model_validator(mode="after")
    def _check_record_type(self):
        self.require_feature(F.GV45)  # Record types
        match self.record_type:
            case RecordType._RecordFieldTypesSpecificationNotNull(not_null=nn):
                self.require_feature(F.GV46)  # Closed record types
                if nn:
                    self.require_feature(F.GV90)  # Explicit value type nullability
            case RecordType._AnyRecordNotNull(not_null=nn):
                self.require_feature(F.GV47)  # Open record types
                if nn:
                    self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class OpenDynamicUnionType(DynamicUnionType):
    """AST Expression for <open dynamic union type>."""

    not_null: bool

    @model_validator(mode="after")
    def _check_open_dynamic_union_type(self):
        self.require_feature(F.GV66)  # Open dynamic union types
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class DynamicPropertyValueType(DynamicUnionType):
    """AST Expression for <dynamic property value type>."""

    any: bool
    not_null: bool

    @model_validator(mode="after")
    def _check_dynamic_property_value_type(self):
        self.require_feature(F.GV68)  # Dynamic property value types
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class ClosedDynamicUnionType(DynamicUnionType):
    """AST Expression for <closed dynamic union type>."""

    any_value: bool  # ANY and ANY VALUE are syntactic synonyms
    component_type_list: ComponentTypeList

    @model_validator(mode="after")
    def _check_closed_dynamic_union_type(self):
        self.require_feature(F.GV67)  # Closed dynamic union types
        return self


class SignedNumericLiteral(Literal):
    """AST Expression for <signed numeric literal>."""

    sign: Sign = Sign.PLUS_SIGN
    unsigned_numeric_literal: UnsignedNumericLiteral


LowerBound: t.TypeAlias = UnsignedInteger

UpperBound: t.TypeAlias = UnsignedInteger

MinLength: t.TypeAlias = UnsignedInteger

MaxLength: t.TypeAlias = UnsignedInteger

FixedLength: t.TypeAlias = UnsignedInteger

Precision: t.TypeAlias = UnsignedInteger

Scale: t.TypeAlias = UnsignedInteger

Iso8601Uint: t.TypeAlias = UnsignedInteger


class SimpleCase(CaseSpecification):
    """AST Expression for <simple case>."""

    case_operand: CaseOperand
    list_simple_when_clause: list[SimpleWhenClause]
    else_clause: ElseClause | None


class SearchedCase(CaseSpecification):
    """AST Expression for <searched case>."""

    list_searched_when_clause: list[SearchedWhenClause]
    else_clause: ElseClause | None


DeleteItem: t.TypeAlias = ValueExpression

ProcedureArgument: t.TypeAlias = ValueExpression


class CommonValueExpression(ValueExpression):
    """Semantic marker for <common value expression> in the Abstract Syntax Tree (AST)."""

    pass


@nonstandard("Parse-time ambiguity: expression type undetermined until semantic analysis")
class AmbiguousValueExpression(CommonValueExpression):
    """Intermediate class for expressions that can't be definitively typed at parse time.

    When parsing identifiers with operators, we don't know if `a || b` is string,
    list, or path concatenation, or if `a + b` is numeric or duration arithmetic.
    This class groups such ambiguous expressions together.
    """

    pass


class ConcatenationValueExpression(AmbiguousValueExpression):
    """AST Expression for ambiguous concatenation expressions."""

    operands: list[ValueExpressionPrimary] = field(..., min_length=2)


@nonstandard("Parse-time ambiguity: ABS() could be numeric or duration")
class ArithmeticAbsoluteValueFunction(Expression):
    """AST Expression for ambiguous ABS function calls."""

    arithmetic_value_expression: ArithmeticValueExpression

    @model_validator(mode="after")
    def _check_arithmetic_absolute_value_function(self):
        self.require_feature(F.GF01)
        return self


@nonstandard("Parse convenience: not a concept from the GQL spec")
class ArithmeticFactor(Expression):
    """AST Expression for <arithmetic factor>."""

    sign: Sign = Sign.PLUS_SIGN
    arithmetic_primary: ArithmeticPrimary


@nonstandard("Parse convenience: not a concept from the GQL spec")
class ArithmeticTerm(Expression):
    """AST Expression for <arithmetic term>."""

    class _MultiplicativeFactor(Expression):
        """Internal expression."""

        operator: MultiplicativeOperator
        factor: ArithmeticFactor

    base: ArithmeticFactor
    steps: list[_MultiplicativeFactor] | None = None


@nonstandard("Parse-time ambiguity: arithmetic could be numeric or duration")
class ArithmeticValueExpression(AmbiguousValueExpression):
    """Generic arithmetic value expression for type-ambiguous expressions."""

    class _SignedTerm(Expression):
        """Internal expression."""

        sign: Sign
        term: ArithmeticTerm

    base: ArithmeticTerm
    steps: list[_SignedTerm] | None = None


AggregatingValueExpression: t.TypeAlias = ValueExpression

ResultExpression: t.TypeAlias = ValueExpression

ListElement: t.TypeAlias = ValueExpression


class BooleanValueExpression(ValueExpression):
    """AST Expression for <boolean value expression>."""

    class Operator(Enum):
        OR = auto()
        XOR = auto()

    class _OpBooleanTerm(Expression):
        """Internal expression."""

        operator: BooleanValueExpression.Operator
        boolean_term: BooleanTerm

    boolean_term: BooleanTerm
    ops: list[_OpBooleanTerm] | None

    @model_validator(mode="after")
    def _check_boolean_value_expression(self):
        if self.ops:
            for op in self.ops:
                if op.operator == BooleanValueExpression.Operator.XOR:
                    self.require_feature(F.GE07)
                    break
        return self


class Predicate(Expression):
    """Semantic marker for <predicate> in the Abstract Syntax Tree (AST)."""

    pass


class ComparisonPredicate(Predicate):
    """AST Expression for <comparison predicate> and <comparison predicate part 2>."""

    comparison_predicand: ComparisonPredicand
    comparison_predicate_part_2: ComparisonPredicatePart2


class ExistsPredicate(Predicate):
    """AST Expression for <exists predicate>."""

    class _ExistsGraphPattern(Expression):
        """Internal expression."""

        graph_pattern: GraphPattern

    class _ExistsMatchStatementBlock(Expression):
        """Internal expression."""

        match_statement_block: MatchStatementBlock

    exists_predicate: _ExistsGraphPattern | _ExistsMatchStatementBlock | NestedQuerySpecification

    @model_validator(mode="after")
    def _check_exists_predicate(self):
        if isinstance(self.exists_predicate, self._ExistsMatchStatementBlock):
            self.require_feature(F.GQ22)  # EXISTS predicate: multiple MATCH statements
        return self


class NullPredicate(Predicate):
    """AST Expression for <null predicate>."""

    value_expression_primary: ValueExpressionPrimary
    null_predicate_part_2: NullPredicatePart2


class ValueTypePredicate(Predicate):
    """AST Expression for <value type predicate>."""

    value_expression_primary: ValueExpressionPrimary
    value_type_predicate_part_2: ValueTypePredicatePart2

    @model_validator(mode="after")
    def _check_value_type_predicate(self):
        self.require_feature(F.GA06)
        return self


class NormalizedPredicate(Predicate):
    """AST Expression for <normalized predicate>."""

    string_value_expression: StringValueExpression
    normalized_predicate_part_2: NormalizedPredicatePart2


class DirectedPredicate(Predicate):
    """AST Expression for <directed predicate>."""

    element_variable_reference: ElementVariableReference
    directed_predicate_part_2: DirectedPredicatePart2

    @model_validator(mode="after")
    def _check_directed_predicate(self):
        self.require_feature(F.G110)
        return self


class LabeledPredicate(Predicate):
    """AST Expression for <labeled predicate>."""

    element_variable_reference: ElementVariableReference
    labeled_predicate_part_2: LabeledPredicatePart2

    @model_validator(mode="after")
    def _check_labeled_predicate(self):
        self.require_feature(F.G111)
        return self


class SourceDestinationPredicate(Predicate):
    """AST Expression for <source/destination predicate>."""

    node_reference: NodeReference
    predicate_part_2: SourcePredicatePart2 | DestinationPredicatePart2

    @model_validator(mode="after")
    def _check_source_destination_predicate(self):
        self.require_feature(F.G112)
        return self


class AllDifferentPredicate(Predicate):
    """AST Expression for <all_different predicate>."""

    list_element_variable_reference: list[ElementVariableReference]

    @model_validator(mode="after")
    def _check_all_different_predicate(self):
        self.require_feature(F.G113)
        return self


class SamePredicate(Predicate):
    """AST Expression for <same predicate>."""

    list_element_variable_reference: list[ElementVariableReference]

    @model_validator(mode="after")
    def _check_same_predicate(self):
        self.require_feature(F.G114)
        return self


class PropertyExistsPredicate(Predicate):
    """AST Expression for <property_exists predicate>."""

    element_variable_reference: ElementVariableReference
    property_name: PropertyName

    @model_validator(mode="after")
    def _check_property_exists_predicate(self):
        self.require_feature(F.G115)
        return self


class ParenthesizedBooleanValueExpression(Expression):
    """AST Expression for <parenthesized boolean value expression>."""

    boolean_value_expression: BooleanValueExpression


class CharLengthExpression(LengthExpression):
    """AST Expression for <char length expression>."""

    character_string_value_expression: CharacterStringValueExpression


class ByteLengthExpression(LengthExpression):
    """AST Expression for <byte length expression>."""

    byte_string_value_expression: ByteStringValueExpression

    @model_validator(mode="after")
    def _check_byte_length_expression(self):
        self.require_feature(F.GV35)  # Byte string types
        return self


class PathLengthExpression(LengthExpression):
    """AST Expression for <path length expression>."""

    path_value_expression: PathValueExpression

    @model_validator(mode="after")
    def _check_path_length_expression(self):
        self.require_feature(F.GF04)
        return self


class SingleCharacterTrimFunction(TrimFunction):
    """AST Expression for <single-character trim function>."""

    trim_operands: TrimOperands

    @model_validator(mode="after")
    def _check_single_character_trim_function(self):
        # GF06 required when FROM is present (trim_specification_trim_character_string_from is set)
        if self.trim_operands.trim_specification_trim_character_string_from is not None:
            self.require_feature(F.GF06)
        return self


class MultiCharacterTrimFunction(TrimFunction):
    """AST Expression for <multi-character trim function>."""

    class Mode(Enum):
        BTRIM = auto()
        LTRIM = auto()
        RTRIM = auto()

    mode: Mode
    trim_source: TrimSource
    trim_character_string: TrimCharacterString | None

    @model_validator(mode="after")
    def _check_multi_character_trim_function(self):
        self.require_feature(F.GF05)
        return self


RecordLiteral: t.TypeAlias = RecordConstructor

SubpathVariable: t.TypeAlias = Identifier

SetTimeZoneValue: t.TypeAlias = TimeZoneString


YieldItemName: t.TypeAlias = FieldName


class BindingVariableReference(Expression):
    """AST Expression for <binding variable reference>."""

    binding_variable: BindingVariable


ElementVariable: t.TypeAlias = BindingVariable

PathVariable: t.TypeAlias = BindingVariable


class FocusedLinearDataModifyingStatementBody(FocusedLinearDataModifyingStatement):
    """AST Expression for <focused linear data-modifying statement body>."""

    use_graph_clause: UseGraphClause
    simple_linear_data_accessing_statement: SimpleLinearDataAccessingStatement
    primitive_result_statement: PrimitiveResultStatement | None


class FocusedNestedDataModifyingProcedureSpecification(FocusedLinearDataModifyingStatement):
    """AST Expression for <focused nested data-modifying procedure specification>."""

    use_graph_clause: UseGraphClause
    nested_data_modifying_procedure_specification: NestedDataModifyingProcedureSpecification


class NestedDataModifyingProcedureSpecification(AmbientLinearDataModifyingStatement):
    """AST Expression for <nested data-modifying procedure specification>."""

    data_modifying_procedure_specification: DataModifyingProcedureSpecification


class AmbientLinearDataModifyingStatementBody(AmbientLinearDataModifyingStatement):
    """AST Expression for <ambient linear data-modifying statement body>."""

    simple_linear_data_accessing_statement: SimpleLinearDataAccessingStatement
    primitive_result_statement: PrimitiveResultStatement | None


class InsertStatement(PrimitiveDataModifyingStatement):
    """AST Expression for <insert statement>."""

    insert_graph_pattern: InsertGraphPattern


class SetStatement(PrimitiveDataModifyingStatement):
    """AST Expression for <set statement>."""

    set_item_list: SetItemList


class RemoveStatement(PrimitiveDataModifyingStatement):
    """AST Expression for <remove statement>."""

    remove_item_list: RemoveItemList


class DeleteStatement(PrimitiveDataModifyingStatement):
    """AST Expression for <delete statement>."""

    class Mode(Enum):
        DETACH = auto()
        NODETACH = auto()

    mode: Mode = Mode.NODETACH
    delete_item_list: DeleteItemList


class MatchStatement(PrimitiveQueryStatement):
    """Semantic marker for <match statement> in the Abstract Syntax Tree (AST)."""

    pass


class FilterStatement(PrimitiveQueryStatement):
    """AST Expression for <filter statement>."""

    filter_statement: WhereClause | SearchCondition

    @model_validator(mode="after")
    def _check_filter_statement(self):
        self.require_feature(F.GQ08)  # FILTER statement
        return self


class LetStatement(PrimitiveQueryStatement):
    """AST Expression for <let statement>."""

    let_variable_definition_list: LetVariableDefinitionList

    @model_validator(mode="after")
    def _check_let_statement(self):
        self.require_feature(F.GQ09)  # LET statement
        return self


class ForStatement(PrimitiveQueryStatement):
    """AST Expression for <for statement>."""

    for_item: ForItem
    for_ordinality_or_offset: ForOrdinalityOrOffset | None

    @model_validator(mode="after")
    def _check_for_statement(self):
        # GQ10: FOR statement with list value expression
        # Check if for_item_source is a ListValueExpression or contains list-related expressions
        source = self.for_item.for_item_source
        if isinstance(source, ListValueExpression):
            self.require_feature(F.GQ10)  # FOR statement: list value support
        elif isinstance(source, BindingTableReferenceValueExpression):
            inner = source.binding_table_reference_value_expression
            if isinstance(inner, BindingTableReferenceValueExpression._TableBindingTableExpression):
                self.require_feature(F.GQ23)  # FOR statement: binding table support
            elif source.find_first(ListValueConstructorByEnumeration) is not None:
                self.require_feature(F.GQ10)  # FOR statement: list value support
        # GQ11: FOR statement with WITH ORDINALITY
        if (
            self.for_ordinality_or_offset is not None
            and self.for_ordinality_or_offset.mode == ForOrdinalityOrOffset.Mode.ORDINALITY
        ):
            self.require_feature(F.GQ11)  # FOR statement: WITH ORDINALITY
        # GQ24: FOR statement with WITH OFFSET
        if (
            self.for_ordinality_or_offset is not None
            and self.for_ordinality_or_offset.mode == ForOrdinalityOrOffset.Mode.OFFSET
        ):
            self.require_feature(F.GQ24)  # FOR statement: WITH OFFSET
        return self


class OrderByAndPageStatement(PrimitiveQueryStatement):
    """AST Expression for <order by and page statement>."""

    class _OrderByClauseOffsetClauseLimitClause(Expression):
        """Internal expression."""

        order_by_clause: OrderByClause
        offset_clause: OffsetClause | None
        limit_clause: LimitClause | None

    class _OffsetClauseLimitClause(Expression):
        """Internal expression."""

        offset_clause: OffsetClause
        limit_clause: LimitClause | None

    order_by_and_page_statement: (
        _OrderByClauseOffsetClauseLimitClause | _OffsetClauseLimitClause | LimitClause
    )

    @model_validator(mode="after")
    def _check_order_by_and_page_statement(self):
        stmt = self.order_by_and_page_statement
        has_offset = False
        has_limit = False
        if isinstance(stmt, self._OrderByClauseOffsetClauseLimitClause):
            has_offset = stmt.offset_clause is not None
            has_limit = stmt.limit_clause is not None
        elif isinstance(stmt, self._OffsetClauseLimitClause):
            has_offset = True
            has_limit = stmt.limit_clause is not None
        elif isinstance(stmt, LimitClause):
            has_limit = True
        if has_offset:
            self.require_feature(F.GQ12)  # OFFSET clause
        if has_limit:
            self.require_feature(F.GQ13)  # LIMIT clause
        return self


class AllShortestPathSearch(ShortestPathSearch):
    """AST Expression for <all shortest path search>."""

    path_mode: PathMode | None
    path_or_paths: PathOrPaths | None

    @model_validator(mode="after")
    def _check_all_shortest_path_search(self):
        self.require_feature(F.G017)
        return self


class AnyShortestPathSearch(ShortestPathSearch):
    """AST Expression for <any shortest path search>."""

    path_mode: PathMode | None
    path_or_paths: PathOrPaths | None

    @model_validator(mode="after")
    def _check_any_shortest_path_search(self):
        self.require_feature(F.G018)
        return self


class CountedShortestPathSearch(ShortestPathSearch):
    """AST Expression for <counted shortest path search>."""

    number_of_paths: NumberOfPaths
    path_mode: PathMode | None
    path_or_paths: PathOrPaths | None

    @model_validator(mode="after")
    def _check_counted_shortest_path_search(self):
        self.require_feature(F.G019)
        return self


class CountedShortestGroupSearch(ShortestPathSearch):
    """AST Expression for <counted shortest group search>."""

    number_of_groups: NumberOfGroups | None
    path_mode: PathMode | None
    path_or_paths: PathOrPaths | None

    @model_validator(mode="after")
    def _check_counted_shortest_group_search(self):
        self.require_feature(F.G020)
        return self


class QuantifiedPathPrimary(PathFactor):
    """AST Expression for <quantified path primary>."""

    path_primary: PathPrimary
    graph_pattern_quantifier: GraphPatternQuantifier

    @model_validator(mode="after")
    def _check_quantified_path_primary(self):
        if isinstance(self.path_primary, EdgePattern):
            self.require_feature(F.G036)
        else:
            self.require_feature(F.G035)

        return self


class QuestionedPathPrimary(PathFactor):
    """AST Expression for <questioned path primary>."""

    path_primary: PathPrimary

    @model_validator(mode="after")
    def _check_questioned_path_primary(self):
        self.path_primary.require_feature(F.G037)
        return self


class PathPrimary(PathFactor):
    """Semantic marker for <path primary> in the Abstract Syntax Tree (AST)."""

    pass


class LabelNegation(LabelFactor):
    """AST Expression for <label negation>."""

    label_primary: LabelPrimary


class LabelPrimary(LabelFactor):
    """Semantic marker for <label primary> in the Abstract Syntax Tree (AST)."""

    pass


class SimplifiedConjunction(SimplifiedFactorLow):
    """AST Expression for <simplified conjunction>."""

    simplified_factor_low: SimplifiedFactorLow
    simplified_factor_high: SimplifiedFactorHigh


class SimplifiedFactorHigh(SimplifiedFactorLow):
    """Semantic marker for <simplified factor high> in the Abstract Syntax Tree (AST)."""

    pass


class ExactNumericType(NumericType):
    """Semantic marker for <exact numeric type> in the Abstract Syntax Tree (AST)."""

    pass


class ApproximateNumericType(NumericType):
    """AST Expression for <approximate numeric type>."""

    class _Float16(Expression):
        """Internal expression."""

        pass

    class _Float32(Expression):
        """Internal expression."""

        pass

    class _Float64(Expression):
        """Internal expression."""

        pass

    class _Float128(Expression):
        """Internal expression."""

        pass

    class _Float256(Expression):
        """Internal expression."""

        pass

    class _Float(Expression):
        """Internal expression."""

        precision_scale: ApproximateNumericType._PrecisionScale | None

    class _PrecisionScale(Expression):
        """Internal expression."""

        precision: Precision
        scale: Scale | None

    class _Real(Expression):
        """Internal expression."""

        pass

    class _DoublePrecision(Expression):
        """Internal expression."""

        pass

    approximate_numeric_type: (
        _Float16 | _Float32 | _Float64 | _Float128 | _Float256 | _Float | _Real | _DoublePrecision
    )
    not_null: bool

    @model_validator(mode="after")
    def _check_approximate_numeric_type(self):
        match self.approximate_numeric_type:
            case ApproximateNumericType._Float16():
                self.require_feature(F.GV20)  # 16 bit floating point numbers
            case ApproximateNumericType._Float32():
                self.require_feature(F.GV21)  # 32 bit floating point numbers
            case ApproximateNumericType._Float(precision_scale=ps) if ps is not None:
                self.require_feature(F.GV22)  # Specified floating point number precision
            case ApproximateNumericType._Real() | ApproximateNumericType._DoublePrecision():
                self.require_feature(F.GV23)  # Floating point type name synonyms
            case ApproximateNumericType._Float64():
                self.require_feature(F.GV24)  # 64 bit floating point numbers
            case ApproximateNumericType._Float128():
                self.require_feature(F.GV25)  # 128 bit floating point numbers
            case ApproximateNumericType._Float256():
                self.require_feature(F.GV26)  # 256 bit floating point numbers
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class TemporalInstantType(TemporalType):
    """Semantic marker for <temporal instant type> in the Abstract Syntax Tree (AST)."""

    pass


class TemporalDurationType(TemporalType):
    """AST Expression for <temporal duration type>."""

    temporal_duration_qualifier: TemporalDurationQualifier
    not_null: bool

    @model_validator(mode="after")
    def _check_temporal_duration_type(self):
        self.require_feature(F.GV41)  # Temporal types: duration support
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class GraphReferenceValueType(ReferenceValueType):
    """Semantic marker for <graph reference value type> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_graph_reference_value_type(self):
        self.require_feature(F.GV60)  # Graph reference value types
        return self


class BindingTableReferenceValueType(ReferenceValueType):
    """AST Expression for <binding table reference value type>."""

    binding_table_type: BindingTableType
    not_null: bool

    @model_validator(mode="after")
    def _check_binding_table_reference_value_type(self):
        self.require_feature(F.GV61)  # Binding table reference value types
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class NodeReferenceValueType(ReferenceValueType):
    """Semantic marker for <node reference value type> in the Abstract Syntax Tree (AST)."""

    pass


class EdgeReferenceValueType(ReferenceValueType):
    """Semantic marker for <edge reference value type> in the Abstract Syntax Tree (AST)."""

    pass


class NullType(ImmaterialValueType):
    """AST Expression for <null type>."""

    @model_validator(mode="after")
    def _check_null_type(self):
        self.require_feature(F.GV71)  # Immaterial value types: null type support
        return self


class EmptyType(ImmaterialValueType):
    """AST Expression for <empty type>."""

    class _NullNotNull(Expression):
        """Internal expression."""

        not_null: NotNull

    class _Nothing(Expression):
        """Internal expression."""

        pass

    empty_type: _NullNotNull | _Nothing

    @model_validator(mode="after")
    def _check_empty_type(self):
        self.require_feature(F.GV72)  # Immaterial value types: empty type support
        return self


class ReferenceValueExpression(CommonValueExpression):
    """Semantic marker for <reference value expression> in the Abstract Syntax Tree (AST)."""

    pass


class PathValueExpression(CommonValueExpression):
    """AST Expression for <path value expression> and <path value concatenation>."""

    list_path_value_primary: list[PathValuePrimary] = field(..., min_length=1)

    @model_validator(mode="after")
    def _check_path_value_expression(self):
        self.require_feature(F.GV55)  # No path value expressions without GV55
        if len(self.list_path_value_primary) > 1:
            self.require_feature(F.GE06)  # Path value concatenation
        return self


class ListValueExpression(CommonValueExpression):
    """AST Expression for <list value expression> and <list concatenation>."""

    list_list_primary: list[ListPrimary] = field(..., min_length=1)

    @model_validator(mode="after")
    def _check_list_value_expression(self):
        self.require_feature(F.GV50)  # List value types
        return self


class NumericValueExpression(CommonValueExpression):
    """AST Expression for <numeric value expression>."""

    class _SignedTerm(Expression):
        """Internal expression."""

        sign: Sign
        term: Term

    base: Term
    steps: list[_SignedTerm] | None = None


class StringValueExpression(CommonValueExpression):
    """Semantic marker for <string value expression> in the Abstract Syntax Tree (AST)."""

    pass


class DatetimeValueExpression(CommonValueExpression):
    """AST Expression for <datetime value expression>."""

    class _DurationValueExpressionPlusDatetimePrimary(Expression):
        """Internal expression."""

        duration_value_expression: DurationValueExpression
        datetime_primary: DatetimePrimary

    class _SignedDurationTerm(Expression):
        """Internal expression."""

        sign: Sign
        duration_term: DurationTerm

    base: DatetimePrimary | _DurationValueExpressionPlusDatetimePrimary
    steps: list[_SignedDurationTerm] | None


class DurationValueExpression(CommonValueExpression):
    """AST Expression for <duration value expression>."""

    class _SignedDurationTerm(Expression):
        """Internal expression."""

        sign: Sign
        duration_term: DurationTerm

    # Can be either:
    # 1. Duration arithmetic: base DurationTerm with optional +/- steps
    # 2. Datetime subtraction: DURATION_BETWEEN(...)
    base: DurationTerm | DatetimeSubtraction
    steps: list[_SignedDurationTerm] | None = None

    @model_validator(mode="after")
    def _check_duration_value_expression(self):
        self.require_feature(F.GV41)  # Temporal types: duration support
        return self


SortKey: t.TypeAlias = AggregatingValueExpression

SearchCondition: t.TypeAlias = BooleanValueExpression

GeneralLiteral: t.TypeAlias = (
    BooleanLiteral
    | CharacterStringLiteral
    | ByteStringLiteral
    | TemporalLiteral
    | DurationLiteral
    | NullLiteral
    | ListLiteral
    | RecordLiteral
)

PathVariableReference: t.TypeAlias = BindingVariableReference

ElementVariableReference: t.TypeAlias = BindingVariableReference

GroupingElement: t.TypeAlias = BindingVariableReference

UnsignedLiteral: t.TypeAlias = UnsignedNumericLiteral | GeneralLiteral

UnsignedValueSpecification: t.TypeAlias = UnsignedLiteral | GeneralValueSpecification

NonParenthesizedValueExpressionPrimarySpecialCase: t.TypeAlias = (
    AggregateFunction
    | UnsignedValueSpecification
    | ListValueConstructor
    | RecordConstructor
    | PathValueConstructor
    | PropertyReference
    | ValueQueryExpression
    | CaseExpression
    | CastSpecification
    | ElementIdFunction
    | LetValueExpression
)

NonParenthesizedValueExpressionPrimary: t.TypeAlias = (
    NonParenthesizedValueExpressionPrimarySpecialCase | BindingVariableReference
)


ValueExpressionPrimary: t.TypeAlias = (
    ParenthesizedValueExpression | NonParenthesizedValueExpressionPrimary
)

NumericPrimary: t.TypeAlias = ValueExpressionPrimary | NumericValueFunction

DatetimePrimary: t.TypeAlias = ValueExpressionPrimary | DatetimeValueFunction

DurationPrimary: t.TypeAlias = ValueExpressionPrimary | DurationValueFunction

ArithmeticPrimary: t.TypeAlias = (
    ValueExpressionPrimary
    | NumericValueFunction
    | DurationValueFunction
    | ArithmeticAbsoluteValueFunction
)

RecordExpression: t.TypeAlias = ValueExpressionPrimary


class SimpleMatchStatement(MatchStatement):
    """AST Expression for <simple match statement>."""

    graph_pattern_binding_table: GraphPatternBindingTable


class OptionalMatchStatement(MatchStatement):
    """AST Expression for <optional match statement>."""

    optional_operand: OptionalOperand


class ElementPattern(PathPrimary):
    """Semantic marker for <element pattern> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_element_pattern(self):
        filler = self.find_first(ElementPatternFiller)
        if filler is None:
            return self
        if not isinstance(filler.element_pattern_predicate, ElementPatternWhereClause):
            return self

        declared_name = None
        if filler.element_variable_declaration is not None:
            declared_name = filler.element_variable_declaration.element_variable.name

        prop_name_ids: set[int] = set()
        for prop_ref in filler.element_pattern_predicate.search_condition.find_all(
            PropertyReference
        ):
            for pn in prop_ref.property_name:
                prop_name_ids.add(id(pn.identifier))

        for ident in filler.element_pattern_predicate.search_condition.find_all(Identifier):
            if id(ident) in prop_name_ids:
                continue
            if ident.name != declared_name:
                self.require_feature(F.G041)
                return self

        return self


class ParenthesizedPathPatternExpression(PathPrimary):
    """AST Expression for <parenthesized path pattern expression>."""

    subpath_variable_declaration: SubpathVariableDeclaration | None
    path_mode_prefix: PathModePrefix | None
    path_pattern_expression: PathPatternExpression
    parenthesized_path_pattern_where_clause: ParenthesizedPathPatternWhereClause | None

    @model_validator(mode="after")
    def _check_parenthesized_path_pattern_expression(self):
        self.require_feature(F.G038)

        if self.subpath_variable_declaration is not None:
            self.subpath_variable_declaration.require_feature(F.G048)

        if self.parenthesized_path_pattern_where_clause is not None:
            self.parenthesized_path_pattern_where_clause.require_feature(F.G050)

        if self.path_mode_prefix is not None:
            self.require_feature(F.G049)

        if self.parenthesized_path_pattern_where_clause is not None:
            declared_names: set[str] = set()
            for evd in self.path_pattern_expression.find_all(ElementVariableDeclaration):
                declared_names.add(evd.element_variable.name)

            search = self.parenthesized_path_pattern_where_clause.search_condition
            prop_name_ids: set[int] = set()
            for prop_ref in search.find_all(PropertyReference):
                for pn in prop_ref.property_name:
                    prop_name_ids.add(id(pn))

            for ident in search.find_all(Identifier):
                if id(ident) in prop_name_ids:
                    continue
                if ident.name not in declared_names:
                    self.require_feature(F.G051)
                    break

        return self


class SimplifiedPathPatternExpression(PathPrimary):
    """Semantic marker for <simplified path pattern expression> in the Abstract Syntax Tree."""

    pass


class ParenthesizedLabelExpression(LabelPrimary):
    """AST Expression for <parenthesized label expression>."""

    label_expression: LabelExpression


class LabelName(LabelPrimary):
    """AST Expression for <label name>."""

    identifier: Identifier


class SimplifiedQuantified(SimplifiedFactorHigh):
    """AST Expression for <simplified quantified>."""

    simplified_tertiary: SimplifiedTertiary
    graph_pattern_quantifier: GraphPatternQuantifier


class SimplifiedQuestioned(SimplifiedFactorHigh):
    """AST Expression for <simplified questioned>."""

    simplified_tertiary: SimplifiedTertiary


class SimplifiedTertiary(SimplifiedFactorHigh):
    """Semantic marker for <simplified tertiary> in the Abstract Syntax Tree (AST)."""

    pass


class BinaryExactNumericType(ExactNumericType):
    """Semantic marker for <binary exact numeric type> in the Abstract Syntax Tree (AST)."""

    pass


class DecimalExactNumericType(ExactNumericType):
    """AST Expression for <decimal exact numeric type>."""

    class _PrecisionScale(Expression):
        """Internal expression."""

        precision: Precision
        scale: Scale | None

    precision_scale: _PrecisionScale | None
    not_null: bool

    @model_validator(mode="after")
    def _check_decimal_exact_numeric_type(self):
        self.require_feature(F.GV17)  # Decimal numbers
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class DatetimeType(TemporalInstantType):
    """AST Expression for <datetime type>."""

    # 4.16.6.2 Temporal instant types: ZONED DATETIME [...] Equivalent to TIMESTAMP WITH TIME ZONE

    not_null: bool

    @model_validator(mode="after")
    def _check_datetime_type(self):
        self.require_feature(F.GV40)  # Temporal types: zoned datetime and zoned time
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class LocaldatetimeType(TemporalInstantType):
    """AST Expression for <localdatetime type>."""

    # 4.16.6.3 Temporal instant types: LOCAL DATETIME [...] Equivalent to
    # TIMESTAMP WITHOUT TIME ZONE

    not_null: bool

    @model_validator(mode="after")
    def _check_localdatetime_type(self):
        self.require_feature(F.GV39)  # Temporal types: date, local datetime and local time
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class DateType(TemporalInstantType):
    """AST Expression for <date type>."""

    not_null: bool

    @model_validator(mode="after")
    def _check_date_type(self):
        self.require_feature(F.GV39)  # Temporal types: date, local datetime and local time
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class TimeType(TemporalInstantType):
    """AST Expression for <time type>."""

    not_null: bool

    @model_validator(mode="after")
    def _check_time_type(self):
        self.require_feature(F.GV40)  # Temporal types: zoned datetime and zoned time
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class LocaltimeType(TemporalInstantType):
    """AST Expression for <localtime type>."""

    # 4.16.6.4 Temporal instant types: LOCAL TIME [...] Equivalent to TIME WITHOUT TIME ZONE

    not_null: bool

    @model_validator(mode="after")
    def _check_localtime_type(self):
        self.require_feature(F.GV39)  # Temporal types: date, local datetime and local time
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class ClosedGraphReferenceValueType(GraphReferenceValueType):
    """AST Expression for <closed graph reference value type>."""

    nested_graph_type_specification: NestedGraphTypeSpecification
    not_null: bool

    @model_validator(mode="after")
    def _check_closed_graph_reference_value_type(self):
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class OpenGraphReferenceValueType(GraphReferenceValueType):
    """AST Expression for <open graph reference value type>."""

    any: bool
    not_null: bool

    @model_validator(mode="after")
    def _check_open_graph_reference_value_type(self):
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class ClosedNodeReferenceValueType(NodeReferenceValueType):
    """AST Expression for <closed node reference value type>."""

    node_type_specification: NodeTypeSpecification
    not_null: bool

    @model_validator(mode="after")
    def _check_closed_node_reference_value_type(self):
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class OpenNodeReferenceValueType(NodeReferenceValueType):
    """AST Expression for <open node reference value type>."""

    any: bool
    not_null: bool

    @model_validator(mode="after")
    def _check_open_node_reference_value_type(self):
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class ClosedEdgeReferenceValueType(EdgeReferenceValueType):
    """AST Expression for <closed edge reference value type>."""

    edge_type_specification: EdgeTypeSpecification
    not_null: bool

    @model_validator(mode="after")
    def _check_closed_edge_reference_value_type(self):
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class OpenEdgeReferenceValueType(EdgeReferenceValueType):
    """AST Expression for <open edge reference value type>."""

    any: bool
    not_null: bool

    @model_validator(mode="after")
    def _check_open_edge_reference_value_type(self):
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class GraphReferenceValueExpression(ReferenceValueExpression):
    """AST Expression for <graph reference value expression>."""

    class _GraphGraphExpression(Expression):
        """Internal expression."""

        graph_expression: GraphExpression

    graph_reference_value_expression: _GraphGraphExpression | ValueExpressionPrimary

    @model_validator(mode="after")
    def _check_graph_reference_value_expression(self):
        self.require_feature(F.GV60)  # Graph reference value types
        return self


class BindingTableReferenceValueExpression(ReferenceValueExpression):
    """AST Expression for <binding table reference value expression>."""

    class _TableBindingTableExpression(Expression):
        """Internal expression."""

        binding_table_expression: BindingTableExpression

    binding_table_reference_value_expression: _TableBindingTableExpression | ValueExpressionPrimary

    @model_validator(mode="after")
    def _check_binding_table_reference_value_expression(self):
        self.require_feature(F.GV61)  # Binding table reference value types
        return self


NodeReferenceValueExpression: t.TypeAlias = ValueExpressionPrimary

EdgeReferenceValueExpression: t.TypeAlias = ValueExpressionPrimary


class PathValueConcatenation(PathValueExpression):
    """AST Expression for <path value concatenation>."""

    path_value_expression_1: PathValueExpression1
    path_value_primary: PathValuePrimary

    @model_validator(mode="after")
    def _check_path_value_concatenation(self):
        self.require_feature(F.GE06)
        return self


PathValueExpression1: t.TypeAlias = PathValueExpression

PathValuePrimary: t.TypeAlias = ValueExpressionPrimary


ListPrimary: t.TypeAlias = ListValueFunction | ValueExpressionPrimary

IndependentValueExpression: t.TypeAlias = NumericValueExpression

NumericValueExpressionDividend: t.TypeAlias = NumericValueExpression

NumericValueExpressionDivisor: t.TypeAlias = NumericValueExpression

GeneralLogarithmBase: t.TypeAlias = NumericValueExpression

GeneralLogarithmArgument: t.TypeAlias = NumericValueExpression

NumericValueExpressionBase: t.TypeAlias = NumericValueExpression

NumericValueExpressionExponent: t.TypeAlias = NumericValueExpression

StringLength: t.TypeAlias = NumericValueExpression


class CharacterStringValueExpression(StringValueExpression):
    """AST Expression for <character string value expression> and <character string."""

    list_character_string_value_expression: list[CharacterStringPrimary]


class ByteStringValueExpression(StringValueExpression):
    """AST Expression for <byte string value expression> and <byte string concatenation>."""

    list_byte_string_primary: list[ByteStringPrimary]


DatetimeValueExpression1: t.TypeAlias = DatetimeValueExpression

DatetimeValueExpression2: t.TypeAlias = DatetimeValueExpression


class DatetimeSubtraction(Expression):
    """AST Expression for <datetime subtraction>."""

    datetime_subtraction_parameters: DatetimeSubtractionParameters
    temporal_duration_qualifier: TemporalDurationQualifier | None


class DurationTerm(Expression):
    """AST Expression for <duration term>."""

    class _MultiplicativeFactor(Expression):
        """Internal expression."""

        operator: MultiplicativeOperator
        factor: Factor

    multiplicative_term: Term | None  # Optional multiplicative Term
    base: DurationFactor
    steps: list[_MultiplicativeFactor] | None


DurationValueExpression1: t.TypeAlias = DurationValueExpression

NodeReference: t.TypeAlias = ElementVariableReference

EdgeReference: t.TypeAlias = ElementVariableReference


class NodePattern(ElementPattern):
    """AST Expression for <node pattern>."""

    element_pattern_filler: ElementPatternFiller


class EdgePattern(ElementPattern):
    """Semantic marker for <edge pattern> in the Abstract Syntax Tree (AST)."""

    pass


class SimplifiedDefaultingLeft(SimplifiedPathPatternExpression):
    """AST Expression for <simplified defaulting left>."""

    simplified_contents: SimplifiedContents

    @model_validator(mode="after")
    def _check_simplified_defaulting_left(self):
        self.require_feature(F.G080)
        return self


class SimplifiedDefaultingUndirected(SimplifiedPathPatternExpression):
    """AST Expression for <simplified defaulting undirected>."""

    simplified_contents: SimplifiedContents

    @model_validator(mode="after")
    def _check_simplified_defaulting_undirected(self):
        self.require_feature(F.G039)
        return self


class SimplifiedDefaultingRight(SimplifiedPathPatternExpression):
    """AST Expression for <simplified defaulting right>."""

    simplified_contents: SimplifiedContents

    @model_validator(mode="after")
    def _check_simplified_defaulting_right(self):
        self.require_feature(F.G080)
        return self


class SimplifiedDefaultingLeftOrUndirected(SimplifiedPathPatternExpression):
    """AST Expression for <simplified defaulting left or undirected>."""

    simplified_contents: SimplifiedContents

    @model_validator(mode="after")
    def _check_simplified_defaulting_left_or_undirected(self):
        self.require_feature(F.G039)
        return self


class SimplifiedDefaultingUndirectedOrRight(SimplifiedPathPatternExpression):
    """AST Expression for <simplified defaulting undirected or right>."""

    simplified_contents: SimplifiedContents

    @model_validator(mode="after")
    def _check_simplified_defaulting_undirected_or_right(self):
        self.require_feature(F.G039)
        return self


class SimplifiedDefaultingLeftOrRight(SimplifiedPathPatternExpression):
    """AST Expression for <simplified defaulting left or right>."""

    simplified_contents: SimplifiedContents

    @model_validator(mode="after")
    def _check_simplified_defaulting_left_or_right(self):
        self.require_feature(F.G039)
        return self


class SimplifiedDefaultingAnyDirection(SimplifiedPathPatternExpression):
    """AST Expression for <simplified defaulting any direction>."""

    simplified_contents: SimplifiedContents

    @model_validator(mode="after")
    def _check_simplified_defaulting_any_direction(self):
        self.require_feature(F.G080)
        return self


class SimplifiedDirectionOverride(SimplifiedTertiary):
    """Semantic marker for <simplified direction override> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_simplified_direction_override(self):
        if not isinstance(
            self, SimplifiedOverrideLeft | SimplifiedOverrideRight | SimplifiedOverrideAnyDirection
        ):
            self.require_feature(F.G081)
        return self


class SimplifiedSecondary(SimplifiedTertiary):
    """Semantic marker for <simplified secondary> in the Abstract Syntax Tree (AST)."""

    pass


class SignedBinaryExactNumericType(BinaryExactNumericType):
    """AST Expression for <signed binary exact numeric type>."""

    class _Int8(Expression):
        """Internal expression."""

        pass

    class _Int16(Expression):
        """Internal expression."""

        pass

    class _Int32(Expression):
        """Internal expression."""

        pass

    class _Int64(Expression):
        """Internal expression."""

        pass

    class _Int128(Expression):
        """Internal expression."""

        pass

    class _Int256(Expression):
        """Internal expression."""

        pass

    class _Smallint(Expression):
        """Internal expression."""

        pass

    class _Int(Expression):
        """Internal expression."""

        precision: Precision | None

    class _Bigint(Expression):
        """Internal expression."""

        pass

    signed_type: _Int8 | _Int16 | _Int32 | _Int64 | _Int128 | _Int256 | _Smallint | _Int | _Bigint
    not_null: bool

    @model_validator(mode="after")
    def _check_signed_binary_exact_numeric_type(self):
        match self.signed_type:
            case SignedBinaryExactNumericType._Int8():
                self.require_feature(F.GV02)  # 8 bit signed integer numbers
            case SignedBinaryExactNumericType._Int16():
                self.require_feature(F.GV04)  # 16 bit signed integer numbers
            case SignedBinaryExactNumericType._Int32():
                self.require_feature(F.GV07)  # 32 bit signed integer numbers
            case SignedBinaryExactNumericType._Int64():
                self.require_feature(F.GV12)  # 64 bit signed integer numbers
            case SignedBinaryExactNumericType._Int128():
                self.require_feature(F.GV14)  # 128 bit signed integer numbers
            case SignedBinaryExactNumericType._Int256():
                self.require_feature(F.GV16)  # 256 bit signed integer numbers
            case SignedBinaryExactNumericType._Smallint():
                self.require_feature(F.GV18)  # Small signed integer numbers
            case SignedBinaryExactNumericType._Bigint():
                self.require_feature(F.GV19)  # Big signed integer numbers
            case SignedBinaryExactNumericType._Int(precision=p) if p is not None:
                self.require_feature(F.GV09)  # Specified integer number precision
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


class UnsignedBinaryExactNumericType(BinaryExactNumericType):
    """AST Expression for <unsigned binary exact numeric type>."""

    class _Uint8(Expression):
        """Internal expression."""

        pass

    class _Uint16(Expression):
        """Internal expression."""

        pass

    class _Uint32(Expression):
        """Internal expression."""

        pass

    class _Uint64(Expression):
        """Internal expression."""

        pass

    class _Uint128(Expression):
        """Internal expression."""

        pass

    class _Uint256(Expression):
        """Internal expression."""

        pass

    class _Usmallint(Expression):
        """Internal expression."""

        pass

    class _Uint(Expression):
        """Internal expression."""

        precision: Precision | None

    class _Ubigint(Expression):
        """Internal expression."""

        pass

    unsigned_type: (
        _Uint8 | _Uint16 | _Uint32 | _Uint64 | _Uint128 | _Uint256 | _Usmallint | _Uint | _Ubigint
    )
    not_null: bool

    @model_validator(mode="after")
    def _check_unsigned_binary_exact_numeric_type(self):
        match self.unsigned_type:
            case UnsignedBinaryExactNumericType._Uint8():
                self.require_feature(F.GV01)  # 8 bit unsigned integer numbers
            case UnsignedBinaryExactNumericType._Uint16():
                self.require_feature(F.GV03)  # 16 bit unsigned integer numbers
            case UnsignedBinaryExactNumericType._Usmallint():
                self.require_feature(F.GV05)  # Small unsigned integer numbers
            case UnsignedBinaryExactNumericType._Uint32():
                self.require_feature(F.GV06)  # 32 bit unsigned integer numbers
            case UnsignedBinaryExactNumericType._Uint():
                self.require_feature(F.GV08)  # Regular unsigned integer numbers
            case UnsignedBinaryExactNumericType._Ubigint():
                self.require_feature(F.GV10)  # Big unsigned integer numbers
            case UnsignedBinaryExactNumericType._Uint64():
                self.require_feature(F.GV11)  # 64 bit unsigned integer numbers
            case UnsignedBinaryExactNumericType._Uint128():
                self.require_feature(F.GV13)  # 128 bit unsigned integer numbers
            case UnsignedBinaryExactNumericType._Uint256():
                self.require_feature(F.GV15)  # 256 bit unsigned integer numbers
        if self.not_null:
            self.require_feature(F.GV90)  # Explicit value type nullability
        return self


ForItemSource: t.TypeAlias = ListValueExpression | BindingTableReferenceValueExpression

CardinalityExpressionArgument: t.TypeAlias = (
    BindingTableReferenceValueExpression
    | PathValueExpression
    | ListValueExpression
    | RecordExpression
)

PathElementListStart: t.TypeAlias = NodeReferenceValueExpression


CharacterStringPrimary: t.TypeAlias = ValueExpressionPrimary | CharacterStringFunction

TrimSource: t.TypeAlias = CharacterStringValueExpression

TrimCharacterString: t.TypeAlias = CharacterStringValueExpression

ByteStringPrimary: t.TypeAlias = ValueExpressionPrimary | ByteStringFunction


ByteStringTrimSource: t.TypeAlias = ByteStringValueExpression

TrimByteString: t.TypeAlias = ByteStringValueExpression

DurationTerm1: t.TypeAlias = DurationTerm


class FullEdgePattern(EdgePattern):
    """Semantic marker for <full edge pattern> in the Abstract Syntax Tree (AST)."""

    @model_validator(mode="after")
    def _check_full_edge_pattern(self):
        # Per ISO/IEC 39075:2024 §16.7: Without G043, conforming GQL shall
        # not contain a <full edge pattern> that is not <full edge any direction>,
        # <full edge pointing left>, or <full edge pointing right>.
        # Those three are mandatory; G043 adds the undirected/combined forms.
        if isinstance(
            self,
            FullEdgeUndirected
            | FullEdgeLeftOrUndirected
            | FullEdgeUndirectedOrRight
            | FullEdgeLeftOrRight,
        ):
            self.require_feature(F.G043)

        # GG:UE01 additionally gates the 3 tilde (undirected) full edge forms.
        # Databases with only directed edges (e.g. Neo4j) exclude these.
        if isinstance(
            self,
            FullEdgeUndirected | FullEdgeLeftOrUndirected | FullEdgeUndirectedOrRight,
        ):
            self.require_feature(F.GG_UE01)

        return self


class AbbreviatedEdgePattern(EdgePattern):
    """AST Expression for <abbreviated edge pattern>."""

    class PatternType(Enum):
        LEFT_ARROW = auto()
        TILDE = auto()
        RIGHT_ARROW = auto()
        LEFT_ARROW_TILDE = auto()
        TILDE_RIGHT_ARROW = auto()
        LEFT_MINUS_RIGHT = auto()
        MINUS_SIGN = auto()

    pattern: AbbreviatedEdgePattern.PatternType

    @model_validator(mode="after")
    def _check_abbreviated_edge_pattern(self):
        if self.pattern in [
            AbbreviatedEdgePattern.PatternType.MINUS_SIGN,
            AbbreviatedEdgePattern.PatternType.LEFT_ARROW,
            AbbreviatedEdgePattern.PatternType.RIGHT_ARROW,
        ]:
            self.require_feature(F.G044)
        else:
            self.require_feature(F.G045)

        # GG:UE02 additionally gates the 3 tilde (undirected) abbreviated forms.
        # Databases with only directed edges (e.g. Neo4j) exclude these.
        if self.pattern in [
            AbbreviatedEdgePattern.PatternType.TILDE,
            AbbreviatedEdgePattern.PatternType.LEFT_ARROW_TILDE,
            AbbreviatedEdgePattern.PatternType.TILDE_RIGHT_ARROW,
        ]:
            self.require_feature(F.GG_UE02)

        return self


class SimplifiedOverrideLeft(SimplifiedDirectionOverride):
    """AST Expression for <simplified override left>."""

    simplified_secondary: SimplifiedSecondary

    @model_validator(mode="after")
    def _check_simplified_override_left(self):
        self.require_feature(F.G082)
        return self


class SimplifiedOverrideUndirected(SimplifiedDirectionOverride):
    """AST Expression for <simplified override undirected>."""

    simplified_secondary: SimplifiedSecondary


class SimplifiedOverrideRight(SimplifiedDirectionOverride):
    """AST Expression for <simplified override right>."""

    simplified_secondary: SimplifiedSecondary

    @model_validator(mode="after")
    def _check_simplified_override_right(self):
        self.require_feature(F.G082)
        return self


class SimplifiedOverrideLeftOrUndirected(SimplifiedDirectionOverride):
    """AST Expression for <simplified override left or undirected>."""

    simplified_secondary: SimplifiedSecondary


class SimplifiedOverrideUndirectedOrRight(SimplifiedDirectionOverride):
    """AST Expression for <simplified override undirected or right>."""

    simplified_secondary: SimplifiedSecondary


class SimplifiedOverrideLeftOrRight(SimplifiedDirectionOverride):
    """AST Expression for <simplified override left or right>."""

    simplified_secondary: SimplifiedSecondary


class SimplifiedOverrideAnyDirection(SimplifiedDirectionOverride):
    """AST Expression for <simplified override any direction>."""

    simplified_secondary: SimplifiedSecondary

    @model_validator(mode="after")
    def _check_simplified_override_any_direction(self):
        self.require_feature(F.G082)
        return self


class SimplifiedNegation(SimplifiedSecondary):
    """AST Expression for <simplified negation>."""

    simplified_primary: SimplifiedPrimary


class SimplifiedPrimary(SimplifiedSecondary):
    """AST Expression for <simplified primary>."""

    class _LeftParenSimplifiedContentsRightParen(Expression):
        """Internal expression."""

        simplified_contents: SimplifiedContents

    simplified_primary: LabelName | _LeftParenSimplifiedContentsRightParen


class FullEdgePointingLeft(FullEdgePattern):
    """AST Expression for <full edge pointing left>."""

    element_pattern_filler: ElementPatternFiller


class FullEdgeUndirected(FullEdgePattern):
    """AST Expression for <full edge undirected>."""

    element_pattern_filler: ElementPatternFiller


class FullEdgePointingRight(FullEdgePattern):
    """AST Expression for <full edge pointing right>."""

    element_pattern_filler: ElementPatternFiller


class FullEdgeLeftOrUndirected(FullEdgePattern):
    """AST Expression for <full edge left or undirected>."""

    element_pattern_filler: ElementPatternFiller


class FullEdgeUndirectedOrRight(FullEdgePattern):
    """AST Expression for <full edge undirected or right>."""

    element_pattern_filler: ElementPatternFiller


class FullEdgeLeftOrRight(FullEdgePattern):
    """AST Expression for <full edge left or right>."""

    element_pattern_filler: ElementPatternFiller


class FullEdgeAnyDirection(FullEdgePattern):
    """AST Expression for <full edge any direction>."""

    element_pattern_filler: ElementPatternFiller


class WildcardLabel(LabelPrimary):
    """AST Expression for <wildcard label>."""

    @model_validator(mode="after")
    def _check_wildcard_label(self):
        self.require_feature(F.G074)
        return self


PropertySource: t.TypeAlias = (
    NodeReferenceValueExpression | EdgeReferenceValueExpression | RecordExpression
)

_PropertySourceExceptPropertyReference: t.TypeAlias = (
    ParenthesizedValueExpression
    | AggregateFunction
    | UnsignedNumericLiteral
    | BooleanLiteral
    | CharacterStringLiteral
    | ByteStringLiteral
    | TemporalLiteral
    | DurationLiteral
    | NullLiteral
    | ListValueConstructorByEnumeration
    | RecordConstructor
    | GeneralValueSpecification
    | PathValueConstructorByEnumeration
    | ValueQueryExpression
    | CaseExpression
    | CastSpecification
    | ElementIdFunction
    | LetValueExpression
    | BindingVariableReference
)

GraphPatternYieldItem: t.TypeAlias = ElementVariableReference | PathVariableReference


Result: t.TypeAlias = ResultExpression | NullLiteral

BooleanPredicand: t.TypeAlias = (
    ParenthesizedBooleanValueExpression | NonParenthesizedValueExpressionPrimary
)

ComparisonPredicand: t.TypeAlias = CommonValueExpression | BooleanPredicand


BooleanPrimary: t.TypeAlias = Predicate | BooleanPredicand

WhenOperand: t.TypeAlias = (
    NonParenthesizedValueExpressionPrimary
    | ComparisonPredicatePart2
    | NullPredicatePart2
    | ValueTypePredicatePart2
    | NormalizedPredicatePart2
    | DirectedPredicatePart2
    | LabeledPredicatePart2
    | SourcePredicatePart2
    | DestinationPredicatePart2
)

CaseOperand: t.TypeAlias = NonParenthesizedValueExpressionPrimary | ElementVariableReference

DateFunctionParameters: t.TypeAlias = DateString | RecordConstructor

DatetimeFunctionParameters: t.TypeAlias = DatetimeString | RecordConstructor

DurationFunctionParameters: t.TypeAlias = DurationString | RecordConstructor

TimeFunctionParameters: t.TypeAlias = TimeString | RecordConstructor

GraphName: t.TypeAlias = Identifier

BindingTableExpression: t.TypeAlias = (
    NestedBindingTableQuerySpecification
    | ObjectExpressionPrimary
    | BindingTableReference
    | ObjectNameOrBindingVariable
)

CastOperand: t.TypeAlias = ValueExpression | NullLiteral
