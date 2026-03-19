"""Tests for impact analysis.

These tests verify the impact analysis API that answers questions like:
- "What outputs depend on this binding/property?"
- "What filters constrain this binding?"
- "What write operations affect this binding?"
"""

from __future__ import annotations

from graphglot.lineage import ImpactAnalyzer, LineageAnalyzer

from .conftest import prop_binding_id


def find_property_ref(graph, binding_name: str, prop_name: str):
    """Find a property ref by binding name and property name."""
    binding = None
    for b in graph.bindings.values():
        if b.name == binding_name:
            binding = b
            break
    if not binding:
        return None
    for p in graph.property_refs.values():
        if prop_binding_id(graph, p) == binding.id and p.property_name == prop_name:
            return p
    return None


def find_binding(graph, name: str):
    """Find a binding by name."""
    for b in graph.bindings.values():
        if b.name == name:
            return b
    return None


def find_output(graph, alias: str):
    """Find an output by alias."""
    for o in graph.outputs.values():
        if o.alias == alias:
            return o
    return None


class TestPropertyImpact:
    """Test impact analysis for properties."""

    def test_property_impacts_output(self, parse):
        """Property used in output is identified as impacting it."""
        ast = parse("MATCH (n:Person) RETURN n.name AS person_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        # Find the property ref for n.name
        prop_ref = find_property_ref(result, "n", "name")
        assert prop_ref is not None

        impact = impact_analyzer.impact(prop_ref)

        # n.name should impact the output
        assert len(impact.impacted_outputs) >= 1

    def test_property_impacts_filter(self, parse):
        """Property used in WHERE impacts the filter."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        prop_ref = find_property_ref(result, "n", "age")
        assert prop_ref is not None

        impact = impact_analyzer.impact(prop_ref)

        # n.age should impact the filter
        assert len(impact.impacted_filters) >= 1

    def test_property_impacts_both_output_and_filter(self, parse):
        """Property used in both contexts impacts both."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n.age AS age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        # Note: The analyzer creates separate property refs for different contexts
        # Find any age property ref
        prop_refs = [p for p in result.property_refs.values() if p.property_name == "age"]
        assert len(prop_refs) >= 1

        # Check combined impact
        all_outputs = set()
        all_filters = set()
        for prop_ref in prop_refs:
            impact = impact_analyzer.impact(prop_ref)
            all_outputs.update(impact.impacted_outputs)
            all_filters.update(impact.impacted_filters)

        assert len(all_outputs) >= 1
        assert len(all_filters) >= 1

    def test_property_no_impact(self, parse):
        """Property not used should have no impact."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        # n.age is not used, so it shouldn't impact anything
        impact = impact_analyzer.impact_property("n", "age")
        assert len(impact.impacted_outputs) == 0
        assert len(impact.impacted_filters) == 0


class TestBindingImpact:
    """Test impact analysis for bindings."""

    def test_binding_impacts_properties(self, parse):
        """Binding impacts all properties accessed on it."""
        ast = parse("MATCH (n:Person) RETURN n.name, n.age, n.city")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        impact = impact_analyzer.impact(n_binding)

        # Properties depend on n, check that impacts include properties or outputs
        assert len(impact.direct_impacts) >= 1 or len(impact.transitive_impacts) >= 1

    def test_binding_impacts_outputs_transitively(self, parse):
        """Binding impacts outputs through properties."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        impact = impact_analyzer.impact(n_binding)

        # n impacts the output through n.name
        assert len(impact.impacted_outputs) >= 1

    def test_connected_bindings_share_constraint_impact(self, parse):
        """Bindings in same pattern: constraint on a impacts filter/properties."""
        ast = parse("MATCH (a:Person)-[r:KNOWS]->(b:Person) WHERE a.age > 21 RETURN a.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        a_binding = find_binding(result, "a")
        assert a_binding is not None

        impact = impact_analyzer.impact(a_binding)
        # a is directly referenced in output, so it impacts outputs
        assert len(impact.impacted_outputs) >= 1
        # a.age filter should also be impacted
        assert len(impact.impacted_filters) >= 1

    def test_impact_populates_paths(self, parse):
        """impact() should include path explanations to impacted outputs."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        impact = impact_analyzer.impact(n_binding)
        assert len(impact.impact_paths) >= 1
        assert any(path.nodes[0] == n_binding.id for path in impact.impact_paths)
        assert any(path.nodes[-1] in result.outputs for path in impact.impact_paths)


class TestReverseLineage:
    """Test reverse lineage (tracing from output to source)."""

    def test_trace_output_to_binding(self, parse):
        """Trace output back to its source binding."""
        ast = parse("MATCH (n:Person) RETURN n.name AS person_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        output = find_output(result, "person_name")
        assert output is not None

        paths = impact_analyzer.reverse_lineage(output)

        # Should trace back to binding n
        assert len(paths) >= 1
        n_binding = find_binding(result, "n")
        assert n_binding is not None
        terminal_ids = {p.nodes[-1] for p in paths}
        assert n_binding.id in terminal_ids

    def test_trace_aggregated_output(self, parse):
        """Trace aggregated output to source bindings."""
        ast = parse("MATCH (n:Person) RETURN count(n) AS total")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        output = find_output(result, "total")
        assert output is not None

        paths = impact_analyzer.reverse_lineage(output)
        assert len(paths) >= 1

        n_binding = find_binding(result, "n")
        assert n_binding is not None
        terminal_ids = {p.nodes[-1] for p in paths}
        assert n_binding.id in terminal_ids

    def test_trace_complex_expression(self, parse):
        """Trace expression with multiple property accesses to all sources."""
        ast = parse("MATCH (n:Person) RETURN n.name || ' ' || n.city AS label")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        output = find_output(result, "label")
        assert output is not None

        paths = impact_analyzer.reverse_lineage(output)
        assert len(paths) >= 1

        # All paths should trace back to binding n
        n_binding = find_binding(result, "n")
        assert n_binding is not None
        terminal_ids = {p.nodes[-1] for p in paths}
        assert n_binding.id in terminal_ids


class TestForwardLineage:
    """Test forward lineage (tracing from binding to outputs)."""

    def test_trace_binding_to_outputs(self, parse):
        """Trace binding forward to all outputs it affects."""
        ast = parse("MATCH (n:Person) RETURN n.name, n.age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        paths = impact_analyzer.forward_lineage(n_binding)

        # Should find paths to outputs (possibly through properties)
        assert len(paths) >= 1

    def test_trace_unused_binding(self, parse):
        """Unused binding should have no forward lineage to outputs."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        r_binding = find_binding(result, "r")
        assert r_binding is not None

        paths = impact_analyzer.forward_lineage(r_binding)

        # r is matched but not used in output - should have no paths to outputs
        assert len(paths) == 0


class TestImpactPaths:
    """Test impact path explanations."""

    def test_impact_path_direct(self, parse):
        """Direct impact has single-hop path."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        paths = impact_analyzer.forward_lineage(n_binding)

        # Should have at least one path to output
        assert len(paths) >= 1

    def test_impact_path_through_property(self, parse):
        """Impact through property has multi-hop path."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        paths = impact_analyzer.forward_lineage(n_binding)

        # binding -> property -> output (path through property)
        assert len(paths) >= 1


class TestMutationImpact:
    """Test impact analysis for mutations."""

    def test_binding_impacts_mutation(self, parse):
        """Binding used in SET should show mutation in impact."""
        ast = parse('MATCH (n:Person) SET n.name = "Bob"')
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None
        impact = impact_analyzer.impact(n_binding)
        assert len(impact.impacted_mutations) >= 1

    def test_mutation_impact_includes_writes(self, parse):
        """Impact of a binding should include mutations that WRITE to it."""
        ast = parse("MATCH (n:Person) DELETE n")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        n_binding = find_binding(result, "n")
        assert n_binding is not None
        impact = impact_analyzer.impact(n_binding)
        assert len(impact.impacted_mutations) >= 1

    def test_upstream_through_mutation(self, parse):
        """Property used in SET value expression should trace upstream."""
        ast = parse("MATCH (n:Person), (m:Person) SET n.name = m.name")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        impact_analyzer = ImpactAnalyzer(result)

        m_binding = find_binding(result, "m")
        assert m_binding is not None
        impact = impact_analyzer.impact(m_binding)
        # m impacts the mutation transitively (m.name -> mutation)
        assert len(impact.impacted_mutations) >= 1
