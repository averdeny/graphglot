"""Structural validation rules (always enforced, not feature-gated).

duplicate-alias                    — Duplicate column aliases in RETURN/WITH
union-column-mismatch              — UNION branches with different column names
mixed-query-conjunction            — Mixing different conjunctions in one CQE
mixed-focused-ambient              — Mixing focused (USE) and ambient statements
nested-aggregation                 — Aggregate function containing another aggregate
aggregation-in-non-return-context  — Aggregate outside RETURN/SELECT/ORDER BY
same-pattern-node-edge-conflict    — Same variable as node and edge in one pattern
boolean-operand-type               — Non-boolean operands to AND/OR/XOR/NOT
orderby-aggregate-without-groupby  — Aggregate in ORDER BY without GROUP BY
non-constant-skip-limit            — Non-constant expression in SKIP/LIMIT
invalid-merge-pattern              — Invalid MERGE relationship pattern
exists-no-update                   — Data-modifying statement inside EXISTS
type-mismatch                      — Incompatible operand types in concat/arithmetic
"""

from __future__ import annotations

import typing as t

from graphglot.analysis.models import AnalysisContext, SemanticDiagnostic
from graphglot.analysis.rules._registry import structural_rule
from graphglot.analysis.rules.scope_rules import semantic_type
from graphglot.ast import expressions as ast
from graphglot.typing.types import GqlType, TypeKind

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_return_body_inner(
    body: ast.ReturnStatementBody,
) -> ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause | None:
    """Extract the inner variant that contains a return item list, if present."""
    inner = body.return_statement_body
    if isinstance(inner, ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause):
        return inner
    return None


def _extract_column_names(branch: ast.Expression) -> list[str] | None:
    """Extract ordered column alias names from a composite query branch.

    Returns *None* when the branch uses ``RETURN *`` (can't validate without scope).
    """
    prs = t.cast(
        ast.PrimitiveResultStatement | None,
        branch.find_first(ast.PrimitiveResultStatement),
    )
    if prs is None:
        return None
    stmt = prs.primitive_result_statement
    if not isinstance(stmt, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement):
        return None
    body = stmt.return_statement.return_statement_body
    inner = _get_return_body_inner(body)
    if inner is None:
        return None  # RETURN * or NO BINDINGS
    names: list[str] = []
    for item in inner.return_item_list.list_return_item:
        if item.return_item_alias is not None:
            names.append(item.return_item_alias.identifier.name)
        else:
            names.append("")  # un-aliased column
    return names


def _conjunction_identity(
    conj: ast.SetOperator | ast.QueryConjunction._Otherwise,
) -> tuple[str, str]:
    """Return a comparable identity for a query conjunction.

    SetOperator → (operator_type.name, quantifier_or_none),
    _Otherwise  → ("OTHERWISE", "").
    """
    if isinstance(conj, ast.SetOperator):
        q = ""
        if conj.set_quantifier is not None:
            q = conj.set_quantifier.set_quantifier.name
        return (conj.set_operator_type.name, q)
    return ("OTHERWISE", "")


# ---------------------------------------------------------------------------
# duplicate-alias — §4.15.4: Duplicate column aliases in RETURN/WITH
# ---------------------------------------------------------------------------


@structural_rule("duplicate-alias")
def check_duplicate_column_aliases(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect duplicate aliases in RETURN/WITH clauses."""
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.ReturnStatementBody):
        body = t.cast(ast.ReturnStatementBody, node)
        inner = _get_return_body_inner(body)
        if inner is None:
            continue
        seen: set[str] = set()
        for item in inner.return_item_list.list_return_item:
            if item.return_item_alias is None:
                continue
            name = item.return_item_alias.identifier.name
            if name in seen:
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="duplicate-alias",
                        message=f"Duplicate column alias '{name}' in RETURN/WITH clause.",
                        node=item,
                    )
                )
            else:
                seen.add(name)

    return diagnostics


# ---------------------------------------------------------------------------
# union-column-mismatch — §14.2 SR 10.a.v: UNION column mismatch
# ---------------------------------------------------------------------------


@structural_rule("union-column-mismatch")
def check_union_column_mismatch(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect UNION branches with different column names."""
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.CompositeQueryExpression):
        cqe = t.cast(ast.CompositeQueryExpression, node)
        if not cqe.query_conjunction_elements:
            continue
        left_cols = _extract_column_names(cqe.left_composite_query_primary)
        if left_cols is None:
            continue
        for element in cqe.query_conjunction_elements:
            # Only check set operators (UNION/EXCEPT/INTERSECT), not OTHERWISE.
            conj = element.query_conjunction.query_conjunction
            if not isinstance(conj, ast.SetOperator):
                continue
            right_cols = _extract_column_names(element.composite_query_primary)
            if right_cols is None:
                continue
            if left_cols != right_cols:
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="union-column-mismatch",
                        message=(
                            f"UNION branches have different columns: {left_cols} vs {right_cols}."
                        ),
                        node=element,
                    )
                )

    return diagnostics


# ---------------------------------------------------------------------------
# mixed-query-conjunction — §14.2 SR 3: all conjunctions in a CQE must match
# ---------------------------------------------------------------------------


@structural_rule("mixed-query-conjunction")
def check_mixed_query_conjunction(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect mixing of different query conjunctions in the same CQE (§14.2 SR 3)."""
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.CompositeQueryExpression):
        cqe = t.cast(ast.CompositeQueryExpression, node)
        if not cqe.query_conjunction_elements or len(cqe.query_conjunction_elements) < 2:
            continue
        first_id: tuple[str, str] | None = None
        for element in cqe.query_conjunction_elements:
            conj = element.query_conjunction.query_conjunction
            cid = _conjunction_identity(conj)
            if first_id is None:
                first_id = cid
            elif cid != first_id:
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="mixed-query-conjunction",
                        message="Cannot mix different query conjunctions in the same query.",
                        node=element,
                    )
                )
                break

    return diagnostics


# ---------------------------------------------------------------------------
# mixed-focused-ambient — §9.2 SR 5 / §14.2 SR 4: focused and ambient
# statements must not be mixed in the same block or composite query
# ---------------------------------------------------------------------------

_FOCUSED = (ast.FocusedLinearQueryStatement, ast.FocusedLinearDataModifyingStatement)
_AMBIENT = (ast.AmbientLinearQueryStatement, ast.AmbientLinearDataModifyingStatement)


def _is_focused(node: ast.Expression) -> bool | None:
    """True=focused, False=ambient, None=neither (e.g. catalog-modifying)."""
    if isinstance(node, _FOCUSED):
        return True
    if isinstance(node, _AMBIENT):
        return False
    # StatementBlock: Statement may be a CompositeQueryExpression wrapping a linear query.
    if isinstance(node, ast.CompositeQueryExpression):
        return _is_focused(node.left_composite_query_primary)
    return None


def _check_mixed(stmts: t.Sequence[ast.Expression], diagnostics: list[SemanticDiagnostic]) -> None:
    first: bool | None = None
    for stmt in stmts:
        classification = _is_focused(stmt)
        if classification is None:
            continue
        if first is None:
            first = classification
        elif classification != first:
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="mixed-focused-ambient",
                    message="Cannot mix focused (USE) and ambient statements in the same block.",
                    node=stmt,
                )
            )
            break


@structural_rule("mixed-focused-ambient")
def check_mixed_focused_ambient(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect mixing focused and ambient statements (§9.2 SR 5, §14.2 SR 4).

    Only checks StatementBlock (NEXT boundaries).  §14.2 SR 4 (UNION/OTHERWISE)
    is already enforced by the parser which rejects mixed focused/ambient branches.
    """
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.StatementBlock):
        sblk = t.cast(ast.StatementBlock, node)
        if not sblk.list_next_statement:
            continue
        stmts = [sblk.statement, *(ns.statement for ns in sblk.list_next_statement)]
        _check_mixed(stmts, diagnostics)

    return diagnostics


# ---------------------------------------------------------------------------
# nested-aggregation — §20.9 SR 4: aggregate shall not contain an aggregate
# ---------------------------------------------------------------------------


@structural_rule("nested-aggregation")
def check_nested_aggregation(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect nested aggregate functions like count(count(*)) (§20.9 SR 4)."""
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.AggregateFunction):
        agg = t.cast(ast.AggregateFunction, node)
        # Walk _parent chain — if any ancestor is also AggregateFunction, it's nested.
        parent = agg._parent
        while parent is not None:
            if isinstance(parent, ast.AggregateFunction):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="nested-aggregation",
                        message="Aggregate function cannot contain another aggregate.",
                        node=agg,
                    )
                )
                break
            parent = parent._parent

    return diagnostics


# ---------------------------------------------------------------------------
# aggregation-in-non-return-context — §20.1 CR 4: aggregates only in
# RETURN items, SELECT items, or sort keys
# ---------------------------------------------------------------------------

_VALID_AGGREGATE_CONTEXTS = (
    ast.ReturnItem,
    ast.SortSpecification,
    ast.SelectItem,
)


@structural_rule("aggregation-in-non-return-context")
def check_aggregation_in_non_return_context(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect aggregate functions outside RETURN/SELECT/ORDER BY (§20.1 CR 4)."""
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.AggregateFunction):
        agg = t.cast(ast.AggregateFunction, node)
        # Walk _parent chain to find a valid containing context.
        valid = False
        parent = agg._parent
        while parent is not None:
            if isinstance(parent, _VALID_AGGREGATE_CONTEXTS):
                valid = True
                break
            parent = parent._parent
        if not valid:
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="aggregation-in-non-return-context",
                    message="Aggregate function not allowed outside RETURN/SELECT/ORDER BY.",
                    node=agg,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# same-pattern-node-edge-conflict — §16.4 SR 5: node variable name shall not
# equal edge variable name within the same graph pattern
# ---------------------------------------------------------------------------


def _shallow_fillers(gp: ast.GraphPattern) -> t.Iterator[ast.ElementPatternFiller]:
    """Yield ElementPatternFiller nodes within *gp* without crossing nested GraphPatterns.

    §16.4 SR 5 says "without an intervening instance of <graph pattern>", so we must
    not descend into sub-patterns (e.g. EXISTS { MATCH ... } or pattern comprehensions).
    """
    stack = list(gp.children())
    while stack:
        child = stack.pop()
        if isinstance(child, ast.ElementPatternFiller):
            yield child
        elif isinstance(child, ast.GraphPattern):
            # Nested graph pattern boundary — do not descend.
            continue
        else:
            stack.extend(child.children())


@structural_rule("same-pattern-node-edge-conflict")
def check_same_pattern_node_edge_conflict(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect same variable used as node and edge in one graph pattern (§16.4 SR 5)."""
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.GraphPattern):
        gp = t.cast(ast.GraphPattern, node)
        node_vars: set[str] = set()
        edge_vars: set[str] = set()

        for filler in _shallow_fillers(gp):
            decl = filler.element_variable_declaration
            if decl is None:
                continue
            name = decl.element_variable.name
            # Determine node vs edge by checking filler's parent.
            parent = filler._parent
            if isinstance(parent, ast.NodePattern):
                node_vars.add(name)
            elif isinstance(parent, ast.FullEdgePattern):
                edge_vars.add(name)

        conflicts = node_vars & edge_vars
        for name in sorted(conflicts):
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="same-pattern-node-edge-conflict",
                    message=(
                        f"Variable '{name}' used as both node and edge in the same graph pattern."
                    ),
                    node=gp,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# boolean-operand-type — §20.20 SR 3: boolean operators require boolean operands
# ---------------------------------------------------------------------------


def _is_definitely_not_boolean(resolved: GqlType | None) -> bool:
    """True when the type is known and definitely not boolean."""
    if resolved is None or resolved.is_unknown or resolved.is_error:
        return False
    if resolved.kind in (TypeKind.BOOLEAN, TypeKind.ANY, TypeKind.NULL):
        return False
    if resolved.is_union:
        return not any(m.kind == TypeKind.BOOLEAN for m in (resolved.union_members or ()))
    return True


def _boolean_operand_type(factor: ast.BooleanFactor) -> GqlType | None:
    """Get the semantic type of a BooleanFactor's actual content.

    Grammar wrappers (BooleanFactor, BooleanTest) are annotated as BOOLEAN
    by the TypeAnnotator because of their grammar role.  We need to reach
    through to ``boolean_primary`` to get the actual operand type.

    For compound expressions (lists, records) ``semantic_type`` walks too
    deep — use the primary's own ``_resolved_type`` when it is concrete.
    """
    bp = factor.boolean_test.boolean_primary
    resolved = bp._resolved_type
    if resolved is not None and not resolved.is_unknown:
        return resolved
    return semantic_type(bp)


def _boolean_term_operand_type(term: ast.BooleanTerm) -> GqlType | None:
    """Get the semantic type of a BooleanTerm's actual content.

    A single-factor BooleanTerm is just a grammar wrapper — extract the
    factor's type.  A multi-factor term (with AND) is boolean by definition.
    """
    if len(term.list_boolean_factor) == 1:
        return _boolean_operand_type(term.list_boolean_factor[0])
    # Multi-factor means AND is present → result is boolean
    return None


@structural_rule("boolean-operand-type")
def check_boolean_operand_type(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect non-boolean operands to AND/OR/XOR/NOT (§20.20 SR 3)."""
    diagnostics: list[SemanticDiagnostic] = []

    # NOT operands (BooleanFactor with not_=True)
    for node in ctx.expression.find_all(ast.BooleanFactor):
        factor = t.cast(ast.BooleanFactor, node)
        if not factor.not_:
            continue
        inner_type = _boolean_operand_type(factor)
        if _is_definitely_not_boolean(inner_type):
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="boolean-operand-type",
                    message=f"NOT requires a boolean operand, got {inner_type}.",
                    node=factor,
                )
            )

    # AND operands (BooleanTerm with >1 factors)
    for node in ctx.expression.find_all(ast.BooleanTerm):
        term = t.cast(ast.BooleanTerm, node)
        if len(term.list_boolean_factor) < 2:
            continue
        for factor in term.list_boolean_factor:
            factor_type = _boolean_operand_type(factor)
            if _is_definitely_not_boolean(factor_type):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="boolean-operand-type",
                        message=f"AND requires boolean operands, got {factor_type}.",
                        node=factor,
                    )
                )

    # OR/XOR operands (BooleanValueExpression with ops)
    for node in ctx.expression.find_all(ast.BooleanValueExpression):
        bve = t.cast(ast.BooleanValueExpression, node)
        if not bve.ops:
            continue
        first_type = _boolean_term_operand_type(bve.boolean_term)
        if _is_definitely_not_boolean(first_type):
            op_name = bve.ops[0].operator.name
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="boolean-operand-type",
                    message=f"{op_name} requires boolean operands, got {first_type}.",
                    node=bve.boolean_term,
                )
            )
        for op in bve.ops:
            op_type = _boolean_term_operand_type(op.boolean_term)
            if _is_definitely_not_boolean(op_type):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="boolean-operand-type",
                        message=f"{op.operator.name} requires boolean operands, got {op_type}.",
                        node=op,
                    )
                )

    return diagnostics


# ---------------------------------------------------------------------------
# orderby-aggregate-without-groupby — §14.10 SR 4.c.i.A.V: aggregate in
# ORDER BY requires both GROUP BY and aggregate in RETURN items
# ---------------------------------------------------------------------------

_ReturnWithOrderBy = ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement
_ReturnItemsWithGroupBy = ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause


@structural_rule("orderby-aggregate-without-groupby")
def check_orderby_aggregate_without_groupby(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect aggregate functions in ORDER BY without GROUP BY (§14.10 SR 4)."""
    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.PrimitiveResultStatement):
        prs = t.cast(ast.PrimitiveResultStatement, node)
        stmt = prs.primitive_result_statement
        if not isinstance(stmt, _ReturnWithOrderBy):
            continue
        order_by = stmt.order_by_and_page_statement
        if order_by is None:
            continue

        body = stmt.return_statement.return_statement_body.return_statement_body
        has_group_by = (
            isinstance(body, _ReturnItemsWithGroupBy) and body.group_by_clause is not None
        )
        has_return_agg = isinstance(body, _ReturnItemsWithGroupBy) and any(
            body.return_item_list.find_all(ast.AggregateFunction)
        )

        # Per §14.10 SR 4.c.i.A.V: aggregates in ORDER BY require BOTH
        # GROUP BY present AND at least one return item with an aggregate.
        if has_group_by and has_return_agg:
            continue

        for spec in order_by.find_all(ast.SortSpecification):
            spec = t.cast(ast.SortSpecification, spec)
            if any(spec.find_all(ast.AggregateFunction)):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="orderby-aggregate-without-groupby",
                        message="Aggregate function in ORDER BY requires GROUP BY.",
                        node=spec,
                    )
                )

    return diagnostics


# ---------------------------------------------------------------------------
# Helpers — Cypher arithmetic unwrapping
# ---------------------------------------------------------------------------


def _unwrap_arithmetic(val: ast.Expression) -> ast.Expression:
    """Unwrap Cypher arithmetic wrapper chain to reach the inner primary.

    Returns the wrapper itself if any level has operations (steps),
    indicating a true arithmetic expression rather than a plain wrapper.
    """
    if isinstance(val, ast.ArithmeticValueExpression):
        if val.steps:
            return val
        return _unwrap_arithmetic(val.base)
    if isinstance(val, ast.ArithmeticTerm):
        if val.steps:
            return val
        return _unwrap_arithmetic(val.base)
    if isinstance(val, ast.ArithmeticFactor):
        return _unwrap_arithmetic(val.arithmetic_primary)
    return val


# ---------------------------------------------------------------------------
# non-constant-skip-limit — §16.18/§16.19: SKIP/LIMIT take only
# <non-negative integer specification> (unsigned integer or $param)
# ---------------------------------------------------------------------------


def _is_constant_integer(val: ast.Expression) -> bool:
    """Check if an expression is a constant integer (literal or parameter).

    Unwraps the Cypher arithmetic wrapper chain, rejecting anything
    with arithmetic operations at any level.
    """
    if isinstance(val, ast.NonNegativeIntegerSpecification):
        return True
    inner = _unwrap_arithmetic(val)
    if inner is not val:
        return _is_constant_integer(inner)
    if isinstance(val, ast.GeneralValueSpecification):
        return _is_constant_integer(val.general_value_specification)
    return isinstance(val, ast.UnsignedNumericLiteral | ast.GeneralParameterReference)


@structural_rule("non-constant-skip-limit")
def check_non_constant_skip_limit(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect non-constant expressions in SKIP/LIMIT (§16.18-19)."""
    diagnostics: list[SemanticDiagnostic] = []

    for clause_type, label in (
        (ast.OffsetClause, "SKIP"),
        (ast.LimitClause, "LIMIT"),
    ):
        for node in ctx.expression.find_all(clause_type):
            clause = t.cast(ast.OffsetClause | ast.LimitClause, node)
            if not _is_constant_integer(clause.non_negative_integer_specification):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="non-constant-skip-limit",
                        message=f"{label} requires a non-negative integer literal or parameter.",
                        node=clause,
                    )
                )

    return diagnostics


# ---------------------------------------------------------------------------
# invalid-merge-pattern — Cypher MERGE constraints: relationships must have
# exactly one type, and no variable-length patterns
# ---------------------------------------------------------------------------


@structural_rule("invalid-merge-pattern")
def check_invalid_merge_pattern(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect invalid MERGE relationship patterns (Cypher-only)."""
    from graphglot.ast.cypher import MergeClause

    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(MergeClause):
        mc = t.cast(MergeClause, node)
        # Check for variable-length patterns (QuantifiedPathPrimary)
        for qpp in mc.path_pattern.find_all(ast.QuantifiedPathPrimary):
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="invalid-merge-pattern",
                    message="MERGE does not support variable-length relationships.",
                    node=qpp,
                )
            )
        # Check edges
        for edge in mc.path_pattern.find_all(ast.EdgePattern):
            edge = t.cast(ast.EdgePattern, edge)
            if isinstance(edge, ast.AbbreviatedEdgePattern):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="invalid-merge-pattern",
                        message="MERGE relationships must have a type.",
                        node=edge,
                    )
                )
                continue
            if isinstance(edge, ast.FullEdgePattern):
                filler: ast.ElementPatternFiller = edge.element_pattern_filler  # type: ignore[attr-defined]
                if filler.is_label_expression is None:
                    diagnostics.append(
                        SemanticDiagnostic(
                            feature_id="invalid-merge-pattern",
                            message="MERGE relationships must have a type.",
                            node=edge,
                        )
                    )
                    continue
                # Check for multi-type: disjunction = multiple LabelTerms
                le = filler.is_label_expression.label_expression
                if len(le.label_terms) > 1:
                    diagnostics.append(
                        SemanticDiagnostic(
                            feature_id="invalid-merge-pattern",
                            message="MERGE relationships must have exactly one type.",
                            node=edge,
                        )
                    )

    return diagnostics


# ---------------------------------------------------------------------------
# exists-no-update — §19.4: EXISTS cannot contain data-modifying statements
# ---------------------------------------------------------------------------

_DATA_MODIFYING_TYPES = (
    ast.SetStatement,
    ast.DeleteStatement,
    ast.RemoveStatement,
    ast.InsertStatement,
)


@structural_rule("exists-no-update")
def check_exists_no_update(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect data-modifying statements inside EXISTS (§19.4)."""
    from graphglot.ast.cypher import CreateClause, MergeClause

    diagnostics: list[SemanticDiagnostic] = []

    for node in ctx.expression.find_all(ast.ExistsPredicate):
        ep = t.cast(ast.ExistsPredicate, node)
        for child in ep.find_all(ast.Expression):
            if isinstance(child, (*_DATA_MODIFYING_TYPES, CreateClause, MergeClause)):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="exists-no-update",
                        message="Data-modifying statements are not allowed inside EXISTS.",
                        node=child,
                    )
                )
                break  # one diagnostic per EXISTS is enough

    return diagnostics


# ---------------------------------------------------------------------------
# type-mismatch — §20.13, §20.21, §20.23: Incompatible operand types in
# concatenation (||) and arithmetic (+, -, *, /) (compatibility layer).
#
# This is layer 2 of two-layer operand type validation.  Layer 1
# (typing/rules/resolution.py) rejects operands entirely implausible for the
# operation.  This layer catches operands that are individually plausible but
# incompatible with each other (e.g. INT + DATE, STRING || PATH).
# See Dialect.validate for the full picture.
# ---------------------------------------------------------------------------

_CONCAT_KINDS = frozenset({TypeKind.STRING, TypeKind.BYTE_STRING, TypeKind.PATH, TypeKind.LIST})


def _is_concrete(rt: GqlType | None) -> bool:
    """True when type is known and concrete enough to check for mismatches."""
    if rt is None or rt.is_unknown or rt.is_error or rt.is_union:
        return False
    if rt.kind in (TypeKind.ANY, TypeKind.NULL):
        return False
    return True


def _arithmetic_family(tp: GqlType) -> str:
    if tp.is_numeric:
        return "numeric"
    if tp.is_temporal:
        return "temporal"
    if tp.kind == TypeKind.DURATION:
        return "duration"
    return "other"


def _check_concat_mismatch(node: ast.ConcatenationValueExpression) -> SemanticDiagnostic | None:
    concrete: list[GqlType] = [
        t.cast(GqlType, op._resolved_type)
        for op in node.operands
        if _is_concrete(op._resolved_type)
    ]
    if len(concrete) < 2:
        return None
    for rt in concrete:
        if rt.kind not in _CONCAT_KINDS:
            msg = (
                "Concatenation (||) requires string, byte string, list,"
                f" or path operands, got {rt.kind.value}."
            )
            return SemanticDiagnostic(feature_id="type-mismatch", message=msg, node=node)
    kinds = {rt.kind for rt in concrete}
    if len(kinds) > 1:
        mixed = ", ".join(sorted(k.value for k in kinds))
        msg = f"Concatenation (||) operands have incompatible types: {mixed}."
        return SemanticDiagnostic(feature_id="type-mismatch", message=msg, node=node)
    return None


def _collect_additive_types(node: ast.ArithmeticValueExpression) -> list[GqlType]:
    types: list[GqlType] = []
    if _is_concrete(node.base._resolved_type):
        types.append(node.base._resolved_type)  # type: ignore[arg-type]
    for step in node.steps or ():
        if _is_concrete(step.term._resolved_type):
            types.append(step.term._resolved_type)  # type: ignore[arg-type]
    return types


def _check_additive_mismatch(node: ast.ArithmeticValueExpression) -> SemanticDiagnostic | None:
    if not node.steps:
        return None
    types = _collect_additive_types(node)
    if len(types) < 2:
        return None
    families = {_arithmetic_family(tp) for tp in types}
    if "other" in families:
        other = next(tp for tp in types if _arithmetic_family(tp) == "other")
        return SemanticDiagnostic(
            feature_id="type-mismatch",
            message=f"Arithmetic (+/-) not supported for {other.kind.value}.",
            node=node,
        )
    if "numeric" in families and families & {"temporal", "duration"}:
        return SemanticDiagnostic(
            feature_id="type-mismatch",
            message="Cannot mix numeric and temporal/duration types in arithmetic (+/-).",
            node=node,
        )
    return None


def _collect_multiplicative_types(node: ast.ArithmeticTerm) -> list[GqlType]:
    types: list[GqlType] = []
    if _is_concrete(node.base._resolved_type):
        types.append(node.base._resolved_type)  # type: ignore[arg-type]
    for step in node.steps or ():
        if _is_concrete(step.factor._resolved_type):
            types.append(step.factor._resolved_type)  # type: ignore[arg-type]
    return types


def _check_multiplicative_mismatch(node: ast.ArithmeticTerm) -> SemanticDiagnostic | None:
    if not node.steps:
        return None
    types = _collect_multiplicative_types(node)
    if len(types) < 2:
        return None
    families = {_arithmetic_family(tp) for tp in types}
    if "other" in families:
        other = next(tp for tp in types if _arithmetic_family(tp) == "other")
        return SemanticDiagnostic(
            feature_id="type-mismatch",
            message=f"Arithmetic (*/) not supported for {other.kind.value}.",
            node=node,
        )
    if "temporal" in families:
        return SemanticDiagnostic(
            feature_id="type-mismatch",
            message="Temporal types do not support multiplication/division.",
            node=node,
        )
    if sum(1 for tp in types if tp.kind == TypeKind.DURATION) >= 2:
        return SemanticDiagnostic(
            feature_id="type-mismatch",
            message="Cannot multiply/divide two duration values.",
            node=node,
        )
    return None


@structural_rule("type-mismatch")
def check_type_mismatch(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect incompatible operand types in concatenation and arithmetic."""
    diagnostics: list[SemanticDiagnostic] = []
    for node in ctx.expression.dfs():
        diag = None
        if isinstance(node, ast.ConcatenationValueExpression):
            diag = _check_concat_mismatch(node)
        elif isinstance(node, ast.ArithmeticValueExpression):
            diag = _check_additive_mismatch(node)
        elif isinstance(node, ast.ArithmeticTerm):
            diag = _check_multiplicative_mismatch(node)
        if diag is not None:
            diagnostics.append(diag)
    return diagnostics
