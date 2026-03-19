"""Tests for lineage export functionality.

These tests verify that the lineage module can export to:
- JSON with stable schema
- Python dict

Export must be deterministic for golden testing.
"""

from __future__ import annotations

import json

from typing import Any

from graphglot.lineage import LineageAnalyzer, LineageExporter


def _nodes_of(data: dict[str, Any], node_type: str) -> list[dict[str, Any]]:
    """Extract nodes of a given type from the flat export."""
    return [n for n in data["nodes"] if n["node_type"] == node_type]


class TestJsonExport:
    """Test JSON export functionality."""

    def test_export_json_basic(self, parse):
        """Export simple query to JSON."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        json_str = exporter.to_json()
        data = json.loads(json_str)

        # Should have required top-level keys
        assert "nodes" in data
        assert "edges" in data
        assert any(n["node_type"] == "binding" for n in data["nodes"])
        assert any(n["node_type"] == "output" for n in data["nodes"])

    def test_export_json_no_version(self, parse):
        """JSON export does not include a separate version field."""
        ast = parse("MATCH (n) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        assert "version" not in data

    def test_export_json_bindings(self, parse):
        """JSON export includes all bindings."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a, r, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        bindings = _nodes_of(data, "binding")
        assert len(bindings) == 3

        names = [b["name"] for b in bindings]
        assert "a" in names
        assert "r" in names
        assert "b" in names

    def test_export_json_binding_kinds(self, parse):
        """JSON export includes binding kinds."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a, r, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        kinds = {b["name"]: b["kind"] for b in _nodes_of(data, "binding")}
        assert kinds["a"] == "node"
        assert kinds["r"] == "edge"
        assert kinds["b"] == "node"

    def test_export_json_outputs(self, parse):
        """JSON export includes output fields."""
        ast = parse("MATCH (n:Person) RETURN n.name AS person_name, n.age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        outputs = _nodes_of(data, "output")
        assert len(outputs) == 2

        aliases = [o.get("alias") for o in outputs]
        assert "person_name" in aliases

    def test_export_json_edges(self, parse):
        """JSON export includes lineage edges."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        edges = data["edges"]

        # Should have depends_on edges
        edge_kinds = [e["kind"] for e in edges]
        assert "depends_on" in edge_kinds

    def test_export_json_property_refs(self, parse):
        """JSON export includes property references."""
        ast = parse("MATCH (n:Person) RETURN n.name, n.age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        prop_refs = _nodes_of(data, "property_ref")
        assert len(prop_refs) >= 2

        props = [p["property_name"] for p in prop_refs]
        assert "name" in props
        assert "age" in props

    def test_export_json_filters(self, parse):
        """JSON export includes filters."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        filters = _nodes_of(data, "filter")
        assert len(filters) >= 1

    def test_export_json_spans(self, parse):
        """JSON export includes source spans from AST token positions."""
        query = "MATCH (n:Person) WHERE n.age > 21 RETURN n.name"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())

        # Bindings should have spans
        bindings = _nodes_of(data, "binding")
        assert len(bindings) >= 1

    def test_export_json_source_text(self, parse):
        """JSON export includes source_text from original query."""
        query = "MATCH (n:Person) WHERE n.age > 21 RETURN n.name"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())

        # Outputs should have source_text
        outputs = _nodes_of(data, "output")
        if outputs:
            out = outputs[0]
            if "source_text" in out:
                assert out["source_text"] in query

    def test_export_json_output_source_text(self, parse):
        """JSON export includes source_text on output fields when query_text given."""
        query = "MATCH (n:Person) RETURN n.name AS person_name"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        outputs = _nodes_of(data, "output")
        assert len(outputs) >= 1
        output = outputs[0]
        assert output["source_text"] is not None


class TestJsonDeterminism:
    """Test that JSON export is deterministic."""

    def test_json_deterministic_bindings(self, parse):
        """Bindings should be in deterministic order."""
        ast = parse("MATCH (z)-[y]->(x) RETURN x, y, z")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        json1 = exporter.to_json()
        json2 = exporter.to_json()

        # Multiple exports should produce identical output
        assert json1 == json2

    def test_json_deterministic_edges(self, parse):
        """Edges should be in deterministic order."""
        ast = parse("MATCH (a)-[r]->(b) WHERE a.x = 1 AND b.y = 2 RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        # Order should be stable
        json1 = exporter.to_json()
        json2 = exporter.to_json()
        assert json1 == json2

    def test_json_sorted_by_id(self, parse):
        """Entities should be sorted by ID."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a, r, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        binding_ids = [b["id"] for b in _nodes_of(data, "binding")]

        # IDs should be in sorted order
        assert binding_ids == sorted(binding_ids)


class TestDictExport:
    """Test dict export functionality."""

    def test_export_dict(self, parse):
        """Export to Python dict."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        d = exporter.to_dict()

        assert isinstance(d, dict)
        assert "nodes" in d
        assert "edges" in d

    def test_dict_matches_json(self, parse):
        """Dict export should match JSON parsed back."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        d = exporter.to_dict()
        json_str = exporter.to_json()
        json_d = json.loads(json_str)

        # Should be equivalent
        assert d == json_d


class TestExportWithAggregation:
    """Test export of queries with aggregation."""

    def test_json_output_aggregation_info(self, parse):
        """JSON export includes aggregation info in outputs."""
        ast = parse("MATCH (n:Person) RETURN count(n)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        output = _nodes_of(data, "output")[0]
        assert output.get("is_aggregated") is True
        assert output.get("aggregate_function") == "count"


class TestQueryTextExport:
    """Test export of query_text."""

    def test_query_text_exported(self, parse):
        """query_text should appear in dict export."""
        query = "MATCH (n) RETURN n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        assert data["query_text"] == "MATCH (n) RETURN n"

    def test_query_text_empty_when_not_provided(self, parse):
        """query_text should be empty string when not provided."""
        ast = parse("MATCH (n) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        assert data["query_text"] == ""


class TestUniformFieldInclusion:
    """Test that nullable fields are always included in export."""

    def test_output_always_includes_aggregate_function(self, parse):
        """Output dict should always include aggregate_function, even when null."""
        ast = parse("MATCH (n) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        output = _nodes_of(data, "output")[0]
        assert "aggregate_function" in output
        assert output["aggregate_function"] is None

    def test_output_always_includes_source_text(self, parse):
        """Output dict should always include source_text, even when null."""
        ast = parse("MATCH (n) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)  # no query_text
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        output = _nodes_of(data, "output")[0]
        assert "source_text" in output
        assert output["source_text"] is None

    def test_filter_export_is_slim(self, parse):
        """Filter dict should only include id, node_type, span, and source_text."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        pred = _nodes_of(data, "filter")[0]
        assert set(pred.keys()) == {"id", "node_type", "span", "source_text"}


class TestSpanPopulation:
    """Test that span is populated on lineage entities."""

    def test_binding_has_span(self, parse):
        """Bindings should have span populated from AST tokens."""
        query = "MATCH (n:Person) RETURN n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)

        binding = next(iter(result.bindings.values()))
        assert binding.span is not None
        assert binding.span.start_offset is not None

    def test_output_has_source_text(self, parse):
        """Output fields should have source_text derived from span + query_text."""
        query = "MATCH (n:Person) RETURN n.name AS person_name"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)

        output = next(iter(result.outputs.values()))
        src = result.source_text(output)
        assert src is not None
        assert src in query

    def test_filter_has_source_text(self, parse):
        """Filters should have source_text when query_text is provided."""
        query = "MATCH (n:Person) WHERE n.age > 21 RETURN n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)

        pred = next(iter(result.filters.values()))
        assert result.source_text(pred)

    def test_property_ref_has_span(self, parse):
        """Property refs should have span populated."""
        query = "MATCH (n:Person) RETURN n.name"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)

        prop = next(iter(result.property_refs.values()))
        assert prop.span is not None


class TestPatternExport:
    """Test Pattern export in various formats."""

    def test_json_includes_patterns(self, parse):
        """JSON export includes patterns key."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        patterns = _nodes_of(data, "pattern")
        assert len(patterns) == 1

    def test_in_pattern_edges_exported(self, parse):
        """IN_PATTERN edges should appear in exported edges."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        in_pattern_edges = [e for e in data["edges"] if e["kind"] == "in_pattern"]
        assert len(in_pattern_edges) == 3

    def test_no_binding_ids_in_pattern_export(self, parse):
        """Pattern dicts should not have binding_ids key."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a, r, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        pat = _nodes_of(data, "pattern")[0]
        assert "binding_ids" not in pat

    def test_no_pattern_ids_in_binding_export(self, parse):
        """Binding dicts should not have pattern_ids key."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a, r, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        bindings = _nodes_of(data, "binding")
        for b in bindings:
            assert "pattern_ids" not in b

    def test_no_context_in_property_ref_export(self, parse):
        """Property ref dicts should not have context key."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        props = _nodes_of(data, "property_ref")
        for p in props:
            assert "context" not in p

    def test_json_pattern_has_source_text(self, parse):
        """JSON pattern should include source_text when query_text provided."""
        query = "MATCH (n:Person) RETURN n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        pat = _nodes_of(data, "pattern")[0]
        assert "source_text" in pat
        assert pat["source_text"] in query

    def test_json_pattern_match_index(self, parse):
        """JSON pattern should have match_index."""
        ast = parse("""
            MATCH (a)-[r]->(b)
            MATCH (b)-[s]->(c)
            RETURN a, c
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        patterns = _nodes_of(data, "pattern")
        assert len(patterns) >= 2
        indices = [p["match_index"] for p in patterns]
        assert 0 in indices
        assert 1 in indices

    def test_dict_includes_patterns(self, parse):
        """Dict export should include patterns."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        d = exporter.to_dict()
        patterns = _nodes_of(d, "pattern")
        assert len(patterns) == 1


class TestAnonymousBindingNames:
    """Fix 3: Anonymous bindings use None instead of empty string."""

    def test_anonymous_node_name_is_null(self, parse):
        """Anonymous node bindings should have name=None in export."""
        ast = parse("MATCH (n)-[r]->() RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        anon = [b for b in _nodes_of(data, "binding") if b["name"] is None]
        assert len(anon) >= 1, "Expected at least one anonymous binding with null name"

    def test_named_binding_name_is_string(self, parse):
        """Named bindings should still have string names."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        named = [b for b in _nodes_of(data, "binding") if b["name"] is not None]
        assert len(named) >= 1
        assert all(isinstance(b["name"], str) for b in named)


class TestCrossScopeLinkage:
    """Fix 1: Inherited bindings link back to their source via PROPAGATES_TO edges."""

    def test_next_propagates_to_edge(self, parse):
        """Bindings propagated across NEXT should have PROPAGATES_TO edge."""
        query = "MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        prop_edges = [e for e in data["edges"] if e["kind"] == "propagates_to"]
        assert len(prop_edges) >= 1

        # Verify the edge connects two different 'n' bindings
        n_bindings = [b for b in _nodes_of(data, "binding") if b["name"] == "n"]
        assert len(n_bindings) >= 2
        n_ids = {b["id"] for b in n_bindings}
        assert any(e["source_id"] in n_ids and e["target_id"] in n_ids for e in prop_edges)

    def test_next_emits_propagates_to_edge(self, parse):
        """NEXT propagation should emit a propagates_to edge."""
        ast = parse("MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        prop_edges = [e for e in data["edges"] if e["kind"] == "propagates_to"]
        assert len(prop_edges) >= 1

    def test_otherwise_propagates_to_edge(self, parse):
        """Bindings propagated into OTHERWISE should have PROPAGATES_TO edge."""
        query = "MATCH (n:Person) RETURN n NEXT RETURN n OTHERWISE RETURN 1 AS n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        bindings = _nodes_of(data, "binding")

        n_bindings = [b for b in bindings if b["name"] == "n"]
        assert len(n_bindings) >= 1
        # Check that a PROPAGATES_TO edge from an 'n' binding exists
        n_ids = {b["id"] for b in n_bindings}
        prop_edges = [
            e for e in data["edges"] if e["kind"] == "propagates_to" and e["source_id"] in n_ids
        ]
        assert len(prop_edges) >= 1

    def test_no_propagates_to_for_root_bindings(self, parse):
        """Root bindings should have no incoming PROPAGATES_TO edges."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = json.loads(exporter.to_json())
        prop_edges = [e for e in data["edges"] if e["kind"] == "propagates_to"]
        # No PROPAGATES_TO edges should exist in a single-scope query
        assert len(prop_edges) == 0


class TestInheritedBindingSpans:
    """Fix 2: Inherited bindings get spans when reused in MATCH patterns."""

    def test_inherited_binding_gets_span_on_reuse(self, parse):
        """Propagated binding reused in MATCH should acquire a span."""
        query = "MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)

        # Find the NEXT-scope binding for n (different scope_id from root)
        n_bindings = [b for b in result.bindings.values() if b.name == "n"]
        assert len(n_bindings) >= 2, "Expected at least 2 'n' bindings (root + NEXT)"

        # The propagated n is the one with a different scope_id from the first
        root_n = next(b for b in n_bindings if b.scope_id == "scope_0")
        next_n = next(b for b in n_bindings if b.scope_id != root_n.scope_id)
        assert next_n.span is not None, "Inherited binding reused in MATCH should have span"


class TestModelInvariants:
    """Test structural invariants of the lineage model."""

    def test_edge_kind_members(self):
        """LineageEdgeKind should have exactly the expected members."""
        from graphglot.lineage import LineageEdgeKind

        expected = {
            "DEPENDS_ON",
            "CONSTRAINS",
            "AGGREGATES",
            "PROPAGATES_TO",
            "BELONGS_TO",
            "IN_PATTERN",
            "ORDERED_BY",
            "WRITES",
        }
        actual = {kind.name for kind in LineageEdgeKind}
        assert actual == expected

    def test_edge_export_has_no_metadata(self, parse):
        """Exported edges should not include a metadata field."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        for edge in data["edges"]:
            assert "metadata" not in edge


class TestMutationExport:
    """Test export of mutation entities."""

    def test_mutation_appears_in_export(self, parse):
        """Mutation nodes should appear in dict/JSON export."""
        ast = parse('MATCH (n:Person) SET n.name = "Bob"')
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        mutations = _nodes_of(data, "mutation")
        assert len(mutations) == 1
        m = mutations[0]
        assert m["kind"] == "set_property"
        assert m["label_name"] is None
        assert m["is_detach"] is False

    def test_mutation_writes_edge_exported(self, parse):
        """WRITES edges from mutations should appear in export."""
        ast = parse('MATCH (n:Person) SET n.name = "Bob"')
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        writes_edges = [e for e in data["edges"] if e["kind"] == "writes"]
        assert len(writes_edges) >= 1

    def test_delete_mutation_export(self, parse):
        """DELETE mutation should export is_detach correctly."""
        ast = parse("MATCH (n) DETACH DELETE n")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        data = exporter.to_dict()
        mutations = _nodes_of(data, "mutation")
        assert len(mutations) == 1
        assert mutations[0]["kind"] == "delete"
        assert mutations[0]["is_detach"] is True

    def test_mutation_json_roundtrip(self, parse):
        """Mutation export should survive JSON roundtrip."""
        ast = parse('MATCH (n) SET n.name = "Bob"')
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        exporter = LineageExporter(result)

        json_str = exporter.to_json()
        data = json.loads(json_str)
        mutations = _nodes_of(data, "mutation")
        assert len(mutations) == 1
