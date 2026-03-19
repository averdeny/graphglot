"""Tests for dependency extraction from expressions.

These tests verify that the lineage module correctly extracts dependencies
(binding references, property accesses, function calls) from expressions
in RETURN, WHERE, and other clauses.
"""

from __future__ import annotations

from graphglot.lineage import LineageAnalyzer, LineageEdgeKind

from .conftest import constrained_bindings, dep_bindings, dep_properties, prop_binding_id


class TestPropertyDependencies:
    """Test extraction of property dependencies."""

    def test_simple_property_in_return(self, parse):
        """Extract property reference from RETURN."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        prop_refs = result.property_refs
        assert len(prop_refs) == 1
        prop = next(iter(prop_refs.values()))
        assert prop.property_name == "name"

    def test_multiple_properties_same_binding(self, parse):
        """Extract multiple properties from same binding."""
        ast = parse("MATCH (n:Person) RETURN n.name, n.age, n.city")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        prop_refs = result.property_refs
        assert len(prop_refs) == 3
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert all(prop_binding_id(result, p) == n_binding.id for p in prop_refs.values())

    def test_property_in_where(self, parse):
        """Extract property reference from WHERE clause."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # Find age property ref
        age_prop = next(
            (p for p in result.property_refs.values() if p.property_name == "age"), None
        )
        assert age_prop is not None

    def test_property_in_both_where_and_return(self, parse):
        """Same property in WHERE and RETURN creates appropriate refs."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n.age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # PropertyRef is deduplicated — same (binding_id, property_name) reuses existing
        age_prop = next(
            (p for p in result.property_refs.values() if p.property_name == "age"), None
        )
        assert age_prop is not None

        # Filter constrains this property (via CONSTRAINS edge)
        pred = next(iter(result.filters.values()))
        constrains_targets = [
            e.target_id
            for e in result.edges
            if e.source_id == pred.id and e.kind == LineageEdgeKind.CONSTRAINS
        ]
        assert age_prop.id in constrains_targets

        # Output also references this property
        output = next(iter(result.outputs.values()))
        assert age_prop.id in dep_properties(result, output.id)

    def test_nested_property_access(self, parse):
        """Extract nested property access like n.address.city."""
        ast = parse("MATCH (n:Person) RETURN n.address.city")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # Nested property should appear as "address.city"
        prop = next((p for p in result.property_refs.values() if "city" in p.property_name), None)
        assert prop is not None
        assert prop.property_name == "address.city"

    def test_property_on_edge(self, parse):
        """Extract property reference on edge binding."""
        ast = parse("MATCH (a)-[r:KNOWS]->(b) WHERE r.since > 2020 RETURN r.since")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        r_binding = next((b for b in result.bindings.values() if b.name == "r"), None)
        assert r_binding is not None

        since_prop = next(
            (p for p in result.property_refs.values() if p.property_name == "since"), None
        )
        assert since_prop is not None
        assert prop_binding_id(result, since_prop) == r_binding.id


class TestOutputDependencies:
    """Test dependency tracking for output fields."""

    def test_output_depends_on_binding(self, parse):
        """Output of binding reference depends on that binding."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert n_binding.id in dep_bindings(result, output.id)

    def test_output_depends_on_property(self, parse):
        """Output of property access depends on property and binding."""
        ast = parse("MATCH (n:Person) RETURN n.name AS person_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "person_name"), None)
        assert output is not None
        assert len(dep_properties(result, output.id)) == 1

    def test_output_expression_dependencies(self, parse):
        """Arithmetic expression output tracks property dependency."""
        ast = parse("MATCH (n:Person) RETURN n.age + 1 AS next_age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "next_age"), None)
        assert output is not None

        # Output should depend on n.age property
        assert len(dep_properties(result, output.id)) >= 1
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert n_binding.id in dep_bindings(result, output.id)

    def test_output_multiple_bindings(self, parse):
        """Output referencing multiple bindings tracks all."""
        ast = parse("MATCH (a)-[r]->(b) RETURN COALESCE(a.name, b.name) AS display_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "display_name"), None)
        assert output is not None

        a_binding = next(b for b in result.bindings.values() if b.name == "a")
        b_binding = next(b for b in result.bindings.values() if b.name == "b")
        out_dep_bindings = dep_bindings(result, output.id)
        assert a_binding.id in out_dep_bindings
        assert b_binding.id in out_dep_bindings
        assert len(dep_properties(result, output.id)) == 2


class TestFilterDependencies:
    """Test dependency tracking for filters."""

    def test_filter_constrains_binding(self, parse):
        """Filter should constrain the bindings it references."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        filt = next(iter(result.filters.values()))
        assert n_binding.id in constrained_bindings(result, filt.id)

    def test_filter_multiple_bindings(self, parse):
        """Filter with multiple bindings constrains all."""
        ast = parse("MATCH (a)-[r]->(b) WHERE a.age > b.age RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        a_binding = next(b for b in result.bindings.values() if b.name == "a")
        b_binding = next(b for b in result.bindings.values() if b.name == "b")
        filt = next(iter(result.filters.values()))
        cb = constrained_bindings(result, filt.id)
        assert a_binding.id in cb
        assert b_binding.id in cb

    def test_filter_and_expression(self, parse):
        """AND expression creates combined constraint with multiple property refs."""
        ast = parse("MATCH (n) WHERE n.age > 21 AND n.score < 100 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # One filter for the whole search condition
        assert len(result.filters) >= 1
        filt = next(iter(result.filters.values()))

        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert n_binding.id in constrained_bindings(result, filt.id)

        # Both properties referenced (via CONSTRAINS edges to property refs)
        constrained_props = [
            e.target_id
            for e in result.edges
            if e.source_id == filt.id
            and e.kind == LineageEdgeKind.CONSTRAINS
            and e.target_id in result.property_refs
        ]
        assert len(constrained_props) == 2

    def test_inline_property_spec_tracks_value_dependencies(self, parse):
        """Pattern property specs should constrain referenced value expressions too."""
        ast = parse("MATCH (m:Person), (n:Person {friendAge: m.age}) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        m_binding = next(b for b in result.bindings.values() if b.name == "m")
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        filt = next(iter(result.filters.values()))

        constrained = constrained_bindings(result, filt.id)
        assert n_binding.id in constrained
        assert m_binding.id in constrained

        age_prop = next(
            (p for p in result.property_refs.values() if p.property_name == "age"), None
        )
        assert age_prop is not None
        assert age_prop.id in [
            e.target_id
            for e in result.edges
            if e.source_id == filt.id and e.kind == LineageEdgeKind.CONSTRAINS
        ]

    def test_filter_or_expression(self, parse):
        """OR expression creates appropriate constraint."""
        ast = parse("MATCH (n) WHERE n.status = 'active' OR n.status = 'pending' RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        filt = next(iter(result.filters.values()))
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert n_binding.id in constrained_bindings(result, filt.id)
        # Same property referenced twice but deduplicated to one PropertyRef
        constrained_props = [
            e.target_id
            for e in result.edges
            if e.source_id == filt.id
            and e.kind == LineageEdgeKind.CONSTRAINS
            and e.target_id in result.property_refs
        ]
        assert len(constrained_props) >= 1


class TestFunctionDependencies:
    """Test dependency tracking for function calls."""

    def test_function_call_dependencies(self, parse):
        """Function call depends on its arguments."""
        ast = parse("MATCH (n:Person) RETURN UPPER(n.name) AS upper_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "upper_name"), None)
        assert output is not None

        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert n_binding.id in dep_bindings(result, output.id)

        name_prop = next(
            (p for p in result.property_refs.values() if p.property_name == "name"), None
        )
        assert name_prop is not None
        assert name_prop.id in dep_properties(result, output.id)

    def test_nested_function_calls(self, parse):
        """Nested functions track all dependencies."""
        ast = parse("MATCH (n) RETURN COALESCE(UPPER(n.name), 'unknown') AS clean_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "clean_name"), None)
        assert output is not None

        # Dependency on n.name should be found through nested functions
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert n_binding.id in dep_bindings(result, output.id)
        assert len(dep_properties(result, output.id)) >= 1

    def test_function_multiple_args(self, parse):
        """Function with multiple arguments tracks all."""
        ast = parse("MATCH (n) RETURN COALESCE(n.nickname, n.name) AS display_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "display_name"), None)
        assert output is not None

        # Both properties should be tracked
        assert len(dep_properties(result, output.id)) == 2
        prop_names = {p.property_name for p in result.property_refs.values()}
        assert "nickname" in prop_names
        assert "name" in prop_names


class TestCaseExpressionDependencies:
    """Test dependency tracking for CASE expressions."""

    def test_simple_case_dependencies(self, parse):
        """CASE expression tracks condition and result dependencies."""
        ast = parse(
            "MATCH (p:Person) "
            "RETURN CASE WHEN p.age >= 18 THEN 'adult' ELSE 'minor' END AS category"
        )

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "category"), None)
        assert output is not None

        p_binding = next(b for b in result.bindings.values() if b.name == "p")
        assert p_binding.id in dep_bindings(result, output.id)

        age_prop = next(
            (p for p in result.property_refs.values() if p.property_name == "age"), None
        )
        assert age_prop is not None
        assert age_prop.id in dep_properties(result, output.id)

    def test_case_multiple_whens(self, parse):
        """CASE with multiple WHENs tracks all conditions."""
        ast = parse(
            "MATCH (p:Person) "
            "RETURN CASE "
            "WHEN p.age < 13 THEN 'child' "
            "WHEN p.age < 20 THEN 'teen' "
            "ELSE 'adult' "
            "END AS age_group"
        )

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "age_group"), None)
        assert output is not None

        p_binding = next(b for b in result.bindings.values() if b.name == "p")
        assert p_binding.id in dep_bindings(result, output.id)

        # p.age referenced multiple times but deduplicated to one PropertyRef
        age_prop = next(
            (p for p in result.property_refs.values() if p.property_name == "age"), None
        )
        assert age_prop is not None

    def test_case_with_value_results(self, parse):
        """CASE with non-literal results tracks result dependencies."""
        ast = parse(
            "MATCH (p:Person) "
            "RETURN CASE "
            "WHEN p.status = 'premium' THEN p.discount_rate "
            "ELSE 0 "
            "END AS discount"
        )

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next((o for o in result.outputs.values() if o.alias == "discount"), None)
        assert output is not None

        # Should depend on both p.status and p.discount_rate
        prop_names = {p.property_name for p in result.property_refs.values()}
        assert "status" in prop_names
        assert "discount_rate" in prop_names
        assert len(dep_properties(result, output.id)) == 2


class TestDependencyEdges:
    """Test lineage graph edges for dependencies."""

    def test_depends_on_edge_output_to_property(self, parse):
        """Output should have depends_on edge to property."""
        ast = parse("MATCH (n:Person) RETURN n.name AS person_name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(o for o in result.outputs.values() if o.alias == "person_name")
        prop = next(p for p in result.property_refs.values() if p.property_name == "name")

        edge = next(
            (
                e
                for e in result.edges
                if e.source_id == output.id
                and e.target_id == prop.id
                and e.kind == LineageEdgeKind.DEPENDS_ON
            ),
            None,
        )
        assert edge is not None

    def test_depends_on_edge_property_to_binding(self, parse):
        """Property should have depends_on edge to binding."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        prop = next(p for p in result.property_refs.values() if p.property_name == "name")

        edge = next(
            (
                e
                for e in result.edges
                if e.source_id == prop.id
                and e.target_id == n_binding.id
                and e.kind == LineageEdgeKind.DEPENDS_ON
            ),
            None,
        )
        assert edge is not None

    def test_constrains_edge_filter_to_binding(self, parse):
        """Filter constrains binding indirectly via property ref."""
        ast = parse("MATCH (n:Person) WHERE n.age > 21 RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        filt = next(iter(result.filters.values()))

        # Filter constrains the property ref (not the binding directly)
        prop = next(p for p in result.property_refs.values() if p.property_name == "age")
        edge = next(
            (
                e
                for e in result.edges
                if e.source_id == filt.id
                and e.target_id == prop.id
                and e.kind == LineageEdgeKind.CONSTRAINS
            ),
            None,
        )
        assert edge is not None

        # Binding reachable via property ref
        from .conftest import constrained_bindings

        assert n_binding.id in constrained_bindings(result, filt.id)


class TestOrderByDependencies:
    """Test ORDER BY dependency scoping."""

    def test_order_by_emits_ordered_by_edges(self, parse):
        """ORDER BY should create ORDERED_BY edges, not DEPENDS_ON."""
        ast = parse("MATCH (n:Person) RETURN n.name ORDER BY n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        ordered_targets = result.targets(output.id, LineageEdgeKind.ORDERED_BY)
        assert len(ordered_targets) >= 1

    def test_order_by_distinct_from_return_deps(self, parse):
        """ORDER BY on a different property creates ORDERED_BY, not DEPENDS_ON."""
        ast = parse("MATCH (n:Person) RETURN n.name ORDER BY n.age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        depends_targets = result.targets(output.id, LineageEdgeKind.DEPENDS_ON)
        ordered_targets = result.targets(output.id, LineageEdgeKind.ORDERED_BY)

        name_prop = next(p for p in result.property_refs.values() if p.property_name == "name")
        age_prop = next(p for p in result.property_refs.values() if p.property_name == "age")
        assert name_prop.id in depends_targets
        assert age_prop.id in ordered_targets
        assert age_prop.id not in depends_targets

    def test_order_by_dedup_binding_deps(self, parse):
        """ORDER BY n.name should not also emit ORDERED_BY edge to binding n."""
        ast = parse("MATCH (n:Person) RETURN n.name ORDER BY n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        ordered_targets = result.targets(output.id, LineageEdgeKind.ORDERED_BY)
        # Binding should NOT appear directly since it's reachable via property ref
        assert n_binding.id not in ordered_targets

    def test_order_by_does_not_affect_other_scope(self, parse):
        """ORDER BY in second NEXT scope should not add edges to first scope outputs.

        Intermediate outputs (before NEXT) are removed, so only the final scope's
        output should exist. Verify the final output has ORDERED_BY edges only from
        its own scope's ORDER BY clause.
        """
        ast = parse("""
            MATCH (a:Person) RETURN a.name
            NEXT
            MATCH (b:Company) RETURN b.name ORDER BY b.name
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # Only the final scope's output should exist (intermediate removed)
        outputs = list(result.outputs.values())
        assert len(outputs) == 1
        final_output = outputs[0]
        # Final output should have ORDERED_BY edges from its own ORDER BY
        ordered = result.targets(final_output.id, LineageEdgeKind.ORDERED_BY)
        assert len(ordered) >= 1
