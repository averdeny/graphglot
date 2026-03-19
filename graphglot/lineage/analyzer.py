"""GQL Lineage Analyzer.

This module provides the main entry point for lineage analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

from graphglot import ast
from graphglot.error import Span, span_from_node
from graphglot.lineage.dependency_extractor import DependencyExtractor
from graphglot.lineage.models import (
    Binding,
    BindingKind,
    ExternalContext,
    Filter,
    Graph,
    LineageEdge,
    LineageEdgeKind,
    LineageGraph,
    Mutation,
    MutationKind,
    OutputField,
    Pattern,
)
from graphglot.lineage.pattern_analyzer import PatternAnalyzer


class _ScopeKind(Enum):
    """Kind of scope boundary (internal to analyzer)."""

    ROOT = "root"
    YIELD = "yield"
    NEXT = "next"
    LET = "let"
    SUBQUERY = "subquery"
    EXISTS = "exists"
    OTHERWISE = "otherwise"


@dataclass
class _Scope:
    """Internal scope boundary used during analysis."""

    id: str
    parent_id: str | None
    kind: _ScopeKind
    graph_id: str = ""
    has_explicit_graph: bool = False

    # Binding visibility — always access via methods below.
    _visible: set[str] = field(default_factory=set, repr=False)
    _name_to_bid: dict[str, str] = field(default_factory=dict, repr=False)

    def add_binding(self, bid: str, name: str | None) -> None:
        """Make a binding visible in this scope."""
        self._visible.add(bid)
        if name is not None:
            self._name_to_bid[name] = bid

    def find_by_name(self, name: str) -> str | None:
        """Return binding ID for *name*, or None."""
        return self._name_to_bid.get(name)

    @property
    def visible_binding_ids(self) -> set[str]:
        """Read-only view of visible binding IDs."""
        return self._visible

    def inherit_from(self, parent: _Scope) -> None:
        """Copy parent's binding visibility into this scope."""
        self._visible = parent._visible.copy()
        self._name_to_bid = parent._name_to_bid.copy()

    def set_visible(self, bids: set[str], bindings_lookup: dict[str, Binding]) -> None:
        """Replace visible set wholesale (e.g. YIELD). Rebuilds name index."""
        self._visible = bids
        self._name_to_bid = {}
        for bid in bids:
            b = bindings_lookup.get(bid)
            if b and b.name is not None:
                self._name_to_bid[b.name] = bid


class _PropagatedBinding(NamedTuple):
    """A binding to propagate across a NEXT or OTHERWISE scope boundary."""

    name: str
    kind: BindingKind
    source_bid: str
    span: Span | None
    property_dep_ids: tuple[str, ...] = ()


# Aggregate functions recognized
AGGREGATE_FUNCTIONS = frozenset(
    {
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "collect",
        "stdev",
        "stdevp",
        "percentile_cont",
        "percentile_disc",
    }
)

# GeneralSetFunctionType inner variant → function name
_SET_FUNCTION_NAMES: dict[type, str] = {
    ast.GeneralSetFunctionType._Count: "count",
    ast.GeneralSetFunctionType._Avg: "avg",
    ast.GeneralSetFunctionType._Sum: "sum",
    ast.GeneralSetFunctionType._Min: "min",
    ast.GeneralSetFunctionType._Max: "max",
    ast.GeneralSetFunctionType._CollectList: "collect",
}


class IdGenerator:
    """Generate unique IDs for lineage entities."""

    def __init__(self):
        self._counters: dict[str, int] = {}

    def next(self, prefix: str) -> str:
        count = self._counters.get(prefix, 0)
        self._counters[prefix] = count + 1
        return f"{prefix}_{count}"


class LineageAnalyzer:
    """Main entry point for lineage analysis."""

    def __init__(self):
        self._id_gen = IdGenerator()
        self._graph = LineageGraph()
        self._current_scope: _Scope | None = None
        self._graph_id_for_name: dict[str, str] = {}
        # _deps and _patterns are created in analyze()
        self._deps: DependencyExtractor
        self._patterns: PatternAnalyzer

    def analyze(
        self,
        root: ast.Expression,
        external_context: ExternalContext | None = None,
        query_text: str = "",
    ) -> LineageGraph:
        """Perform full lineage analysis on a GQL AST."""
        # Reset state
        self._id_gen = IdGenerator()
        self._graph = LineageGraph(query_text=query_text)
        self._graph_id_for_name = {}

        # Create sub-components
        self._deps = DependencyExtractor(
            self._id_gen, self._graph, self._find_binding_by_name, self._span_from_ast
        )
        self._patterns = PatternAnalyzer(
            self._id_gen,
            self._graph,
            self._create_binding,
            self._find_binding_by_name,
            self._span_from_ast,
            self._text_from_ast_span,
        )

        # Create root scope
        root_scope = _Scope(
            id=self._id_gen.next("scope"),
            parent_id=None,
            kind=_ScopeKind.ROOT,
            graph_id="",
        )
        self._scopes: dict[str, _Scope] = {root_scope.id: root_scope}
        self._current_scope = root_scope

        # Seed external bindings into root scope
        ctx = external_context or ExternalContext()
        for name, kind in ctx.bindings.items():
            self._create_binding(name=name, kind=kind, pattern_id="", span=None)

        # Analyze the AST
        self._analyze_node(root)

        return self._graph

    # ------------------------------------------------------------------
    # AST utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _span_from_ast(node: ast.Expression) -> Span | None:
        """Build a Span from an AST node's token range."""
        return span_from_node(node)

    def _text_from_ast_span(self, node: ast.Expression) -> str | None:
        """Extract original query text for an AST node via its span."""
        span = node.source_span
        if span and self._graph.query_text:
            return self._graph.query_text[span[0] : span[1]]
        return None

    def _ensure_default_graph(self) -> str:
        """Lazily create and return the default graph ID."""
        gid = self._graph_id_for_name.get("(default)")
        if not gid:
            graph = Graph(id=self._id_gen.next("g"), name="(default)")
            self._graph.nodes[graph.id] = graph
            self._graph_id_for_name["(default)"] = graph.id
            gid = graph.id
        return gid

    def _get_graph_id(self) -> str:
        """Return the current graph ID, lazily creating the default if needed."""
        graph_id = self._current_scope.graph_id if self._current_scope else ""
        return graph_id or self._ensure_default_graph()

    def _emit_edges(self, source_id: str, target_ids: list[str], kind: LineageEdgeKind) -> None:
        """Create lineage edges from source to each target."""
        for tid in target_ids:
            self._graph.edges.append(LineageEdge(source_id=source_id, target_id=tid, kind=kind))

    # ------------------------------------------------------------------
    # Scope management
    # ------------------------------------------------------------------

    def _push_scope(
        self,
        kind: _ScopeKind,
        inherit_bindings: bool = True,
        inherit_graph: bool = True,
    ) -> _Scope:
        """Create a new scope, optionally inheriting parent bindings and graph context."""
        parent = self._current_scope
        inherit = parent is not None and inherit_graph
        new_scope = _Scope(
            id=self._id_gen.next("scope"),
            parent_id=parent.id if parent else None,
            kind=kind,
            graph_id=parent.graph_id if inherit and parent else "",
            has_explicit_graph=parent.has_explicit_graph if inherit and parent else False,
        )
        if inherit_bindings and parent:
            new_scope.inherit_from(parent)
        self._scopes[new_scope.id] = new_scope
        self._current_scope = new_scope
        return new_scope

    # ------------------------------------------------------------------
    # Binding management
    # ------------------------------------------------------------------

    def _create_binding(
        self,
        name: str | None,
        kind: BindingKind,
        pattern_id: str,
        span: Span | None,
        *,
        inherits_from: str | None = None,
    ) -> Binding:
        """Create a new binding and add it to the graph."""
        if name is not None:
            existing = self._find_binding_by_name(name)
            if existing:
                # Fill in span on inherited bindings when reused in MATCH
                if existing.span is None and span is not None:
                    existing.span = span
                # Reused binding is visible but not newly introduced
                if self._current_scope:
                    self._current_scope.add_binding(existing.id, name)
                return existing

        binding = Binding(
            id=self._id_gen.next("b"),
            name=name,
            kind=kind,
            scope_id=self._current_scope.id if self._current_scope else "",
            span=span,
        )
        self._graph.nodes[binding.id] = binding
        if self._current_scope:
            self._current_scope.add_binding(binding.id, name)

        if inherits_from:
            # Propagated binding — graph context derived via PROPAGATES_TO chain
            self._graph.edges.append(
                LineageEdge(
                    source_id=inherits_from,
                    target_id=binding.id,
                    kind=LineageEdgeKind.PROPAGATES_TO,
                )
            )
        elif not pattern_id:
            # Standalone binding (LET, FOR) — direct BELONGS_TO edge to graph
            graph_id = self._get_graph_id()
            if graph_id:
                self._graph.edges.append(
                    LineageEdge(
                        source_id=binding.id,
                        target_id=graph_id,
                        kind=LineageEdgeKind.BELONGS_TO,
                    )
                )

        return binding

    def _find_binding_by_name(self, name: str) -> Binding | None:
        """Find a binding by name in visible scope."""
        if not self._current_scope:
            return None
        bid = self._current_scope.find_by_name(name)
        if bid is not None:
            return self._graph.bindings.get(bid)
        return None

    # ------------------------------------------------------------------
    # Graph context extraction
    # ------------------------------------------------------------------

    _FocusedType = (
        ast.FocusedLinearQueryStatementPart
        | ast.FocusedLinearQueryAndPrimitiveResultStatementPart
        | ast.FocusedPrimitiveResultStatement
        | ast.FocusedNestedQuerySpecification
        | ast.FocusedLinearDataModifyingStatementBody
        | ast.FocusedNestedDataModifyingProcedureSpecification
    )

    def _extract_graph_name(self, use_clause: ast.UseGraphClause) -> str | None:
        """Extract graph name string from a UseGraphClause."""
        graph_expr = use_clause.graph_expression
        return self._resolve_graph_expression(graph_expr)

    def _resolve_graph_expression(self, expr: ast.Expression) -> str | None:
        """Resolve a graph expression to a name string."""
        # Bare identifier: USE g
        if isinstance(expr, ast.Identifier):
            return expr.name

        # USE CURRENT_GRAPH
        if isinstance(expr, ast.CurrentGraph):
            return "CURRENT_GRAPH"

        # USE $g (general parameter reference)
        if isinstance(expr, ast.GeneralParameterReference):
            return "$" + expr.parameter_name.name

        # GraphReference wraps several variants
        if isinstance(expr, ast.GraphReference):
            ref = expr.graph_reference

            # HomeGraph
            if isinstance(ref, ast.HomeGraph):
                return "HOME_GRAPH"

            # DelimitedGraphName (Identifier alias)
            if isinstance(ref, ast.Identifier):
                return ref.name

            # CatalogObjectParentReference + GraphName
            cat_ref_type = ast.GraphReference._CatalogObjectParentReferenceGraphName
            if isinstance(ref, cat_ref_type):
                return ref.graph_name.name

            # ReferenceParameterSpecification (SubstitutedParameterReference alias)
            if isinstance(ref, ast.SubstitutedParameterReference):
                return "$$" + ref.parameter_name.name

        # Unwrap ObjectExpressionPrimary and similar wrappers
        for child in expr.children():
            result = self._resolve_graph_expression(child)
            if result is not None:
                return result

        return None

    def _get_or_create_graph(self, name: str, ast_node: ast.Expression | None = None) -> Graph:
        """Get existing or create new Graph entity for the given name."""
        if name in self._graph_id_for_name:
            return self._graph.graphs[self._graph_id_for_name[name]]
        graph = Graph(
            id=self._id_gen.next("g"),
            name=name,
            span=self._span_from_ast(ast_node) if ast_node else None,
        )
        self._graph.nodes[graph.id] = graph
        self._graph_id_for_name[name] = graph.id
        return graph

    def _analyze_focused_statement(self, node: _FocusedType) -> None:
        """Analyze a focused statement — extract graph name, set on scope, recurse."""
        use_clause = node.use_graph_clause
        graph_name = self._extract_graph_name(use_clause)
        if graph_name and self._current_scope:
            graph = self._get_or_create_graph(graph_name, use_clause)
            self._current_scope.graph_id = graph.id
            self._current_scope.has_explicit_graph = True

        # Recurse into children, skipping the UseGraphClause itself
        for child in node.children():
            if not isinstance(child, ast.UseGraphClause):
                self._analyze_node(child)

    # ------------------------------------------------------------------
    # Node dispatch
    # ------------------------------------------------------------------

    def _analyze_node(self, node: ast.Expression) -> None:
        """Analyze an AST node and its children."""
        if isinstance(node, ast.GqlProgram):
            self._analyze_program(node)
        elif isinstance(node, self._FocusedType):
            self._analyze_focused_statement(node)
        elif isinstance(node, ast.SimpleMatchStatement | ast.OptionalMatchStatement):
            self._analyze_match(node)
        elif isinstance(node, ast.ReturnStatement):
            self._analyze_return(node)
        elif isinstance(node, ast.FilterStatement):
            self._analyze_filter(node)
        elif isinstance(node, ast.LetStatement):
            self._analyze_let(node)
        elif isinstance(node, ast.NextStatement):
            self._analyze_next(node)
        elif isinstance(node, ast.CompositeQueryExpression):
            self._analyze_composite_query(node)
        elif isinstance(node, ast.YieldClause | ast.GraphPatternYieldClause):
            self._analyze_yield(node)
        elif isinstance(node, ast.OrderByClause):
            self._analyze_order_by(node)
        elif isinstance(node, ast.ForStatement):
            self._analyze_for(node)
        elif isinstance(node, ast.SetStatement):
            self._analyze_set(node)
        elif isinstance(node, ast.RemoveStatement):
            self._analyze_remove(node)
        elif isinstance(node, ast.DeleteStatement):
            self._analyze_delete(node)
        elif isinstance(node, ast.InsertStatement):
            self._analyze_insert(node)
        elif isinstance(node, self._CypherMutationType):
            self._analyze_cypher_mutation(node)
        elif isinstance(node, ast.SelectStatement):
            from graphglot.error import UnsupportedLineageError

            raise UnsupportedLineageError(
                "SELECT statements are not yet supported by lineage analysis", node
            )
        else:
            for child in node.children():
                self._analyze_node(child)

    def _analyze_program(self, program: ast.Expression) -> None:
        """Analyze a GQL program."""
        for child in program.children():
            self._analyze_node(child)

    # ------------------------------------------------------------------
    # MATCH
    # ------------------------------------------------------------------

    def _tag_new_patterns(self, patterns_before: set[str]) -> None:
        """Emit BELONGS_TO edges from new patterns to their graph."""
        graph_id = self._get_graph_id()
        for pid in set(self._graph.patterns.keys()) - patterns_before:
            self._graph.edges.append(
                LineageEdge(source_id=pid, target_id=graph_id, kind=LineageEdgeKind.BELONGS_TO)
            )

    def _analyze_match(self, node: ast.Expression) -> None:
        """Analyze a MATCH statement."""
        patterns_before = set(self._graph.patterns.keys())
        gp_table = self._patterns.analyze_match(node)
        self._tag_new_patterns(patterns_before)

        # Handle yield clause if present
        if gp_table and gp_table.graph_pattern_yield_clause:
            self._analyze_yield(gp_table.graph_pattern_yield_clause)

        # Handle WHERE and inline predicates
        if gp_table:
            self._process_match_results(gp_table.graph_pattern)

    def _process_match_results(self, gp: ast.Expression) -> None:
        """Process WHERE clause and inline predicates after pattern analysis."""
        # Handle WHERE clause within graph pattern
        if isinstance(gp, ast.GraphPattern) and gp.graph_pattern_where_clause:
            self._analyze_where(gp.graph_pattern_where_clause.search_condition)

        # Handle inline predicates from element patterns
        for binding_id, pred_node in self._patterns.element_predicates:
            if binding_id is not None:
                # Property spec {k: v} — binding known from pattern context
                self._analyze_property_spec(binding_id, pred_node)
            else:
                # WHERE inside node/edge — deps extracted from AST
                self._analyze_where(pred_node)
        self._patterns.element_predicates.clear()

    # ------------------------------------------------------------------
    # RETURN
    # ------------------------------------------------------------------

    def _analyze_return(self, return_stmt: ast.Expression) -> None:
        """Analyze a RETURN statement."""
        if not isinstance(return_stmt, ast.ReturnStatement):
            return

        body = return_stmt.return_statement_body
        if not body:
            return

        inner = body.return_statement_body

        # Check for DISTINCT on the inner variant
        is_distinct = False
        sq = getattr(inner, "set_quantifier", None)
        if sq is not None:
            is_distinct = sq.set_quantifier == ast.SetQuantifier.Quantifier.DISTINCT

        return_items = self._get_return_items(inner)

        position = 0
        for item in return_items:
            output = self._analyze_return_item(item, position, is_distinct)
            if output:
                position += 1

    def _get_return_items(self, inner: ast.Expression) -> list[ast.Expression]:
        """Extract return items from inner ReturnStatementBody variant."""
        if isinstance(inner, ast.ReturnStatementBody._SetQuantifierReturnItemListGroupByClause):
            return list(inner.return_item_list.list_return_item)
        return []

    def _analyze_return_item(
        self, item: ast.Expression, position: int, is_distinct: bool
    ) -> OutputField | None:
        """Analyze a single return item."""
        if not isinstance(item, ast.ReturnItem):
            return None

        # Get alias
        alias = None
        if hasattr(item, "return_item_alias") and item.return_item_alias:
            alias_node = item.return_item_alias
            if hasattr(alias_node, "identifier") and alias_node.identifier:
                alias = alias_node.identifier.name

        agg_expr = item.aggregating_value_expression

        # Check for aggregation
        is_aggregated = False
        aggregate_function = None
        for child in agg_expr.dfs():
            if isinstance(child, ast.AggregateFunction):
                agg_func = getattr(child, "aggregate_function", None)
                if isinstance(agg_func, ast.AggregateFunction._CountAsterisk):
                    is_aggregated = True
                    aggregate_function = "count"
                    break

            if isinstance(child, ast.GeneralSetFunctionType):
                func_type = getattr(child, "general_set_function_type", None)
                if func_type is not None:
                    func_name = _SET_FUNCTION_NAMES.get(type(func_type))
                    if func_name:
                        is_aggregated = True
                        aggregate_function = func_name
                        break

        binding_deps, property_deps = self._deps.extract_deps(agg_expr)

        output = OutputField(
            id=self._id_gen.next("o"),
            alias=alias,
            position=position,
            span=self._span_from_ast(item),
            is_aggregated=is_aggregated,
            aggregate_function=aggregate_function,
            is_distinct=is_distinct,
            scope_id=self._current_scope.id if self._current_scope else "",
        )
        self._graph.nodes[output.id] = output

        # Bindings already reachable via property refs don't need direct edges
        direct_binding_deps = self._dedup_binding_deps(binding_deps, property_deps)

        agg_kind = LineageEdgeKind.AGGREGATES if is_aggregated else LineageEdgeKind.DEPENDS_ON
        self._emit_edges(output.id, direct_binding_deps, agg_kind)
        self._emit_edges(output.id, property_deps, LineageEdgeKind.DEPENDS_ON)

        # Outputs without any deps get BELONGS_TO only when an explicit USE graph is set
        if not binding_deps and not property_deps:
            scope = self._current_scope
            if scope and scope.has_explicit_graph:
                self._graph.edges.append(
                    LineageEdge(
                        source_id=output.id,
                        target_id=scope.graph_id,
                        kind=LineageEdgeKind.BELONGS_TO,
                    )
                )

        return output

    # ------------------------------------------------------------------
    # WHERE / FILTER / ORDER BY
    # ------------------------------------------------------------------

    def _scan_exists_predicates(self, expr: ast.Expression) -> None:
        """Scan direct children for EXISTS predicates and analyze inner patterns.

        Uses children() instead of dfs() to avoid recursing into nested EXISTS
        predicates — those will be handled when their own WHERE is analyzed.
        """
        for child in expr.children():
            if isinstance(child, ast.ExistsPredicate):
                self._analyze_exists(child)
            else:
                self._scan_exists_predicates(child)

    def _analyze_exists(self, exists_pred: ast.ExistsPredicate) -> None:
        """Analyze inner patterns of an EXISTS predicate."""
        inner = exists_pred.exists_predicate

        # Save current scope, push EXISTS scope (inherits outer bindings)
        outer_scope = self._current_scope
        self._push_scope(_ScopeKind.EXISTS, inherit_bindings=True)

        if isinstance(inner, ast.ExistsPredicate._ExistsGraphPattern):
            # EXISTS {(p)-(t:Test)} — bare graph pattern
            gp = inner.graph_pattern
            patterns_before = set(self._graph.patterns.keys())
            self._patterns.analyze_graph_pattern(gp)
            self._tag_new_patterns(patterns_before)
            self._process_match_results(gp)

        elif isinstance(inner, ast.ExistsPredicate._ExistsMatchStatementBlock):
            # EXISTS {MATCH (p)-(t) WHERE ...} — match statement block
            for match_stmt in inner.match_statement_block.list_match_statement:
                self._analyze_node(match_stmt)

        # Restore outer scope
        self._current_scope = outer_scope

    def _analyze_where(self, search_condition: ast.Expression) -> None:
        """Analyze a WHERE search condition."""
        # Track bindings before EXISTS analysis to capture new inner bindings
        bindings_before = set(self._graph.bindings.keys())

        # Analyze inner EXISTS subquery patterns first
        self._scan_exists_predicates(search_condition)

        binding_deps, property_deps = self._deps.extract_deps(search_condition)

        # Include bindings created inside EXISTS subqueries
        exists_bindings = set(self._graph.bindings.keys()) - bindings_before
        for bid in exists_bindings:
            if bid not in binding_deps:
                binding_deps.append(bid)

        filt = Filter(
            id=self._id_gen.next("f"),
            span=self._span_from_ast(search_condition),
        )
        self._graph.nodes[filt.id] = filt

        direct_binding_deps = self._dedup_binding_deps(binding_deps, property_deps)
        self._emit_edges(filt.id, direct_binding_deps, LineageEdgeKind.CONSTRAINS)
        self._emit_edges(filt.id, property_deps, LineageEdgeKind.CONSTRAINS)

    def _analyze_property_spec(self, binding_id: str, prop_spec: ast.Expression) -> None:
        """Analyze an ElementPropertySpecification ({key: val}) as a filter."""
        filt = Filter(
            id=self._id_gen.next("f"),
            span=self._span_from_ast(prop_spec),
        )
        self._graph.nodes[filt.id] = filt
        self._emit_edges(filt.id, [binding_id], LineageEdgeKind.CONSTRAINS)

        if isinstance(prop_spec, ast.ElementPropertySpecification):
            for pair in prop_spec.property_key_value_pair_list.list_property_key_value_pair:
                binding_deps, property_deps = self._deps.extract_deps(pair.value_expression)
                direct_binding_deps = self._dedup_binding_deps(binding_deps, property_deps)
                self._emit_edges(filt.id, direct_binding_deps, LineageEdgeKind.CONSTRAINS)
                self._emit_edges(filt.id, property_deps, LineageEdgeKind.CONSTRAINS)

    def _dedup_binding_deps(self, binding_deps: list[str], property_deps: list[str]) -> list[str]:
        """Filter out bindings already reachable through property refs."""
        prop_bindings: set[str] = set()
        for pid in property_deps:
            prop_bindings.update(self._graph.targets(pid, LineageEdgeKind.DEPENDS_ON))
        return [bid for bid in binding_deps if bid not in prop_bindings]

    def _analyze_order_by(self, order_by: ast.Expression) -> None:
        """Analyze an ORDER BY clause."""
        current_scope_id = self._current_scope.id if self._current_scope else ""
        scope_outputs = [o for o in self._graph.outputs.values() if o.scope_id == current_scope_id]
        for child in order_by.dfs():
            if isinstance(child, ast.SortSpecification):
                sort_key = child.sort_key
                binding_deps, property_deps = self._deps.extract_deps(sort_key)
                direct_binding_deps = self._dedup_binding_deps(binding_deps, property_deps)
                order_deps = direct_binding_deps + property_deps
                for output in scope_outputs:
                    self._emit_edges(output.id, order_deps, LineageEdgeKind.ORDERED_BY)

    def _analyze_filter(self, filter_clause: ast.Expression) -> None:
        """Analyze a FILTER statement (contains a WhereClause)."""
        where = getattr(filter_clause, "filter_statement", None)
        if isinstance(where, ast.WhereClause) and where.search_condition:
            self._analyze_where(where.search_condition)

    # ------------------------------------------------------------------
    # LET / FOR / NEXT / YIELD
    # ------------------------------------------------------------------

    def _analyze_let(self, let_clause: ast.Expression) -> None:
        """Analyze a LET clause."""
        self._push_scope(_ScopeKind.LET)

        if isinstance(let_clause, ast.LetStatement):
            for defn in let_clause.let_variable_definition_list.list_let_variable_definition:
                inner = defn.let_variable_definition
                if isinstance(inner, ast.LetVariableDefinition._BindingVariableValueExpression):
                    binding = self._create_binding(
                        name=inner.binding_variable.name,
                        kind=BindingKind.VARIABLE,
                        pattern_id="",
                        span=self._span_from_ast(inner.binding_variable),
                    )
                    binding_deps, property_deps = self._deps.extract_deps(inner.value_expression)
                    direct_binding_deps = self._dedup_binding_deps(binding_deps, property_deps)
                    self._emit_edges(binding.id, direct_binding_deps, LineageEdgeKind.DEPENDS_ON)
                    self._emit_edges(binding.id, property_deps, LineageEdgeKind.DEPENDS_ON)

    def _analyze_for(self, node: ast.Expression) -> None:
        """Analyze a FOR statement — introduces binding variable(s)."""
        if not isinstance(node, ast.ForStatement):
            return

        var_name = node.for_item.for_item_alias.binding_variable.name
        binding = self._create_binding(
            name=var_name,
            kind=BindingKind.VARIABLE,
            pattern_id="",
            span=None,
        )

        if node.for_ordinality_or_offset is not None:
            ord_name = node.for_ordinality_or_offset.binding_variable.name
            self._create_binding(
                name=ord_name,
                kind=BindingKind.VARIABLE,
                pattern_id="",
                span=None,
            )

        # Extract deps from the source expression (e.g. n.tags in FOR tag IN n.tags)
        # Link them to the loop variable so impact traces through.
        source = node.for_item.for_item_source
        if source:
            binding_deps, property_deps = self._deps.extract_deps(source)
            direct = self._dedup_binding_deps(binding_deps, property_deps)
            self._emit_edges(binding.id, direct, LineageEdgeKind.DEPENDS_ON)
            self._emit_edges(binding.id, property_deps, LineageEdgeKind.DEPENDS_ON)

        for child in node.children():
            self._analyze_node(child)

    def _remove_scope_outputs(self, scope_id: str) -> None:
        """Remove all OutputField entities and their edges for a scope."""
        output_ids = {
            oid
            for oid, node in self._graph.nodes.items()
            if isinstance(node, OutputField) and node.scope_id == scope_id
        }
        if not output_ids:
            return
        for oid in output_ids:
            del self._graph.nodes[oid]
        self._graph.edges = [
            e
            for e in self._graph.edges
            if e.source_id not in output_ids and e.target_id not in output_ids
        ]

    def _analyze_next(self, next_stmt: ast.Expression) -> None:
        """Analyze a NEXT statement (scope boundary)."""
        current_scope_id = self._current_scope.id if self._current_scope else ""
        # Span comes from the OutputField — the RETURN item that defines
        # this binding for the next scope (e.g. "s.name AS supplier").
        propagated: list[_PropagatedBinding] = []
        for output in self._graph.outputs.values():
            if output.scope_id != current_scope_id:
                continue
            dep_bids = self._graph.binding_deps(output.id)
            # Collect property ref IDs for aliased outputs (e.g. n.name AS name)
            prop_dep_ids = [
                tid
                for tid in (
                    self._graph.targets(output.id, LineageEdgeKind.DEPENDS_ON)
                    + self._graph.targets(output.id, LineageEdgeKind.AGGREGATES)
                )
                if tid in self._graph.property_refs
            ]
            if output.alias:
                # Try to find original binding kind for the alias
                kind = BindingKind.VARIABLE
                source_bid = dep_bids[0] if dep_bids else ""
                for bid in dep_bids:
                    binding = self._graph.bindings.get(bid)
                    if binding:
                        kind = binding.kind
                        break
                propagated.append(
                    _PropagatedBinding(
                        output.alias, kind, source_bid, output.span, tuple(prop_dep_ids)
                    )
                )
            elif dep_bids:
                for bid in dep_bids:
                    binding = self._graph.bindings.get(bid)
                    if binding and binding.scope_id == current_scope_id:
                        propagated.append(
                            _PropagatedBinding(binding.name, binding.kind, bid, output.span)
                        )

        # Remove intermediate outputs — they feed the next scope, not the caller
        self._remove_scope_outputs(current_scope_id)

        self._push_scope(_ScopeKind.NEXT, inherit_bindings=False, inherit_graph=False)

        yielded_names: set[str] | None = None
        if isinstance(next_stmt, ast.NextStatement) and next_stmt.yield_clause:
            yielded_names = set()
            for child in next_stmt.yield_clause.dfs():
                if isinstance(child, ast.Identifier):
                    yielded_names.add(child.name)

        for pb in propagated:
            if yielded_names is not None and pb.name not in yielded_names:
                continue
            binding = self._create_binding(
                name=pb.name,
                kind=pb.kind,
                pattern_id="",
                span=pb.span,
                inherits_from=pb.source_bid or None,
            )
            if pb.property_dep_ids:
                self._emit_edges(binding.id, list(pb.property_dep_ids), LineageEdgeKind.DEPENDS_ON)

        for child in next_stmt.children():
            self._analyze_node(child)

    def _analyze_composite_query(self, node: ast.CompositeQueryExpression) -> None:
        """Analyze a composite query, handling OTHERWISE branches."""
        # Process the left (main) branch
        self._analyze_node(node.left_composite_query_primary)

        if not node.query_conjunction_elements:
            return

        # Save scope before processing conjunction elements
        pre_conjunction_scope = self._current_scope

        for element in node.query_conjunction_elements:
            conj = element.query_conjunction.query_conjunction
            if isinstance(conj, ast.QueryConjunction._Otherwise):
                self._analyze_otherwise(element, pre_conjunction_scope)
            else:
                # UNION / EXCEPT / INTERSECT — just walk children
                for child in element.children():
                    self._analyze_node(child)

    def _analyze_otherwise(
        self,
        element: ast.CompositeQueryExpression._QueryConjunctionElement,
        pre_conjunction_scope: _Scope | None,
    ) -> None:
        """Analyze an OTHERWISE branch with its own independent scope."""
        # Determine the root (pre-NEXT) scope
        root_scope_id = (
            pre_conjunction_scope.parent_id
            if pre_conjunction_scope and pre_conjunction_scope.parent_id
            else (pre_conjunction_scope.id if pre_conjunction_scope else None)
        )

        # Collect bindings visible in the root scope.
        # NOTE: span comes from the root Binding (e.g. "(n)" in the MATCH
        # pattern), not from an OutputField as in _analyze_next.  The root
        # scope's OutputFields have already been deleted by
        # _remove_scope_outputs during the preceding _analyze_next call, so
        # the Binding span is the best available provenance.  This means
        # NEXT-propagated spans point at the RETURN item while OTHERWISE-
        # propagated spans point at the MATCH pattern — a known asymmetry.
        propagated: list[_PropagatedBinding] = []
        if root_scope_id:
            root_scope = self._scopes.get(root_scope_id)
            if root_scope:
                for bid in root_scope.visible_binding_ids:
                    binding = self._graph.bindings.get(bid)
                    if binding and binding.name is not None:
                        propagated.append(
                            _PropagatedBinding(binding.name, binding.kind, bid, binding.span)
                        )

        # Create a fresh scope for OTHERWISE, parented to the root scope
        if root_scope_id:
            root = self._scopes.get(root_scope_id)
            if root:
                self._current_scope = root
        self._push_scope(_ScopeKind.OTHERWISE, inherit_bindings=False, inherit_graph=False)

        # Propagate bindings from the root scope into OTHERWISE
        for pb in propagated:
            self._create_binding(
                name=pb.name,
                kind=pb.kind,
                pattern_id="",
                span=pb.span,
                inherits_from=pb.source_bid,
            )

        # Analyze the OTHERWISE branch content
        self._analyze_node(element.composite_query_primary)

    def _analyze_yield(self, yield_clause: ast.Expression) -> None:
        """Analyze a YIELD clause."""
        yielded_bindings = set()
        for child in yield_clause.dfs():
            if isinstance(child, ast.Identifier):
                binding = self._find_binding_by_name(child.name)
                if binding:
                    yielded_bindings.add(binding.id)

        scope = self._push_scope(_ScopeKind.YIELD, inherit_bindings=False)
        all_bindings = self._graph.bindings
        lookup = {bid: all_bindings[bid] for bid in yielded_bindings if bid in all_bindings}
        scope.set_visible(yielded_bindings, lookup)

    # ------------------------------------------------------------------
    # Mutations (SET / REMOVE / DELETE / INSERT / CREATE / MERGE)
    # ------------------------------------------------------------------

    # Cypher AST types for mutation analysis.
    from graphglot.ast.cypher import (
        CreateClause,
        CypherSetAllFromExprItem,
        CypherSetMapAppendItem,
        CypherSetPropertyFromExprItem,
        MergeClause,
    )

    _CypherMutationType: tuple[type, ...] = (CreateClause, MergeClause)

    def _create_mutation(
        self,
        kind: MutationKind,
        span: Span | None = None,
        *,
        label_name: str | None = None,
        is_detach: bool = False,
    ) -> Mutation:
        """Create a Mutation entity and add it to the graph."""
        mut = Mutation(
            id=self._id_gen.next("mut"),
            kind=kind,
            label_name=label_name,
            is_detach=is_detach,
            scope_id=self._current_scope.id if self._current_scope else "",
            span=span,
        )
        self._graph.nodes[mut.id] = mut
        return mut

    def _resolve_binding_var(self, bvr: ast.Expression) -> Binding | None:
        """Resolve a BindingVariableReference to a Binding in scope."""
        if isinstance(bvr, ast.BindingVariableReference):
            return self._find_binding_by_name(bvr.binding_variable.name)
        return None

    def _emit_writes(self, mut_id: str, binding: Binding | None) -> None:
        """Emit a WRITES edge from a mutation to a target binding if present."""
        if binding:
            self._emit_edges(mut_id, [binding.id], LineageEdgeKind.WRITES)

    def _emit_value_deps(self, mut_id: str, expr: ast.Expression) -> None:
        """Extract dependencies from a value expression and emit DEPENDS_ON edges."""
        binding_deps, property_deps = self._deps.extract_deps(expr)
        direct = self._dedup_binding_deps(binding_deps, property_deps)
        self._emit_edges(mut_id, direct, LineageEdgeKind.DEPENDS_ON)
        self._emit_edges(mut_id, property_deps, LineageEdgeKind.DEPENDS_ON)

    # ── SET ───────────────────────────────────────────────────────

    def _analyze_set(self, node: ast.SetStatement) -> None:
        """Analyze a SET statement — walk each set item."""
        for item in node.set_item_list.list_set_item:
            self._analyze_set_item(item)

    def _analyze_set_item(self, item: ast.Expression) -> None:
        """Analyze a single SET item, dispatching by type."""
        if isinstance(item, ast.SetPropertyItem):
            binding = self._resolve_binding_var(item.binding_variable_reference)
            mut = self._create_mutation(
                MutationKind.SET_PROPERTY,
                self._span_from_ast(item),
            )
            if binding:
                prop_ref = self._deps.get_or_create_property_ref(
                    binding.id, item.property_name.identifier.name, item
                )
                self._emit_edges(mut.id, [prop_ref.id], LineageEdgeKind.WRITES)
            self._emit_value_deps(mut.id, item.value_expression)

        elif isinstance(item, ast.SetAllPropertiesItem):
            binding = self._resolve_binding_var(item.binding_variable_reference)
            mut = self._create_mutation(MutationKind.SET_ALL, self._span_from_ast(item))
            self._emit_writes(mut.id, binding)
            if item.property_key_value_pair_list:
                self._emit_value_deps(mut.id, item.property_key_value_pair_list)

        elif isinstance(item, ast.SetLabelItem):
            binding = self._resolve_binding_var(item.binding_variable_reference)
            mut = self._create_mutation(
                MutationKind.SET_LABEL,
                self._span_from_ast(item),
                label_name=item.label_name.identifier.name,
            )
            self._emit_writes(mut.id, binding)

        elif isinstance(item, self.CypherSetMapAppendItem):
            binding = self._resolve_binding_var(item.binding_variable_reference)
            mut = self._create_mutation(MutationKind.SET_ALL, self._span_from_ast(item))
            self._emit_writes(mut.id, binding)
            self._emit_value_deps(mut.id, item.map_expression)

        elif isinstance(item, self.CypherSetAllFromExprItem):
            binding = self._resolve_binding_var(item.binding_variable_reference)
            mut = self._create_mutation(MutationKind.SET_ALL, self._span_from_ast(item))
            self._emit_writes(mut.id, binding)
            self._emit_value_deps(mut.id, item.value)

        elif isinstance(item, self.CypherSetPropertyFromExprItem):
            mut = self._create_mutation(
                MutationKind.SET_PROPERTY,
                self._span_from_ast(item),
            )
            # target_expression may reference a binding
            target_deps, _ = self._deps.extract_deps(item.target_expression)
            if target_deps:
                prop_ref = self._deps.get_or_create_property_ref(
                    target_deps[0], item.property_name.identifier.name, item
                )
                self._emit_edges(mut.id, [prop_ref.id], LineageEdgeKind.WRITES)
            self._emit_value_deps(mut.id, item.value)

    # ── REMOVE ────────────────────────────────────────────────────

    def _analyze_remove(self, node: ast.RemoveStatement) -> None:
        """Analyze a REMOVE statement — walk each remove item."""
        for item in node.remove_item_list.list_remove_item:
            if isinstance(item, ast.RemovePropertyItem):
                binding = self._resolve_binding_var(item.binding_variable_reference)
                mut = self._create_mutation(
                    MutationKind.REMOVE_PROPERTY,
                    self._span_from_ast(item),
                )
                if binding:
                    prop_ref = self._deps.get_or_create_property_ref(
                        binding.id, item.property_name.identifier.name, item
                    )
                    self._emit_edges(mut.id, [prop_ref.id], LineageEdgeKind.WRITES)

            elif isinstance(item, ast.RemoveLabelItem):
                binding = self._resolve_binding_var(item.binding_variable_reference)
                mut = self._create_mutation(
                    MutationKind.REMOVE_LABEL,
                    self._span_from_ast(item),
                    label_name=item.label_name.identifier.name,
                )
                self._emit_writes(mut.id, binding)

    # ── DELETE ────────────────────────────────────────────────────

    def _analyze_delete(self, node: ast.DeleteStatement) -> None:
        """Analyze a DELETE statement — one mutation per delete item."""
        is_detach = node.mode == ast.DeleteStatement.Mode.DETACH
        for item in node.delete_item_list.list_delete_item:
            binding_deps, _ = self._deps.extract_deps(item)
            mut = self._create_mutation(
                MutationKind.DELETE,
                self._span_from_ast(item),
                is_detach=is_detach,
            )
            # Each referenced binding is a write target
            for bid in binding_deps:
                self._emit_edges(mut.id, [bid], LineageEdgeKind.WRITES)

    # ── INSERT (GQL) ──────────────────────────────────────────────

    def _analyze_insert(self, node: ast.InsertStatement) -> None:
        """Analyze GQL INSERT — creates bindings from insert patterns."""
        self._analyze_insert_graph_pattern(node.insert_graph_pattern)

    def _analyze_insert_graph_pattern(self, igp: ast.Expression) -> None:
        """Walk InsertPathPatternList, create bindings and mutations."""
        if not isinstance(igp, ast.InsertPathPatternList):
            return
        patterns_before = set(self._graph.patterns.keys())
        for ipp in igp.list_insert_path_pattern:
            binding_ids, prop_ref_ids = self._analyze_insert_path_pattern(ipp)
            mut = self._create_mutation(MutationKind.INSERT, self._span_from_ast(ipp))
            # Only WRITES→binding when no prop_refs already cover it
            covered = {
                self._graph.targets(pid, LineageEdgeKind.DEPENDS_ON)[0]
                for pid in prop_ref_ids
                if self._graph.targets(pid, LineageEdgeKind.DEPENDS_ON)
            }
            uncovered = [bid for bid in binding_ids if bid not in covered]
            self._emit_edges(mut.id, uncovered, LineageEdgeKind.WRITES)
            self._emit_edges(mut.id, prop_ref_ids, LineageEdgeKind.WRITES)
        self._tag_new_patterns(patterns_before)

    def _analyze_insert_path_pattern(
        self, ipp: ast.InsertPathPattern
    ) -> tuple[list[str], list[str]]:
        """Analyze one InsertPathPattern, returning (binding_ids, prop_ref_ids)."""
        # Create a Pattern for this path
        pattern_id = self._patterns.next_pattern_id()
        pattern = Pattern(
            id=pattern_id,
            span=self._span_from_ast(ipp),
            match_index=-1,
        )
        self._graph.nodes[pattern_id] = pattern

        binding_ids: list[str] = []
        prop_ref_ids: list[str] = []

        # First node
        bid, prids = self._analyze_insert_node(ipp.insert_node_pattern)
        if bid:
            binding_ids.append(bid)
            prop_ref_ids.extend(prids)
        # Edge-node pairs
        if ipp.list_insert_edge_pattern_insert_node_pattern:
            for pair in ipp.list_insert_edge_pattern_insert_node_pattern:
                edge_bid, edge_prids = self._analyze_insert_edge(pair.insert_edge_pattern)
                if edge_bid:
                    binding_ids.append(edge_bid)
                    prop_ref_ids.extend(edge_prids)
                node_bid, node_prids = self._analyze_insert_node(pair.insert_node_pattern)
                if node_bid:
                    binding_ids.append(node_bid)
                    prop_ref_ids.extend(node_prids)

        # Link bindings to pattern
        for bid in binding_ids:
            self._graph.edges.append(
                LineageEdge(source_id=bid, target_id=pattern_id, kind=LineageEdgeKind.IN_PATTERN)
            )

        return binding_ids, prop_ref_ids

    _InsertFillerResult = tuple[str | None, list[str]]

    def _analyze_insert_node(self, node: ast.InsertNodePattern) -> _InsertFillerResult:
        """Extract binding from an InsertNodePattern."""
        if not node.insert_element_pattern_filler:
            return None, []
        return self._analyze_insert_filler(node.insert_element_pattern_filler, BindingKind.NODE)

    def _analyze_insert_edge(self, edge: ast.Expression) -> _InsertFillerResult:
        """Extract binding from an InsertEdgePattern variant."""
        if not isinstance(
            edge,
            ast.InsertEdgePointingLeft | ast.InsertEdgePointingRight | ast.InsertEdgeUndirected,
        ):
            return None, []
        filler = edge.insert_element_pattern_filler
        if not filler:
            return None, []
        return self._analyze_insert_filler(filler, BindingKind.EDGE)

    def _analyze_insert_filler(
        self, filler: ast.InsertElementPatternFiller, kind: BindingKind
    ) -> _InsertFillerResult:
        """Extract variable name and properties from InsertElementPatternFiller."""
        inner = filler.insert_element_pattern_filler
        evd_type = ast.InsertElementPatternFiller._ElementVariableDeclarationLabelAndPropertySetSpecification  # noqa: E501
        name: str | None = None
        label_text = ""
        lps: ast.Expression | None = None

        if isinstance(inner, ast.ElementVariableDeclaration):
            name = inner.element_variable.name
        elif isinstance(inner, evd_type):
            name = inner.element_variable_declaration.element_variable.name
            lps = inner.label_and_property_set_specification
            label_text = self._extract_insert_label_text(lps)
        elif isinstance(inner, ast.LabelAndPropertySetSpecification):
            lps = inner
            label_text = self._extract_insert_label_text(lps)

        binding = self._create_binding(
            name=name,
            kind=kind,
            pattern_id="",
            span=self._span_from_ast(filler),
        )
        if label_text and not binding.label_expression:
            binding.label_expression = label_text

        # Extract property refs from inline property spec
        prop_ref_ids = self._extract_insert_property_refs(binding.id, lps) if lps else []

        return binding.id, prop_ref_ids

    def _extract_insert_property_refs(self, binding_id: str, lps: ast.Expression) -> list[str]:
        """Create PropertyRef entities for each property key in an INSERT property spec."""
        prop_ref_ids: list[str] = []
        for child in lps.dfs():
            if isinstance(child, ast.PropertyKeyValuePair):
                prop_name = child.property_name.identifier.name
                prop_ref = self._deps.get_or_create_property_ref(binding_id, prop_name, child)
                prop_ref_ids.append(prop_ref.id)
        return prop_ref_ids

    def _extract_insert_label_text(self, lps: ast.Expression) -> str:
        """Extract label text from a LabelAndPropertySetSpecification."""
        labels: list[str] = []
        for child in lps.dfs():
            if isinstance(child, ast.LabelName) and child.identifier:
                labels.append(child.identifier.name)
        return "&".join(labels) if labels else ""

    # ── CREATE / MERGE (Cypher) ───────────────────────────────────

    def _analyze_cypher_mutation(self, node: ast.Expression) -> None:
        """Dispatch Cypher CREATE or MERGE nodes."""
        if isinstance(node, self.CreateClause):
            self._analyze_create(node)
        elif isinstance(node, self.MergeClause):
            self._analyze_merge(node)

    def _analyze_create(self, node: CreateClause) -> None:
        """Analyze Cypher CREATE — same as GQL INSERT."""
        self._analyze_insert_graph_pattern(node.insert_graph_pattern)

    def _analyze_merge(self, node: MergeClause) -> None:
        """Analyze Cypher MERGE — match-or-create with optional SET clauses."""

        # Analyze path pattern like a MATCH to create bindings
        patterns_before = set(self._graph.patterns.keys())
        self._patterns.analyze_path_pattern(node.path_pattern, self._patterns.match_counter)
        self._patterns.match_counter += 1
        self._tag_new_patterns(patterns_before)

        # Process inline predicates from pattern
        for binding_id, pred_node in self._patterns.element_predicates:
            if binding_id is not None:
                self._analyze_property_spec(binding_id, pred_node)
            else:
                self._analyze_where(pred_node)
        self._patterns.element_predicates.clear()

        # Collect binding IDs from the pattern
        pattern_binding_ids: list[str] = []
        for pid in set(self._graph.patterns.keys()) - patterns_before:
            for bid in self._patterns.pattern_bindings.get(pid, []):
                if bid not in pattern_binding_ids:
                    pattern_binding_ids.append(bid)

        # Create MERGE mutation
        mut = self._create_mutation(MutationKind.MERGE, self._span_from_ast(node))
        self._emit_edges(mut.id, pattern_binding_ids, LineageEdgeKind.WRITES)

        # ON CREATE SET / ON MATCH SET
        if node.on_create_set:
            for item in node.on_create_set.list_set_item:
                self._analyze_set_item(item)
        if node.on_match_set:
            for item in node.on_match_set.list_set_item:
                self._analyze_set_item(item)
