"""Generator functions for clause expressions (WHERE, ORDER BY, LIMIT, etc.)."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.WhereClause)
def generate_where_clause(gen: Generator, expr: ast.WhereClause) -> Fragment:
    return gen.seq(gen.keyword("WHERE"), gen.dispatch(expr.search_condition))


@generates(ast.GraphPatternWhereClause)
def generate_graph_pattern_where_clause(
    gen: Generator, expr: ast.GraphPatternWhereClause
) -> Fragment:
    return gen.seq(gen.keyword("WHERE"), gen.dispatch(expr.search_condition))


@generates(ast.OrderByClause)
def generate_order_by_clause(gen: Generator, expr: ast.OrderByClause) -> Fragment:
    return gen.seq(gen.keyword("ORDER BY"), gen.dispatch(expr.sort_specification_list))


@generates(ast.SortSpecificationList)
def generate_sort_specification_list(gen: Generator, expr: ast.SortSpecificationList) -> Fragment:
    return gen.join([gen.dispatch(s) for s in expr.list_sort_specification], sep=", ")


@generates(ast.SortSpecification)
def generate_sort_specification(gen: Generator, expr: ast.SortSpecification) -> Fragment:
    # Parser is lossless: ordering_specification is None when the user
    # omitted the keyword.  Emit exactly what the user wrote — the
    # cross-dialect materialization step inserts an explicit keyword
    # when source and target dialects disagree on the default, so
    # fidelity here preserves semantics in every case.
    parts = [gen.dispatch(expr.sort_key)]
    if expr.ordering_specification is not None:
        parts.append(gen.dispatch(expr.ordering_specification))
    if expr.null_ordering:
        parts.append(gen.dispatch(expr.null_ordering))
    return gen.seq(*parts)


@generates(ast.OrderingSpecification)
def generate_ordering_specification(gen: Generator, expr: ast.OrderingSpecification) -> Fragment:
    match expr.ordering_specification:
        case ast.OrderingSpecification.Order.ASC:
            return Fragment("ASC")
        case ast.OrderingSpecification.Order.DESC:
            return Fragment("DESC")


@generates(ast.NullOrdering)
def generate_null_ordering(gen: Generator, expr: ast.NullOrdering) -> Fragment:
    match expr.null_ordering:
        case ast.NullOrdering.Order.NULLS_FIRST:
            return Fragment("NULLS FIRST")
        case ast.NullOrdering.Order.NULLS_LAST:
            return Fragment("NULLS LAST")


@generates(ast.LimitClause)
def generate_limit_clause(gen: Generator, expr: ast.LimitClause) -> Fragment:
    return gen.seq(gen.keyword("LIMIT"), gen.dispatch(expr.non_negative_integer_specification))


@generates(ast.OffsetClause)
def generate_offset_clause(gen: Generator, expr: ast.OffsetClause) -> Fragment:
    return gen.seq(gen.keyword("OFFSET"), gen.dispatch(expr.non_negative_integer_specification))


@generates(ast.GroupByClause)
def generate_group_by_clause(gen: Generator, expr: ast.GroupByClause) -> Fragment:
    return gen.seq(gen.keyword("GROUP BY"), gen.dispatch(expr.grouping_element_list))


@generates(ast.GroupingElementList)
def generate_grouping_element_list(gen: Generator, expr: ast.GroupingElementList) -> Fragment:
    inner = expr.grouping_element_list
    if isinstance(inner, ast.EmptyGroupingSet):
        return gen.dispatch(inner)
    else:
        # list of grouping elements
        return gen.join([gen.dispatch(e) for e in inner], sep=", ")


@generates(ast.EmptyGroupingSet)
def generate_empty_grouping_set(gen: Generator, expr: ast.EmptyGroupingSet) -> Fragment:
    return Fragment("()")


@generates(ast.YieldClause)
def generate_yield_clause(gen: Generator, expr: ast.YieldClause) -> Fragment:
    return gen.seq(gen.keyword("YIELD"), gen.dispatch(expr.yield_item_list))


@generates(ast.YieldItemList)
def generate_yield_item_list(gen: Generator, expr: ast.YieldItemList) -> Fragment:
    return gen.join([gen.dispatch(item) for item in expr.list_yield_item], sep=", ")


@generates(ast.YieldItem)
def generate_yield_item(gen: Generator, expr: ast.YieldItem) -> Fragment:
    parts = [gen.dispatch(expr.yield_item_name)]
    if expr.yield_item_alias:
        parts.append(gen.dispatch(expr.yield_item_alias))
    return gen.seq(*parts)


@generates(ast.YieldItemAlias)
def generate_yield_item_alias(gen: Generator, expr: ast.YieldItemAlias) -> Fragment:
    return gen.seq("AS", gen.dispatch(expr.binding_variable))


@generates(ast.UseGraphClause)
def generate_use_graph_clause(gen: Generator, expr: ast.UseGraphClause) -> Fragment:
    return gen.seq("USE", gen.dispatch(expr.graph_expression))


@generates(ast.KeepClause)
def generate_keep_clause(gen: Generator, expr: ast.KeepClause) -> Fragment:
    return gen.seq("KEEP", gen.dispatch(expr.path_pattern_prefix))


@generates(ast.HavingClause)
def generate_having_clause(gen: Generator, expr: ast.HavingClause) -> Fragment:
    return gen.seq("HAVING", gen.dispatch(expr.search_condition))


@generates(ast.GraphPatternYieldClause)
def generate_graph_pattern_yield_clause(
    gen: Generator, expr: ast.GraphPatternYieldClause
) -> Fragment:
    return gen.seq(gen.keyword("YIELD"), gen.dispatch(expr.graph_pattern_yield_item_list))


@generates(ast.GraphPatternYieldItemList)
def generate_graph_pattern_yield_item_list(
    gen: Generator, expr: ast.GraphPatternYieldItemList
) -> Fragment:
    inner = expr.graph_pattern_yield_item_list
    if isinstance(inner, ast.GraphPatternYieldItemList._NoBindings):
        return Fragment("NO BINDINGS")
    return gen.join([gen.dispatch(item) for item in inner], sep=", ")


@generates(ast.AtSchemaClause)
def generate_at_schema_clause(gen: Generator, expr: ast.AtSchemaClause) -> Fragment:
    return gen.seq("AT", gen.dispatch(expr.schema_reference))


@generates(ast.VariableScopeClause)
def generate_variable_scope_clause(gen: Generator, expr: ast.VariableScopeClause) -> Fragment:
    if expr.binding_variable_reference_list:
        return gen.parens(gen.dispatch(expr.binding_variable_reference_list))
    return Fragment("()")


@generates(ast.BindingVariableReferenceList)
def generate_binding_variable_reference_list(
    gen: Generator, expr: ast.BindingVariableReferenceList
) -> Fragment:
    return gen.join([gen.dispatch(ref) for ref in expr.list_binding_variable_reference], sep=", ")
