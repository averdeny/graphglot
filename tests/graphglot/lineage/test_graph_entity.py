"""Tests for first-class Graph entity in lineage analysis."""

from __future__ import annotations

import json

from graphglot.lineage import LineageAnalyzer, LineageEdgeKind
from graphglot.lineage.exporter import LineageExporter


class TestGraphEntityBasic:
    """Test Graph entity creation and references."""

    def test_default_graph_exists(self, parse):
        """Queries without USE produce a default graph."""
        ast = parse("MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        assert len(result.graphs) == 1
        default = next(iter(result.graphs.values()))
        assert default.name == "(default)"

    def test_default_graph_has_id(self, parse):
        """Default graph has id 'g_0'."""
        ast = parse("MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        assert "g_0" in result.graphs

    def test_use_creates_named_graph(self, parse):
        """USE g creates a Graph with name='g'."""
        ast = parse("USE g MATCH (n:Person) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        names = {g.name for g in result.graphs.values()}
        assert "g" in names

    def test_binding_graph_derived_from_pattern(self, parse):
        """Binding's graph is derived from its pattern's BELONGS_TO edge."""
        from graphglot.lineage.impact import ImpactAnalyzer

        ast = parse("USE g MATCH (n:Person) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        ia = ImpactAnalyzer(result)
        binding = next(b for b in result.bindings.values() if b.name == "n")
        gid = ia._binding_graph_id(binding)
        assert gid in result.graphs
        assert result.graphs[gid].name == "g"

    def test_output_graph_derived_from_bindings(self, parse):
        """OutputField's graph is derived through its dependent bindings."""
        from graphglot.lineage.impact import ImpactAnalyzer

        ast = parse("USE g MATCH (n:Person) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        ia = ImpactAnalyzer(result)
        output = next(iter(result.outputs.values()))
        graph_ids = ia._output_graph_ids(output)
        assert len(graph_ids) == 1
        gid = next(iter(graph_ids))
        assert result.graphs[gid].name == "g"

    def test_let_binding_has_belongs_to_edge(self, parse):
        """LET binding (no pattern) gets a direct BELONGS_TO edge to its graph."""
        ast = parse("USE g LET x = 1 MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)

        x_binding = next((b for b in result.bindings.values() if b.name == "x"), None)
        assert x_binding is not None
        belongs_to = [
            e
            for e in result.edges
            if e.source_id == x_binding.id and e.kind == LineageEdgeKind.BELONGS_TO
        ]
        assert len(belongs_to) >= 1
        assert result.graphs[belongs_to[0].target_id].name == "g"


class TestGraphEntityMultiple:
    """Test multiple Graph entities."""

    def test_two_use_clauses_create_two_graphs(self, parse):
        """USE g1 ... USE g2 creates two Graph entities."""
        ast = parse("USE g1 MATCH (a:Person) USE g2 MATCH (b:Company) RETURN a, b")
        result = LineageAnalyzer().analyze(ast)
        names = {g.name for g in result.graphs.values()}
        assert "g1" in names
        assert "g2" in names

    def test_no_use_all_point_to_default(self, parse):
        """Without USE, all pattern bindings point to default graph via edges."""
        from graphglot.lineage.impact import ImpactAnalyzer

        ast = parse("MATCH (n)-[r]->(m) RETURN n, m")
        result = LineageAnalyzer().analyze(ast)
        ia = ImpactAnalyzer(result)
        default = next(g for g in result.graphs.values() if g.name == "(default)")
        for b in result.bindings.values():
            if result.targets(b.id, LineageEdgeKind.IN_PATTERN):
                gid = ia._binding_graph_id(b)
                assert gid == default.id


class TestGraphEntitySpecial:
    """Test special graph references."""

    def test_current_graph_entity(self, parse):
        """USE CURRENT_GRAPH creates a Graph entity with that name."""
        ast = parse("USE CURRENT_GRAPH MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        names = {g.name for g in result.graphs.values()}
        assert "CURRENT_GRAPH" in names

    def test_home_graph_entity(self, parse):
        """USE HOME_GRAPH creates a Graph entity."""
        ast = parse("USE HOME_GRAPH MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        names = {g.name for g in result.graphs.values()}
        assert "HOME_GRAPH" in names

    def test_parameter_graph_entity(self, parse):
        """USE $g creates a Graph entity with name='$g'."""
        ast = parse("USE $g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        names = {g.name for g in result.graphs.values()}
        assert "$g" in names


class TestGraphEntityEdges:
    """Test BELONGS_TO edges from patterns to graphs."""

    def test_pattern_belongs_to_graph_edge(self, parse):
        """BELONGS_TO edge emitted from pattern to its graph."""
        ast = parse("MATCH (n:Person) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        belongs_to = [e for e in result.edges if e.kind == LineageEdgeKind.BELONGS_TO]
        assert len(belongs_to) >= 1
        edge = belongs_to[0]
        assert edge.source_id in result.patterns
        assert edge.target_id in result.graphs

    def test_pattern_belongs_to_graph(self, parse):
        """Pattern connects to Graph via BELONGS_TO edge."""
        ast = parse("MATCH (n:Person) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        belongs_to = [e for e in result.edges if e.kind == LineageEdgeKind.BELONGS_TO]
        pattern = next(iter(result.patterns.values()))
        edge = next(e for e in belongs_to if e.source_id == pattern.id)
        assert edge.target_id in result.graphs

    def test_bare_output_belongs_to_graph(self, parse):
        """USE g RETURN 1 — output without binding deps gets BELONGS_TO edge."""
        ast = parse("USE g RETURN 1")
        result = LineageAnalyzer().analyze(ast)

        output = next(iter(result.outputs.values()))
        belongs_to = [
            e
            for e in result.edges
            if e.source_id == output.id and e.kind == LineageEdgeKind.BELONGS_TO
        ]
        assert len(belongs_to) == 1
        assert result.graphs[belongs_to[0].target_id].name == "g"


class TestGraphEntityExport:
    """Test Graph entity in exports."""

    def test_dict_export_has_graph_nodes(self, parse):
        """to_dict() nodes include graph entities."""
        ast = parse("USE g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        d = LineageExporter(result).to_dict()
        graphs = [n for n in d["nodes"] if n["node_type"] == "graph"]
        assert len(graphs) >= 1

    def test_no_graph_id_on_entities(self, parse):
        """Graph context is tracked via BELONGS_TO edges, not graph_id fields."""
        ast = parse("USE g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        d = LineageExporter(result).to_dict()
        bindings = [n for n in d["nodes"] if n["node_type"] == "binding"]
        outputs = [n for n in d["nodes"] if n["node_type"] == "output"]
        patterns = [n for n in d["nodes"] if n["node_type"] == "pattern"]
        assert "graph_id" not in bindings[0]
        assert "graph_id" not in outputs[0]
        assert "graph_id" not in patterns[0]

    def test_json_roundtrip_graphs(self, parse):
        """Graphs survive JSON round-trip."""
        ast = parse("USE g MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        j = LineageExporter(result).to_json()
        data = json.loads(j)
        graphs = [n for n in data["nodes"] if n["node_type"] == "graph"]
        assert len(graphs) >= 1
        graph_entry = graphs[0]
        assert "id" in graph_entry
        assert "name" in graph_entry
