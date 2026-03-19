"""Post-parse AST transformations.

Transformation functions take an Expression tree and return a rewritten tree.
They are declared on Dialect subclasses via the TRANSFORMATIONS class variable.
"""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.ast.base import Expression
from graphglot.ast.cypher import CypherWithStatement

Transformation = t.Callable[[Expression], Expression]


def with_to_next(tree: Expression) -> Expression:
    """Rewrite CypherWithStatement nodes into RETURN...NEXT chains.

    Walks the tree to find ``AmbientLinearQueryStatement`` nodes whose inner
    ``SimpleLinearQueryStatement`` contains ``CypherWithStatement`` entries.
    Each such ALQS is rewritten into a ``StatementBlock`` with a chain of
    ``NextStatement`` nodes — the GQL equivalent of Cypher's multi-part WITH.

    The transformation is safe to apply multiple times (idempotent) because
    the output contains no ``CypherWithStatement`` nodes.
    """
    for node in list(tree.dfs()):
        if not isinstance(node, ast.AmbientLinearQueryStatement):
            continue

        inner = node.ambient_linear_query_statement
        if not isinstance(
            inner,
            ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement,
        ):
            continue

        slqs = inner.simple_linear_query_statement
        if slqs is None:
            continue

        stmts = slqs.list_simple_query_statement
        if not any(isinstance(s, CypherWithStatement) for s in stmts):
            continue

        block = _rewrite_alqs(stmts, inner.primitive_result_statement)

        # Replace in the tree. The ALQS sits inside a CQE as
        # left_composite_query_primary. The StatementBlock must replace
        # the CQE (not the ALQS) because StatementBlock is not a
        # LinearQueryStatement.
        cqe_parent = node._parent  # CompositeQueryExpression
        if cqe_parent is None:
            # ALQS is the root (unusual) — return block directly
            return block

        grandparent = cqe_parent._parent
        if grandparent is None:
            # CQE is the root — return block directly
            return block

        # Replace the CQE in its grandparent using __dict__ to bypass
        # Skip validation (consistent with _construct usage).
        key = cqe_parent._arg_key
        if key is None:  # pragma: no cover
            return block
        idx = cqe_parent._index
        if idx is not None:
            current_list = getattr(grandparent, key)
            current_list[idx] = block
            block._parent = grandparent
            block._arg_key = key
            block._index = idx
        else:
            grandparent.__dict__[key] = block
            block._parent = grandparent
            block._arg_key = key
            block._index = None
        return tree

    return tree


def _rewrite_alqs(
    stmts: list[ast.SimpleQueryStatement],
    original_prs: ast.PrimitiveResultStatement,
) -> ast.StatementBlock:
    """Build a StatementBlock from split statement segments and withs."""
    # Split statements at CypherWithStatement boundaries
    segments: list[list[ast.SimpleQueryStatement]] = []
    withs: list[CypherWithStatement] = []
    current_segment: list[ast.SimpleQueryStatement] = []

    for stmt in stmts:
        if isinstance(stmt, CypherWithStatement):
            segments.append(current_segment)
            withs.append(stmt)
            # If the WITH owns a WHERE clause, prepend a FilterStatement
            # to the next segment so it appears after the NEXT keyword.
            if stmt.where_clause is not None:
                fs = ast.FilterStatement._construct(
                    filter_statement=stmt.where_clause,
                )
                # Propagate span tokens from the WhereClause so that
                # diagnostics on the synthetic FilterStatement can report
                # line/col instead of None.
                wc = stmt.where_clause
                if getattr(wc, "_start_token", None) is not None:
                    fs.__dict__["_start_token"] = wc._start_token
                if getattr(wc, "_end_token", None) is not None:
                    fs.__dict__["_end_token"] = wc._end_token
                current_segment = [fs]
            else:
                current_segment = []
        else:
            current_segment.append(stmt)

    # Remaining statements after the last WITH
    segments.append(current_segment)

    # segments[0]  = before first WITH
    # segments[i+1] = after withs[i]
    # segments[-1]  = after last WITH (before RETURN)

    # Build the final ALQS: last segment + original PRS
    chain_alqs = _build_alqs(segments[-1], original_prs)

    # Build NextStatements from bottom up
    next_statements: list[ast.NextStatement] = []
    final_next = _build_next_statement(chain_alqs)
    next_statements.append(final_next)

    # Work backwards through intermediate withs
    for i in range(len(withs) - 1, 0, -1):
        prs = _with_to_prs(withs[i])
        alqs = _build_alqs(segments[i], prs)
        next_statements.append(_build_next_statement(alqs))

    next_statements.reverse()

    # First segment + first WITH → root statement
    first_prs = _with_to_prs(withs[0])
    root_alqs = _build_alqs(segments[0], first_prs)
    root_cqe = _wrap_in_cqe(root_alqs)

    return ast.StatementBlock._construct(
        statement=root_cqe,
        list_next_statement=next_statements,
    )


def _with_to_prs(with_stmt: CypherWithStatement) -> ast.PrimitiveResultStatement:
    """Convert a CypherWithStatement into a PrimitiveResultStatement."""
    ret = ast.ReturnStatement._construct(
        return_statement_body=with_stmt.return_statement_body,
    )
    ret_obps = ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement._construct(
        return_statement=ret,
        order_by_and_page_statement=with_stmt.order_by_and_page_statement,
    )
    return ast.PrimitiveResultStatement._construct(
        primitive_result_statement=ret_obps,
    )


def _build_alqs(
    stmts: list[ast.SimpleQueryStatement],
    prs: ast.PrimitiveResultStatement,
) -> ast.AmbientLinearQueryStatement:
    """Build an AmbientLinearQueryStatement from statements and a PRS."""
    slqs: ast.SimpleLinearQueryStatement | None = None
    if stmts:
        slqs = ast.SimpleLinearQueryStatement._construct(
            list_simple_query_statement=stmts,
        )

    slqs_prs = ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement
    inner = slqs_prs._construct(
        simple_linear_query_statement=slqs,
        primitive_result_statement=prs,
    )
    return ast.AmbientLinearQueryStatement._construct(
        ambient_linear_query_statement=inner,
    )


def _wrap_in_cqe(alqs: ast.AmbientLinearQueryStatement) -> ast.CompositeQueryExpression:
    """Wrap an ALQS in a CompositeQueryExpression (Statement)."""
    return ast.CompositeQueryExpression._construct(
        left_composite_query_primary=alqs,
        query_conjunction_elements=None,
    )


def _build_next_statement(alqs: ast.AmbientLinearQueryStatement) -> ast.NextStatement:
    """Build a NextStatement wrapping an ALQS."""
    cqe = _wrap_in_cqe(alqs)
    return ast.NextStatement._construct(
        yield_clause=None,
        statement=cqe,
    )
