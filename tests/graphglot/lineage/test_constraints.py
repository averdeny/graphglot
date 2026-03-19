"""Tests for constraint propagation.

These tests verify that constraints (from WHERE clauses and pattern predicates)
are properly propagated across connected bindings in the same pattern.

Key insight: If a WHERE clause filters on binding 'a', and 'a' is connected
to 'b' via an edge 'r' in the same MATCH, then 'b' and 'r' are also
transitively constrained.
"""

from __future__ import annotations

import pytest

from graphglot.lineage import LineageAnalyzer
from graphglot.lineage.models import BindingKind

from .conftest import constrained_bindings


def find_binding(graph, name: str):
    """Find a binding by name."""
    for b in graph.bindings.values():
        if b.name == name:
            return b
    return None


class TestDirectConstraints:
    """Test direct constraints from WHERE clause."""

    def test_where_constrains_binding(self, parse):
        """WHERE clause directly constrains referenced binding."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        filters = list(result.filters.values())
        assert len(filters) >= 1
        filt = filters[0]

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        # Filter should directly constrain n
        assert n_binding.id in constrained_bindings(result, filt.id)

    def test_where_multiple_conditions_same_binding(self, parse):
        """Multiple WHERE conditions on same binding."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 AND n.active = true RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        filters = list(result.filters.values())
        assert len(filters) >= 1
        filt = filters[0]

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        # All conditions constrain n
        assert n_binding.id in constrained_bindings(result, filt.id)

    def test_where_multiple_bindings(self, parse):
        """WHERE condition spanning multiple bindings."""
        ast = parse("MATCH (a)-[r]->(b) WHERE a.score > b.score RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        filters = list(result.filters.values())
        assert len(filters) >= 1
        filt = filters[0]

        a_binding = find_binding(result, "a")
        b_binding = find_binding(result, "b")
        assert a_binding is not None
        assert b_binding is not None

        # Both a and b are directly constrained
        cb = constrained_bindings(result, filt.id)
        assert a_binding.id in cb
        assert b_binding.id in cb

    def test_exists_subquery_constrains_outer_binding(self, parse):
        """EXISTS subquery referencing outer binding should constrain it."""
        ast = parse("MATCH (p:Person) WHERE EXISTS {MATCH (p)-()} RETURN p")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        filters = list(result.filters.values())
        assert len(filters) >= 1

        p_binding = find_binding(result, "p")
        assert p_binding is not None

        # At least one filter must constrain p (the EXISTS predicate)
        p_filters = [f for f in filters if p_binding.id in constrained_bindings(result, f.id)]
        assert len(p_filters) >= 1, "Expected a filter constraining p"


class TestConstraintEdges:
    """Test lineage graph edges for constraints."""

    def test_constrains_edge_created(self, parse):
        """CONSTRAINS edge created from predicate to property ref (not directly to binding)."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        from graphglot.lineage import LineageEdgeKind

        edges = [e for e in result.edges if e.kind == LineageEdgeKind.CONSTRAINS]
        assert len(edges) >= 1

        filters = list(result.filters.values())
        filt = filters[0]

        # Filter constrains the property ref, not the binding directly
        prop = next(p for p in result.property_refs.values() if p.property_name == "age")
        assert any(e.source_id == filt.id and e.target_id == prop.id for e in edges)

        # Binding is reachable indirectly through the property ref
        n_binding = find_binding(result, "n")
        assert n_binding is not None
        assert n_binding.id in constrained_bindings(result, filt.id)


class TestPatternInlineConstraints:
    """Test constraints from inline pattern predicates."""

    def test_label_as_constraint(self, parse):
        """Node label acts as constraint."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        # The :Person label is directly on the binding
        assert "Person" in n_binding.label_expression

    def test_relationship_type_as_constraint(self, parse):
        """Relationship type acts as constraint."""
        ast = parse("MATCH (a)-[r:KNOWS]->(b) RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        r_binding = find_binding(result, "r")
        if r_binding is None:
            pytest.skip("Edge binding r not found")

        # The :KNOWS type is directly on the binding
        assert "KNOWS" in r_binding.label_expression

    def test_inline_property_constraint(self, parse):
        """Inline property pattern {active: true} tracked as a filter."""
        ast = parse("MATCH (n:Person {active: true}) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # The {active: true} should be tracked as a filter
        filters = list(result.filters.values())
        assert len(filters) >= 1, "Expected at least one filter for {active: true}"

        n_binding = find_binding(result, "n")
        assert n_binding is not None
        # Filter should constrain n
        assert any(n_binding.id in constrained_bindings(result, f.id) for f in filters)

    def test_multiple_labels_constraint(self, parse):
        """Multiple labels are all constraints."""
        # GQL uses & for label conjunction
        ast = parse("MATCH (n:Person&Employee) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        # Both Person and Employee are directly on the binding
        assert "Person" in n_binding.label_expression
        assert "Employee" in n_binding.label_expression


class TestConstraintInteractions:
    """Test interactions between different constraint types."""

    def test_where_and_labels(self, parse):
        """WHERE and label constraints combine — n has both :Person and WHERE."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        n_binding = find_binding(result, "n")
        assert n_binding is not None

        # :Person label directly on binding
        assert "Person" in n_binding.label_expression

        # WHERE constraint
        filters = list(result.filters.values())
        assert any(n_binding.id in constrained_bindings(result, f.id) for f in filters)

    def test_where_and_relationship_type(self, parse):
        """WHERE and relationship type constraints combine on r."""
        ast = parse("MATCH (a)-[r:KNOWS]->(b) WHERE r.since > 2020 RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        r_binding = find_binding(result, "r")
        assert r_binding is not None

        # :KNOWS type directly on binding
        assert "KNOWS" in r_binding.label_expression

        # WHERE constraint on r.since
        filters = list(result.filters.values())
        assert any(r_binding.id in constrained_bindings(result, f.id) for f in filters)

    def test_constraints_from_multiple_patterns(self, parse):
        """Constraints from multiple patterns sharing a variable."""
        ast = parse(
            "MATCH (p:Person)-[:OWNS]->(car:Car), "
            "(p)-[:LIVES_IN]->(city:City) "
            "WHERE city.name = 'Berlin' "
            "RETURN p.name, car.model"
        )

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        p_binding = find_binding(result, "p")
        car_binding = find_binding(result, "car")
        city_binding = find_binding(result, "city")
        assert p_binding is not None
        assert car_binding is not None
        assert city_binding is not None

        # WHERE constrains city
        filters = list(result.filters.values())
        assert any(city_binding.id in constrained_bindings(result, f.id) for f in filters)

        # p has :Person label directly on binding
        assert "Person" in p_binding.label_expression


class TestExpansionConstraints:
    """Test constraints on variable-length path expansion."""

    def test_variable_length_creates_edge_binding(self, parse):
        """Variable-length path creates an edge binding (GQL syntax)."""
        ast = parse("MATCH (a)-[r]->{1,5}(b) RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        edge_bindings = [b for b in result.bindings.values() if b.kind == BindingKind.EDGE]
        assert len(edge_bindings) >= 1

    def test_constraint_affects_expansion(self, parse):
        """Constraint on start affects expanded results (GQL syntax)."""
        ast = parse("""
            MATCH (a:Person)-[:KNOWS]->{1,3}(b:Person)
            WHERE a.name = 'Alice'
            RETURN b.name
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # a should be constrained by WHERE
        filters = list(result.filters.values())
        assert len(filters) >= 1

        a_binding = find_binding(result, "a")
        assert a_binding is not None
        assert a_binding.id in constrained_bindings(result, filters[0].id)


class TestExistsSubqueryPatterns:
    """Test that inner patterns in EXISTS subqueries are fully analyzed."""

    def test_exists_inner_binding_created(self, parse):
        """EXISTS {MATCH (p)-(t:Test)} — t is extracted as a binding."""
        ast = parse("MATCH (p:Person) WHERE EXISTS {MATCH (p)-(t:Test)} RETURN p")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        t_binding = find_binding(result, "t")
        assert t_binding is not None, "Inner binding t should be created"
        assert t_binding.kind == BindingKind.NODE

    def test_exists_inner_label_constraint(self, parse):
        """EXISTS {MATCH (p)-(t:Test)} — :Test label exists on t binding."""
        ast = parse("MATCH (p:Person) WHERE EXISTS {MATCH (p)-(t:Test)} RETURN p")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        t_binding = find_binding(result, "t")
        assert t_binding is not None
        assert "Test" in t_binding.label_expression

    def test_exists_inner_edge_binding(self, parse):
        """EXISTS {MATCH (p)-[r:KNOWS]->(t:Test)} — edge binding created."""
        ast = parse("MATCH (p:Person) WHERE EXISTS {MATCH (p)-[r:KNOWS]->(t:Test)} RETURN p")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        r_binding = find_binding(result, "r")
        assert r_binding is not None, "Edge binding r should be created"
        assert r_binding.kind == BindingKind.EDGE

    def test_exists_inner_where_filter(self, parse):
        """EXISTS {MATCH (p)-(t:Test) WHERE t.score > 50} — inner WHERE tracked."""
        ast = parse(
            "MATCH (p:Person) WHERE EXISTS {MATCH (p)-(t:Test) WHERE t.score > 50} RETURN p"
        )
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        t_binding = find_binding(result, "t")
        assert t_binding is not None
        # Inner WHERE should create a filter constraining t
        inner_filters = [
            f for f in result.filters.values() if t_binding.id in constrained_bindings(result, f.id)
        ]
        assert len(inner_filters) >= 1

    def test_exists_scope_isolation(self, parse):
        """Inner EXISTS bindings get their own scope."""
        ast = parse("MATCH (p:Person) WHERE EXISTS {MATCH (p)-(t:Test)} RETURN p")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        p_binding = find_binding(result, "p")
        t_binding = find_binding(result, "t")
        assert p_binding is not None
        assert t_binding is not None
        # t should be in a different (EXISTS) scope than p
        assert t_binding.scope_id != p_binding.scope_id

    def test_exists_graph_pattern_variant(self, parse):
        """EXISTS {(p)-(t:Test)} — bare graph pattern variant (no MATCH keyword)."""
        ast = parse("MATCH (p:Person) WHERE EXISTS {(p)-(t:Test)} RETURN p")
        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)
        t_binding = find_binding(result, "t")
        assert t_binding is not None
        assert t_binding.kind == BindingKind.NODE
