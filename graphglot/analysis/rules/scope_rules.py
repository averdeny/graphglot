"""Semantic analysis rules.

GA04 — Universal comparison (type-compatible comparisons)
GA07 — Ordering by discarded binding variables
GA09 — Comparison of paths
GE04 — Graph parameters
GE05 — Binding table parameters
GE09 — Horizontal aggregation
GP14 — Binding tables as procedure arguments
GP15 — Graphs as procedure arguments
GQ17 — Element-wise group variable operations
"""

from __future__ import annotations

from graphglot import features as F
from graphglot.analysis.models import AnalysisContext, SemanticDiagnostic
from graphglot.analysis.rules._registry import analysis_rule
from graphglot.ast import expressions as ast
from graphglot.typing.types import GqlType, TypeKind

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_variable_reference(ident: ast.Identifier) -> bool:
    """True when *ident* is a binding-variable reference (not a property name or alias)."""
    return isinstance(ident._parent, ast.BindingVariableReference)


# Container types whose ``graph_expression`` field constrains children to graph type.
_GRAPH_EXPR_CONTAINERS = (
    ast.UseGraphClause,
    ast.GraphInitializer,
    ast.GraphTypeLikeGraph,
    ast.GraphSource,
    ast.SelectGraphMatch,
    ast.SessionSetGraphClause,
)

# Container types whose ``binding_table_expression`` field constrains children
# to binding-table type.
_BT_EXPR_CONTAINERS = (
    ast.BindingTableInitializer,
    ast.BindingTableReferenceValueExpression._TableBindingTableExpression,
)


def _is_structurally_graph_typed(param: ast.Expression) -> bool:
    """True when *param* sits inside a ``graph_expression`` field of a known container."""
    node = param
    while node._parent is not None:
        if node._arg_key == "graph_expression" and isinstance(node._parent, _GRAPH_EXPR_CONTAINERS):
            return True
        node = node._parent
    return False


def _is_structurally_binding_table_typed(param: ast.Expression) -> bool:
    """True when *param* sits inside a ``binding_table_expression`` field of a known container."""
    node = param
    while node._parent is not None:
        if node._arg_key == "binding_table_expression" and isinstance(
            node._parent, _BT_EXPR_CONTAINERS
        ):
            return True
        node = node._parent
    return False


def _binding_variable_names(node: ast.Expression) -> set[str]:
    """Extract binding variable names from an AST subtree.

    Returns identifiers that act as variable references, excluding property
    names (the right-hand side of ``a.prop``) and return-item aliases.
    """
    names: set[str] = set()
    for ident in node.find_all(ast.Identifier):
        if isinstance(ident, ast.Identifier) and _is_variable_reference(ident):
            names.add(ident.name)
    return names


def _return_output_names(
    body: ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause,
) -> set[str]:
    """Collect all binding variable names visible in the RETURN output.

    This includes:
    - Aliases (``RETURN expr AS x`` → ``x``)
    - Binding variables referenced in expressions (``RETURN n.name`` → ``n``)
    """
    names: set[str] = set()
    for item in body.return_item_list.list_return_item:
        if item.return_item_alias is not None:
            names.add(item.return_item_alias.identifier.name)
        names |= _binding_variable_names(item.aggregating_value_expression)
    return names


# ---------------------------------------------------------------------------
# GA07 — Ordering by discarded binding variables
# ---------------------------------------------------------------------------


@analysis_rule(F.GA07)
def check_ordering_by_discarded_variables(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GA07, ORDER BY can only reference binding variables that
    appear in the RETURN output."""
    diagnostics: list[SemanticDiagnostic] = []

    for prs in ctx.expression.find_all(ast.PrimitiveResultStatement):
        if not isinstance(prs, ast.PrimitiveResultStatement):
            continue
        stmt = prs.primitive_result_statement
        if not isinstance(
            stmt, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement
        ):
            continue

        obs = stmt.order_by_and_page_statement
        if obs is None:
            continue

        page = obs.order_by_and_page_statement
        _obc = ast.OrderByAndPageStatement._OrderByClauseOffsetClauseLimitClause
        if not isinstance(page, _obc):
            continue

        order_by = page.order_by_clause

        # Extract return output variables
        ret_body = stmt.return_statement.return_statement_body.return_statement_body

        if isinstance(ret_body, ast.ReturnStatementBody._SetQuantifierAsteriskGroupByClause):
            # RETURN * — all variables are in scope, so ORDER BY can't reference
            # anything "discarded".
            continue

        if isinstance(ret_body, ast.ReturnStatementBody._NoBindings):
            # NO BINDINGS — no output variables at all, ORDER BY shouldn't exist
            # but if it does, everything is discarded.
            order_vars = _binding_variable_names(order_by)
            if order_vars:
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="GA07",
                        message=(
                            f"ORDER BY references variable(s) {_fmt(order_vars)} "
                            f"but RETURN has NO BINDINGS. "
                            f"Feature GA07 (ordering by discarded binding variables) is required."
                        ),
                        node=order_by,
                    )
                )
            continue

        # Normal case: RETURN item_list
        output_vars = _return_output_names(ret_body)

        # Variables referenced in ORDER BY
        order_vars = _binding_variable_names(order_by)

        discarded = order_vars - output_vars
        if discarded:
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="GA07",
                    message=(
                        f"ORDER BY references variable(s) {_fmt(discarded)} "
                        f"not present in RETURN output. "
                        f"Feature GA07 (ordering by discarded binding variables) is required."
                    ),
                    node=order_by,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# GE09 — Horizontal aggregation
# ---------------------------------------------------------------------------


@analysis_rule(F.GE09)
def check_horizontal_aggregation(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GE09, aggregate functions may only appear at the top-level
    RETURN scope (vertical aggregation).  Aggregation inside a list/pattern
    comprehension is horizontal aggregation."""
    diagnostics: list[SemanticDiagnostic] = []

    for agg in ctx.expression.find_all(ast.AggregateFunction):
        # Walk up the parent chain to check if inside a comprehension
        node = agg._parent
        while node is not None:
            if isinstance(node, ast.ListValueConstructorByEnumeration):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="GE09",
                        message=(
                            "Aggregate function inside list comprehension requires "
                            "feature GE09 (horizontal aggregation)."
                        ),
                        node=agg,
                    )
                )
                break
            node = node._parent

    return diagnostics


# ---------------------------------------------------------------------------
# GQ17 — Element-wise group variable operations
# ---------------------------------------------------------------------------


@analysis_rule(F.GQ17)
def check_elementwise_group_variable_ops(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GQ17, non-grouped variables in RETURN (after GROUP BY) may only
    be referenced inside aggregate functions.  Element-wise operations like
    property access on group variables require GQ17."""
    diagnostics: list[SemanticDiagnostic] = []

    for prs in ctx.expression.find_all(ast.PrimitiveResultStatement):
        if not isinstance(prs, ast.PrimitiveResultStatement):
            continue
        stmt = prs.primitive_result_statement
        if not isinstance(
            stmt, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement
        ):
            continue

        ret_body = stmt.return_statement.return_statement_body.return_statement_body
        if not isinstance(
            ret_body, ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause
        ):
            continue

        group_by = ret_body.group_by_clause
        if group_by is None:
            continue

        # Extract grouping variable names
        gel = group_by.grouping_element_list.grouping_element_list
        if isinstance(gel, ast.EmptyGroupingSet):
            grouping_vars: set[str] = set()
        else:
            # gel is list[GroupingElement] which is list[BindingVariableReference]
            grouping_vars = {elem.binding_variable.name for elem in gel}

        # Check each return item for non-grouped variable references outside aggregates
        for item in ret_body.return_item_list.list_return_item:
            expr = item.aggregating_value_expression
            flagged = _non_grouped_vars_outside_aggregates(expr, grouping_vars)
            if flagged:
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="GQ17",
                        message=(
                            f"RETURN references non-grouped variable(s) {_fmt(flagged)} "
                            f"outside of aggregate functions. "
                            f"Feature GQ17 (element-wise group variable operations) is required."
                        ),
                        node=item,
                    )
                )

    return diagnostics


def _non_grouped_vars_outside_aggregates(node: ast.Expression, grouping_vars: set[str]) -> set[str]:
    """Find binding variable names referenced outside aggregate functions
    that are not in the grouping set."""
    result: set[str] = set()
    _walk_outside_aggregates(node, grouping_vars, result)
    return result


def _walk_outside_aggregates(
    node: ast.Expression, grouping_vars: set[str], result: set[str]
) -> None:
    """Walk the AST, skipping AggregateFunction subtrees."""
    if isinstance(node, ast.AggregateFunction):
        return
    if isinstance(node, ast.Identifier):
        if _is_variable_reference(node) and node.name not in grouping_vars:
            result.add(node.name)
        return
    for child in node.children():
        _walk_outside_aggregates(child, grouping_vars, result)


def _fmt(names: set[str]) -> str:
    """Format a set of variable names for display."""
    return ", ".join(sorted(names))


# ---------------------------------------------------------------------------
# GA09 — Comparison of paths
# ---------------------------------------------------------------------------


@analysis_rule(F.GA09)
def check_comparison_of_paths(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GA09, path-typed values may not appear as comparison operands.

    Uses ``semantic_type`` on each direct comparand (not ``find_all`` on the
    whole predicate) so that functions like ``PATH_LENGTH(p)`` — which return
    INTEGER — do not trigger a false positive.
    """
    diagnostics: list[SemanticDiagnostic] = []

    for cp in ctx.expression.find_all(ast.ComparisonPredicate):
        if not isinstance(cp, ast.ComparisonPredicate):
            continue
        left_type = semantic_type(cp.comparison_predicand)
        right_type = semantic_type(cp.comparison_predicate_part_2.comparison_predicand)
        if (left_type and left_type.kind == TypeKind.PATH) or (
            right_type and right_type.kind == TypeKind.PATH
        ):
            # Collect path variable names for a helpful message
            path_names: set[str] = set()
            if left_type and left_type.kind == TypeKind.PATH:
                for ident in cp.comparison_predicand.find_all(ast.Identifier):
                    if (
                        isinstance(ident, ast.Identifier)
                        and ident._resolved_type
                        and ident._resolved_type.kind == TypeKind.PATH
                    ):
                        path_names.add(ident.name)
            if right_type and right_type.kind == TypeKind.PATH:
                for ident in cp.comparison_predicate_part_2.comparison_predicand.find_all(
                    ast.Identifier
                ):
                    if (
                        isinstance(ident, ast.Identifier)
                        and ident._resolved_type
                        and ident._resolved_type.kind == TypeKind.PATH
                    ):
                        path_names.add(ident.name)
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="GA09",
                    message=(
                        f"Comparison involves path variable(s) {_fmt(path_names)}. "
                        f"Feature GA09 (comparison of paths) is required."
                    ),
                    node=cp,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# GA04 — Universal comparison (type-compatible comparisons)
# ---------------------------------------------------------------------------


def semantic_type(node: ast.Expression) -> GqlType | None:
    """Return the most informative resolved type from a comparand subtree.

    Wrapper AST nodes (ArithmeticValueExpression, ArithmeticTerm, etc.)
    may infer a generic type from their grammar role rather than their
    actual content.  Walk down single-child chains to reach the deepest
    node with a resolved type — this gives the actual semantic type
    rather than the wrapper's grammar-constrained type.

    Stops at type-transformation boundaries: if the accumulated type is
    concrete (non-UNKNOWN) and the child's type is also concrete but
    *different*, the current node is a function (e.g. PathLengthExpression)
    rather than a transparent grammar wrapper.
    """
    best: GqlType | None = node._resolved_type
    cur = node
    while True:
        children = list(cur.children())
        if len(children) != 1:
            # Multi-child or leaf — use this node's type if available
            if cur._resolved_type is not None:
                best = cur._resolved_type
            break
        child = children[0]
        # Stop at type-transformation boundaries: if the accumulated type
        # is concrete and the child's type is concrete but different, this
        # node is a function (e.g. PathLengthExpression), not a grammar
        # wrapper.  The accumulated type is the correct semantic type.
        if (
            best is not None
            and best.kind != TypeKind.UNKNOWN
            and child._resolved_type is not None
            and child._resolved_type.kind != TypeKind.UNKNOWN
            and best.kind != child._resolved_type.kind
        ):
            break
        cur = child
        if cur._resolved_type is not None:
            best = cur._resolved_type
    return best


@analysis_rule(F.GA04)
def check_universal_comparison(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GA04, comparison operands must be type-compatible.

    Uses ``_resolved_type`` set by the TypeAnnotator pre-pass to check that
    left and right sides of each comparison are comparable.
    """
    diagnostics: list[SemanticDiagnostic] = []

    for cp in ctx.expression.find_all(ast.ComparisonPredicate):
        if not isinstance(cp, ast.ComparisonPredicate):
            continue
        left_type = semantic_type(cp.comparison_predicand)
        right_type = semantic_type(cp.comparison_predicate_part_2.comparison_predicand)
        if left_type is None or right_type is None:
            continue
        if not left_type.is_comparable_with(right_type):
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="GA04",
                    message=(
                        f"Comparison between incompatible types {left_type!r} and "
                        f"{right_type!r}. Feature GA04 (universal comparison) is required."
                    ),
                    node=cp,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# GE04 — Graph parameters
# ---------------------------------------------------------------------------


@analysis_rule(F.GE04)
def check_graph_parameters(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GE04, session parameters may not be graph-typed.

    Fires in two cases:

    1. The TypeAnnotator resolves a parameter to ``GRAPH`` type (requires
       ``ExternalContext`` from the caller).
    2. The parameter appears inside a ``graph_expression`` field of a known
       container (structural inference — no ``ExternalContext`` needed).
    """
    diagnostics: list[SemanticDiagnostic] = []

    for param in ctx.expression.find_all(ast.GeneralParameterReference):
        if not isinstance(param, ast.GeneralParameterReference):
            continue
        if param._resolved_type and param._resolved_type.kind == TypeKind.GRAPH:
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="GE04",
                    message=(
                        f"Parameter ${param.parameter_name.name} is graph-typed. "
                        f"Feature GE04 (graph parameters) is required."
                    ),
                    node=param,
                )
            )
        elif _is_structurally_graph_typed(param):
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="GE04",
                    message=(
                        f"Parameter ${param.parameter_name.name} is graph-typed. "
                        f"Feature GE04 (graph parameters) is required."
                    ),
                    node=param,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# GE05 — Binding table parameters
# ---------------------------------------------------------------------------


@analysis_rule(F.GE05)
def check_binding_table_parameters(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GE05, session parameters may not be binding-table-typed.

    Fires in two cases:

    1. The TypeAnnotator resolves a parameter to ``BINDING_TABLE`` type
       (requires ``ExternalContext`` from the caller).
    2. The parameter appears inside a ``binding_table_expression`` field of a
       known container (structural inference — no ``ExternalContext`` needed).
    """
    diagnostics: list[SemanticDiagnostic] = []

    for param in ctx.expression.find_all(ast.GeneralParameterReference):
        if not isinstance(param, ast.GeneralParameterReference):
            continue
        if param._resolved_type and param._resolved_type.kind == TypeKind.BINDING_TABLE:
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="GE05",
                    message=(
                        f"Parameter ${param.parameter_name.name} is binding-table-typed. "
                        f"Feature GE05 (binding table parameters) is required."
                    ),
                    node=param,
                )
            )
        elif _is_structurally_binding_table_typed(param):
            diagnostics.append(
                SemanticDiagnostic(
                    feature_id="GE05",
                    message=(
                        f"Parameter ${param.parameter_name.name} is binding-table-typed. "
                        f"Feature GE05 (binding table parameters) is required."
                    ),
                    node=param,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# GP15 — Graphs as procedure arguments
# ---------------------------------------------------------------------------


@analysis_rule(F.GP15)
def check_graphs_as_procedure_arguments(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GP15, procedure arguments shall not be graph-typed.

    See ISO/IEC 39075:2024 §15.3, Conformance Rule 2. Detects
    GraphReferenceValueExpression nodes inside procedure argument lists.
    """
    diagnostics: list[SemanticDiagnostic] = []

    for call in ctx.expression.find_all(ast.NamedProcedureCall):
        if call.procedure_argument_list is None:
            continue
        for arg in call.procedure_argument_list.list_procedure_argument:
            if arg.find_first(ast.GraphReferenceValueExpression):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="GP15",
                        message=(
                            "Procedure argument is graph-typed. "
                            "Feature GP15 (graphs as procedure arguments) is required."
                        ),
                        node=arg,
                    )
                )

    return diagnostics


# ---------------------------------------------------------------------------
# GP14 — Binding tables as procedure arguments
# ---------------------------------------------------------------------------


@analysis_rule(F.GP14)
def check_binding_tables_as_procedure_arguments(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Without GP14, procedure arguments shall not be binding-table-typed.

    See ISO/IEC 39075:2024 §15.3, Conformance Rule 3. Detects
    BindingTableReferenceValueExpression nodes inside procedure argument lists.
    """
    diagnostics: list[SemanticDiagnostic] = []

    for call in ctx.expression.find_all(ast.NamedProcedureCall):
        if call.procedure_argument_list is None:
            continue
        for arg in call.procedure_argument_list.list_procedure_argument:
            if arg.find_first(ast.BindingTableReferenceValueExpression):
                diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="GP14",
                        message=(
                            "Procedure argument is binding-table-typed. "
                            "Feature GP14 (binding tables as procedure arguments) is required."
                        ),
                        node=arg,
                    )
                )

    return diagnostics
