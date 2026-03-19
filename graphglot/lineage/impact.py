"""Impact analysis for lineage graphs.

Provides analysis to answer questions like:
- "What outputs depend on this binding/property?"
- "What filters constrain this binding?"
- "What are the paths from a source to outputs?"
"""

from __future__ import annotations

from collections import deque
from typing import Any

from graphglot.lineage.models import (
    Binding,
    DependencyKind,
    ImpactPath,
    ImpactResult,
    LineageEdgeKind,
    LineageGraph,
    OutputField,
    PropertyRef,
    UpstreamDependency,
    UpstreamGraph,
    UpstreamNode,
    UpstreamRelationship,
    UpstreamSummary,
)

_KIND_PRIORITY = {
    DependencyKind.DIRECT: 3,
    DependencyKind.CONSTRAINT: 2,
    DependencyKind.PATTERN: 1,
}


class ImpactAnalyzer:
    """Analyze impact of changes in the lineage graph."""

    def __init__(self, graph: LineageGraph):
        self.graph = graph
        # Build reverse index: target -> list of (source, edge_kind)
        self._reverse_edges: dict[str, list[tuple[str, LineageEdgeKind]]] = {}
        # Build forward index: source -> list of (target, edge_kind)
        self._forward_edges: dict[str, list[tuple[str, LineageEdgeKind]]] = {}
        # binding_id -> set of binding_ids co-constrained by the same filter(s)
        self._constraint_peers: dict[str, set[str]] = {}
        # pattern_id -> set of binding_ids (from IN_PATTERN edges)
        self._pattern_bindings: dict[str, set[str]] = {}
        self._build_edge_indices()

    def _graph_name(self, graph_id: str) -> str:
        """Resolve a graph entity ID to its display name."""
        g = self.graph.graphs.get(graph_id)
        return g.name if g else graph_id

    def _is_default_graph(self, graph_id: str) -> bool:
        """Check if a graph_id refers to the implicit default graph."""
        g = self.graph.graphs.get(graph_id)
        return g is not None and g.name == "(default)"

    def _upstream_graph_name(self, graph_id: str) -> str:
        """Resolve graph_id to a name for upstream summaries.

        Returns empty string for the default graph — the default is implicit,
        not a named USE reference, so it should not appear as a dependency.
        """
        return "" if self._is_default_graph(graph_id) else self._graph_name(graph_id)

    def _binding_graph_id(self, binding: Binding) -> str:
        """Derive a binding's graph from edges.

        Checks: pattern → BELONGS_TO → graph, then binding → BELONGS_TO → graph
        (for LET/NEXT bindings), then inherits_from chain.
        """
        # Try pattern → BELONGS_TO edge → graph
        for pid in self.graph.targets(binding.id, LineageEdgeKind.IN_PATTERN):
            gid = self._pattern_graph_id(pid)
            if gid:
                return gid
        # Try direct binding → BELONGS_TO edge (LET variables, NEXT-propagated)
        for target, kind in self._forward_edges.get(binding.id, []):
            if kind == LineageEdgeKind.BELONGS_TO:
                return target
        # Follow inherits_from chain (NEXT propagation)
        parent_id = self._inherits_from(binding.id)
        if parent_id:
            source = self.graph.bindings.get(parent_id)
            if source:
                return self._binding_graph_id(source)
        return ""

    def _pattern_graph_id(self, pattern_id: str) -> str:
        """Find the graph ID for a pattern via its BELONGS_TO edge."""
        for target, kind in self._forward_edges.get(pattern_id, []):
            if kind == LineageEdgeKind.BELONGS_TO:
                return target
        return ""

    def _output_graph_ids(self, output: OutputField) -> set[str]:
        """Derive an output's graphs from its dependent bindings.

        An output can depend on bindings from multiple graphs,
        so this returns a set of graph IDs.
        """
        graph_ids: set[str] = set()
        for bid in self._dep_bindings(output.id):
            binding = self.graph.bindings.get(bid)
            if binding:
                gid = self._binding_graph_id(binding)
                if gid:
                    graph_ids.add(gid)
        # Fallback to output → BELONGS_TO → graph (e.g., USE g RETURN 1)
        if not graph_ids:
            for target, kind in self._forward_edges.get(output.id, []):
                if kind == LineageEdgeKind.BELONGS_TO:
                    graph_ids.add(target)
        return graph_ids

    def _build_edge_indices(self) -> None:
        """Build forward, reverse, pattern-binding, and constraint-peer edge indices."""
        for edge in self.graph.edges:
            # Forward: source -> target
            self._forward_edges.setdefault(edge.source_id, []).append((edge.target_id, edge.kind))

            # Reverse: target -> source
            self._reverse_edges.setdefault(edge.target_id, []).append((edge.source_id, edge.kind))

            # Pattern membership: pattern_id -> binding_ids
            if edge.kind == LineageEdgeKind.IN_PATTERN:
                self._pattern_bindings.setdefault(edge.target_id, set()).add(edge.source_id)

        # Build constraint peers: binding → co-constrained bindings
        for filt in self.graph.filters.values():
            cbs = self._constrained_bindings(filt.id)
            for bid in cbs:
                peers = self._constraint_peers.setdefault(bid, set())
                peers.update(cbs)

    # ------------------------------------------------------------------
    # Edge-based relationship helpers
    # ------------------------------------------------------------------

    def _dep_bindings(self, entity_id: str) -> list[str]:
        """Binding IDs that entity depends on (direct or via property refs)."""
        result: list[str] = []
        for tid, kind in self._forward_edges.get(entity_id, []):
            if kind not in (
                LineageEdgeKind.DEPENDS_ON,
                LineageEdgeKind.AGGREGATES,
                LineageEdgeKind.ORDERED_BY,
            ):
                continue
            if tid in self.graph.bindings:
                if tid not in result:
                    result.append(tid)
            elif tid in self.graph.property_refs:
                # Follow property ref → binding
                for bid, bkind in self._forward_edges.get(tid, []):
                    if bkind == LineageEdgeKind.DEPENDS_ON and bid in self.graph.bindings:
                        if bid not in result:
                            result.append(bid)
        return result

    def _dep_properties(self, entity_id: str) -> list[str]:
        """PropertyRef IDs that entity depends on (via DEPENDS_ON or ORDERED_BY edges)."""
        return [
            tid
            for tid, kind in self._forward_edges.get(entity_id, [])
            if kind in (LineageEdgeKind.DEPENDS_ON, LineageEdgeKind.ORDERED_BY)
            and tid in self.graph.property_refs
        ]

    def _constrained_bindings(self, filter_id: str) -> list[str]:
        """Binding IDs constrained by a filter (direct or via property refs)."""
        result: list[str] = []
        for tid, kind in self._forward_edges.get(filter_id, []):
            if kind != LineageEdgeKind.CONSTRAINS:
                continue
            if tid in self.graph.bindings:
                if tid not in result:
                    result.append(tid)
            elif tid in self.graph.property_refs:
                for bid, ek in self._forward_edges.get(tid, []):
                    if ek == LineageEdgeKind.DEPENDS_ON and bid in self.graph.bindings:
                        if bid not in result:
                            result.append(bid)
        return result

    def _constrained_properties(self, filter_id: str) -> list[str]:
        """PropertyRef IDs constrained by a filter (via CONSTRAINS edges)."""
        return [
            tid
            for tid, kind in self._forward_edges.get(filter_id, [])
            if kind == LineageEdgeKind.CONSTRAINS and tid in self.graph.property_refs
        ]

    def _inherits_from(self, binding_id: str) -> str | None:
        """Source binding ID via PROPAGATES_TO reverse edge."""
        for sid, kind in self._reverse_edges.get(binding_id, []):
            if kind == LineageEdgeKind.PROPAGATES_TO:
                return sid
        return None

    def _prop_binding_id(self, prop: PropertyRef) -> str:
        """Find the binding ID for a property ref via its DEPENDS_ON edge."""
        for tid, kind in self._forward_edges.get(prop.id, []):
            if kind == LineageEdgeKind.DEPENDS_ON and tid in self.graph.bindings:
                return tid
        return ""

    def impact(self, entity: Binding | PropertyRef | OutputField) -> ImpactResult:
        """Analyze the impact of an entity."""
        return self.impact_by_id(entity.id)

    def impact_by_id(self, entity_id: str) -> ImpactResult:
        """Analyze the impact of an entity by ID."""
        result = ImpactResult(source_id=entity_id)

        # Find direct impacts (things that depend on this entity)
        direct = set()
        for source, _ in self._reverse_edges.get(entity_id, []):
            direct.add(source)
            result.direct_impacts.append(source)

            # Categorize
            if source in self.graph.outputs:
                result.impacted_outputs.append(source)
            elif source in self.graph.filters:
                result.impacted_filters.append(source)
            elif source in self.graph.mutations:
                result.impacted_mutations.append(source)
            elif source in self.graph.bindings:
                result.impacted_bindings.append(source)
            elif source in self.graph.property_refs:
                result.impacted_properties.append(source)

        # Find transitive impacts (BFS)
        visited = {entity_id}
        queue = deque(direct)
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            result.transitive_impacts.append(current)

            # Categorize transitive impacts
            if current in self.graph.outputs and current not in result.impacted_outputs:
                result.impacted_outputs.append(current)
            elif current in self.graph.filters and current not in result.impacted_filters:
                result.impacted_filters.append(current)
            elif current in self.graph.mutations and current not in result.impacted_mutations:
                result.impacted_mutations.append(current)

            # Continue traversal
            for source, _ in self._reverse_edges.get(current, []):
                if source not in visited:
                    queue.append(source)

        self._find_impact_paths(entity_id, [], [], result.impact_paths)
        return result

    def impact_property(self, binding_name: str, property_name: str) -> ImpactResult:
        """Analyze impact of a specific property on a binding."""
        # Find the binding
        binding = None
        for b in self.graph.bindings.values():
            if b.name == binding_name:
                binding = b
                break

        if not binding:
            return ImpactResult(source_id="")

        # Find the property ref
        for prop in self.graph.property_refs.values():
            if self._prop_binding_id(prop) == binding.id and prop.property_name == property_name:
                return self.impact(prop)

        # Property not found - return empty result
        return ImpactResult(source_id="")

    def reverse_lineage(self, output: OutputField) -> list[ImpactPath]:
        """Trace an output back to its source bindings."""
        paths: list[ImpactPath] = []
        self._find_paths_to_bindings(output.id, [], [], paths)
        return paths

    def _find_paths_to_bindings(
        self,
        current_id: str,
        current_nodes: list[str],
        current_edges: list[str],
        result_paths: list[ImpactPath],
        visited: set[str] | None = None,
    ) -> None:
        """Recursively find paths from current node to bindings."""
        if visited is None:
            visited = set()

        if current_id in visited:
            return
        visited.add(current_id)

        current_nodes = [*current_nodes, current_id]

        # If we reached a binding, record the path
        if current_id in self.graph.bindings:
            result_paths.append(ImpactPath(nodes=current_nodes.copy(), edges=current_edges.copy()))
            return

        # Follow edges to dependencies
        for target, kind in self._forward_edges.get(current_id, []):
            if kind in (
                LineageEdgeKind.DEPENDS_ON,
                LineageEdgeKind.AGGREGATES,
                LineageEdgeKind.ORDERED_BY,
            ):
                edge_desc = f"{current_id}->{target}"
                self._find_paths_to_bindings(
                    target,
                    current_nodes,
                    [*current_edges, edge_desc],
                    result_paths,
                    visited.copy(),
                )

    def forward_lineage(self, binding: Binding) -> list[ImpactPath]:
        """Trace a binding forward to all outputs it affects."""
        paths: list[ImpactPath] = []
        self._find_paths_to_outputs(binding.id, [], [], paths)
        return paths

    def upstream_graph(self, output: OutputField) -> UpstreamGraph:
        """Build a graph-structured upstream view for one output field."""
        upstream_bindings = self._collect_upstream_bindings(output)
        nodes: dict[str, UpstreamNode] = {}
        rels: list[UpstreamRelationship] = []
        rel_counter = 0

        def _next_rel_id() -> str:
            nonlocal rel_counter
            rid = f"r_{rel_counter}"
            rel_counter += 1
            return rid

        # --- Output node ---
        out_id = output.id
        out_props: dict[str, Any] = {
            "alias": output.alias,
            "expression": self.output_display_name(output),
            "position": output.position,
            "is_aggregated": output.is_aggregated,
        }
        if output.aggregate_function:
            out_props["aggregate_function"] = output.aggregate_function
        nodes[out_id] = UpstreamNode(id=out_id, labels=["Output"], properties=out_props)

        # --- Binding nodes ---
        binding_id_map: dict[str, str] = {}  # lineage binding id -> upstream node id
        for bid in sorted(upstream_bindings):
            binding = self.graph.bindings.get(bid)
            if not binding:
                continue
            kind_label = binding.kind.value.capitalize()
            node_id = bid
            binding_id_map[bid] = node_id
            b_props: dict[str, Any] = {"name": binding.name}
            gid = self._binding_graph_id(binding)
            if gid:
                b_props["graph"] = self._graph_name(gid)
            nodes[node_id] = UpstreamNode(
                id=node_id, labels=["Binding", kind_label], properties=b_props
            )

        # --- Property nodes ---
        upstream_prop_ids: set[str] = set(self._dep_properties(output.id))
        for filt in self.graph.filters.values():
            if any(cb in upstream_bindings for cb in self._constrained_bindings(filt.id)):
                upstream_prop_ids.update(self._constrained_properties(filt.id))
        prop_id_map: dict[str, str] = {}
        for pid in sorted(upstream_prop_ids):
            prop = self.graph.property_refs.get(pid)
            if not prop:
                continue
            node_id = pid
            prop_id_map[pid] = node_id
            pbid = self._prop_binding_id(prop)
            binding = self.graph.bindings.get(pbid)
            bname = binding.name if binding else pbid
            # Derive context from edge structure
            contexts: set[str] = set()
            for src_id, ek in self._reverse_edges.get(pid, []):
                if ek == LineageEdgeKind.CONSTRAINS:
                    contexts.add("filter")
                elif ek == LineageEdgeKind.DEPENDS_ON and src_id in self.graph.outputs:
                    contexts.add("output")
                elif ek == LineageEdgeKind.ORDERED_BY:
                    contexts.add("order")
            context_str = ",".join(sorted(contexts)) if contexts else "output"
            nodes[node_id] = UpstreamNode(
                id=node_id,
                labels=["Property"],
                properties={
                    "name": prop.property_name,
                    "binding": bname,
                    "context": context_str,
                },
            )

        # --- Pattern nodes ---
        pattern_ids: set[str] = set()
        for bid in upstream_bindings:
            for pid in self.graph.targets(bid, LineageEdgeKind.IN_PATTERN):
                pattern_ids.add(pid)
        pat_id_map: dict[str, str] = {}
        for pid in sorted(pattern_ids):
            pat = self.graph.patterns.get(pid)
            if not pat:
                continue
            node_id = pid
            pat_id_map[pid] = node_id
            p_props: dict[str, Any] = {"index": pat.match_index}
            pat_text = self.graph.source_text(pat)
            if pat_text:
                p_props["text"] = pat_text
            nodes[node_id] = UpstreamNode(id=node_id, labels=["Pattern"], properties=p_props)

        # --- Graph nodes ---
        graph_ids: set[str] = set()
        for bid in upstream_bindings:
            binding = self.graph.bindings.get(bid)
            if binding:
                gid = self._binding_graph_id(binding)
                if gid:
                    graph_ids.add(gid)
        graph_ids.update(self._output_graph_ids(output))
        graph_id_to_node: dict[str, str] = {}
        for gid in sorted(graph_ids):
            gname = self._graph_name(gid)
            node_id = gid
            graph_id_to_node[gid] = node_id
            nodes[node_id] = UpstreamNode(id=node_id, labels=["Graph"], properties={"name": gname})

        # --- Filter nodes ---
        filter_id_map: dict[str, str] = {}
        for filt in self.graph.filters.values():
            if any(cb in upstream_bindings for cb in self._constrained_bindings(filt.id)):
                node_id = filt.id
                filter_id_map[filt.id] = node_id
                nodes[node_id] = UpstreamNode(
                    id=node_id,
                    labels=["Filter"],
                    properties={
                        "expression": self.graph.source_text(filt) or filt.id,
                    },
                )

        # --- Relationships ---
        # Output → Binding: DEPENDS_ON
        for bid in self._dep_bindings(output.id):
            if bid in binding_id_map:
                rels.append(
                    UpstreamRelationship(
                        id=_next_rel_id(),
                        type="DEPENDS_ON",
                        start_node=out_id,
                        end_node=binding_id_map[bid],
                        properties={"context": "direct"},
                    )
                )

        # Output → Property: DEPENDS_ON
        for pid in self._dep_properties(output.id):
            if pid in prop_id_map:
                rels.append(
                    UpstreamRelationship(
                        id=_next_rel_id(),
                        type="DEPENDS_ON",
                        start_node=out_id,
                        end_node=prop_id_map[pid],
                        properties={"context": "direct"},
                    )
                )

        # Binding → Property: HAS_PROPERTY
        for pid, pnode_id in prop_id_map.items():
            prop = self.graph.property_refs.get(pid)
            pbid = self._prop_binding_id(prop) if prop else ""
            if prop and pbid in binding_id_map:
                rels.append(
                    UpstreamRelationship(
                        id=_next_rel_id(),
                        type="HAS_PROPERTY",
                        start_node=binding_id_map[pbid],
                        end_node=pnode_id,
                        properties={},
                    )
                )

        # Filter → Binding: CONSTRAINS
        for filt in self.graph.filters.values():
            if filt.id in filter_id_map:
                for cb in self._constrained_bindings(filt.id):
                    if cb in binding_id_map:
                        rels.append(
                            UpstreamRelationship(
                                id=_next_rel_id(),
                                type="CONSTRAINS",
                                start_node=filter_id_map[filt.id],
                                end_node=binding_id_map[cb],
                                properties={},
                            )
                        )
                # Filter → Property: REFERENCES
                for cp in self._constrained_properties(filt.id):
                    if cp in prop_id_map:
                        rels.append(
                            UpstreamRelationship(
                                id=_next_rel_id(),
                                type="REFERENCES",
                                start_node=filter_id_map[filt.id],
                                end_node=prop_id_map[cp],
                                properties={},
                            )
                        )

        # Binding → Pattern: IN_PATTERN
        for bid in upstream_bindings:
            for pat_id in self.graph.targets(bid, LineageEdgeKind.IN_PATTERN):
                if pat_id in pat_id_map:
                    rels.append(
                        UpstreamRelationship(
                            id=_next_rel_id(),
                            type="IN_PATTERN",
                            start_node=binding_id_map[bid],
                            end_node=pat_id_map[pat_id],
                            properties={},
                        )
                    )

        # Pattern → Graph: ON_GRAPH (derive from BELONGS_TO edge)
        pat_graph_ids: dict[str, set[str]] = {}
        for pid in pat_id_map:
            gid = self._pattern_graph_id(pid)
            if gid:
                pat_graph_ids.setdefault(pid, set()).add(gid)
        for pid, gids in pat_graph_ids.items():
            if pid in pat_id_map:
                for gid in sorted(gids):
                    graph_node_id = graph_id_to_node.get(gid)
                    if graph_node_id and graph_node_id in nodes:
                        rels.append(
                            UpstreamRelationship(
                                id=_next_rel_id(),
                                type="ON_GRAPH",
                                start_node=pat_id_map[pid],
                                end_node=graph_node_id,
                                properties={},
                            )
                        )

        # Binding → Binding: INHERITS_FROM
        for bid in upstream_bindings:
            parent_id = self._inherits_from(bid)
            if parent_id and parent_id in binding_id_map:
                rels.append(
                    UpstreamRelationship(
                        id=_next_rel_id(),
                        type="INHERITS_FROM",
                        start_node=binding_id_map[bid],
                        end_node=binding_id_map[parent_id],
                        properties={},
                    )
                )

        return UpstreamGraph(nodes=list(nodes.values()), relationships=rels)

    def upstream_graph_all(self) -> UpstreamGraph:
        """Build a merged upstream graph across all outputs."""
        merged_nodes: dict[str, UpstreamNode] = {}
        merged_rels: dict[tuple[str, str, str], UpstreamRelationship] = {}

        for output in self.graph.outputs.values():
            ug = self.upstream_graph(output)
            for n in ug.nodes:
                merged_nodes[n.id] = n
            for r in ug.relationships:
                # Dedup by (type, start, end) to avoid duplicate edges
                key = (r.type, r.start_node, r.end_node)
                if key not in merged_rels:
                    merged_rels[key] = r

        # Re-number relationship IDs
        rels = list(merged_rels.values())
        for i, r in enumerate(rels):
            r.id = f"r_{i}"

        return UpstreamGraph(nodes=list(merged_nodes.values()), relationships=rels)

    def upstream(self, output: OutputField) -> UpstreamSummary:
        """Compute upstream summary for one output field.

        Returns one UpstreamDependency row per unique (graph, label, property)
        combination, giving a flat, scannable view of what data affects this output.
        Each row is classified as DIRECT, CONSTRAINT, or PATTERN.
        """
        binding_kinds = self._classify_upstream_bindings(output)
        upstream_bindings = set(binding_kinds.keys())
        prop_kinds = self._classify_upstream_properties(output, binding_kinds)
        upstream_prop_ids = set(prop_kinds.keys())
        prop_info: dict[str, tuple[str, str]] = {}
        bindings_with_props: set[str] = set()
        for prop_id in upstream_prop_ids:
            prop = self.graph.property_refs.get(prop_id)
            if not prop:
                continue
            prop_bid = self._prop_binding_id(prop)
            prop_info[prop_id] = (prop_bid, prop.property_name)
            if prop_bid:
                bindings_with_props.add(prop_bid)

        # Build binding_id -> (graph_name, label_expressions) index
        binding_info: dict[str, tuple[str, list[str]]] = {}
        for bid in upstream_bindings:
            binding = self.graph.bindings.get(bid)
            graph_ctx = ""
            if binding:
                gid = self._binding_graph_id(binding)
                if gid:
                    graph_ctx = self._upstream_graph_name(gid)
            label_exprs: list[str] = []
            if binding and binding.label_expression:
                label_exprs.append(binding.label_expression)
            binding_info[bid] = (graph_ctx, label_exprs)

        # Track best kind per dedup key; highest priority wins
        best: dict[tuple[str, str, str, str], UpstreamDependency] = {}

        def _add(graph: str, label: str, prop: str, kind: DependencyKind) -> None:
            key = (output.id, graph, label, prop)
            if key in best:
                if _KIND_PRIORITY[kind] > _KIND_PRIORITY[best[key].kind]:
                    best[key].kind = kind
            else:
                best[key] = UpstreamDependency(*key, kind=kind)

        # Emit rows for properties (property implies its binding's graph+label)
        for prop_id in sorted(upstream_prop_ids):
            prop_kind = prop_kinds[prop_id]
            info = prop_info.get(prop_id)
            if not info:
                continue
            prop_bid, prop_name = info
            graph_ctx, label_exprs = binding_info.get(prop_bid, ("", [])) if prop_bid else ("", [])
            if label_exprs:
                for le in label_exprs:
                    _add(graph_ctx, le, prop_name, prop_kind)
            else:
                _add(graph_ctx, "", prop_name, prop_kind)

        # Emit rows for bindings without property access (pattern-only labels)
        for bid, (graph_ctx, label_exprs) in binding_info.items():
            if bid in bindings_with_props:
                continue
            bid_kind = binding_kinds.get(bid, DependencyKind.PATTERN)
            if label_exprs:
                for le in label_exprs:
                    _add(graph_ctx, le, "", bid_kind)
            elif graph_ctx:
                # Pure graph dependency (no labels, no properties)
                _add(graph_ctx, "", "", bid_kind)

        # Output's own graph context (e.g. USE g RETURN 1) when no bindings
        if not upstream_bindings:
            out_gids = self._output_graph_ids(output)
            for gid in out_gids:
                if not self._is_default_graph(gid):
                    _add(self._upstream_graph_name(gid), "", "", DependencyKind.DIRECT)

        return UpstreamSummary(output_id=output.id, dependencies=list(best.values()))

    def upstream_all(self) -> list[UpstreamSummary]:
        """Compute upstream summary for all outputs."""
        return [self.upstream(o) for o in self.graph.outputs.values()]

    def output_display_name(self, output: OutputField) -> str:
        """Human-readable name for an output: alias > source_text > deps > id."""
        if output.alias:
            return output.alias
        src = self.graph.source_text(output)
        if src:
            return src
        # Reconstruct from graph structure for simple cases (no query_text)
        bids = self._dep_bindings(output.id)
        pids = self._dep_properties(output.id)
        if len(bids) == 1:
            b = self.graph.bindings.get(bids[0])
            if b and b.name:
                if len(pids) == 1:
                    p = self.graph.property_refs.get(pids[0])
                    if p:
                        base = f"{b.name}.{p.property_name}"
                        if output.aggregate_function:
                            return f"{output.aggregate_function}({base})"
                        return base
                elif not pids:
                    if output.aggregate_function:
                        return f"{output.aggregate_function}({b.name})"
                    return b.name
        return output.id

    def output_names(self) -> list[str]:
        """Return the output column names from the last RETURN clause.

        Uses the alias if present, otherwise the source text derived from
        the span, or reconstructed from the dependency graph as a fallback.
        In queries with NEXT chains, only the final scope's outputs are returned.
        """
        if not self.graph.outputs:
            return []

        all_outputs = list(self.graph.outputs.values())
        last_scope_id = max((o.scope_id for o in all_outputs), key=self._scope_sort_key)

        return [
            self.output_display_name(o)
            for o in sorted(all_outputs, key=lambda o: o.position)
            if o.scope_id == last_scope_id
        ]

    def _collect_upstream_bindings(self, output: OutputField) -> set[str]:
        """Collect all upstream binding IDs for an output.

        Delegates to _classify_upstream_bindings and discards the classification.
        """
        return set(self._classify_upstream_bindings(output).keys())

    def _classify_upstream_bindings(self, output: OutputField) -> dict[str, DependencyKind]:
        """Classify each upstream binding by how it reaches the output.

        Returns a mapping from binding_id to DependencyKind (DIRECT, PATTERN,
        or CONSTRAINT), tracking the reason each binding was reached.
        """
        kinds: dict[str, DependencyKind] = {}
        queue: deque[tuple[str, DependencyKind]] = deque(
            (bid, DependencyKind.DIRECT) for bid in self._dep_bindings(output.id)
        )

        while queue:
            bid, kind = queue.popleft()
            if bid in kinds:
                # Keep highest priority
                if _KIND_PRIORITY[kind] > _KIND_PRIORITY[kinds[bid]]:
                    kinds[bid] = kind
                continue
            kinds[bid] = kind

            binding = self.graph.bindings.get(bid)
            if not binding:
                continue

            # Chase inherits_from chains (preserve kind)
            parent_id = self._inherits_from(bid)
            if parent_id and parent_id not in kinds:
                queue.append((parent_id, kind))

            # Include pattern-connected bindings (same pattern via IN_PATTERN edges)
            for pat_id in self.graph.targets(bid, LineageEdgeKind.IN_PATTERN):
                for mate in self._pattern_bindings.get(pat_id, ()):
                    if mate not in kinds:
                        queue.append((mate, DependencyKind.PATTERN))

            # Add co-constrained bindings (from same filter)
            for peer in self._constraint_peers.get(bid, ()):
                if peer not in kinds:
                    queue.append((peer, DependencyKind.CONSTRAINT))

        return kinds

    def _classify_upstream_properties(
        self, output: OutputField, binding_kinds: dict[str, DependencyKind]
    ) -> dict[str, DependencyKind]:
        """Classify upstream properties by how they reach the output.

        Returns a mapping from property-ref ID to DependencyKind.
        """
        direct_prop_ids = set(self._dep_properties(output.id))  # includes ORDERED_BY

        constraint_prop_ids: set[str] = set()
        for filt in self.graph.filters.values():
            if any(cb in binding_kinds for cb in self._constrained_bindings(filt.id)):
                constraint_prop_ids.update(self._constrained_properties(filt.id))

        result: dict[str, DependencyKind] = {}
        for pid in direct_prop_ids | constraint_prop_ids:
            if pid in direct_prop_ids:
                kind = DependencyKind.DIRECT
            else:
                kind = DependencyKind.CONSTRAINT

            if pid not in result or _KIND_PRIORITY[kind] > _KIND_PRIORITY[result[pid]]:
                result[pid] = kind

        return result

    def _find_paths_to_outputs(
        self,
        current_id: str,
        current_nodes: list[str],
        current_edges: list[str],
        result_paths: list[ImpactPath],
        visited: set[str] | None = None,
    ) -> None:
        """Recursively find paths from current node to outputs."""
        if visited is None:
            visited = set()

        if current_id in visited:
            return
        visited.add(current_id)

        current_nodes = [*current_nodes, current_id]

        # If we reached an output, record the path
        if current_id in self.graph.outputs:
            result_paths.append(ImpactPath(nodes=current_nodes.copy(), edges=current_edges.copy()))
            return

        # Follow reverse edges to dependents
        for source, kind in self._reverse_edges.get(current_id, []):
            if kind in (
                LineageEdgeKind.DEPENDS_ON,
                LineageEdgeKind.AGGREGATES,
                LineageEdgeKind.ORDERED_BY,
            ):
                edge_desc = f"{source}->{current_id}"
                self._find_paths_to_outputs(
                    source,
                    current_nodes,
                    [*current_edges, edge_desc],
                    result_paths,
                    visited.copy(),
                )

    @staticmethod
    def _scope_sort_key(scope_id: str) -> tuple[str, int]:
        """Sort scope IDs by prefix and numeric suffix instead of lexicographically."""
        prefix, _, suffix = scope_id.rpartition("_")
        if prefix and suffix.isdigit():
            return (prefix, int(suffix))
        return (scope_id, -1)

    def _find_impact_paths(
        self,
        current_id: str,
        current_nodes: list[str],
        current_edges: list[str],
        result_paths: list[ImpactPath],
        visited: set[str] | None = None,
    ) -> None:
        """Recursively find paths from a source entity to impacted entities."""
        if visited is None:
            visited = set()

        if current_id in visited:
            return
        visited.add(current_id)

        current_nodes = [*current_nodes, current_id]

        if len(current_nodes) > 1 and (
            current_id in self.graph.outputs
            or current_id in self.graph.filters
            or current_id in self.graph.mutations
            or current_id in self.graph.bindings
            or current_id in self.graph.property_refs
        ):
            result_paths.append(ImpactPath(nodes=current_nodes.copy(), edges=current_edges.copy()))

        for source, kind in self._reverse_edges.get(current_id, []):
            if kind in (
                LineageEdgeKind.DEPENDS_ON,
                LineageEdgeKind.AGGREGATES,
                LineageEdgeKind.ORDERED_BY,
                LineageEdgeKind.CONSTRAINS,
                LineageEdgeKind.WRITES,
                LineageEdgeKind.PROPAGATES_TO,
            ):
                edge_desc = f"{current_id}<-{source}"
                self._find_impact_paths(
                    source,
                    current_nodes,
                    [*current_edges, edge_desc],
                    result_paths,
                    visited.copy(),
                )
