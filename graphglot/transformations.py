"""Post-parse AST transformations.

Transformation functions take an Expression tree and return a rewritten tree.
They are declared on Dialect subclasses via the TRANSFORMATIONS class variable.
"""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.ast.base import Expression
from graphglot.ast.cypher import (
    CypherChainedComparison,
    CypherPatternPredicate,
    CypherWithStatement,
    StringMatchPredicate,
)
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


# ===========================================================================
# rewrite_cypher_predicates — Cypher predicates → GQL equivalents
# ===========================================================================


def rewrite_cypher_predicates(tree: Expression) -> Expression:
    """Rewrite Cypher-specific predicate nodes into standard GQL equivalents.

    Walks the tree bottom-up and replaces:
    - ``CypherChainedComparison`` → AND chain of ``ComparisonPredicate``
    - ``StringMatchPredicate`` (STARTS WITH / ENDS WITH) → LEFT/RIGHT + comparison
    - ``CypherPatternPredicate`` → ``ExistsPredicate``

    CONTAINS is left untouched (no GQL equivalent).
    """
    for node in reversed(list(tree.dfs())):
        replacement: Expression | None = None
        if isinstance(node, CypherChainedComparison):
            replacement = _rewrite_chained_comparison(node)
        elif isinstance(node, StringMatchPredicate):
            replacement = _rewrite_string_match(node)
        elif isinstance(node, CypherPatternPredicate):
            replacement = _rewrite_pattern_predicate(node)

        if replacement is not None:
            if getattr(node, "_start_token", None) is not None:
                replacement.__dict__["_start_token"] = node._start_token
            if getattr(node, "_end_token", None) is not None:
                replacement.__dict__["_end_token"] = node._end_token
            _replace_in_parent(node, replacement)
    return tree


def _rewrite_chained_comparison(node: CypherChainedComparison) -> Expression:
    """``1 < n.num < 3`` → ``(1 < n.num AND n.num < 3)``.

    The parser shares the middle operand between adjacent comparisons
    (e.g. ``n.num`` is the same object in both ``1 < n.num`` and
    ``n.num < 3``).  We deep-copy the ``comparison_predicand`` of every
    comparison after the first so each ``ComparisonPredicate`` owns its
    own subtree.
    """
    factors = []
    for i, cmp in enumerate(node.comparisons):
        if i > 0:
            # The LHS of this comparison is shared with the RHS of the
            # previous one — deep-copy to give each its own subtree.
            cmp = ast.ComparisonPredicate._construct(
                comparison_predicand=cmp.comparison_predicand.deep_copy(),
                comparison_predicate_part_2=cmp.comparison_predicate_part_2,
            )
        bt = ast.BooleanTest._construct(boolean_primary=cmp, truth_value=None)
        bf = ast.BooleanFactor._construct(not_=False, boolean_test=bt)
        factors.append(bf)
    bool_term = ast.BooleanTerm._construct(list_boolean_factor=factors)
    bve = ast.BooleanValueExpression._construct(boolean_term=bool_term, ops=None)
    return ast.ParenthesizedBooleanValueExpression._construct(
        boolean_value_expression=bve,
    )


def _rewrite_string_match(node: StringMatchPredicate) -> Expression | None:
    """``x STARTS WITH 'A'`` → ``LEFT(x, CHAR_LENGTH('A')) = 'A'``.

    Returns None for CONTAINS (no GQL equivalent).
    """
    if node.kind == StringMatchPredicate.MatchKind.CONTAINS:
        return None

    mode = (
        ast.SubstringFunction.Mode.LEFT
        if node.kind == StringMatchPredicate.MatchKind.STARTS_WITH
        else ast.SubstringFunction.Mode.RIGHT
    )

    # rhs is used in two places (CHAR_LENGTH and comparison RHS),
    # so deep-copy to avoid shared parent pointers.
    rhs_for_len = node.rhs.deep_copy()
    rhs_for_cmp = node.rhs.deep_copy()

    lhs_csve = ast.CharacterStringValueExpression._construct(
        list_character_string_value_expression=[node.lhs],
    )
    rhs_csve = ast.CharacterStringValueExpression._construct(
        list_character_string_value_expression=[rhs_for_len],
    )

    # CHAR_LENGTH(rhs) wrapped into NumericValueExpression
    char_len = ast.CharLengthExpression._construct(
        character_string_value_expression=rhs_csve,
    )
    factor = ast.Factor._construct(sign=None, numeric_primary=char_len)
    term = ast.Term._construct(base=factor, steps=None)
    nve = ast.NumericValueExpression._construct(base=term, steps=None)

    # LEFT/RIGHT(lhs, CHAR_LENGTH(rhs))
    substr = ast.SubstringFunction._construct(
        mode=mode,
        character_string_value_expression=lhs_csve,
        string_length=nve,
    )

    # substr = rhs
    part2 = ast.ComparisonPredicatePart2._construct(
        comp_op=ast.ComparisonPredicatePart2.CompOp.EQUALS,
        comparison_predicand=rhs_for_cmp,
    )
    return ast.ComparisonPredicate._construct(
        comparison_predicand=substr,
        comparison_predicate_part_2=part2,
    )


def _rewrite_pattern_predicate(node: CypherPatternPredicate) -> Expression:
    """``(n)-[:KNOWS]->()`` → ``EXISTS { (n)-[:KNOWS]->() }``."""
    ppl = ast.PathPatternList._construct(list_path_pattern=[node.pattern])
    gp = ast.GraphPattern._construct(
        match_mode=None,
        path_pattern_list=ppl,
        keep_clause=None,
        graph_pattern_where_clause=None,
    )
    egp = ast.ExistsPredicate._ExistsGraphPattern._construct(graph_pattern=gp)
    return ast.ExistsPredicate._construct(exists_predicate=egp)


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
