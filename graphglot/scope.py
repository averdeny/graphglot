"""Shared scope utilities for GQL analysis.

Functions used by both analysis/rules/scope_validator.py and lineage modules
for extracting pattern bindings, identifying variable references, etc.
"""

from __future__ import annotations

import typing as t

from graphglot.ast import expressions as ast
from graphglot.ast.cypher import (
    ListComprehension,
    ListPredicateFunction,
)

SUBQUERY_BOUNDARY_TYPES = (
    ast.NestedQuerySpecification,
    ast.NestedProcedureSpecification,
    ast.NestedDataModifyingProcedureSpecification,
    ast.ExistsPredicate,
)


# ---------------------------------------------------------------------------
# Element / binding extraction
# ---------------------------------------------------------------------------


def element_kind(parent: ast.Expression | None) -> str | None:
    """Return 'node' or 'edge' based on the parent of an ElementPatternFiller."""
    if isinstance(parent, ast.NodePattern):
        return "node"
    if isinstance(parent, ast.FullEdgePattern):
        return "edge"
    return None


def insert_element_kind(parent: ast.Expression | None) -> str | None:
    """Return 'node' or 'edge' based on the parent of an InsertElementPatternFiller."""
    if isinstance(parent, ast.InsertNodePattern):
        return "node"
    if isinstance(parent, ast.InsertEdgePattern):
        return "edge"
    return None


def is_inside_nested_subquery(node: ast.Expression, root: ast.Expression) -> bool:
    """True if *node* is inside a subquery boundary between it and *root*."""
    cur = getattr(node, "_parent", None)
    while cur is not None and cur is not root:
        if isinstance(cur, SUBQUERY_BOUNDARY_TYPES):
            return True
        cur = getattr(cur, "_parent", None)
    return False


def extract_pattern_bindings(
    subtree: ast.Expression,
) -> list[tuple[str, str, ast.Expression]]:
    """Extract (name, kind, node) tuples from pattern variable declarations.

    Walks ElementPatternFiller (MATCH patterns), InsertElementPatternFiller
    (INSERT/CREATE patterns), and PathVariableDeclaration nodes in *subtree*.

    WATCHPOINT: traverses ALL descendants. Callers must pass narrow subtrees
    (e.g. gp.path_pattern_list, not the full MATCH statement) to prevent
    bindings inside EXISTS/subqueries from leaking into the outer scope.
    """
    bindings: list[tuple[str, str, ast.Expression]] = []
    # MATCH-style patterns: ElementPatternFiller → NodePattern / FullEdgePattern
    for filler in subtree.find_all(ast.ElementPatternFiller):
        filler = t.cast(ast.ElementPatternFiller, filler)
        decl = filler.element_variable_declaration
        if decl is None:
            continue
        name = decl.element_variable.name
        kind = element_kind(filler._parent)
        if kind is not None:
            bindings.append((name, kind, filler))
    # INSERT/CREATE-style patterns: InsertElementPatternFiller
    for ifiller in subtree.find_all(ast.InsertElementPatternFiller):
        ifiller = t.cast(ast.InsertElementPatternFiller, ifiller)
        inner = ifiller.insert_element_pattern_filler
        insert_decl: ast.ElementVariableDeclaration | None = None
        if isinstance(inner, ast.ElementVariableDeclaration):
            insert_decl = inner
        elif isinstance(
            inner,
            ast.InsertElementPatternFiller._ElementVariableDeclarationLabelAndPropertySetSpecification,
        ):
            insert_decl = inner.element_variable_declaration
        if insert_decl is None:
            continue
        name = insert_decl.element_variable.name
        kind = insert_element_kind(ifiller._parent)
        if kind is not None:
            bindings.append((name, kind, ifiller))
    # Path variable declarations
    for pvd in subtree.find_all(ast.PathVariableDeclaration):
        pvd = t.cast(ast.PathVariableDeclaration, pvd)
        bindings.append((pvd.path_variable.name, "path", pvd))
    # Subpath variable declarations
    for spvd in subtree.find_all(ast.SubpathVariableDeclaration):
        spvd = t.cast(ast.SubpathVariableDeclaration, spvd)
        bindings.append((spvd.subpath_variable.name, "path", spvd))
    return bindings


def is_variable_reference(ident: ast.Identifier) -> bool:
    """True when *ident* is a binding-variable reference (not a property name, alias, or label).

    Safe default: ``False`` for any unknown context (identifier not inside
    ``BindingVariableReference``).
    """
    parent = ident._parent
    if not isinstance(parent, ast.BindingVariableReference):
        return False
    # ObjectExpressionPrimary._VariableValueExpressionPrimary is a dual-use
    # production: the identifier may refer to a catalog graph name rather than
    # a pattern-bound variable.  Exclude it to avoid false positives.
    grandparent = getattr(parent, "_parent", None)
    if isinstance(grandparent, ast.ObjectExpressionPrimary._VariableValueExpressionPrimary):
        return False
    return True


def extract_let_bound_names(subtree: ast.Expression) -> set[str]:
    """Collect variable names introduced by LetValueExpression nodes in *subtree*.

    These names are self-satisfied within the LET body and should not be
    reported as needing outer-scope resolution.
    """
    names: set[str] = set()
    for let_expr in subtree.find_all(ast.LetValueExpression):
        let_expr = t.cast(ast.LetValueExpression, let_expr)
        for defn in let_expr.let_variable_definition_list.list_let_variable_definition:
            inner = defn.let_variable_definition
            if isinstance(inner, ast.LetVariableDefinition._BindingVariableValueExpression):
                names.add(inner.binding_variable.name)
            elif isinstance(inner, ast.ValueVariableDefinition):
                names.add(inner.binding_variable.name)
    return names


def extract_comprehension_bound_names(subtree: ast.Expression) -> set[str]:
    """Collect variable names introduced by Cypher list comprehensions/predicates.

    These names (e.g. ``x`` in ``[x IN list | x * 2]``) are self-satisfied
    within the comprehension body and should not be reported as undefined.
    """
    names: set[str] = set()
    for lc in subtree.find_all(ListComprehension):
        lc = t.cast(ListComprehension, lc)
        names.add(lc.variable.name)
    for lpf in subtree.find_all(ListPredicateFunction):
        lpf = t.cast(ListPredicateFunction, lpf)
        names.add(lpf.variable.name)
    return names


def extract_variable_references(subtree: ast.Expression) -> dict[str, ast.Identifier]:
    """Extract variable reference names from a subtree, mapped to first Identifier node.

    Stops at nested subquery boundaries (NestedQuerySpecification) so that
    variables bound inside TABLE { ... } or EXISTS { ... } subqueries are
    not treated as references in the outer scope.

    Names introduced by ``LetValueExpression`` and Cypher comprehension
    bindings are subtracted — they are satisfied within their body, not by
    the enclosing scope.
    """
    refs: dict[str, ast.Identifier] = {}
    for ident in subtree.find_all(ast.Identifier):
        if isinstance(ident, ast.Identifier) and is_variable_reference(ident):
            if not is_inside_nested_subquery(ident, subtree):
                refs.setdefault(ident.name, ident)
    # Subtract LET-bound names — they're defined within the subtree.
    let_bound = extract_let_bound_names(subtree)
    if let_bound:
        for name in let_bound:
            refs.pop(name, None)
    # Subtract comprehension-bound names (Cypher list comprehension/predicate).
    comp_bound = extract_comprehension_bound_names(subtree)
    if comp_bound:
        for name in comp_bound:
            refs.pop(name, None)
    return refs
