"""Tests for upstream summary analysis.

These tests verify the upstream() API that answers:
"For each output, what are its upstream dependencies?"
Each dependency is a row with (output_id, graph, label, property).
"""

from __future__ import annotations

from graphglot.lineage import (
    Binding,
    BindingKind,
    DependencyKind,
    Filter,
    Graph,
    ImpactAnalyzer,
    LineageAnalyzer,
    LineageEdge,
    LineageEdgeKind,
    LineageGraph,
    OutputField,
    PropertyRef,
    UpstreamDependency,
    UpstreamSummary,
)
from graphglot.lineage.impact import UpstreamGraph


def _analyze(parse, query: str):
    """Parse query and return (graph, impact_analyzer)."""
    ast = parse(query)
    result = LineageAnalyzer().analyze(ast, query_text=query)
    return result, ImpactAnalyzer(result)


def _find_output_by_pos(graph, pos: int):
    for o in graph.outputs.values():
        if o.position == pos:
            return o
    return None


def _dep_graphs(summary: UpstreamSummary) -> set[str]:
    return {d.graph for d in summary.dependencies if d.graph}


def _dep_labels(summary: UpstreamSummary) -> set[str]:
    return {d.label for d in summary.dependencies if d.label}


def _dep_properties(summary: UpstreamSummary) -> set[str]:
    return {d.property for d in summary.dependencies if d.property}


class TestUpstreamSummary:
    """Test upstream summary for output fields."""

    def test_simple_upstream(self, parse):
        """MATCH (n:Person) RETURN n — labels={Person}, no properties."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        summary = ia.upstream(output)
        assert isinstance(summary, UpstreamSummary)
        assert summary.output_id == output.id
        assert _dep_labels(summary) == {"Person"}
        assert _dep_properties(summary) == set()
        assert _dep_graphs(summary) == set()

    def test_upstream_with_property(self, parse):
        """MATCH (n:Person) RETURN n.name — includes property ref."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        summary = ia.upstream(output)
        assert "name" in _dep_properties(summary)
        assert "Person" in _dep_labels(summary)

    def test_upstream_with_filter(self, parse):
        """Predicate property n.age should appear in upstream properties."""
        graph, ia = _analyze(parse, "MATCH (n:Person) WHERE n.age > 21 RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        summary = ia.upstream(output)
        assert "name" in _dep_properties(summary)
        assert "age" in _dep_properties(summary)
        assert "Person" in _dep_labels(summary)

    def test_upstream_with_graph(self, parse):
        """USE g MATCH (n:Person) RETURN n — graphs={g}."""
        graph, ia = _analyze(parse, "USE g MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        summary = ia.upstream(output)
        assert "g" in _dep_graphs(summary)
        assert "Person" in _dep_labels(summary)

    def test_upstream_edge_labels(self, parse):
        """Edge type labels appear in upstream summary."""
        graph, ia = _analyze(parse, "MATCH (n)-[r:KNOWS]->(m) RETURN n")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        summary = ia.upstream(output)
        assert "KNOWS" in _dep_labels(summary)

    def test_upstream_multi_graph(self, parse):
        """Multi-graph query: each output has correct upstream graph."""
        query = "USE g1 MATCH (a:X) RETURN a NEXT USE g2 MATCH (b:Y) RETURN a, b"
        graph, ia = _analyze(parse, query)

        # Find outputs in the second RETURN (has both a and b)
        outputs = sorted(graph.outputs.values(), key=lambda o: (o.scope_id, o.position))
        # Last scope outputs
        last_scope_outputs = [o for o in outputs if o.scope_id == outputs[-1].scope_id]

        # Output for 'a' should trace back to g1  (position 0 = first in RETURN a, b)
        out_a = next((o for o in last_scope_outputs if o.position == 0), None)
        if out_a:
            summary_a = ia.upstream(out_a)
            assert "g1" in _dep_graphs(summary_a)
            assert "X" in _dep_labels(summary_a)

        # Output for 'b' should trace back to g2  (position 1 = second in RETURN a, b)
        out_b = next((o for o in last_scope_outputs if o.position == 1), None)
        if out_b:
            summary_b = ia.upstream(out_b)
            assert "g2" in _dep_graphs(summary_b)
            assert "Y" in _dep_labels(summary_b)

    def test_upstream_inherited_binding(self, parse):
        """Inherited bindings carry upstream context through inherits_from chain."""
        query = "USE g MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n"
        graph, ia = _analyze(parse, query)

        # Find the output in the second RETURN
        outputs = sorted(graph.outputs.values(), key=lambda o: (o.scope_id, o.position))
        last_output = outputs[-1]

        summary = ia.upstream(last_output)
        assert "g" in _dep_graphs(summary)
        assert "Person" in _dep_labels(summary)

    def test_upstream_all_outputs(self, parse):
        """upstream_all() returns summaries for all outputs."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name, n.age")
        summaries = ia.upstream_all()
        assert len(summaries) >= 2
        all_props = set()
        for s in summaries:
            all_props |= _dep_properties(s)
        assert "name" in all_props
        assert "age" in all_props

    def test_upstream_no_bindings(self, parse):
        """USE g RETURN 1 — graphs={g}, no labels or properties."""
        graph, ia = _analyze(parse, "USE g RETURN 1")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        summary = ia.upstream(output)
        assert "g" in _dep_graphs(summary)
        assert _dep_labels(summary) == set()
        assert _dep_properties(summary) == set()


class TestUpstreamRowPerDependency:
    """Test row-per-dependency model for upstream summary."""

    def test_row_per_dependency(self, parse):
        """Each label/property combo is a separate row."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name, n.age")
        output_name = _find_output_by_pos(graph, 0)
        output_age = _find_output_by_pos(graph, 1)
        assert output_name is not None and output_age is not None

        s = ia.upstream(output_name)
        # Should have a row with label=Person and property=n.name
        assert any(d.label == "Person" and d.property == "name" for d in s.dependencies)

        s2 = ia.upstream(output_age)
        assert any(d.label == "Person" and d.property == "age" for d in s2.dependencies)

    def test_dedup(self, parse):
        """Duplicate (graph, label, prop) collapsed to one row."""
        graph, ia = _analyze(parse, "MATCH (n:Person) WHERE n.name > 'A' RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        s = ia.upstream(output)
        name_rows = [d for d in s.dependencies if d.property == "name"]
        assert len(name_rows) == 1

    def test_pattern_only_label(self, parse):
        """Label from pattern co-membership (no property access) -> row with empty property."""
        graph, ia = _analyze(parse, "MATCH (n:Person)-[:KNOWS]->(m:Company) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        s = ia.upstream(output)
        # Company and KNOWS should appear as labels with empty property
        assert any(d.label == "Company" and d.property == "" for d in s.dependencies)
        assert any(d.label == "KNOWS" and d.property == "" for d in s.dependencies)

    def test_no_label_with_property(self, parse):
        """Anonymous binding (n) with n.name -> row with empty label."""
        graph, ia = _analyze(parse, "MATCH (n) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        s = ia.upstream(output)
        assert any(d.property == "name" and d.label == "" for d in s.dependencies)

    def test_label_without_property(self, parse):
        """(n:Person) referenced but no property access -> row with label, empty property."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        s = ia.upstream(output)
        assert any(d.label == "Person" and d.property == "" for d in s.dependencies)

    def test_dependencies_are_upstream_dependency(self, parse):
        """Each dependency is an UpstreamDependency instance."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        assert all(isinstance(d, UpstreamDependency) for d in s.dependencies)

    def test_multi_graph_rows(self, parse):
        """Different outputs from different graphs -> correct graph per row."""
        query = "USE g1 MATCH (a:X) RETURN a NEXT USE g2 MATCH (b:Y) RETURN a, b"
        graph, ia = _analyze(parse, query)
        outputs = sorted(graph.outputs.values(), key=lambda o: (o.scope_id, o.position))
        last_scope_outputs = [o for o in outputs if o.scope_id == outputs[-1].scope_id]

        out_b = next((o for o in last_scope_outputs if o.position == 1), None)  # position 1 = 'b'
        if out_b:
            s = ia.upstream(out_b)
            # b is from g2 with label Y
            assert any(d.graph == "g2" and d.label == "Y" for d in s.dependencies)


class TestUpstreamComplexPatterns:
    """Test upstream summary with multi-hop, multi-pattern, and compound WHERE."""

    def test_multi_hop_chain(self, parse):
        """Three-hop path: all labels and edge types in upstream."""
        query = (
            "MATCH (a:Person)-[r1:WORKS_AT]->(c:Company)"
            "-[r2:LOCATED]->(ci:City) "
            "RETURN a.name, ci.name"
        )
        graph, ia = _analyze(parse, query)
        outputs = sorted(graph.outputs.values(), key=lambda o: o.position)

        # a.name: all five bindings share one pattern, so all labels appear
        s_a = ia.upstream(outputs[0])
        assert _dep_labels(s_a) == {"Person", "WORKS_AT", "Company", "LOCATED", "City"}
        assert "name" in _dep_properties(s_a)

        # ci.name: same pattern, same labels
        s_ci = ia.upstream(outputs[1])
        assert "City" in _dep_labels(s_ci)
        assert "Person" in _dep_labels(s_ci)
        assert "name" in _dep_properties(s_ci)

    def test_compound_where_cross_binding(self, parse):
        """WHERE constrains multiple bindings: properties propagate across."""
        query = (
            "MATCH (a:Person)-[r:WORKS_AT]->(c:Company) "
            "WHERE a.age > 25 AND c.revenue > 100 "
            "RETURN a.name, c.name"
        )
        graph, ia = _analyze(parse, query)
        outputs = sorted(graph.outputs.values(), key=lambda o: o.position)

        # a.name should include c.revenue (predicate on c, which is
        # pattern-connected to a in the same pattern)
        s_a = ia.upstream(outputs[0])
        assert "name" in _dep_properties(s_a)
        assert "age" in _dep_properties(s_a)
        assert "revenue" in _dep_properties(s_a)
        assert "Person" in _dep_labels(s_a)
        assert "Company" in _dep_labels(s_a)
        assert "WORKS_AT" in _dep_labels(s_a)

        # c.name should include a.age for the same reason
        s_c = ia.upstream(outputs[1])
        assert "name" in _dep_properties(s_c)
        assert "age" in _dep_properties(s_c)
        assert "revenue" in _dep_properties(s_c)

    def test_multi_pattern_shared_bindings(self, parse):
        """Two patterns sharing node bindings: both edge types appear."""
        query = (
            "MATCH (a:Person)-[r1:KNOWS]->(b:Person), "
            "(a)-[r2:WORKS_WITH]->(b) "
            "WHERE a.age > 30 "
            "RETURN a.name, b.name"
        )
        graph, ia = _analyze(parse, query)
        outputs = sorted(graph.outputs.values(), key=lambda o: o.position)

        # Both edge types should appear via pattern co-membership
        s_a = ia.upstream(outputs[0])
        assert "KNOWS" in _dep_labels(s_a)
        assert "WORKS_WITH" in _dep_labels(s_a)
        assert "Person" in _dep_labels(s_a)
        assert "age" in _dep_properties(s_a)

        s_b = ia.upstream(outputs[1])
        assert "KNOWS" in _dep_labels(s_b)
        assert "WORKS_WITH" in _dep_labels(s_b)
        # Predicate on a propagates to b (via same-pattern)
        assert "age" in _dep_properties(s_b)

    def test_next_chain_filter_propagation(self, parse):
        """NEXT chain: final scope output picks up its own WHERE properties."""
        query = (
            "USE g MATCH (a:Employee) WHERE a.dept = 'eng' "
            "RETURN a.name AS name, a.salary AS salary "
            "NEXT MATCH (x) WHERE x.salary > 100000 "
            "RETURN x.name"
        )
        graph, ia = _analyze(parse, query)

        # Intermediate outputs (before NEXT) are removed — only final output exists
        outputs = list(graph.outputs.values())
        assert len(outputs) == 1

        s_x = ia.upstream(outputs[0])
        assert "salary" in _dep_properties(s_x)
        assert "name" in _dep_properties(s_x)

    def test_inherited_binding_with_property_access(self, parse):
        """Property access on inherited binding traces through to original labels."""
        query = "USE g MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n.name"
        graph, ia = _analyze(parse, query)

        # The second RETURN's n.name should trace back through inheritance
        outputs = sorted(graph.outputs.values(), key=lambda o: (o.scope_id, o.position))
        last_output = outputs[-1]

        summary = ia.upstream(last_output)
        assert "g" in _dep_graphs(summary)
        assert "Person" in _dep_labels(summary)
        assert "name" in _dep_properties(summary)

    def test_predicate_introduces_additional_properties(self, parse):
        """WHERE clause on a different property than RETURN adds to upstream."""
        query = "MATCH (n:Person) WHERE n.active = TRUE AND n.score > 50 RETURN n.name"
        graph, ia = _analyze(parse, query)
        output = _find_output_by_pos(graph, 0)
        assert output is not None

        summary = ia.upstream(output)
        assert "name" in _dep_properties(summary)
        # Both WHERE properties should appear even though only n.name is returned
        assert "active" in _dep_properties(summary)
        assert "score" in _dep_properties(summary)
        assert "Person" in _dep_labels(summary)

    def test_upstream_per_output_independence(self, parse):
        """Each output's upstream reflects its own binding dependencies."""
        query = "MATCH (a:Person)-[r:KNOWS]->(b:Researcher) RETURN a.name, b.title"
        graph, ia = _analyze(parse, query)
        outputs = sorted(graph.outputs.values(), key=lambda o: o.position)

        s_a = ia.upstream(outputs[0])
        s_b = ia.upstream(outputs[1])

        # Both share the same pattern, so both see all labels
        assert "Person" in _dep_labels(s_a)
        assert "Researcher" in _dep_labels(s_a)
        assert "KNOWS" in _dep_labels(s_a)

        # But each output's direct property is specific
        assert "name" in _dep_properties(s_a)
        assert "title" in _dep_properties(s_b)

    def test_multi_output_aggregation_upstream(self, parse):
        """Aggregated and non-aggregated outputs share upstream labels."""
        query = "MATCH (n:Person)-[r:BOUGHT]->(p:Item) RETURN p.category, count(n)"
        graph, ia = _analyze(parse, query)
        outputs = sorted(graph.outputs.values(), key=lambda o: o.position)

        # Non-aggregated output
        s_cat = ia.upstream(outputs[0])
        assert "Item" in _dep_labels(s_cat)
        assert "BOUGHT" in _dep_labels(s_cat)
        assert "Person" in _dep_labels(s_cat)
        assert "category" in _dep_properties(s_cat)

        # Aggregated output (count(n))
        s_count = ia.upstream(outputs[1])
        assert "Person" in _dep_labels(s_count)


class TestUpstreamGraph:
    """Test graph-structured upstream export (Neo4j-style nodes + relationships)."""

    def test_graph_nodes(self, parse):
        """MATCH (n:Person) RETURN n.name — Output, Binding, Pattern, Property nodes."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        ug = ia.upstream_graph(output)

        assert isinstance(ug, UpstreamGraph)

        # Should have Output, Binding, Pattern, Property nodes
        output_nodes = [n for n in ug.nodes if "Output" in n.labels]
        binding_nodes = [n for n in ug.nodes if "Binding" in n.labels]
        pattern_nodes = [n for n in ug.nodes if "Pattern" in n.labels]
        property_nodes = [n for n in ug.nodes if "Property" in n.labels]

        assert len(output_nodes) == 1
        assert len(binding_nodes) >= 1
        assert len(pattern_nodes) >= 1
        assert len(property_nodes) >= 1

        # Output node properties
        out_n = output_nodes[0]
        assert out_n.properties["expression"] == "n.name"

        # Binding node has kind label
        b_n = next(n for n in binding_nodes if n.properties.get("name") == "n")
        assert "Node" in b_n.labels

        # Property node
        p_n = next(n for n in property_nodes if n.properties.get("name") == "name")
        assert p_n.properties["binding"] == "n"

    def test_graph_depends_on(self, parse):
        """MATCH (n:Person) RETURN n.name — DEPENDS_ON edges from output."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        ug = ia.upstream_graph(output)

        depends_on = [r for r in ug.relationships if r.type == "DEPENDS_ON"]
        assert len(depends_on) >= 1

        # At least one DEPENDS_ON from the output node
        output_node = next(n for n in ug.nodes if "Output" in n.labels)
        out_deps = [r for r in depends_on if r.start_node == output_node.id]
        assert len(out_deps) >= 1

    def test_graph_in_pattern(self, parse):
        """MATCH (n:Person) RETURN n — IN_PATTERN edge from binding to pattern."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        ug = ia.upstream_graph(output)

        in_pattern = [r for r in ug.relationships if r.type == "IN_PATTERN"]
        assert len(in_pattern) >= 1

        # Verify it goes from a Binding to a Pattern
        binding_ids = {n.id for n in ug.nodes if "Binding" in n.labels}
        pattern_ids = {n.id for n in ug.nodes if "Pattern" in n.labels}
        for r in in_pattern:
            assert r.start_node in binding_ids
            assert r.end_node in pattern_ids

    def test_graph_on_graph(self, parse):
        """USE g MATCH (n:Person) RETURN n — Graph node + ON_GRAPH edge."""
        graph, ia = _analyze(parse, "USE g MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        ug = ia.upstream_graph(output)

        graph_nodes = [n for n in ug.nodes if "Graph" in n.labels]
        assert len(graph_nodes) >= 1
        assert graph_nodes[0].properties["name"] == "g"

        on_graph = [r for r in ug.relationships if r.type == "ON_GRAPH"]
        assert len(on_graph) >= 1

    def test_graph_filter_constrains(self, parse):
        """MATCH (n:Person) WHERE n.age > 21 RETURN n.name — Filter node + edges."""
        graph, ia = _analyze(parse, "MATCH (n:Person) WHERE n.age > 21 RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        ug = ia.upstream_graph(output)

        pred_nodes = [n for n in ug.nodes if "Filter" in n.labels]
        assert len(pred_nodes) >= 1

        constrains = [r for r in ug.relationships if r.type == "CONSTRAINS"]
        assert len(constrains) >= 1

    def test_graph_no_topology_relationships(self, parse):
        """MATCH (n)-[r:KNOWS]->(m) RETURN n — no TOPOLOGY rels (removed)."""
        graph, ia = _analyze(parse, "MATCH (n)-[r:KNOWS]->(m) RETURN n")
        output = _find_output_by_pos(graph, 0)
        ug = ia.upstream_graph(output)

        topology = [r for r in ug.relationships if r.type == "TOPOLOGY"]
        assert len(topology) == 0

    def test_graph_inherits_from(self, parse):
        """NEXT chain — INHERITS_FROM relationship between bindings."""
        query = "USE g MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n"
        graph, ia = _analyze(parse, query)

        outputs = sorted(graph.outputs.values(), key=lambda o: (o.scope_id, o.position))
        last_output = outputs[-1]
        ug = ia.upstream_graph(last_output)

        inherits = [r for r in ug.relationships if r.type == "INHERITS_FROM"]
        assert len(inherits) >= 1

    def test_graph_all_deduplicates(self, parse):
        """upstream_graph_all() deduplicates shared binding nodes."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name, n.age")
        ug = ia.upstream_graph_all()

        # Should have exactly one binding node for n, not two
        binding_nodes = [
            n for n in ug.nodes if "Binding" in n.labels and n.properties.get("name") == "n"
        ]
        assert len(binding_nodes) == 1

        # Two output nodes
        output_nodes = [n for n in ug.nodes if "Output" in n.labels]
        assert len(output_nodes) == 2

    def test_graph_all_keeps_distinct_branch_outputs(self, parse):
        """Merged upstream graph should not collapse outputs from different branches."""
        query = "MATCH (n:Person) RETURN n OTHERWISE MATCH (m:Company) RETURN m"
        graph, ia = _analyze(parse, query)
        ug = ia.upstream_graph_all()

        output_nodes = [n for n in ug.nodes if "Output" in n.labels]
        assert len(output_nodes) == 2

        output_expressions = {n.properties["expression"] for n in output_nodes}
        assert output_expressions == {"n", "m"}

        binding_names = {
            n.properties["name"]
            for n in ug.nodes
            if "Binding" in n.labels and n.properties.get("name") is not None
        }
        assert {"n", "m"}.issubset(binding_names)

    def test_graph_to_dict_structure(self, parse):
        """to_dict() returns proper Neo4j-style structure."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        ug = ia.upstream_graph(output)
        d = ug.to_dict()

        assert "nodes" in d
        assert "relationships" in d
        assert isinstance(d["nodes"], list)
        assert isinstance(d["relationships"], list)

        # Each node has id, labels, properties
        for node in d["nodes"]:
            assert "id" in node
            assert "labels" in node
            assert "properties" in node

        # Each relationship has id, type, startNode, endNode, properties
        for rel in d["relationships"]:
            assert "id" in rel
            assert "type" in rel
            assert "startNode" in rel
            assert "endNode" in rel
            assert "properties" in rel


class TestDependencyKind:
    """Test dependency kind classification on upstream rows."""

    def test_direct_property(self, parse):
        """RETURN n.name → n.name row has kind=DIRECT."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        name_dep = next(d for d in s.dependencies if d.property == "name")
        assert name_dep.kind == DependencyKind.DIRECT

    def test_constraint_property(self, parse):
        """WHERE n.age > 21 RETURN n.name → n.age row has kind=CONSTRAINT."""
        graph, ia = _analyze(parse, "MATCH (n:Person) WHERE n.age > 21 RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        name_dep = next(d for d in s.dependencies if d.property == "name")
        assert name_dep.kind == DependencyKind.DIRECT
        age_dep = next(d for d in s.dependencies if d.property == "age")
        assert age_dep.kind == DependencyKind.CONSTRAINT

    def test_pattern_label(self, parse):
        """Pattern-connected labels have kind=PATTERN."""
        graph, ia = _analyze(parse, "MATCH (n:Person)-[:KNOWS]->(m:Company) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        company_dep = next(d for d in s.dependencies if d.label == "Company" and not d.property)
        assert company_dep.kind == DependencyKind.PATTERN
        knows_dep = next(d for d in s.dependencies if d.label == "KNOWS" and not d.property)
        assert knows_dep.kind == DependencyKind.PATTERN

    def test_direct_label(self, parse):
        """Directly referenced binding's label appears on the property row."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        # Label is carried on the property row, no separate label-only row
        name_dep = next(d for d in s.dependencies if d.property == "name")
        assert name_dep.label == "Person"
        assert name_dep.kind == DependencyKind.DIRECT

    def test_direct_binding_return_whole_node(self, parse):
        """MATCH (n:Person) RETURN n → Person label has kind=DIRECT."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        person_dep = next(d for d in s.dependencies if d.label == "Person")
        assert person_dep.kind == DependencyKind.DIRECT

    def test_mixed_direct_wins(self, parse):
        """Property in both RETURN and WHERE → single row with kind=DIRECT."""
        graph, ia = _analyze(parse, "MATCH (n:Person) WHERE n.name > 'A' RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        name_rows = [d for d in s.dependencies if d.property == "name"]
        assert len(name_rows) == 1
        assert name_rows[0].kind == DependencyKind.DIRECT

    def test_graph_dependency_kind(self, parse):
        """USE g RETURN 1 → pure graph dep has kind=DIRECT."""
        graph, ia = _analyze(parse, "USE g RETURN 1")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        graph_dep = next(d for d in s.dependencies if d.graph == "g")
        assert graph_dep.kind == DependencyKind.DIRECT


class TestUpstreamSummaryIdentity:
    """Test that upstream summaries track property refs by ID internally."""

    def test_same_binding_name_property_from_different_bindings_stays_distinct(self):
        """Rows should remain distinct when two bindings both spell as n.name."""
        graph = LineageGraph()

        graph.nodes["g_0"] = Graph(id="g_0", name="g1")
        graph.nodes["g_1"] = Graph(id="g_1", name="g2")
        graph.nodes["b_0"] = Binding(
            id="b_0",
            name="n",
            kind=BindingKind.NODE,
            label_expression="Person",
        )
        graph.nodes["b_1"] = Binding(
            id="b_1",
            name="n",
            kind=BindingKind.NODE,
            label_expression="Company",
        )
        graph.nodes["prop_0"] = PropertyRef(id="prop_0", property_name="name")
        graph.nodes["prop_1"] = PropertyRef(id="prop_1", property_name="name")
        graph.nodes["f_0"] = Filter(id="f_0")
        graph.nodes["o_0"] = OutputField(id="o_0", position=0)

        graph.edges.extend(
            [
                LineageEdge("b_0", "g_0", LineageEdgeKind.BELONGS_TO),
                LineageEdge("b_1", "g_1", LineageEdgeKind.BELONGS_TO),
                LineageEdge("prop_0", "b_0", LineageEdgeKind.DEPENDS_ON),
                LineageEdge("prop_1", "b_1", LineageEdgeKind.DEPENDS_ON),
                LineageEdge("o_0", "prop_0", LineageEdgeKind.DEPENDS_ON),
                LineageEdge("f_0", "b_0", LineageEdgeKind.CONSTRAINS),
                LineageEdge("f_0", "b_1", LineageEdgeKind.CONSTRAINS),
                LineageEdge("f_0", "prop_1", LineageEdgeKind.CONSTRAINS),
            ]
        )

        summary = ImpactAnalyzer(graph).upstream(graph.outputs["o_0"])

        name_rows = [d for d in summary.dependencies if d.property == "name"]
        assert len(name_rows) == 2
        assert {(d.graph, d.label, d.kind) for d in name_rows} == {
            ("g1", "Person", DependencyKind.DIRECT),
            ("g2", "Company", DependencyKind.CONSTRAINT),
        }


class TestUpstreamSummaryToDict:
    """Test UpstreamSummary.to_dict() serialization."""

    def test_to_dict_structure(self, parse):
        """to_dict() returns output + dependencies list."""
        graph, ia = _analyze(parse, "MATCH (n:Person) WHERE n.age > 21 RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        d = s.to_dict(output_label="n.name")

        assert d["output"] == "n.name"
        assert isinstance(d["dependencies"], list)
        assert len(d["dependencies"]) >= 2

        # Each dependency has the right keys
        for dep in d["dependencies"]:
            assert set(dep.keys()) == {"graph", "label", "property", "type"}
            assert dep["type"] in ("direct", "constraint", "pattern")

    def test_to_dict_null_for_empty(self, parse):
        """Empty graph/label/property serialize as null, not empty string."""
        graph, ia = _analyze(parse, "MATCH (n) RETURN n.name")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        d = s.to_dict()

        prop_dep = next(dep for dep in d["dependencies"] if dep["property"] == "name")
        assert prop_dep["graph"] is None
        assert prop_dep["label"] is None

    def test_to_dict_fallback_to_output_id(self, parse):
        """Without output_label, falls back to output_id."""
        graph, ia = _analyze(parse, "MATCH (n:Person) RETURN n")
        output = _find_output_by_pos(graph, 0)
        s = ia.upstream(output)
        d = s.to_dict()
        assert d["output"] == output.id


class TestMultiPatternBindings:
    """Test multi-pattern binding support (binding in multiple MATCH clauses)."""

    def test_binding_has_both_pattern_ids(self, parse):
        """MATCH (a:Person) MATCH (a:Dog) RETURN a — a has IN_PATTERN edges to pat_0 AND pat_1."""
        graph, ia = _analyze(parse, "MATCH (a:Person) MATCH (a:Dog) RETURN a")
        a_binding = next(b for b in graph.bindings.values() if b.name == "a")
        a_patterns = graph.targets(a_binding.id, LineageEdgeKind.IN_PATTERN)
        assert "pat_0" in a_patterns
        assert "pat_1" in a_patterns

    def test_both_label_constraints_created(self, parse):
        """MATCH (a:Person) MATCH (a:Dog) RETURN a — :Person and :Dog labels on binding."""
        graph, ia = _analyze(parse, "MATCH (a:Person) MATCH (a:Dog) RETURN a")
        a_binding = next(b for b in graph.bindings.values() if b.name == "a")
        assert "Person" in a_binding.label_expression
        assert "Dog" in a_binding.label_expression

    def test_upstream_includes_both_labels(self, parse):
        """MATCH (a:Person) MATCH (a:Dog) RETURN a.name — upstream has Person AND Dog."""
        graph, ia = _analyze(parse, "MATCH (a:Person) MATCH (a:Dog) RETURN a.name")
        output = _find_output_by_pos(graph, 0)
        assert output is not None
        summary = ia.upstream(output)
        labels = _dep_labels(summary)
        # Both labels merged into single expression "Person&Dog"
        merged = next(lbl for lbl in labels if "Person" in lbl and "Dog" in lbl)
        assert merged is not None

    def test_pattern_across_patterns(self, parse):
        """MATCH (a:Person)-[r:KNOWS]->(b) MATCH (a:Dog) RETURN b.name — Dog in upstream."""
        graph, ia = _analyze(parse, "MATCH (a:Person)-[r:KNOWS]->(b) MATCH (a:Dog) RETURN b.name")
        output = _find_output_by_pos(graph, 0)
        assert output is not None
        summary = ia.upstream(output)
        labels = _dep_labels(summary)
        # Person&Dog merged on binding, KNOWS separate
        all_labels = " ".join(labels)
        assert "Dog" in all_labels
        assert "Person" in all_labels
        assert "KNOWS" in all_labels

    def test_collect_upstream_follows_both_patterns(self, parse):
        """MATCH (a)-[r]->(b) MATCH (a)-[s]->(c) RETURN a — b and c both reachable."""
        graph, ia = _analyze(parse, "MATCH (a)-[r]->(b:X) MATCH (a)-[s]->(c:Y) RETURN a")
        output = _find_output_by_pos(graph, 0)
        assert output is not None
        summary = ia.upstream(output)
        labels = _dep_labels(summary)
        assert "X" in labels
        assert "Y" in labels

    def test_upstream_graph_includes_both_patterns(self, parse):
        """upstream_graph has Pattern nodes for both pat_0 and pat_1."""
        graph, ia = _analyze(parse, "MATCH (a:Person) MATCH (a:Dog) RETURN a")
        output = _find_output_by_pos(graph, 0)
        assert output is not None
        ug = ia.upstream_graph(output)
        pattern_nodes = [n for n in ug.nodes if "Pattern" in n.labels]
        assert len(pattern_nodes) >= 2
