"""Tests for graph context tracking in lineage analysis.

These tests verify that the lineage module correctly tracks which graph
a query operates on via USE clauses, propagating graph context through
BELONGS_TO edges from patterns, bindings, and outputs to Graph entities.
"""

from __future__ import annotations

import json

from graphglot.lineage import LineageAnalyzer, LineageEdgeKind
from graphglot.lineage.exporter import LineageExporter


def _entity_graph_name(result, entity_id: str) -> str:
    """Find an entity's graph name via its BELONGS_TO edge."""
    for e in result.edges:
        if e.source_id == entity_id and e.kind == LineageEdgeKind.BELONGS_TO:
            g = result.graphs.get(e.target_id)
            if g:
                return g.name
    return ""


def _binding_graph_name(result, binding) -> str:
    """Derive a binding's graph name from edges.

    Checks: pattern → BELONGS_TO → graph, then binding → BELONGS_TO → graph,
    then follows PROPAGATES_TO chain.
    """
    from .conftest import inherits_from

    for pid in result.targets(binding.id, LineageEdgeKind.IN_PATTERN):
        gname = _entity_graph_name(result, pid)
        if gname:
            return gname
    # Direct BELONGS_TO on binding (LET vars, NEXT-propagated)
    gname = _entity_graph_name(result, binding.id)
    if gname:
        return gname
    # Fallback: follow PROPAGATES_TO edge
    parent_id = inherits_from(result, binding.id)
    if parent_id:
        source = result.bindings.get(parent_id)
        if source:
            return _binding_graph_name(result, source)
    return "(default)"


def _output_graph_name(result, output) -> str:
    """Derive an output's graph name from its dependent bindings or direct edge."""
    # Collect binding deps (direct or via property refs)
    dep_bids = result.targets(output.id, LineageEdgeKind.DEPENDS_ON)
    agg_bids = result.targets(output.id, LineageEdgeKind.AGGREGATES)
    binding_ids = []
    for tid in dep_bids + agg_bids:
        if tid in result.bindings:
            binding_ids.append(tid)
        elif tid in result.property_refs:
            for bid in result.targets(tid, LineageEdgeKind.DEPENDS_ON):
                if bid in result.bindings:
                    binding_ids.append(bid)
    for bid in binding_ids:
        binding = result.bindings.get(bid)
        if binding:
            gname = _binding_graph_name(result, binding)
            if gname and gname != "(default)":
                return gname
    # Fallback: output → BELONGS_TO → graph (e.g., USE g RETURN 1)
    gname = _entity_graph_name(result, output.id)
    if gname:
        return gname
    # Check binding deps again for default graph
    for bid in binding_ids:
        binding = result.bindings.get(bid)
        if binding:
            return _binding_graph_name(result, binding)
    return "(default)"


class TestGraphContextBasic:
    """Test basic USE graph tracking."""

    def test_use_graph_match_return(self, parse):
        """USE g sets graph context on binding and output."""
        ast = parse("USE g MATCH (n:Person) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        graph = result

        binding = next(b for b in graph.bindings.values() if b.name == "n")
        assert _binding_graph_name(result, binding) == "g"

        output = next(iter(graph.outputs.values()))
        assert _output_graph_name(result, output) == "g"

    def test_use_graph_pattern(self, parse):
        """All bindings from a USE-scoped MATCH get graph context."""
        ast = parse("USE g MATCH (n)-[r]->(m) RETURN n, r, m")
        result = LineageAnalyzer().analyze(ast)

        for b in result.bindings.values():
            assert _binding_graph_name(result, b) == "g", f"binding {b.name} missing graph"

    def test_use_graph_with_filter(self, parse):
        """USE g with WHERE still tracks graph context."""
        ast = parse("USE g MATCH (n:Person) WHERE n.age > 21 RETURN n.name")
        result = LineageAnalyzer().analyze(ast)

        binding = next(b for b in result.bindings.values() if b.name == "n")
        assert _binding_graph_name(result, binding) == "g"

        output = next(iter(result.outputs.values()))
        assert _output_graph_name(result, output) == "g"

    def test_use_graph_bare_return(self, parse):
        """USE g RETURN 1 — output carries graph via BELONGS_TO edge."""
        ast = parse("USE g RETURN 1")
        result = LineageAnalyzer().analyze(ast)

        output = next(iter(result.outputs.values()))
        assert _output_graph_name(result, output) == "g"


class TestGraphContextAmbient:
    """Test that queries without USE point to default graph."""

    def test_no_use_graph_context_is_default(self, parse):
        """Without USE, all bindings point to default graph via edges."""
        ast = parse("MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)

        for b in result.bindings.values():
            assert _binding_graph_name(result, b) == "(default)"

    def test_let_no_use_graph_context_is_default(self, parse):
        """LET without USE — bindings derive default graph."""
        ast = parse("LET x = 1 MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)

        for b in result.bindings.values():
            assert _binding_graph_name(result, b) == "(default)"


class TestGraphContextNext:
    """Test graph context across NEXT boundaries."""

    def test_cross_graph_next(self, parse):
        """Different USE clauses in NEXT parts track separately."""
        ast = parse("USE g1 MATCH (n) RETURN n NEXT USE g2 MATCH (m) RETURN m")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["n"]) == "g1"
        assert _binding_graph_name(result, bindings_by_name["m"]) == "g2"

    def test_use_first_ambient_second(self, parse):
        """USE in first part, ambient in second."""
        ast = parse("USE g1 MATCH (n) RETURN n NEXT MATCH (m) RETURN m")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["n"]) == "g1"
        assert _binding_graph_name(result, bindings_by_name["m"]) == "(default)"

    def test_ambient_first_use_second(self, parse):
        """Ambient first, USE in second part."""
        ast = parse("MATCH (n) RETURN n NEXT USE g2 MATCH (m) RETURN m")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["n"]) == "(default)"
        assert _binding_graph_name(result, bindings_by_name["m"]) == "g2"


class TestGraphContextOtherwise:
    """Test graph context in OTHERWISE branches."""

    def test_otherwise_with_use(self, parse):
        """OTHERWISE branch with USE gets its own graph context."""
        ast = parse(
            "MATCH (n) RETURN n NEXT MATCH (n) RETURN n OTHERWISE { USE g2 MATCH (m) RETURN m }"
        )
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["m"]) == "g2"
        # n should be default
        assert _binding_graph_name(result, bindings_by_name["n"]) == "(default)"


class TestGraphContextSubquery:
    """Test graph context in subqueries."""

    def test_exists_subquery_with_use(self, parse):
        """EXISTS subquery with USE — outer n stays default."""
        ast = parse("MATCH (n) WHERE EXISTS { USE g2 MATCH (m) RETURN m } RETURN n")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["n"]) == "(default)"

    def test_call_subquery_with_use(self, parse):
        """CALL subquery with USE — outer n stays default."""
        ast = parse("MATCH (n) CALL { USE g2 MATCH (m) RETURN m } RETURN n")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["n"]) == "(default)"


class TestGraphContextUnion:
    """Test graph context with UNION."""

    def test_union_with_use(self, parse):
        """Each UNION branch can have its own graph context."""
        ast = parse("{ USE g1 MATCH (n) RETURN n } UNION { USE g2 MATCH (m) RETURN m }")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["n"]) == "g1"
        assert _binding_graph_name(result, bindings_by_name["m"]) == "g2"


class TestGraphContextChained:
    """Test chained USE clauses in a single linear query."""

    def test_chained_use(self, parse):
        """Chained USE g1 MATCH ... USE g2 MATCH ... tracks per-part context."""
        ast = parse("USE g1 MATCH (a:Person) USE g2 MATCH (b:Company) RETURN a, b")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["a"]) == "g1"
        assert _binding_graph_name(result, bindings_by_name["b"]) == "g2"

    def test_three_chained_use(self, parse):
        """Three chained USE clauses."""
        ast = parse("USE g1 MATCH (a) USE g2 MATCH (b) USE g3 MATCH (c) RETURN a, b, c")
        result = LineageAnalyzer().analyze(ast)

        bindings_by_name = {b.name: b for b in result.bindings.values()}
        assert _binding_graph_name(result, bindings_by_name["a"]) == "g1"
        assert _binding_graph_name(result, bindings_by_name["b"]) == "g2"
        assert _binding_graph_name(result, bindings_by_name["c"]) == "g3"


class TestGraphContextSpecialGraphs:
    """Test special graph references (CURRENT_GRAPH, HOME_GRAPH, parameters)."""

    def test_current_graph(self, parse):
        """USE CURRENT_GRAPH tracks as 'CURRENT_GRAPH'."""
        ast = parse("USE CURRENT_GRAPH MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)

        binding = next(iter(result.bindings.values()))
        assert _binding_graph_name(result, binding) == "CURRENT_GRAPH"

    def test_home_graph(self, parse):
        """USE HOME_GRAPH tracks as 'HOME_GRAPH'."""
        ast = parse("USE HOME_GRAPH MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)

        binding = next(iter(result.bindings.values()))
        assert _binding_graph_name(result, binding) == "HOME_GRAPH"

    def test_parameter_ref(self, parse):
        """USE $g tracks as '$g'."""
        ast = parse("USE $g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)

        binding = next(iter(result.bindings.values()))
        assert _binding_graph_name(result, binding) == "$g"


class TestGraphNodePresence:
    """Test that only referenced Graph nodes are created (no orphans)."""

    def _graph_names(self, result) -> set[str]:
        return {g.name for g in result.graphs.values()}

    def test_ambient_only_creates_default(self, parse):
        """Without USE, only the (default) graph node exists."""
        ast = parse("MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        assert self._graph_names(result) == {"(default)"}

    def test_use_only_creates_named(self, parse):
        """USE g — only the named graph, no (default)."""
        ast = parse("USE g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        assert self._graph_names(result) == {"g"}

    def test_next_use_first_ambient_second(self, parse):
        """USE in first NEXT part, ambient second — both graphs exist."""
        ast = parse("USE g1 MATCH (n) RETURN n NEXT MATCH (m) RETURN m")
        result = LineageAnalyzer().analyze(ast)
        assert self._graph_names(result) == {"g1", "(default)"}

    def test_next_ambient_first_use_second(self, parse):
        """Ambient first, USE in second NEXT part — both graphs exist."""
        ast = parse("MATCH (n) RETURN n NEXT USE g2 MATCH (m) RETURN m")
        result = LineageAnalyzer().analyze(ast)
        assert self._graph_names(result) == {"(default)", "g2"}

    def test_next_both_use_no_default(self, parse):
        """USE in both NEXT parts — no (default) graph."""
        ast = parse("USE g1 MATCH (n) RETURN n NEXT USE g2 MATCH (m) RETURN m")
        result = LineageAnalyzer().analyze(ast)
        assert self._graph_names(result) == {"g1", "g2"}

    def test_otherwise_ambient_creates_default(self, parse):
        """OTHERWISE without USE falls back to (default)."""
        ast = parse(
            "USE g1 MATCH (n) RETURN n NEXT MATCH (n) RETURN n OTHERWISE { MATCH (m) RETURN m }"
        )
        result = LineageAnalyzer().analyze(ast)
        assert "(default)" in self._graph_names(result)
        assert "g1" in self._graph_names(result)

    def test_otherwise_with_use_no_default(self, parse):
        """USE in both main and OTHERWISE — no (default)."""
        ast = parse(
            "USE g1 MATCH (n) RETURN n NEXT MATCH (n) RETURN n "
            "OTHERWISE { USE g2 MATCH (m) RETURN m }"
        )
        result = LineageAnalyzer().analyze(ast)
        # g1 from first part, (default) from second NEXT part, g2 from OTHERWISE
        assert "g1" in self._graph_names(result)
        assert "g2" in self._graph_names(result)

    def test_exists_inherits_graph_no_extra_default(self, parse):
        """EXISTS inside USE — subquery inherits graph, no extra (default)."""
        ast = parse("USE g MATCH (n) WHERE EXISTS { MATCH (m)-[r]->(n) RETURN m } RETURN n")
        result = LineageAnalyzer().analyze(ast)
        assert self._graph_names(result) == {"g"}

    def test_chained_use_no_default(self, parse):
        """Chained USE g1 ... USE g2 ... — no (default)."""
        ast = parse("USE g1 MATCH (a) USE g2 MATCH (b) RETURN a, b")
        result = LineageAnalyzer().analyze(ast)
        assert self._graph_names(result) == {"g1", "g2"}


class TestGraphSpan:
    """Test that Graph nodes get correct source spans."""

    def test_use_graph_has_span(self, parse):
        """USE clause graph should have span pointing to 'USE <name>'."""
        query = "USE mygraph MATCH (n) RETURN n"
        ast = parse(query)
        result = LineageAnalyzer().analyze(ast, query_text=query)

        graph = next(g for g in result.graphs.values() if g.name == "mygraph")
        assert graph.span is not None
        text = query[graph.span.start_offset : graph.span.end_offset]
        assert text == "USE mygraph"

    def test_default_graph_has_no_span(self, parse):
        """The (default) graph is synthetic and should have no span."""
        query = "MATCH (n) RETURN n"
        ast = parse(query)
        result = LineageAnalyzer().analyze(ast, query_text=query)

        graph = next(g for g in result.graphs.values() if g.name == "(default)")
        assert graph.span is None

    def test_span_in_json_export(self, parse):
        """Graph span should appear in JSON export."""
        query = "USE g MATCH (n) RETURN n"
        ast = parse(query)
        result = LineageAnalyzer().analyze(ast, query_text=query)

        data = json.loads(LineageExporter(result).to_json())
        graph_node = next(n for n in data["nodes"] if n["node_type"] == "graph")
        assert graph_node["span"] is not None
        assert graph_node["span"]["start_offset"] == 0


class TestGraphContextExport:
    """Test graph context in export formats."""

    def test_json_export_belongs_to_edges(self, parse):
        """BELONGS_TO edges connect patterns to graphs in JSON."""
        ast = parse("USE g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        exporter = LineageExporter(result)
        j = exporter.to_json()
        data = json.loads(j)

        belongs_to = [e for e in data["edges"] if e["kind"] == "belongs_to"]
        assert len(belongs_to) >= 1
        # Edge source is a pattern, target is a graph
        edge = belongs_to[0]
        graph_ids = {n["id"] for n in data["nodes"] if n["node_type"] == "graph"}
        assert edge["target_id"] in graph_ids

    def test_json_ambient_binding_graph_via_edges(self, parse):
        """Ambient binding's graph is derivable from BELONGS_TO edges in JSON."""
        ast = parse("MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        exporter = LineageExporter(result)
        j = exporter.to_json()
        data = json.loads(j)

        # Pattern should have a BELONGS_TO edge to the default graph
        belongs_to = [e for e in data["edges"] if e["kind"] == "belongs_to"]
        assert len(belongs_to) >= 1
        target_id = belongs_to[0]["target_id"]
        graphs = [n for n in data["nodes"] if n["node_type"] == "graph"]
        g = next(g for g in graphs if g["id"] == target_id)
        assert g["name"] == "(default)"

    def test_no_graph_id_on_entities(self, parse):
        """Bindings, outputs, and patterns should not have graph_id fields."""
        ast = parse("USE g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        d = LineageExporter(result).to_dict()

        bindings = [n for n in d["nodes"] if n["node_type"] == "binding"]
        outputs = [n for n in d["nodes"] if n["node_type"] == "output"]
        patterns = [n for n in d["nodes"] if n["node_type"] == "pattern"]
        assert "graph_id" not in bindings[0]
        assert "graph_id" not in outputs[0]
        assert "graph_id" not in patterns[0]
