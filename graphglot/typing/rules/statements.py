"""Type rules for statement-level scope propagation."""

from __future__ import annotations

from graphglot.ast import expressions as ast
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


def _bind_return_aliases(annotator, statement) -> None:
    """Extract RETURN item aliases and bind their resolved types in scope."""
    for prs in statement.find_all(ast.PrimitiveResultStatement):
        inner = prs.primitive_result_statement
        if not hasattr(inner, "return_statement"):
            continue
        body = inner.return_statement.return_statement_body.return_statement_body
        if not isinstance(body, _ReturnItemsWithGroupBy):
            continue
        for item in body.return_item_list.list_return_item:
            alias = item.return_item_alias
            if alias is None:
                continue
            name = alias.identifier.name
            expr_type = item.aggregating_value_expression._resolved_type
            if expr_type is not None and not expr_type.is_unknown:
                annotator.current_scope.bind(name, expr_type, item)
