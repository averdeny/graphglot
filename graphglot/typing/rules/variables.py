"""Type rules for variable declarations and references."""

from __future__ import annotations

from graphglot.ast import expressions as ast
from graphglot.typing.rules import type_rule
from graphglot.typing.types import GqlType


def _extract_labels(filler: ast.ElementPatternFiller) -> frozenset[str]:
    """Extract label names from an element pattern filler."""
    if filler.is_label_expression is None:
        return frozenset()
    labels: set[str] = set()
    for label_name in filler.is_label_expression.label_expression.find_all(ast.LabelName):
        if isinstance(label_name, ast.LabelName):
            labels.add(label_name.identifier.name)
    return frozenset(labels)


@type_rule(ast.ElementVariableDeclaration)
def type_element_variable_declaration(annotator, expr):
    annotator.annotate_children(expr)
    # Determine NODE vs EDGE from parent context
    parent = expr._parent
    labels = frozenset()

    if isinstance(parent, ast.ElementPatternFiller):
        labels = _extract_labels(parent)
        # Walk up to find if this is inside NodePattern or EdgePattern
        grandparent = parent._parent
        if isinstance(grandparent, ast.NodePattern):
            typ = GqlType.node(labels)
        elif isinstance(grandparent, ast.EdgePattern) or (
            grandparent is not None and isinstance(grandparent._parent, ast.EdgePattern)
        ):
            typ = GqlType.edge(labels)
        else:
            typ = GqlType.unknown()
    else:
        typ = GqlType.unknown()

    # Bind the variable in the current scope
    name = expr.element_variable.name
    annotator.current_scope.bind(name, typ, expr)
    return typ


@type_rule(ast.PathVariableDeclaration)
def type_path_variable_declaration(annotator, expr):
    annotator.annotate_children(expr)
    typ = GqlType.path()
    annotator.current_scope.bind(expr.path_variable.name, typ, expr)
    return typ


@type_rule(ast.GraphVariableDefinition)
def type_graph_variable_definition(annotator, expr):
    annotator.annotate_children(expr)
    typ = GqlType.graph()
    annotator.current_scope.bind(expr.binding_variable.name, typ, expr)
    return typ


@type_rule(ast.BindingTableVariableDefinition)
def type_binding_table_variable_definition(annotator, expr):
    annotator.annotate_children(expr)
    typ = GqlType.binding_table()
    annotator.current_scope.bind(expr.binding_variable.name, typ, expr)
    return typ


@type_rule(ast.Identifier)
def type_identifier(annotator, expr):
    """Resolve identifier type from scope (variable reference)."""
    # Skip identifiers that are property names, label names, aliases, etc.
    if isinstance(expr._parent, ast.PropertyReference) and expr._arg_key == "property_name":
        return GqlType.unknown()
    if isinstance(expr._parent, ast.ReturnItemAlias):
        return GqlType.unknown()
    if isinstance(expr._parent, ast.LabelName):
        return GqlType.unknown()
    if isinstance(expr._parent, ast.ElementVariableDeclaration):
        # The declaration itself handles typing
        return GqlType.unknown()
    if isinstance(expr._parent, ast.PathVariableDeclaration):
        return GqlType.unknown()

    # Look up in scope
    binding = annotator.current_scope.lookup(expr.name)
    if binding is not None:
        return binding.type
    return GqlType.unknown()


@type_rule(ast.GeneralParameterReference)
def type_general_parameter_reference(annotator, expr):
    annotator.annotate_children(expr)
    # Check external context for parameter types
    name = expr.parameter_name.name
    param_type = annotator.external_context.parameter_types.get(name)
    if param_type is not None:
        return param_type
    return GqlType.unknown()


@type_rule(ast.NodePattern)
def type_node_pattern(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.node()


@type_rule(ast.FullEdgePointingRight, ast.FullEdgePointingLeft, ast.FullEdgeUndirected)
def type_full_edge_pattern(annotator, expr):
    annotator.annotate_children(expr)
    return GqlType.edge()


@type_rule(ast.AbbreviatedEdgePattern)
def type_abbreviated_edge_pattern(annotator, expr):
    return GqlType.edge()
