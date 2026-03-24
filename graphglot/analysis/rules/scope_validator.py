"""Scope validation rules (always enforced, not feature-gated).

variable-type-conflict            — Cross-clause node/edge/path type mismatch
variable-already-bound            — Re-declaration in CREATE/MERGE
undefined-variable                — Reference to variable not in current scope
return-star-no-variables          — RETURN * with no variables in scope
distinct-order-by-non-projected   — ORDER BY key not in RETURN with DISTINCT
"""

# Architecture: recursive tree walker (ADR-006).  Known watchpoints:
#
# (1) The walker runs once per analysis (cached by _get_scope_diagnostics);
#     each @structural_rule entry point filters from the cached result.
#
# (2) _walk_clause is a large dispatch table (one branch per clause type).
#     If more clause types are added, consider extracting a handler registry
#     or breaking it into per-clause functions.
#
# (3) _extract_pattern_bindings traverses ALL descendants of its argument.
#     Callers must pass narrow subtrees (e.g. gp.path_pattern_list, not the
#     full MATCH statement) to prevent bindings inside EXISTS/subqueries from
#     leaking into the outer scope.  This is a verbal contract enforced by
#     comments, not by the type system — see ADR-006 §Consequences.

from __future__ import annotations

from dataclasses import dataclass, field

from graphglot.analysis.models import AnalysisContext, SemanticDiagnostic
from graphglot.analysis.rules._registry import structural_rule
from graphglot.ast import expressions as ast
from graphglot.scope import (
    extract_pattern_bindings as _extract_pattern_bindings,
    extract_variable_references as _extract_variable_references,
    is_inside_nested_subquery as _is_inside_nested_subquery,
    is_variable_reference as _is_variable_reference,
)

# ---------------------------------------------------------------------------
# Value-kind tracking
# ---------------------------------------------------------------------------

_VALUE_PRODUCING_TYPES = (
    ast.UnsignedNumericLiteral,
    ast.CharacterStringLiteral,
    ast.ListValueConstructorByEnumeration,
    ast.PropertyReference,
    ast.RecordConstructor,
)


def _is_bare_variable_projection(
    expr: ast.Expression,
    bindings: dict[str, tuple[str, ast.Expression]],
) -> str | None:
    """If *expr* is a bare variable reference to a known binding, return its name."""
    refs = _extract_variable_references(expr)
    if len(refs) != 1:
        return None
    source = next(iter(refs))
    if source not in bindings:
        return None
    for node in expr.find_all(ast.Expression):
        if isinstance(node, _VALUE_PRODUCING_TYPES):
            return None
    return source


# ---------------------------------------------------------------------------
# Projection extraction
# ---------------------------------------------------------------------------


def _extract_return_item_names(
    body: ast.Expression,
) -> tuple[bool, set[str]]:
    """Extract projection names from a ReturnStatementBody inner node.

    Returns (is_star, names).  If *is_star* is True the projection
    forwards all bindings and *names* is empty.
    """
    if isinstance(body, ast.ReturnStatementBody._SetQuantifierAsteriskGroupByClause):
        return True, set()
    if isinstance(body, ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause):
        names: set[str] = set()
        for item in body.return_item_list.list_return_item:
            if item.return_item_alias is not None:
                names.add(item.return_item_alias.identifier.name)
            else:
                # No alias — use the variable reference name (RETURN n → alias is n)
                for ident in item.aggregating_value_expression.find_all(ast.Identifier):
                    if _is_variable_reference(ident):
                        names.add(ident.name)
                        break
        return False, names
    return False, set()


def _get_return_projections(
    prs: ast.Expression | None,
) -> tuple[bool, set[str]]:
    """Extract projection names from a PrimitiveResultStatement (RETURN).

    Returns (is_star, names).  If *is_star* is True, the RETURN projects
    all bindings.
    """
    if not isinstance(prs, ast.PrimitiveResultStatement):
        return False, set()

    stmt = prs.primitive_result_statement
    if not isinstance(stmt, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement):
        return False, set()

    inner = stmt.return_statement.return_statement_body.return_statement_body
    return _extract_return_item_names(inner)


def _project_type_bindings(
    prs: ast.Expression | None,
    bindings: dict[str, tuple[str, ast.Expression]],
) -> dict[str, tuple[str, ast.Expression]]:
    """Project bindings through a RETURN, tracking value kinds for non-element aliases."""
    if not isinstance(prs, ast.PrimitiveResultStatement):
        return {}

    stmt = prs.primitive_result_statement
    if not isinstance(stmt, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement):
        return {}

    body = stmt.return_statement.return_statement_body.return_statement_body
    if isinstance(body, ast.ReturnStatementBody._SetQuantifierAsteriskGroupByClause):
        return dict(bindings)  # RETURN * keeps all

    if not isinstance(body, ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause):
        return {}

    new: dict[str, tuple[str, ast.Expression]] = {}
    for item in body.return_item_list.list_return_item:
        # Resolve alias name
        if item.return_item_alias is not None:
            alias = item.return_item_alias.identifier.name
        else:
            refs = _extract_variable_references(item.aggregating_value_expression)
            if len(refs) == 1:
                alias = next(iter(refs))
            else:
                continue

        # Resolve kind: bare variable reference (self-forward or rename),
        # or value expression.  Always inspect the expression — do not
        # short-circuit on alias name alone (see ticket 001).
        source = _is_bare_variable_projection(item.aggregating_value_expression, bindings)
        if source is not None:
            new[alias] = bindings[source]
        else:
            new[alias] = ("value", prs)
    return new


# ---------------------------------------------------------------------------
# ScopeState — bundles all three rule states into one object
# ---------------------------------------------------------------------------


@dataclass
class _ScopeState:
    """Mutable scope state carried through the recursive walker.

    ``names``, ``bindings``, and ``bound`` are forked when entering scope
    boundaries (CALL bodies, UNION branches).  ``diagnostics`` is a shared
    list — all forks accumulate into the same output.
    """

    names: set[str] = field(default_factory=set)
    """Variable names in scope (for undefined-variable checks)."""

    bindings: dict[str, tuple[str, ast.Expression]] = field(default_factory=dict)
    """Variable → (element-kind, declaration-node) for type-conflict checks."""

    bound: set[str] = field(default_factory=set)
    """Variables already bound (for already-bound-in-CREATE/MERGE checks)."""

    diagnostics: list[SemanticDiagnostic] = field(default_factory=list)
    """Shared diagnostic accumulator (not forked)."""

    def copy(self) -> _ScopeState:
        """Fork names/bindings/bound but share diagnostics."""
        return _ScopeState(
            names=set(self.names),
            bindings=dict(self.bindings),
            bound=set(self.bound),
            diagnostics=self.diagnostics,
        )

    def add_binding(self, name: str, kind: str, node: ast.Expression) -> None:
        """Add a pattern binding, checking for type conflicts."""
        if name in self.bindings:
            existing_kind, _ = self.bindings[name]
            if existing_kind != kind:
                self.diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="variable-type-conflict",
                        message=(
                            f"Variable '{name}' used as {kind} but was "
                            f"previously declared as {existing_kind}."
                        ),
                        node=node,
                    )
                )
        else:
            self.bindings[name] = (kind, node)
        self.names.add(name)
        self.bound.add(name)

    def add_name(self, name: str) -> None:
        """Add a name to scope without type-binding (e.g. LET, FOR, YIELD)."""
        self.names.add(name)
        self.bound.add(name)

    def check_refs(self, subtree: ast.Expression) -> None:
        """Check variable references in *subtree* against current scope."""
        refs = _extract_variable_references(subtree)
        for ref, ident_node in refs.items():
            if ref not in self.names:
                self.diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="undefined-variable",
                        message=f"Variable '{ref}' is not defined in the current scope.",
                        node=ident_node,
                    )
                )

    def check_already_bound(self, name: str, kind: str, node: ast.Expression, clause: str) -> None:
        """Check if *name* is already bound, then add it."""
        if name in self.bound:
            self.diagnostics.append(
                SemanticDiagnostic(
                    feature_id="variable-already-bound",
                    message=f"Variable '{name}' is already bound; cannot re-declare in {clause}.",
                    node=node,
                )
            )
        else:
            self.bound.add(name)
            self.bindings[name] = (kind, node)
            self.names.add(name)


# ---------------------------------------------------------------------------
# Recursive walker
# ---------------------------------------------------------------------------


def _walk_scope(root: ast.Expression) -> list[SemanticDiagnostic]:
    """Walk the AST recursively, validating scope rules.

    Entry point for all scope rules.  Returns all diagnostics found.
    """
    diagnostics: list[SemanticDiagnostic] = []
    state = _ScopeState(diagnostics=diagnostics)

    # Find the outermost StatementBlock
    for sb in root.find_all(ast.StatementBlock):
        _walk_statement_block(sb, state)
        return diagnostics

    # Fallback: walk the root directly if no StatementBlock
    _walk_statement(root, state)
    return diagnostics


def _walk_statement_block(sb: ast.StatementBlock, state: _ScopeState) -> None:
    """Walk a StatementBlock, processing its statement and any NEXT chain."""
    _walk_statement(sb.statement, state)
    if sb.list_next_statement:
        for ns in sb.list_next_statement:
            _walk_statement(ns.statement, state)


def _walk_statement(stmt: ast.Expression, state: _ScopeState) -> None:
    """Dispatch a top-level statement to the appropriate walker."""
    if isinstance(stmt, ast.StatementBlock):
        _walk_statement_block(stmt, state)
    elif isinstance(stmt, ast.CompositeQueryExpression):
        _walk_composite_query(stmt, state)
    elif isinstance(
        stmt,
        ast.AmbientLinearDataModifyingStatementBody | ast.FocusedLinearDataModifyingStatementBody,
    ):
        _walk_data_modifying_body(stmt, state)
    elif isinstance(stmt, ast.FocusedLinearQueryStatement):
        _walk_flqs(stmt, state)
    # Other top-level wrappers are transparent — descend into children


def _walk_composite_query(cqe: ast.CompositeQueryExpression, state: _ScopeState) -> None:
    """Walk a CompositeQueryExpression (handles UNION/INTERSECT/EXCEPT branches)."""
    left = cqe.left_composite_query_primary
    _walk_linear_query(left, state)

    # UNION/INTERSECT/EXCEPT branches get fresh scope (independent)
    if cqe.query_conjunction_elements:
        for elem in cqe.query_conjunction_elements:
            branch_state = _ScopeState(diagnostics=state.diagnostics)
            _walk_linear_query(elem.composite_query_primary, branch_state)


def _walk_linear_query(lqs: ast.Expression, state: _ScopeState) -> None:
    """Walk a LinearQueryStatement (ALQS, ALDMSB, or focused variants)."""
    if isinstance(lqs, ast.AmbientLinearQueryStatement):
        _walk_alqs(lqs, state)
    elif isinstance(
        lqs,
        ast.AmbientLinearDataModifyingStatementBody | ast.FocusedLinearDataModifyingStatementBody,
    ):
        _walk_data_modifying_body(lqs, state)
    elif isinstance(lqs, ast.FocusedLinearQueryStatement):
        _walk_flqs(lqs, state)


def _walk_alqs(alqs: ast.AmbientLinearQueryStatement, state: _ScopeState) -> None:
    """Walk an AmbientLinearQueryStatement (MATCH...RETURN)."""
    inner = alqs.ambient_linear_query_statement
    if isinstance(
        inner,
        ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement,
    ):
        slqs = inner.simple_linear_query_statement
        if slqs is not None:
            for stmt in slqs.list_simple_query_statement:
                _walk_clause(stmt, state)
        if inner.primitive_result_statement is not None:
            _walk_prs(inner.primitive_result_statement, state)


def _walk_data_modifying_body(
    body: ast.AmbientLinearDataModifyingStatementBody | ast.FocusedLinearDataModifyingStatementBody,
    state: _ScopeState,
) -> None:
    """Walk clauses and PRS shared by ambient/focused data-modifying bodies."""
    sldas = body.simple_linear_data_accessing_statement
    for stmt in sldas.list_simple_data_accessing_statement:
        _walk_clause(stmt, state)
    if body.primitive_result_statement is not None:
        _walk_prs(body.primitive_result_statement, state)


def _walk_flqs(flqs: ast.FocusedLinearQueryStatement, state: _ScopeState) -> None:
    """Walk a FocusedLinearQueryStatement (USE graph ... RETURN)."""
    inner = flqs.focused_linear_query_statement
    if isinstance(
        inner,
        ast.FocusedLinearQueryStatement._ListFocusedLinearQueryStatementPartFocusedLinearQueryAndPrimitiveResultStatementPart,
    ):
        if inner.list_focused_linear_query_statement_part:
            for part in inner.list_focused_linear_query_statement_part:
                for stmt in part.simple_linear_query_statement.list_simple_query_statement:
                    _walk_clause(stmt, state)
        final = inner.focused_linear_query_and_primitive_result_statement_part
        for stmt in final.simple_linear_query_statement.list_simple_query_statement:
            _walk_clause(stmt, state)
        _walk_prs(final.primitive_result_statement, state)
    elif isinstance(inner, ast.FocusedPrimitiveResultStatement):
        _walk_prs(inner.primitive_result_statement, state)
    elif isinstance(inner, ast.FocusedNestedQuerySpecification):
        _walk_statement(inner.nested_query_specification, state)
    # TODO: handle SelectStatement (fourth union variant) when SELECT support is added


def _is_bare_filler(node: ast.Expression) -> bool:
    """True when *node* is a variable-only pattern filler (no labels/properties)."""
    if isinstance(node, ast.InsertElementPatternFiller):
        return isinstance(node.insert_element_pattern_filler, ast.ElementVariableDeclaration)
    if isinstance(node, ast.ElementPatternFiller):
        return node.is_label_expression is None and node.element_pattern_predicate is None
    return False


def _walk_insert_or_create(
    bindings: list[tuple[str, str, ast.Expression]],
    state: _ScopeState,
    clause: str,
) -> None:
    """Process INSERT/CREATE/MERGE bindings with bare-reference semantics.

    Bare fillers (no labels/properties) are always references — whether to
    a variable declared earlier in the same statement or in an outer scope.
    Only decorated fillers (with labels or properties) are declarations.
    """
    seen_in_stmt: set[str] = set()
    has_new_binding = False
    bare_outer_refs: list[tuple[str, ast.Expression]] = []
    for name, kind, node in bindings:
        bare = _is_bare_filler(node)
        if name in seen_in_stmt:
            if bare:
                continue  # bare reference to intra-statement variable
            state.diagnostics.append(
                SemanticDiagnostic(
                    feature_id="variable-already-bound",
                    message=f"Variable '{name}' is already bound; cannot re-declare in {clause}.",
                    node=node,
                )
            )
        elif bare and name in state.bound:
            # Edge rebinding is always an error in CREATE/MERGE/INSERT
            if kind == "edge":
                state.diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="variable-already-bound",
                        message=(
                            f"Variable '{name}' is already bound; cannot re-declare in {clause}."
                        ),
                        node=node,
                    )
                )
            else:
                # Bare node reference to outer scope — might be valid
                bare_outer_refs.append((name, node))
        else:
            state.check_already_bound(name, kind, node, clause)
            has_new_binding = True
        seen_in_stmt.add(name)
    # CREATE/MERGE with only bare outer refs and no new bindings is an error
    if clause in ("CREATE", "MERGE") and bare_outer_refs and not has_new_binding:
        name, node = bare_outer_refs[0]
        state.diagnostics.append(
            SemanticDiagnostic(
                feature_id="variable-already-bound",
                message=f"Variable '{name}' is already bound; cannot re-declare in {clause}.",
                node=node,
            )
        )


def _walk_clause(stmt: ast.Expression, state: _ScopeState) -> None:
    """Walk a single clause/statement, updating scope state."""
    # WATCHPOINT (2): large dispatch table.  If adding a new clause type,
    # add a branch here.  If this grows much larger, consider extracting
    # per-clause handler functions.  See module-level comment and ADR-006.
    from graphglot.ast.cypher import CreateClause, MergeClause

    # --- MATCH (simple) ---
    if isinstance(stmt, ast.SimpleMatchStatement):
        # Extract bindings from path patterns only (not from WHERE subqueries)
        gp = stmt.graph_pattern_binding_table.graph_pattern
        for name, kind, node in _extract_pattern_bindings(gp.path_pattern_list):
            state.add_binding(name, kind, node)
        # Check refs in WHERE clause (GraphPatternWhereClause)
        if gp.graph_pattern_where_clause is not None:
            state.check_refs(gp.graph_pattern_where_clause)
            # Cypher pattern predicates in WHERE must not introduce new variables
            from graphglot.ast.cypher import CypherPatternPredicate

            where = gp.graph_pattern_where_clause
            for pp in where.find_all(CypherPatternPredicate):
                if _is_inside_nested_subquery(pp, where):
                    continue  # inside EXISTS { ... } — handled by its own scope
                for name, _kind, node in _extract_pattern_bindings(pp):
                    if name not in state.names:
                        state.diagnostics.append(
                            SemanticDiagnostic(
                                feature_id="undefined-variable",
                                message=f"Variable '{name}' is not defined in the current scope.",
                                node=node,
                            )
                        )
        return

    # --- OPTIONAL MATCH ---
    if isinstance(stmt, ast.OptionalMatchStatement):
        operand = stmt.optional_operand.optional_operand
        if isinstance(operand, ast.SimpleMatchStatement):
            _walk_clause(operand, state)
        elif isinstance(operand, ast.MatchStatementBlock):
            for ms in operand.find_all(ast.SimpleMatchStatement):
                _walk_clause(ms, state)
        return

    # --- LET ---
    if isinstance(stmt, ast.LetStatement):
        for defn in stmt.let_variable_definition_list.list_let_variable_definition:
            inner = defn.let_variable_definition
            if isinstance(inner, ast.LetVariableDefinition._BindingVariableValueExpression):
                state.check_refs(inner.value_expression)
                state.add_name(inner.binding_variable.name)
            elif isinstance(inner, ast.ValueVariableDefinition):
                state.check_refs(inner.opt_typed_value_initializer)
                state.add_name(inner.binding_variable.name)
        return

    # --- FOR ---
    if isinstance(stmt, ast.ForStatement):
        state.add_name(stmt.for_item.for_item_alias.binding_variable.name)
        if stmt.for_ordinality_or_offset is not None:
            state.add_name(stmt.for_ordinality_or_offset.binding_variable.name)
        return

    # --- CALL ---
    if isinstance(stmt, ast.CallProcedureStatement):
        pc = stmt.procedure_call
        # Named procedure call: CALL proc() YIELD x, y → binds x, y
        if isinstance(pc, ast.NamedProcedureCall):
            if pc.yield_clause is not None:
                seen_in_yield: set[str] = set()
                for yi in pc.yield_clause.yield_item_list.list_yield_item:
                    name = (
                        yi.yield_item_alias.binding_variable.name
                        if yi.yield_item_alias is not None
                        else yi.yield_item_name.name
                    )
                    if name in seen_in_yield or name in state.bound:
                        state.diagnostics.append(
                            SemanticDiagnostic(
                                feature_id="variable-already-bound",
                                message=(
                                    f"Variable '{name}' is already bound;"
                                    " cannot re-declare in YIELD."
                                ),
                                node=yi,
                            )
                        )
                    else:
                        state.add_name(name)
                    seen_in_yield.add(name)
            return
        # Inline CALL { ... } → fork, recurse, merge exports
        if isinstance(pc, ast.InlineProcedureCall):
            proc_spec = pc.nested_procedure_specification.procedure_specification
            if not isinstance(proc_spec, ast.ProcedureBody):
                return
            inner_sb = proc_spec.statement_block
            inner_state = state.copy()
            _walk_statement_block(inner_sb, inner_state)
            # Merge exports: get projections from the CALL body's PRS
            _merge_call_exports(inner_sb, inner_state, state)
            return
        return

    # --- FILTER / WHERE ---
    if isinstance(stmt, ast.FilterStatement):
        state.check_refs(stmt)
        return

    # --- CREATE / INSERT ---
    if isinstance(stmt, CreateClause):
        _walk_insert_or_create(
            _extract_pattern_bindings(stmt.insert_graph_pattern), state, "CREATE"
        )
        state.check_refs(stmt)
        return

    if isinstance(stmt, ast.InsertStatement):
        _walk_insert_or_create(_extract_pattern_bindings(stmt), state, "INSERT")
        state.check_refs(stmt)
        return

    # --- MERGE ---
    if isinstance(stmt, MergeClause):
        _walk_insert_or_create(_extract_pattern_bindings(stmt.path_pattern), state, "MERGE")
        state.check_refs(stmt)
        return

    # --- Generic fallback (SET, DELETE, REMOVE, etc.) ---
    for name, kind, node in _extract_pattern_bindings(stmt):
        state.add_binding(name, kind, node)
    state.check_refs(stmt)


def _merge_call_exports(
    inner_sb: ast.StatementBlock,
    inner_state: _ScopeState,
    outer_state: _ScopeState,
) -> None:
    """Merge CALL body exports into the outer scope.

    Finds the PRS of the CALL body and projects through it.
    """
    prs = _find_call_body_prs(inner_sb)
    if prs is None:
        return

    is_star, names = _get_return_projections(prs)
    if is_star:
        outer_state.names.update(inner_state.names)
        outer_state.bindings.update(inner_state.bindings)
        outer_state.bound.update(inner_state.bound)
    else:
        # Project type bindings through the CALL body's RETURN
        projected = _project_type_bindings(prs, inner_state.bindings)
        outer_state.names.update(names)
        outer_state.bindings.update(projected)
        outer_state.bound.update(names)


def _find_call_body_prs(sb: ast.StatementBlock) -> ast.PrimitiveResultStatement | None:
    """Find the PrimitiveResultStatement in a CALL body's StatementBlock."""
    stmt = sb.statement
    # Handle NEXT chains: the PRS is in the last block
    if sb.list_next_statement:
        stmt = sb.list_next_statement[-1].statement

    if isinstance(stmt, ast.CompositeQueryExpression):
        lqs = stmt.left_composite_query_primary
        if isinstance(lqs, ast.AmbientLinearQueryStatement):
            inner = lqs.ambient_linear_query_statement
            if isinstance(
                inner,
                ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement,
            ):
                return inner.primitive_result_statement
        elif isinstance(lqs, ast.FocusedLinearQueryStatement):
            return _find_flqs_prs(lqs)
    if isinstance(
        stmt,
        ast.AmbientLinearDataModifyingStatementBody | ast.FocusedLinearDataModifyingStatementBody,
    ):
        return stmt.primitive_result_statement
    return None


def _find_flqs_prs(
    flqs: ast.FocusedLinearQueryStatement,
) -> ast.PrimitiveResultStatement | None:
    """Extract the PRS from a FocusedLinearQueryStatement."""
    inner = flqs.focused_linear_query_statement
    if isinstance(
        inner,
        ast.FocusedLinearQueryStatement._ListFocusedLinearQueryStatementPartFocusedLinearQueryAndPrimitiveResultStatementPart,
    ):
        final = inner.focused_linear_query_and_primitive_result_statement_part
        return final.primitive_result_statement
    if isinstance(inner, ast.FocusedPrimitiveResultStatement):
        return inner.primitive_result_statement
    return None


def _expr_key(expr: ast.Expression) -> tuple[str, ...] | None:
    """Return a structural key for simple expressions (variables, property refs).

    Returns None for complex expressions (function calls, arithmetic, etc.)
    that cannot be cheaply compared.  Unwraps Cypher arithmetic wrappers.
    """
    # Unwrap arithmetic wrappers (AVE → AT → AF chain with no operations)
    while isinstance(expr, ast.ArithmeticValueExpression | ast.ArithmeticTerm):
        if expr.steps:
            return None  # actual arithmetic — too complex
        expr = expr.base
    if isinstance(expr, ast.ArithmeticFactor):
        expr = expr.arithmetic_primary

    if isinstance(expr, ast.BindingVariableReference):
        return (expr.binding_variable.name,)
    if isinstance(expr, ast.Identifier) and _is_variable_reference(expr):
        return (expr.name,)
    if isinstance(expr, ast.PropertyReference):
        parts: list[str] = []
        if isinstance(expr.property_source, ast.BindingVariableReference):
            parts.append(expr.property_source.binding_variable.name)
        for pn in expr.property_name:
            parts.append(pn.identifier.name)
        return tuple(parts) if parts else None
    return None


def _check_distinct_order_by(
    body: ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause,
    order_by: ast.Expression,
    state: _ScopeState,
) -> None:
    """Check DISTINCT + ORDER BY constraint (§14.10 SR III).

    With DISTINCT, ORDER BY sort keys must be an explicit alias or
    an expression that structurally matches a RETURN item expression.
    """
    allowed: set[tuple[str, ...]] = set()
    for item in body.return_item_list.list_return_item:
        if item.return_item_alias is not None:
            allowed.add((item.return_item_alias.identifier.name,))
        key = _expr_key(item.aggregating_value_expression)
        if key is not None:
            allowed.add(key)

    for spec in order_by.find_all(ast.SortSpecification):
        sort_key = _expr_key(spec.sort_key)
        if sort_key is None:
            continue  # complex expression — skip (conservative)
        if sort_key not in allowed:
            state.diagnostics.append(
                SemanticDiagnostic(
                    feature_id="distinct-order-by-non-projected",
                    message="With DISTINCT, ORDER BY expression must appear in the RETURN clause.",
                    node=spec,
                )
            )


def _walk_prs(prs: ast.PrimitiveResultStatement, state: _ScopeState) -> None:
    """Walk a PrimitiveResultStatement (RETURN), check refs, and project scope."""
    stmt = prs.primitive_result_statement
    if not isinstance(stmt, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement):
        return

    body = stmt.return_statement.return_statement_body.return_statement_body

    # RETURN * — check non-empty scope; no projection
    if isinstance(body, ast.ReturnStatementBody._SetQuantifierAsteriskGroupByClause):
        if not state.names:
            state.diagnostics.append(
                SemanticDiagnostic(
                    feature_id="return-star-no-variables",
                    message="RETURN * with no variables in scope.",
                    node=prs,
                )
            )
        return  # scope unchanged

    # RETURN items — check refs (with extended alias scope for ORDER BY)
    if isinstance(body, ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause):
        extended = set(state.names)
        for item in body.return_item_list.list_return_item:
            if item.return_item_alias is not None:
                extended.add(item.return_item_alias.identifier.name)

        refs = _extract_variable_references(prs)
        for ref, ident_node in refs.items():
            if ref not in extended:
                state.diagnostics.append(
                    SemanticDiagnostic(
                        feature_id="undefined-variable",
                        message=f"Variable '{ref}' is not defined in the current scope.",
                        node=ident_node,
                    )
                )

        # DISTINCT + ORDER BY: sort keys must be in projected scope (§14.10 SR III)
        is_distinct = (
            body.set_quantifier is not None
            and body.set_quantifier.set_quantifier == ast.SetQuantifier.Quantifier.DISTINCT
        )
        order_by = stmt.order_by_and_page_statement
        if is_distinct and order_by is not None:
            _check_distinct_order_by(body, order_by, state)

        # Project scope for next block in NEXT chain
        new_bindings = _project_type_bindings(prs, state.bindings)
        is_star, names = _get_return_projections(prs)
        if not is_star:
            state.names = names.copy()
            state.bindings = new_bindings
            state.bound = names.copy()


# ---------------------------------------------------------------------------
# Rules — each filters from a single cached _walk_scope pass
# ---------------------------------------------------------------------------

# Single-entry cache: all four scope rules operate on the same AST, so we
# walk once and let each rule filter by feature_id.
_scope_walk_cache: tuple[int, list[SemanticDiagnostic]] = (0, [])


def _get_scope_diagnostics(expr: ast.Expression) -> list[SemanticDiagnostic]:
    """Return scope diagnostics, caching the walk result by expression identity."""
    global _scope_walk_cache
    expr_id = id(expr)
    if _scope_walk_cache[0] != expr_id:
        _scope_walk_cache = (expr_id, _walk_scope(expr))
    return _scope_walk_cache[1]


@structural_rule("variable-type-conflict")
def check_variable_type_conflict(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect variable used as different element kinds across clauses."""
    return [
        d
        for d in _get_scope_diagnostics(ctx.expression)
        if d.feature_id == "variable-type-conflict"
    ]


@structural_rule("variable-already-bound")
def check_variable_already_bound(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect re-declaration of already-bound variables in CREATE/MERGE."""
    return [
        d
        for d in _get_scope_diagnostics(ctx.expression)
        if d.feature_id == "variable-already-bound"
    ]


@structural_rule("undefined-variable")
def check_undefined_variable(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect references to variables not in the current scope."""
    return [
        d
        for d in _get_scope_diagnostics(ctx.expression)
        if d.feature_id in ("undefined-variable", "return-star-no-variables")
    ]


@structural_rule("distinct-order-by-non-projected")
def check_distinct_order_by(ctx: AnalysisContext) -> list[SemanticDiagnostic]:
    """Detect ORDER BY keys not in RETURN projection when DISTINCT is used."""
    return [
        d
        for d in _get_scope_diagnostics(ctx.expression)
        if d.feature_id == "distinct-order-by-non-projected"
    ]
