"""Dependency extraction for GQL lineage.

Walks expressions to find binding/property references.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from graphglot import ast
from graphglot.lineage.models import (
    Binding,
    LineageEdge,
    LineageEdgeKind,
    LineageGraph,
    PropertyRef,
    Span,
)
from graphglot.scope import is_variable_reference

if TYPE_CHECKING:
    from graphglot.lineage.analyzer import IdGenerator


class DependencyExtractor:
    """Walk expressions to find binding/property references."""

    def __init__(
        self,
        id_gen: IdGenerator,
        graph: LineageGraph,
        find_binding_by_name: Callable[[str], Binding | None],
        span_from_ast: Callable[[ast.Expression], Span | None],
    ):
        self._id_gen = id_gen
        self._graph = graph
        self._find_binding_by_name = find_binding_by_name
        self._span_from_ast = span_from_ast
        # Dedup index: (binding_id, property_name) -> PropertyRef
        self._prop_ref_index: dict[tuple[str, str], PropertyRef] = {}

    def extract_deps(
        self,
        expr_node: ast.Expression,
    ) -> tuple[list[str], list[str]]:
        """Extract binding and property dependency IDs from an expression."""
        binding_deps: list[str] = []
        property_deps: list[str] = []
        self._extract_expression_deps(expr_node, binding_deps, property_deps)
        return binding_deps, property_deps

    def _extract_expression_deps(
        self,
        expr_node: ast.Expression,
        binding_deps: list[str],
        property_deps: list[str],
    ) -> None:
        """Extract binding and property dependencies from an expression."""
        for child in expr_node.dfs():
            # Property reference like n.name
            if isinstance(child, ast.PropertyReference):
                prop_source = child.property_source
                binding_name = self._get_binding_name_from_source(prop_source)
                if binding_name:
                    binding = self._find_binding_by_name(binding_name)
                    if binding:
                        prop_names = [p.identifier.name for p in child.property_name]
                        prop_name = ".".join(prop_names)
                        prop_ref = self.get_or_create_property_ref(
                            binding.id, prop_name, span_node=child
                        )
                        property_deps.append(prop_ref.id)
                        if binding.id not in binding_deps:
                            binding_deps.append(binding.id)

            # Direct binding reference (filtered by scope utility)
            elif isinstance(child, ast.Identifier):
                # Skip identifiers that are property sources — already handled above
                grandparent = getattr(getattr(child, "_parent", None), "_parent", None)
                if isinstance(grandparent, ast.PropertyReference):
                    continue
                # Element variable declarations inside subqueries (e.g. EXISTS {MATCH (p)-()})
                # reference outer bindings by reusing the name
                parent = getattr(child, "_parent", None)
                if isinstance(parent, ast.ElementVariableDeclaration):
                    binding = self._find_binding_by_name(child.name)
                    if binding and binding.id not in binding_deps:
                        binding_deps.append(binding.id)
                    continue
                if not is_variable_reference(child):
                    continue
                binding = self._find_binding_by_name(child.name)
                if binding:
                    if binding.id not in binding_deps:
                        binding_deps.append(binding.id)

    def _get_binding_name_from_source(self, prop_source: ast.Expression) -> str | None:
        """Extract binding name from a property source."""
        for child in prop_source.dfs():
            if isinstance(child, ast.Identifier):
                return child.name
        return None

    def get_or_create_property_ref(
        self,
        binding_id: str,
        property_name: str,
        span_node: ast.Expression | None = None,
    ) -> PropertyRef:
        """Get existing or create new property reference."""
        key = (binding_id, property_name)
        existing = self._prop_ref_index.get(key)
        if existing is not None:
            return existing

        span = self._span_from_ast(span_node) if span_node else None
        prop_ref = PropertyRef(
            id=self._id_gen.next("prop"),
            property_name=property_name,
            span=span,
        )
        self._graph.nodes[prop_ref.id] = prop_ref
        self._prop_ref_index[key] = prop_ref

        edge = LineageEdge(
            source_id=prop_ref.id,
            target_id=binding_id,
            kind=LineageEdgeKind.DEPENDS_ON,
        )
        self._graph.edges.append(edge)

        return prop_ref
