"""Type rules for statement-level scope propagation."""

from __future__ import annotations

from graphglot.ast import expressions as ast
from graphglot.ast.cypher import CypherWithStatement
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType

_ReturnItemsWithGroupBy = ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause


@type_rule(ast.StatementBlock)
def type_statement_block(annotator, expr):
    """Propagate RETURN alias types across NEXT boundaries.

    After annotating each segment, extract alias→type from RETURN items
    and bind them in scope so the next segment can resolve them.
    """
    annotator.annotate_child(expr.statement)
    _bind_return_aliases(annotator, expr.statement)

    if expr.list_next_statement:
        for next_stmt in expr.list_next_statement:
            if next_stmt.yield_clause:
                annotator.annotate_child(next_stmt.yield_clause)
            annotator.annotate_child(next_stmt.statement)
            next_stmt._resolved_type = GqlType.unknown()
            _bind_return_aliases(annotator, next_stmt.statement)

    return GqlType.unknown()


@type_rule(CypherWithStatement)
def type_cypher_with_statement(annotator, expr):
    """Bind WITH projection aliases in scope (Cypher-form analog of NEXT boundary).

    When ``with_to_next`` has *not* run (Neo4j reads in the un-normalized
    AST), a ``CypherWithStatement`` plays the role of a NEXT segment
    boundary inside a single ``SimpleLinearQueryStatement``: its
    projection aliases must be visible to downstream clauses.  Without
    this rule, aliases like ``nodes`` in
    ``WITH collect(a) AS nodes`` would be invisible to ``RETURN
    size(nodes)`` and ``resolve_ambiguous`` couldn't rewrite the size
    call to ``CARDINALITY``.

    Order matters: bind aliases *after* annotating the projection (so
    the alias has a resolved type) but *before* annotating the WHERE /
    ORDER BY (where the alias may be referenced — e.g. ``WITH list AS l
    WHERE size(l) > 0``).
    """
    annotator.annotate_child(expr.return_statement_body)
    _bind_return_item_aliases(annotator, expr.return_statement_body)
    if expr.order_by_and_page_statement is not None:
        annotator.annotate_child(expr.order_by_and_page_statement)
    if expr.where_clause is not None:
        annotator.annotate_child(expr.where_clause)
    return GqlType.unknown()


def _bind_return_item_aliases(annotator, return_statement_body) -> None:
    """Bind each ``expr AS alias`` from a return statement body's projection."""
    body = return_statement_body.return_statement_body
    if not isinstance(body, _ReturnItemsWithGroupBy):
        return
    for item in body.return_item_list.list_return_item:
        alias = item.return_item_alias
        if alias is None:
            continue
        name = alias.identifier.name
        expr_type = item.aggregating_value_expression._resolved_type
        if expr_type is not None and not expr_type.is_unknown:
            annotator.current_scope.bind(name, expr_type, item)


def _bind_return_aliases(annotator, statement) -> None:
    """Extract RETURN item aliases from any PRS in *statement* and bind them."""
    for prs in statement.find_all(ast.PrimitiveResultStatement):
        inner = prs.primitive_result_statement
        if not hasattr(inner, "return_statement"):
            continue
        _bind_return_item_aliases(annotator, inner.return_statement.return_statement_body)
