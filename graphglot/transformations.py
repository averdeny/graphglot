"""Post-parse AST transformations.

Transformation functions take an Expression tree and return a rewritten tree.
They are declared on Dialect subclasses via the TRANSFORMATIONS class variable.
"""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.ast.base import Expression
from graphglot.ast.cypher import CypherWithStatement
from graphglot.typing.types import TypeKind

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

            if stmt.where_clause is None:
                withs.append(stmt)
                current_segment = []
                continue

            projected, alias_map = _analyze_projection(stmt)
            losing = (
                set()
                if projected is None
                else {
                    n.binding_variable.name
                    for n in stmt.where_clause.dfs()
                    if isinstance(n, ast.BindingVariableReference)
                    and n.binding_variable.name not in projected
                }
            )

            if not losing:
                # No scope loss — filter after NEXT with raw WHERE
                withs.append(_strip_where(stmt))
                current_segment = [_make_filter_stmt(stmt.where_clause)]

            else:
                # Scope loss — inline aliases so the condition only uses
                # pre-WITH binding variables, then decide placement.
                inlined_where = _inline_aliases(stmt.where_clause, alias_map)
                has_obsl = stmt.order_by_and_page_statement is not None

                if not has_obsl:
                    # Pre-filter: move filter before the RETURN
                    segments[-1].append(_make_filter_stmt(inlined_where))
                    withs.append(_strip_where(stmt))
                    current_segment = []

                else:
                    # Carry-through: widen projection with extra vars, filter
                    # after NEXT, narrow back to original projection.
                    withs.append(_widen_projection(stmt, losing))
                    segments.append([_make_filter_stmt(inlined_where)])
                    withs.append(_narrow_projection(stmt))
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


# ===========================================================================
# WITH...WHERE scope-loss helpers
# ===========================================================================


def _make_filter_stmt(where: ast.WhereClause) -> ast.FilterStatement:
    """Build a FilterStatement from a WhereClause, preserving span tokens."""
    fs = ast.FilterStatement._construct(filter_statement=where)
    if getattr(where, "_start_token", None) is not None:
        fs.__dict__["_start_token"] = where._start_token
    if getattr(where, "_end_token", None) is not None:
        fs.__dict__["_end_token"] = where._end_token
    return fs


def _analyze_projection(
    stmt: CypherWithStatement,
) -> tuple[set[str] | None, dict[str, Expression]]:
    """Projected names and alias→source map.

    Returns ``(None, {})`` for star projections (all names pass through).
    """
    inner = stmt.return_statement_body.return_statement_body
    if not hasattr(inner, "return_item_list") or inner.return_item_list is None:
        return None, {}
    names: set[str] = set()
    alias_map: dict[str, Expression] = {}
    for item in inner.return_item_list.list_return_item:
        if item.return_item_alias is not None:
            name = item.return_item_alias.identifier.name
            names.add(name)
            alias_map[name] = item.aggregating_value_expression
        else:
            for sub in item.aggregating_value_expression.dfs():
                if isinstance(sub, ast.BindingVariableReference):
                    names.add(sub.binding_variable.name)
                    break
    return names, alias_map


def _inline_aliases(
    where: ast.WhereClause,
    alias_map: dict[str, Expression],
) -> ast.WhereClause:
    """Replace alias references in *where* with their source expressions."""
    if not alias_map:
        return where
    where_copy: ast.WhereClause = t.cast(ast.WhereClause, where.deep_copy())
    for node in list(where_copy.dfs()):
        if not isinstance(node, ast.BindingVariableReference):
            continue
        name = node.binding_variable.name
        if name in alias_map:
            replacement = alias_map[name].deep_copy()
            _replace_in_parent(node, replacement)
    return where_copy


def _strip_where(stmt: CypherWithStatement) -> CypherWithStatement:
    """Return a copy of *stmt* with where_clause removed."""
    return CypherWithStatement._construct(
        return_statement_body=stmt.return_statement_body,
        order_by_and_page_statement=stmt.order_by_and_page_statement,
        where_clause=None,
    )


def _wrap_var_as_ave(name: str) -> ast.ArithmeticValueExpression:
    """Wrap a variable name in the ArithmeticValueExpression chain the parser produces."""
    bvr = ast.BindingVariableReference._construct(
        binding_variable=ast.Identifier._construct(name=name),
    )
    af = ast.ArithmeticFactor._construct(arithmetic_primary=bvr)
    at = ast.ArithmeticTerm._construct(base=af, steps=None)
    return ast.ArithmeticValueExpression._construct(base=at, steps=None)


def _widen_projection(
    stmt: CypherWithStatement,
    extra_vars: set[str],
) -> CypherWithStatement:
    """Add extra variables to the projection.  Keeps OBSL, drops WHERE."""
    inner = stmt.return_statement_body.return_statement_body
    inner_cls = ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause
    if not isinstance(
        inner, inner_cls
    ):  # pragma: no cover - guaranteed: scope loss requires non-star
        return _strip_where(stmt)
    items = list(inner.return_item_list.list_return_item)
    for var_name in sorted(extra_vars):
        items.append(
            ast.ReturnItem._construct(
                aggregating_value_expression=_wrap_var_as_ave(var_name),
                return_item_alias=None,
            )
        )
    new_ril = ast.ReturnItemList._construct(list_return_item=items)
    new_inner = inner_cls._construct(
        set_quantifier=inner.set_quantifier,
        return_item_list=new_ril,
        group_by_clause=inner.group_by_clause,
    )
    new_body = ast.ReturnStatementBody._construct(
        return_statement_body=new_inner,
    )
    return CypherWithStatement._construct(
        return_statement_body=new_body,
        order_by_and_page_statement=stmt.order_by_and_page_statement,
        where_clause=None,
    )


def _narrow_projection(stmt: CypherWithStatement) -> CypherWithStatement:
    """Build a RETURN that re-projects just the original names (by reference).

    After the widened RETURN + NEXT, only projected names + extra vars are
    in scope.  The narrowing RETURN references each original projected name
    as a bare variable (not the source expression) so it works in post-NEXT
    scope, then drops the extra vars.
    """
    projected, _ = _analyze_projection(stmt)
    if projected is None:
        # Star projection — just pass through
        return CypherWithStatement._construct(
            return_statement_body=stmt.return_statement_body,
            order_by_and_page_statement=None,
            where_clause=None,
        )
    items = [
        ast.ReturnItem._construct(
            aggregating_value_expression=_wrap_var_as_ave(name),
            return_item_alias=None,
        )
        for name in sorted(projected)
    ]
    inner_cls = ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause
    new_inner = inner_cls._construct(
        set_quantifier=None,
        return_item_list=ast.ReturnItemList._construct(list_return_item=items),
        group_by_clause=None,
    )
    new_body = ast.ReturnStatementBody._construct(return_statement_body=new_inner)
    return CypherWithStatement._construct(
        return_statement_body=new_body,
        order_by_and_page_statement=None,
        where_clause=None,
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


# ===========================================================================
# resolve_ambiguous — replace AmbiguousValueExpression with concrete GQL types
# ===========================================================================


def resolve_ambiguous(tree: Expression) -> Expression:
    """Replace ambiguous expression nodes with concrete GQL types.

    Runs type annotation internally, then walks bottom-up to replace
    ``ConcatenationValueExpression``, ``ArithmeticValueExpression``, and
    ``ArithmeticAbsoluteValueFunction`` with their concrete GQL equivalents
    when the resolved type is unambiguous.
    """
    from graphglot.typing import TypeAnnotator

    TypeAnnotator().annotate(tree)
    return _resolve_ambiguous_nodes(tree)


def _resolve_ambiguous_nodes(tree: Expression) -> Expression:
    """Replace ambiguous nodes using existing ``_resolved_type`` annotations."""
    for node in reversed(list(tree.dfs())):
        replacement = _try_resolve(node)
        if replacement is None:
            continue
        # Preserve span tokens
        if getattr(node, "_start_token", None) is not None:
            replacement.__dict__["_start_token"] = node._start_token
        if getattr(node, "_end_token", None) is not None:
            replacement.__dict__["_end_token"] = node._end_token
        replacement._resolved_type = node._resolved_type
        _replace_in_parent(node, replacement)
    return tree


def _try_resolve(node: Expression) -> Expression | None:
    """Dispatch to the appropriate resolution function."""
    if isinstance(node, ast.ConcatenationValueExpression):
        return _resolve_concatenation(node)
    if isinstance(node, ast.ArithmeticValueExpression):
        return _resolve_arithmetic(node)
    if isinstance(node, ast.ArithmeticAbsoluteValueFunction):
        return _resolve_abs(node)
    return None


# -- Concatenation ----------------------------------------------------------


def _resolve_concatenation(node: ast.ConcatenationValueExpression) -> Expression | None:
    rt = node._resolved_type
    if rt is None or rt.is_unknown or rt.is_union:
        return None
    kind = rt.kind
    if kind == TypeKind.STRING:
        return ast.CharacterStringValueExpression._construct(
            list_character_string_value_expression=node.operands,
        )
    if kind == TypeKind.BYTE_STRING:
        return ast.ByteStringValueExpression._construct(
            list_byte_string_primary=node.operands,
        )
    if kind == TypeKind.PATH:
        return ast.PathValueExpression._construct(
            list_path_value_primary=node.operands,
        )
    if kind == TypeKind.LIST:
        return ast.ListValueExpression._construct(
            list_list_primary=node.operands,
        )
    return None


# -- Arithmetic -------------------------------------------------------------


def _resolve_arithmetic(node: ast.ArithmeticValueExpression) -> Expression | None:
    # Only transform when there are actual arithmetic operations
    if not node.steps and not node.base.steps:
        return None
    rt = node._resolved_type
    if rt is None or rt.is_unknown or rt.is_union:
        return None
    if rt.is_numeric:
        return _resolve_arithmetic_numeric(node)
    if rt.kind == TypeKind.DURATION:
        return _resolve_arithmetic_duration(node)
    if rt.is_temporal:
        return _resolve_arithmetic_datetime(node)
    if rt.kind == TypeKind.LIST:
        return _resolve_arithmetic_list(node)
    return None


def _resolve_arithmetic_numeric(
    node: ast.ArithmeticValueExpression,
) -> ast.NumericValueExpression:
    base_term = _at_to_term(node.base)
    steps = None
    if node.steps:
        steps = [
            ast.NumericValueExpression._SignedTerm._construct(
                sign=s.sign,
                term=_at_to_term(s.term),
            )
            for s in node.steps
        ]
    return ast.NumericValueExpression._construct(base=base_term, steps=steps)


def _resolve_arithmetic_duration(
    node: ast.ArithmeticValueExpression,
) -> ast.DurationValueExpression:
    base_dt = _at_to_duration_term(node.base)
    steps = None
    if node.steps:
        steps = [
            ast.DurationValueExpression._SignedDurationTerm._construct(
                sign=s.sign,
                duration_term=_at_to_duration_term(s.term),
            )
            for s in node.steps
        ]
    return ast.DurationValueExpression._construct(base=base_dt, steps=steps)


def _resolve_arithmetic_datetime(
    node: ast.ArithmeticValueExpression,
) -> ast.DatetimeValueExpression | None:
    # Multiplicative steps on datetime don't make sense — skip
    if node.base.steps:
        return None
    datetime_primary = node.base.base.arithmetic_primary
    steps = None
    if node.steps:
        steps = []
        for s in node.steps:
            # Multiplicative steps on duration in datetime context — skip
            if s.term.steps:
                return None
            duration_factor = _af_to_duration_factor(s.term.base)
            duration_term = ast.DurationTerm._construct(
                multiplicative_term=None,
                base=duration_factor,
                steps=None,
            )
            steps.append(
                ast.DatetimeValueExpression._SignedDurationTerm._construct(
                    sign=s.sign,
                    duration_term=duration_term,
                )
            )
    return ast.DatetimeValueExpression._construct(base=datetime_primary, steps=steps)


def _resolve_arithmetic_list(
    node: ast.ArithmeticValueExpression,
) -> ast.ListValueExpression | None:
    """Convert list+list ArithmeticValueExpression → ListValueExpression."""
    # Only transform concat (+), not difference (-)
    if not all(s.sign == ast.Sign.PLUS_SIGN for s in node.steps):
        return None
    primaries = []
    p = _at_to_list_primary(node.base)
    if p is None:
        return None
    primaries.append(p)
    for step in node.steps:
        p = _at_to_list_primary(step.term)
        if p is None:
            return None
        primaries.append(p)
    return ast.ListValueExpression._construct(list_list_primary=primaries)


def _at_to_list_primary(at: ast.ArithmeticTerm) -> ast.Expression | None:
    """Extract inner primary from ArithmeticTerm for list concat."""
    if at.steps:
        return None  # multiplicative steps → not simple list concat
    ap = at.base.arithmetic_primary
    # Unwrap unnecessary ParenthesizedValueExpression added by Cypher parser
    if isinstance(ap, ast.ParenthesizedValueExpression):
        ap = ap.value_expression
    return ap


# -- ABS --------------------------------------------------------------------


def _resolve_abs(node: ast.ArithmeticAbsoluteValueFunction) -> Expression | None:
    rt = node._resolved_type
    if rt is None or rt.is_unknown or rt.is_union:
        return None

    # After bottom-up processing, inner may already be converted.
    # If not (e.g. bare ABS(x) with no arithmetic steps), the converters
    # handle the no-steps case correctly — they produce steps=None.
    inner = node.arithmetic_value_expression

    if rt.is_numeric:
        if isinstance(inner, ast.NumericValueExpression):
            nve = inner
        elif isinstance(inner, ast.ArithmeticValueExpression):
            nve = _resolve_arithmetic_numeric(inner)
        else:
            return None
        return ast.AbsoluteValueExpression._construct(numeric_value_expression=nve)

    if rt.kind == TypeKind.DURATION:
        if isinstance(inner, ast.DurationValueExpression):
            dve = inner
        elif isinstance(inner, ast.ArithmeticValueExpression):
            dve = _resolve_arithmetic_duration(inner)
        else:
            return None
        return ast.DurationAbsoluteValueFunction._construct(
            duration_value_expression=dve,
        )

    return None


# -- Structural converters --------------------------------------------------


def _af_to_factor(af: ast.ArithmeticFactor) -> ast.Factor:
    return ast.Factor._construct(sign=af.sign, numeric_primary=af.arithmetic_primary)


def _af_to_duration_factor(af: ast.ArithmeticFactor) -> ast.DurationFactor:
    return ast.DurationFactor._construct(sign=af.sign, duration_primary=af.arithmetic_primary)


def _at_to_term(at: ast.ArithmeticTerm) -> ast.Term:
    steps = None
    if at.steps:
        steps = [
            ast.Term._MultiplicativeFactor._construct(
                operator=s.operator,
                factor=_af_to_factor(s.factor),
            )
            for s in at.steps
        ]
    return ast.Term._construct(base=_af_to_factor(at.base), steps=steps)


def _at_to_duration_term(at: ast.ArithmeticTerm) -> ast.DurationTerm:
    steps = None
    if at.steps:
        steps = [
            ast.DurationTerm._MultiplicativeFactor._construct(
                operator=s.operator,
                factor=_af_to_factor(s.factor),
            )
            for s in at.steps
        ]
    return ast.DurationTerm._construct(
        multiplicative_term=None,
        base=_af_to_duration_factor(at.base),
        steps=steps,
    )


def _replace_in_parent(old: Expression, new: Expression) -> None:
    """Replace *old* with *new* in old's parent node."""
    parent = old._parent
    if parent is None:
        return
    key = old._arg_key
    if key is None:
        return
    idx = old._index
    if idx is not None:
        current_list = getattr(parent, key)
        current_list[idx] = new
    else:
        parent.__dict__[key] = new
    new._parent = parent
    new._arg_key = key
    new._index = idx
