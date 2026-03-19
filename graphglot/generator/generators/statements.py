"""Generator functions for statement expressions (MATCH, RETURN, INSERT, etc.)."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.SimpleMatchStatement)
def generate_simple_match_statement(gen: Generator, expr: ast.SimpleMatchStatement) -> Fragment:
    return gen.seq(gen.keyword("MATCH"), gen.dispatch(expr.graph_pattern_binding_table))


@generates(ast.OptionalMatchStatement)
def generate_optional_match_statement(gen: Generator, expr: ast.OptionalMatchStatement) -> Fragment:
    return gen.seq(gen.keyword("OPTIONAL"), gen.dispatch(expr.optional_operand))


@generates(ast.OptionalOperand)
def generate_optional_operand(gen: Generator, expr: ast.OptionalOperand) -> Fragment:
    inner = expr.optional_operand
    if isinstance(inner, ast.SimpleMatchStatement):
        return gen.dispatch(inner)
    else:
        # MatchStatementBlock - wrap in braces
        return gen.braces(gen.dispatch(inner))


@generates(ast.MatchStatementBlock)
def generate_match_statement_block(gen: Generator, expr: ast.MatchStatementBlock) -> Fragment:
    return gen.join([gen.dispatch(stmt) for stmt in expr.list_match_statement], sep=" ")


@generates(ast.ReturnStatement)
def generate_return_statement(gen: Generator, expr: ast.ReturnStatement) -> Fragment:
    return gen.seq(gen.keyword("RETURN"), gen.dispatch(expr.return_statement_body))


@generates(ast.ReturnStatementBody)
def generate_return_statement_body(gen: Generator, expr: ast.ReturnStatementBody) -> Fragment:
    inner = expr.return_statement_body
    if isinstance(inner, ast.ReturnStatementBody._SetQuantifierAsteriskGroupByClause):
        parts: list[str | Fragment] = []
        if inner.set_quantifier:
            parts.append(gen.dispatch(inner.set_quantifier))
        parts.append("*")
        if inner.group_by_clause:
            parts.append(gen.dispatch(inner.group_by_clause))
        return gen.seq(*parts)
    elif isinstance(inner, ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause):
        parts = []
        if inner.set_quantifier:
            parts.append(gen.dispatch(inner.set_quantifier))
        parts.append(gen.dispatch(inner.return_item_list))
        if inner.group_by_clause:
            parts.append(gen.dispatch(inner.group_by_clause))
        return gen.seq(*parts)
    elif isinstance(inner, ast.ReturnStatementBody._NoBindings):
        return Fragment("NO BINDINGS")
    else:
        return gen.dispatch(inner)


@generates(ast.ReturnItemList)
def generate_return_item_list(gen: Generator, expr: ast.ReturnItemList) -> Fragment:
    return gen.join([gen.dispatch(item) for item in expr.list_return_item], sep=", ")


@generates(ast.ReturnItem)
def generate_return_item(gen: Generator, expr: ast.ReturnItem) -> Fragment:
    parts = [gen.dispatch(expr.aggregating_value_expression)]
    if expr.return_item_alias:
        parts.append(gen.dispatch(expr.return_item_alias))
    return gen.seq(*parts)


@generates(ast.ReturnItemAlias)
def generate_return_item_alias(gen: Generator, expr: ast.ReturnItemAlias) -> Fragment:
    return gen.seq("AS", gen.dispatch(expr.identifier))


@generates(ast.SetQuantifier)
def generate_set_quantifier(gen: Generator, expr: ast.SetQuantifier) -> Fragment:
    match expr.set_quantifier:
        case ast.SetQuantifier.Quantifier.DISTINCT:
            return Fragment("DISTINCT")
        case ast.SetQuantifier.Quantifier.ALL:
            return Fragment("ALL")


@generates(ast.FilterStatement)
def generate_filter_statement(gen: Generator, expr: ast.FilterStatement) -> Fragment:
    inner = expr.filter_statement
    if isinstance(inner, ast.WhereClause):
        return gen.seq(gen.keyword("FILTER"), gen.dispatch(inner))
    else:
        # SearchCondition - wrap in WHERE style
        return gen.seq(gen.keyword("FILTER"), gen.dispatch(inner))


@generates(ast.LetStatement)
def generate_let_statement(gen: Generator, expr: ast.LetStatement) -> Fragment:
    return gen.seq(gen.keyword("LET"), gen.dispatch(expr.let_variable_definition_list))


@generates(ast.LetVariableDefinitionList)
def generate_let_variable_definition_list(
    gen: Generator, expr: ast.LetVariableDefinitionList
) -> Fragment:
    return gen.join([gen.dispatch(d) for d in expr.list_let_variable_definition], sep=", ")


@generates(ast.LetVariableDefinition)
def generate_let_variable_definition(gen: Generator, expr: ast.LetVariableDefinition) -> Fragment:
    inner = expr.let_variable_definition
    if isinstance(inner, ast.ValueVariableDefinition):
        return gen.dispatch(inner)
    elif isinstance(inner, ast.LetVariableDefinition._BindingVariableValueExpression):
        return gen.seq(
            gen.dispatch(inner.binding_variable), "=", gen.dispatch(inner.value_expression)
        )
    else:
        return gen.dispatch(inner)


@generates(ast.ForStatement)
def generate_for_statement(gen: Generator, expr: ast.ForStatement) -> Fragment:
    parts: list[str | Fragment] = [gen.keyword("FOR"), gen.dispatch(expr.for_item)]
    if expr.for_ordinality_or_offset:
        parts.append(gen.dispatch(expr.for_ordinality_or_offset))
    return gen.seq(*parts)


@generates(ast.ForItem)
def generate_for_item(gen: Generator, expr: ast.ForItem) -> Fragment:
    return gen.seq(gen.dispatch(expr.for_item_alias), gen.dispatch(expr.for_item_source))


@generates(ast.ForItemAlias)
def generate_for_item_alias(gen: Generator, expr: ast.ForItemAlias) -> Fragment:
    return gen.seq(gen.dispatch(expr.binding_variable), "IN")


@generates(ast.ForOrdinalityOrOffset)
def generate_for_ordinality_or_offset(gen: Generator, expr: ast.ForOrdinalityOrOffset) -> Fragment:
    mode = "ORDINALITY" if expr.mode == ast.ForOrdinalityOrOffset.Mode.ORDINALITY else "OFFSET"
    return gen.seq("WITH", mode, gen.dispatch(expr.binding_variable))


@generates(ast.OrderByAndPageStatement)
def generate_order_by_and_page_statement(
    gen: Generator, expr: ast.OrderByAndPageStatement
) -> Fragment:
    inner = expr.order_by_and_page_statement
    if isinstance(inner, ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause):
        parts = [gen.dispatch(inner.order_by_clause)]
        if inner.offset_clause:
            parts.append(gen.dispatch(inner.offset_clause))
        if inner.limit_clause:
            parts.append(gen.dispatch(inner.limit_clause))
        return gen.seq(*parts, sep=gen.sep())
    elif isinstance(inner, ast.OrderByAndPageStatement._OffsetClauseLimitClause):
        parts = [gen.dispatch(inner.offset_clause)]
        if inner.limit_clause:
            parts.append(gen.dispatch(inner.limit_clause))
        return gen.seq(*parts, sep=gen.sep())
    elif isinstance(inner, ast.LimitClause):
        return gen.dispatch(inner)
    else:
        return gen.dispatch(inner)


@generates(ast.InsertStatement)
def generate_insert_statement(gen: Generator, expr: ast.InsertStatement) -> Fragment:
    return gen.seq(gen.keyword("INSERT"), gen.dispatch(expr.insert_graph_pattern))


@generates(ast.SetStatement)
def generate_set_statement(gen: Generator, expr: ast.SetStatement) -> Fragment:
    return gen.seq(gen.keyword("SET"), gen.dispatch(expr.set_item_list))


@generates(ast.SetItemList)
def generate_set_item_list(gen: Generator, expr: ast.SetItemList) -> Fragment:
    return gen.join([gen.dispatch(item) for item in expr.list_set_item], sep=", ")


@generates(ast.SetPropertyItem)
def generate_set_property_item(gen: Generator, expr: ast.SetPropertyItem) -> Fragment:
    return gen.seq(
        f"{gen.dispatch(expr.binding_variable_reference)}.{gen.dispatch(expr.property_name)}",
        "=",
        gen.dispatch(expr.value_expression),
    )


@generates(ast.SetAllPropertiesItem)
def generate_set_all_properties_item(gen: Generator, expr: ast.SetAllPropertiesItem) -> Fragment:
    props: str | Fragment
    if expr.property_key_value_pair_list:
        props = gen.dispatch(expr.property_key_value_pair_list)
    else:
        props = ""
    return gen.seq(gen.dispatch(expr.binding_variable_reference), "=", gen.braces(props))


@generates(ast.SetLabelItem)
def generate_set_label_item(gen: Generator, expr: ast.SetLabelItem) -> Fragment:
    return Fragment(
        f"{gen.dispatch(expr.binding_variable_reference)}:{gen.dispatch(expr.label_name)}"
    )


@generates(ast.RemoveStatement)
def generate_remove_statement(gen: Generator, expr: ast.RemoveStatement) -> Fragment:
    return gen.seq(gen.keyword("REMOVE"), gen.dispatch(expr.remove_item_list))


@generates(ast.RemoveItemList)
def generate_remove_item_list(gen: Generator, expr: ast.RemoveItemList) -> Fragment:
    return gen.join([gen.dispatch(item) for item in expr.list_remove_item], sep=", ")


@generates(ast.RemovePropertyItem)
def generate_remove_property_item(gen: Generator, expr: ast.RemovePropertyItem) -> Fragment:
    return Fragment(
        f"{gen.dispatch(expr.binding_variable_reference)}.{gen.dispatch(expr.property_name)}"
    )


@generates(ast.RemoveLabelItem)
def generate_remove_label_item(gen: Generator, expr: ast.RemoveLabelItem) -> Fragment:
    return Fragment(
        f"{gen.dispatch(expr.binding_variable_reference)}:{gen.dispatch(expr.label_name)}"
    )


@generates(ast.DeleteStatement)
def generate_delete_statement(gen: Generator, expr: ast.DeleteStatement) -> Fragment:
    parts: list[str | Fragment] = []
    if expr.mode == ast.DeleteStatement.Mode.DETACH:
        parts.append(gen.keyword("DETACH"))
    parts.append(gen.keyword("DELETE"))
    parts.append(gen.dispatch(expr.delete_item_list))
    return gen.seq(*parts)


@generates(ast.DeleteItemList)
def generate_delete_item_list(gen: Generator, expr: ast.DeleteItemList) -> Fragment:
    return gen.join([gen.dispatch(item) for item in expr.list_delete_item], sep=", ")


@generates(ast.SelectStatement)
def generate_select_statement(gen: Generator, expr: ast.SelectStatement) -> Fragment:
    parts: list[str | Fragment] = [gen.keyword("SELECT")]
    if expr.set_quantifier:
        parts.append(gen.dispatch(expr.set_quantifier))

    if isinstance(expr.projection, ast.Asterisk):
        parts.append("*")
    else:
        parts.append(gen.dispatch(expr.projection))

    if expr.body:
        clauses = expr.body
        if clauses.select_statement_body:
            parts.append(gen.dispatch(clauses.select_statement_body))
        if clauses.where_clause:
            parts.append(gen.dispatch(clauses.where_clause))
        if clauses.group_by_clause:
            parts.append(gen.dispatch(clauses.group_by_clause))
        if clauses.having_clause:
            parts.append(gen.dispatch(clauses.having_clause))
        if clauses.order_by_clause:
            parts.append(gen.dispatch(clauses.order_by_clause))
        if clauses.offset_clause:
            parts.append(gen.dispatch(clauses.offset_clause))
        if clauses.limit_clause:
            parts.append(gen.dispatch(clauses.limit_clause))

    return gen.seq(*parts, sep=gen.sep())


@generates(ast.SelectItemList)
def generate_select_item_list(gen: Generator, expr: ast.SelectItemList) -> Fragment:
    return gen.dispatch_list(expr.list_select_item)


@generates(ast.SelectItem)
def generate_select_item(gen: Generator, expr: ast.SelectItem) -> Fragment:
    parts = [gen.dispatch(expr.aggregating_value_expression)]
    if expr.select_item_alias:
        parts.append(gen.dispatch(expr.select_item_alias))
    return gen.seq(*parts)


@generates(ast.SelectItemAlias)
def generate_select_item_alias(gen: Generator, expr: ast.SelectItemAlias) -> Fragment:
    return gen.seq("AS", gen.dispatch(expr.identifier))


@generates(ast.SelectStatementBody)
def generate_select_statement_body(gen: Generator, expr: ast.SelectStatementBody) -> Fragment:
    return gen.seq("FROM", gen.dispatch(expr.select_statement_body))


@generates(ast.SelectGraphMatchList)
def generate_select_graph_match_list(gen: Generator, expr: ast.SelectGraphMatchList) -> Fragment:
    return gen.dispatch_list(expr.list_select_graph_match)


@generates(ast.SelectGraphMatch)
def generate_select_graph_match(gen: Generator, expr: ast.SelectGraphMatch) -> Fragment:
    return gen.seq(gen.dispatch(expr.graph_expression), gen.dispatch(expr.match_statement))


@generates(ast.CallProcedureStatement)
def generate_call_procedure_statement(gen: Generator, expr: ast.CallProcedureStatement) -> Fragment:
    parts: list[str | Fragment] = []
    if expr.optional:
        parts.append(gen.keyword("OPTIONAL"))
    parts.append("CALL")
    parts.append(gen.dispatch(expr.procedure_call))
    return gen.seq(*parts)


@generates(ast.InlineProcedureCall)
def generate_inline_procedure_call(gen: Generator, expr: ast.InlineProcedureCall) -> Fragment:
    parts = []
    if expr.variable_scope_clause:
        parts.append(gen.dispatch(expr.variable_scope_clause))
    parts.append(gen.dispatch(expr.nested_procedure_specification))
    return gen.seq(*parts)


@generates(ast.NamedProcedureCall)
def generate_named_procedure_call(gen: Generator, expr: ast.NamedProcedureCall) -> Fragment:
    call_parts = [gen.dispatch(expr.procedure_reference)]
    if expr.procedure_argument_list is not None:
        args = gen.dispatch(expr.procedure_argument_list) if expr.procedure_argument_list else ""
        call_parts.append(gen.parens(args))
    result = gen.seq(*call_parts, sep="")
    if expr.yield_clause:
        result = gen.seq(result, gen.dispatch(expr.yield_clause))
    return result


@generates(ast.CatalogObjectParentReference)
def generate_catalog_object_parent_reference(
    gen: Generator, expr: ast.CatalogObjectParentReference
) -> Fragment:
    ref = expr.catalog_object_parent_reference
    if isinstance(ref, list):
        return gen.join([gen.dispatch(ident) for ident in ref], sep=".")
    return gen.dispatch(ref)


@generates(ast.ProcedureReference)
def generate_procedure_reference(gen: Generator, expr: ast.ProcedureReference) -> Fragment:
    return gen.dispatch(expr)


@generates(ast.CatalogProcedureParentAndName)
def generate_catalog_procedure_parent_and_name(
    gen: Generator, expr: ast.CatalogProcedureParentAndName
) -> Fragment:
    if expr.catalog_object_parent_reference:
        parent = gen.dispatch(expr.catalog_object_parent_reference)
        name = gen.dispatch(expr.procedure_name)
        return gen.seq(parent, Fragment("."), name, sep="")
    return gen.dispatch(expr.procedure_name)


@generates(ast.ProcedureArgumentList)
def generate_procedure_argument_list(gen: Generator, expr: ast.ProcedureArgumentList) -> Fragment:
    return gen.join([gen.dispatch(arg) for arg in expr.list_procedure_argument], sep=", ")
