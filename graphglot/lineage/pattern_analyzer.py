"""Pattern analysis for GQL lineage.

Extracts bindings from MATCH patterns.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from graphglot import ast
from graphglot.lineage.models import (
    Binding,
    BindingKind,
    LineageEdge,
    LineageEdgeKind,
    LineageGraph,
    Pattern,
    Span,
)

if TYPE_CHECKING:
    from graphglot.lineage.analyzer import IdGenerator


_FULL_EDGE_TYPES = (
    ast.FullEdgePointingRight,
    ast.FullEdgePointingLeft,
    ast.FullEdgeUndirected,
    ast.FullEdgeLeftOrUndirected,
    ast.FullEdgeUndirectedOrRight,
    ast.FullEdgeLeftOrRight,
    ast.FullEdgeAnyDirection,
)


class PatternAnalyzer:
    """Extract bindings from MATCH patterns."""

    def __init__(
        self,
        id_gen: IdGenerator,
        graph: LineageGraph,
        create_binding: Callable[..., Binding],
        find_binding_by_name: Callable[[str], Binding | None],
        span_from_ast: Callable[[ast.Expression], Span | None],
        text_from_ast_span: Callable[[ast.Expression], str | None],
    ):
        self._id_gen = id_gen
        self._graph = graph
        self._create_binding = create_binding
        self._find_binding_by_name = find_binding_by_name
        self._span_from_ast = span_from_ast
        self._text_from_ast_span = text_from_ast_span
        self.match_counter = 0
        self.pattern_counter = 0
        self.pattern_bindings: dict[str, list[str]] = {}
        # Inline predicates from element patterns.
        # Each entry is (binding_id_or_none, ast_expression):
        #   - WHERE inside node/edge: (None, search_condition) — deps extracted from AST
        #   - Property spec {k: v}:   (binding_id, prop_spec) — binding known from context
        self.element_predicates: list[tuple[str | None, ast.Expression]] = []

    def analyze_graph_pattern(self, graph_pattern: ast.GraphPattern) -> None:
        """Analyze a bare graph pattern (e.g. from EXISTS {(p)-(t:Test)})."""
        match_index = self.match_counter
        self.match_counter += 1
        self._analyze_graph_pattern(graph_pattern, match_index)

    def analyze_match(self, node: ast.Expression) -> ast.GraphPatternBindingTable | None:
        """Analyze a MATCH statement."""
        if isinstance(node, ast.SimpleMatchStatement):
            gp_table = node.graph_pattern_binding_table
        elif isinstance(node, ast.OptionalMatchStatement):
            optional_operand = node.optional_operand.optional_operand
            if isinstance(optional_operand, ast.SimpleMatchStatement):
                gp_table = optional_operand.graph_pattern_binding_table
            else:
                for child in optional_operand.children():
                    if isinstance(child, ast.SimpleMatchStatement | ast.OptionalMatchStatement):
                        self.analyze_match(child)
                return None
        else:
            return None

        match_index = self.match_counter
        self.match_counter += 1

        graph_pattern = gp_table.graph_pattern
        self._analyze_graph_pattern(graph_pattern, match_index)

        return gp_table

    def _analyze_graph_pattern(
        self, graph_pattern: ast.Expression, match_index: int = 0
    ) -> ast.Expression | None:
        """Analyze a graph pattern."""
        if not isinstance(graph_pattern, ast.GraphPattern):
            return None

        if graph_pattern.path_pattern_list:
            self._analyze_path_pattern_list(graph_pattern.path_pattern_list, match_index)

        # Return where clause for the caller to process
        return graph_pattern

    def _analyze_path_pattern_list(self, path_list: ast.Expression, match_index: int = 0) -> None:
        """Analyze a path pattern list."""
        if not isinstance(path_list, ast.PathPatternList):
            return

        for path_pattern in path_list.list_path_pattern:
            self.analyze_path_pattern(path_pattern, match_index)

    def next_pattern_id(self) -> str:
        """Generate the next pattern ID and advance the counter."""
        pid = f"pat_{self.pattern_counter}"
        self.pattern_counter += 1
        return pid

    def analyze_path_pattern(self, path_pattern: ast.Expression, match_index: int = 0) -> None:
        """Analyze a path pattern."""
        pattern_id = self.next_pattern_id()

        if isinstance(path_pattern, ast.PathPattern) and path_pattern.path_variable_declaration:
            var_decl = path_pattern.path_variable_declaration
            if var_decl.path_variable:
                binding = self._create_binding(
                    name=var_decl.path_variable.name,
                    kind=BindingKind.PATH,
                    pattern_id=pattern_id,
                    span=self._span_from_ast(path_pattern),
                )
                self._track_pattern_binding(pattern_id, binding.id)

        if hasattr(path_pattern, "path_pattern_expression"):
            self._analyze_path_pattern_expression(path_pattern.path_pattern_expression, pattern_id)

        binding_ids = self.pattern_bindings.get(pattern_id, [])
        span = self._span_from_ast(path_pattern)
        pattern = Pattern(
            id=pattern_id,
            span=span,
            match_index=match_index,
        )
        self._graph.nodes[pattern_id] = pattern

        # Emit IN_PATTERN edges from bindings to this pattern
        for bid in binding_ids:
            self._graph.edges.append(
                LineageEdge(source_id=bid, target_id=pattern_id, kind=LineageEdgeKind.IN_PATTERN)
            )

    def _analyze_path_pattern_expression(self, expr_node: ast.Expression, pattern_id: str) -> None:
        """Analyze a path pattern expression."""
        skip_ids: set[int] = set()

        for child in expr_node.dfs():
            if id(child) in skip_ids:
                continue

            if isinstance(child, ast.QuantifiedPathPrimary):
                inner = child.path_primary
                for desc in child.dfs():
                    if desc is not child:
                        skip_ids.add(id(desc))

                inner_edge = None
                for desc in inner.dfs():
                    if isinstance(desc, _FULL_EDGE_TYPES):
                        inner_edge = desc
                        break

                if inner_edge:
                    self._analyze_element_pattern(
                        inner_edge,
                        BindingKind.EDGE,
                        pattern_id,
                    )

            elif isinstance(child, ast.NodePattern):
                self._analyze_element_pattern(child, BindingKind.NODE, pattern_id)

            elif isinstance(child, _FULL_EDGE_TYPES):
                self._analyze_element_pattern(child, BindingKind.EDGE, pattern_id)

            elif isinstance(child, ast.AbbreviatedEdgePattern):
                pass

    def _analyze_element_pattern(
        self,
        element: ast.Expression,
        kind: BindingKind,
        pattern_id: str,
    ) -> Binding | None:
        """Analyze a node or edge element pattern and create a binding."""
        filler = getattr(element, "element_pattern_filler", None)
        if not isinstance(filler, ast.ElementPatternFiller):
            return None

        name = None
        if filler.element_variable_declaration:
            var_decl = filler.element_variable_declaration
            if var_decl.element_variable:
                name = var_decl.element_variable.name

        label_expr_text = (
            self._extract_label_expression_text(filler.is_label_expression)
            if filler.is_label_expression
            else ""
        )

        binding = self._create_binding(
            name=name,
            kind=kind,
            pattern_id=pattern_id,
            span=self._span_from_ast(element),
        )

        self._track_pattern_binding(pattern_id, binding.id)

        # Set label expression on the binding
        if label_expr_text:
            if not binding.label_expression:
                binding.label_expression = label_expr_text
            elif label_expr_text not in binding.label_expression:
                binding.label_expression += "&" + label_expr_text

        # Collect inline WHERE predicate (ElementPatternPredicate)
        if filler.element_pattern_predicate:
            pred = filler.element_pattern_predicate
            search_cond = getattr(pred, "search_condition", None)
            if search_cond:
                self.element_predicates.append((None, search_cond))
            elif isinstance(pred, ast.ElementPropertySpecification):
                self.element_predicates.append((binding.id, pred))

        return binding

    def _extract_labels(self, is_label_expr: ast.Expression) -> list[str]:
        """Extract label names from a label expression."""
        labels = []
        for child in is_label_expr.dfs():
            if isinstance(child, ast.LabelName):
                if child.identifier:
                    labels.append(child.identifier.name)
        return labels

    def _extract_label_expression_text(self, is_label_expr: ast.Expression) -> str:
        """Extract the full label expression text, preserving structure.

        Uses source text from the AST span when available, otherwise
        falls back to joining extracted label names.
        """
        # The IsLabelExpression wraps a LabelExpression — get the inner one
        inner = getattr(is_label_expr, "label_expression", is_label_expr)
        text = self._text_from_ast_span(inner)
        if text:
            return text.strip()
        # Fallback: join flat labels (loses negation/conjunction info)
        labels = self._extract_labels(is_label_expr)
        return "|".join(labels) if labels else ""

    def _track_pattern_binding(self, pattern_id: str, binding_id: str) -> None:
        """Record a binding as belonging to a pattern."""
        bindings = self.pattern_bindings.setdefault(pattern_id, [])
        if binding_id not in bindings:
            bindings.append(binding_id)
