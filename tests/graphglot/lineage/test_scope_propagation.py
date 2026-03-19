"""Tests for binding scope propagation across NEXT and OTHERWISE.

These tests verify that:
- Bindings propagated via NEXT get IN_PATTERN edges when reused in a MATCH
- OTHERWISE creates independent scope/bindings from NEXT branches
- _create_binding emits IN_PATTERN edges when an existing binding is reused in a new pattern
"""

from __future__ import annotations

from graphglot.lineage import BindingKind, LineageAnalyzer, LineageEdgeKind, LineageExporter


def find_binding(graph, name: str):
    """Find first binding by name."""
    for b in graph.bindings.values():
        if b.name == name:
            return b
    return None


def find_all_bindings(graph, name: str):
    """Find all bindings with a given name."""
    return [b for b in graph.bindings.values() if b.name == name]


def find_pattern(graph, pattern_id: str):
    """Find a pattern by ID."""
    return graph.patterns.get(pattern_id)


class TestNextPatternId:
    """Bindings reused in a MATCH after NEXT should have correct pattern_id."""

    def test_propagated_binding_gets_pattern_id(self, parse):
        """Binding propagated via NEXT should have IN_PATTERN edge when used in a MATCH."""
        ast = parse("MATCH (n:Person) RETURN n NEXT MATCH (n)-[r:KNOWS]->(m) RETURN m")

        result = LineageAnalyzer().analyze(ast)
        g = result

        # n appears in pat_1 as a node
        pat_1 = find_pattern(g, "pat_1")
        assert pat_1 is not None

        # The n binding used in pat_1 should have IN_PATTERN edge to pat_1
        pat_1_bindings = g.sources(pat_1.id, LineageEdgeKind.IN_PATTERN)
        n_in_pat1 = None
        for bid in pat_1_bindings:
            b = g.bindings[bid]
            if b.name == "n":
                n_in_pat1 = b
                break

        assert n_in_pat1 is not None
        assert "pat_1" in g.targets(n_in_pat1.id, LineageEdgeKind.IN_PATTERN)

    def test_simple_next_binding_reuse(self, parse):
        """Simplest NEXT case: binding reused in second MATCH has IN_PATTERN edge."""
        ast = parse("MATCH (a) RETURN a NEXT MATCH (a)-[r]->(b) RETURN b")

        result = LineageAnalyzer().analyze(ast)
        g = result

        pat_1 = find_pattern(g, "pat_1")
        assert pat_1 is not None

        pat_1_bindings = g.sources(pat_1.id, LineageEdgeKind.IN_PATTERN)
        a_in_pat1 = None
        for bid in pat_1_bindings:
            b = g.bindings[bid]
            if b.name == "a":
                a_in_pat1 = b
                break

        assert a_in_pat1 is not None
        assert "pat_1" in g.targets(a_in_pat1.id, LineageEdgeKind.IN_PATTERN)


class TestOtherwiseScope:
    """OTHERWISE branches should have independent scope from NEXT branches."""

    def test_otherwise_creates_separate_bindings(self, parse):
        """OTHERWISE branch should not reuse bindings from NEXT branch."""
        ast = parse(
            "MATCH (n) RETURN n "
            "NEXT MATCH (n)-[r]->(m) RETURN m "
            "OTHERWISE MATCH (n)-[e]->(x) RETURN x"
        )

        result = LineageAnalyzer().analyze(ast)
        g = result

        # pat_1 is the NEXT branch, pat_2 is the OTHERWISE branch
        pat_1 = find_pattern(g, "pat_1")
        pat_2 = find_pattern(g, "pat_2")
        assert pat_1 is not None
        assert pat_2 is not None

        # The n binding in pat_1 and pat_2 should be DIFFERENT bindings
        n_in_pat1 = None
        n_in_pat2 = None
        for bid in g.sources(pat_1.id, LineageEdgeKind.IN_PATTERN):
            b = g.bindings[bid]
            if b.name == "n":
                n_in_pat1 = b
        for bid in g.sources(pat_2.id, LineageEdgeKind.IN_PATTERN):
            b = g.bindings[bid]
            if b.name == "n":
                n_in_pat2 = b

        assert n_in_pat1 is not None
        assert n_in_pat2 is not None
        assert n_in_pat1.id != n_in_pat2.id, (
            "OTHERWISE should have its own binding, not share with NEXT"
        )

    def test_otherwise_creates_separate_scope_ids(self, parse):
        """OTHERWISE should produce bindings with different scope_ids from NEXT."""
        ast = parse(
            "MATCH (n) RETURN n "
            "NEXT MATCH (n)-[r]->(m) RETURN m "
            "OTHERWISE MATCH (n)-[e]->(x) RETURN x"
        )

        result = LineageAnalyzer().analyze(ast)
        g = result

        # Collect distinct scope_ids across all bindings
        scope_ids = {b.scope_id for b in g.bindings.values()}
        assert len(scope_ids) >= 3, (
            f"Expected at least 3 distinct scope_ids (root, NEXT, OTHERWISE), got {scope_ids}"
        )

    def test_otherwise_edge_bindings_independent(self, parse):
        """Edge bindings in OTHERWISE should not appear in NEXT pattern."""
        ast = parse(
            "MATCH (n) RETURN n "
            "NEXT MATCH (n)-[r]->(m) RETURN m "
            "OTHERWISE MATCH (n)-[e]->(x) RETURN x"
        )

        result = LineageAnalyzer().analyze(ast)
        g = result

        pat_1 = find_pattern(g, "pat_1")
        pat_2 = find_pattern(g, "pat_2")

        pat_1_names = {
            g.bindings[bid].name for bid in g.sources(pat_1.id, LineageEdgeKind.IN_PATTERN)
        }
        pat_2_names = {
            g.bindings[bid].name for bid in g.sources(pat_2.id, LineageEdgeKind.IN_PATTERN)
        }

        # r should only be in pat_1, e should only be in pat_2
        assert "r" in pat_1_names
        assert "r" not in pat_2_names
        assert "e" in pat_2_names
        assert "e" not in pat_1_names


class TestCreateBindingPatternUpdate:
    """_create_binding should update pattern_id when reusing existing binding."""

    def test_binding_reused_in_pattern_gets_updated_pattern_id(self, parse):
        """When a named binding is reused in a new pattern, pattern_id should update."""
        ast = parse("MATCH (n:Person) RETURN n NEXT MATCH (n:Employee) RETURN n")

        result = LineageAnalyzer().analyze(ast)
        g = result

        # There should be a binding for n that's associated with pat_1
        n_bindings = find_all_bindings(g, "n")
        # At least one n should have IN_PATTERN edge to pat_1
        pat_1_n = [b for b in n_bindings if "pat_1" in g.targets(b.id, LineageEdgeKind.IN_PATTERN)]
        assert len(pat_1_n) >= 1, (
            f"Expected at least one 'n' binding with IN_PATTERN edge to pat_1, "
            f"got patterns: {[g.targets(b.id, LineageEdgeKind.IN_PATTERN) for b in n_bindings]}"
        )


class TestPropagatedBindingNotIntroduced:
    """Issue #2: propagated bindings should have PROPAGATES_TO edges."""

    def test_propagated_binding_has_propagates_to_edge(self, parse):
        """Binding propagated via NEXT should have a PROPAGATES_TO edge from the original."""
        ast = parse("MATCH (n) RETURN n NEXT MATCH (n)-[r]->(m) RETURN m")
        result = LineageAnalyzer().analyze(ast)
        g = result

        # Find all n bindings
        n_bindings = [b for b in g.bindings.values() if b.name == "n"]
        assert len(n_bindings) >= 2, "Expected at least 2 'n' bindings (root + NEXT)"

        # There should be a PROPAGATES_TO edge between them
        prop_edges = [e for e in g.edges if e.kind == LineageEdgeKind.PROPAGATES_TO]
        n_ids = {b.id for b in n_bindings}
        n_prop_edges = [e for e in prop_edges if e.source_id in n_ids and e.target_id in n_ids]
        assert len(n_prop_edges) >= 1, "Propagated binding 'n' should have a PROPAGATES_TO edge"

    def test_new_bindings_are_in_next_scope(self, parse):
        """Bindings first created in NEXT should have a different scope_id from root."""
        ast = parse("MATCH (n) RETURN n NEXT MATCH (n)-[r]->(m) RETURN m")
        result = LineageAnalyzer().analyze(ast)
        g = result

        # Root n should have scope_0
        root_n = next(b for b in g.bindings.values() if b.name == "n" and b.scope_id == "scope_0")
        assert root_n is not None

        # r and m should be in a different scope
        r_binding = next(b for b in g.bindings.values() if b.name == "r")
        m_binding = next(b for b in g.bindings.values() if b.name == "m")
        assert r_binding.scope_id != root_n.scope_id, "New binding 'r' should be in NEXT scope"
        assert m_binding.scope_id != root_n.scope_id, "New binding 'm' should be in NEXT scope"


class TestUniformFieldInclusion:
    """Issue #5: JSON export should always include nullable fields (as null)."""

    def test_pattern_always_has_source_text(self, parse):
        """Pattern JSON should always include source_text (even as null)."""
        ast = parse("MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        data = LineageExporter(result).to_dict()

        for p in [n for n in data["nodes"] if n["node_type"] == "pattern"]:
            assert "source_text" in p, f"Pattern {p['id']} missing source_text"


class TestPropagatedBindingKind:
    """Issue #7: propagated bindings should preserve original kind, not hardcode NODE."""

    def test_edge_binding_propagated_via_next_preserves_kind(self, parse):
        """Edge binding propagated via NEXT should keep EDGE kind."""
        ast = parse("MATCH (a)-[r]->(b) RETURN r NEXT MATCH (r)-[]->(c) RETURN c")

        result = LineageAnalyzer().analyze(ast)
        g = result

        # Find r bindings
        r_bindings = find_all_bindings(g, "r")
        assert len(r_bindings) >= 1

        # All r bindings should be EDGE kind (not NODE)
        for rb in r_bindings:
            assert rb.kind == BindingKind.EDGE, (
                f"Propagated binding 'r' should be EDGE, got {rb.kind}"
            )

    def test_path_binding_propagated_via_next_preserves_kind(self, parse):
        """Path binding propagated via NEXT should keep PATH kind."""
        ast = parse("MATCH p = (a)-[r]->(b) RETURN p NEXT RETURN p")

        result = LineageAnalyzer().analyze(ast)
        g = result

        p_bindings = find_all_bindings(g, "p")
        assert len(p_bindings) >= 1
        for pb in p_bindings:
            assert pb.kind == BindingKind.PATH, (
                f"Propagated binding 'p' should be PATH, got {pb.kind}"
            )

    def test_otherwise_preserves_binding_kind(self, parse):
        """OTHERWISE propagation should also preserve original binding kind."""
        ast = parse("MATCH (a)-[r]->(b) RETURN r NEXT RETURN r OTHERWISE RETURN r")

        result = LineageAnalyzer().analyze(ast)
        g = result

        r_bindings = find_all_bindings(g, "r")
        for rb in r_bindings:
            assert rb.kind == BindingKind.EDGE, (
                f"Propagated binding 'r' in OTHERWISE should be EDGE, got {rb.kind}"
            )


class TestPropagatedBindingSpan:
    """Propagated bindings across NEXT/OTHERWISE should carry the output span."""

    def test_aliased_next_binding_has_span(self, parse):
        """RETURN s.name AS supplier ... NEXT RETURN supplier — supplier should have span."""
        query = (
            "MATCH (s:Supplier)-[d:DELIVERED]->(p:Part) "
            "RETURN s.name AS supplier, AVG(d.deliveryDays) AS avgDelivery "
            "NEXT RETURN supplier, avgDelivery"
        )
        ast = parse(query)
        g = LineageAnalyzer().analyze(ast, query_text=query)

        # Find supplier in NEXT scope (any scope other than the root)
        root_scope = find_binding(g, "s").scope_id
        supplier_bindings = find_all_bindings(g, "supplier")
        next_supplier = [b for b in supplier_bindings if b.scope_id != root_scope]
        assert next_supplier, (
            f"Expected supplier in NEXT scope, got scopes: "
            f"{[b.scope_id for b in supplier_bindings]}"
        )
        assert next_supplier[0].span is not None, "Propagated aliased binding should have a span"
        span_text = query[next_supplier[0].span.start_offset : next_supplier[0].span.end_offset]
        assert "supplier" in span_text

    def test_bare_next_binding_has_span(self, parse):
        """RETURN n NEXT RETURN n — propagated n should have span."""
        query = "MATCH (n) RETURN n NEXT RETURN n"
        ast = parse(query)
        g = LineageAnalyzer().analyze(ast, query_text=query)

        # Two n bindings in different scopes — the propagated one is non-root
        n_bindings = find_all_bindings(g, "n")
        root_scope = n_bindings[0].scope_id
        next_n = [b for b in n_bindings if b.scope_id != root_scope]
        assert next_n, f"Expected n in NEXT scope, got scopes: {[b.scope_id for b in n_bindings]}"
        assert next_n[0].span is not None, "Propagated bare binding should have a span"

    def test_chained_next_binding_has_span(self, parse):
        """RETURN a NEXT RETURN a AS b NEXT RETURN b — b in final scope should have span."""
        query = "MATCH (a) RETURN a NEXT RETURN a AS b NEXT RETURN b"
        ast = parse(query)
        g = LineageAnalyzer().analyze(ast, query_text=query)

        # b only exists in non-root scopes; any instance should have a span
        b_bindings = find_all_bindings(g, "b")
        assert b_bindings, "Expected at least one 'b' binding"
        # The last b (furthest from root) is the chained propagation
        assert b_bindings[-1].span is not None, "Chained propagated binding should have a span"

    def test_otherwise_binding_has_span(self, parse):
        """MATCH (n) RETURN n NEXT RETURN n OTHERWISE RETURN n — n in OTHERWISE should have span."""
        query = "MATCH (n) RETURN n NEXT RETURN n OTHERWISE RETURN n"
        ast = parse(query)
        g = LineageAnalyzer().analyze(ast, query_text=query)

        # n appears in 3 scopes; the OTHERWISE one is neither root nor NEXT
        n_bindings = find_all_bindings(g, "n")
        scope_ids = {b.scope_id for b in n_bindings}
        assert len(scope_ids) >= 3, f"Expected at least 3 scopes, got {scope_ids}"
        # Every propagated n should have a span
        for b in n_bindings:
            assert b.span is not None, f"Binding n in {b.scope_id} should have a span"


class TestPropagatedBindingLabels:
    """Issue #3: propagated bindings reused in patterns should get labels/types."""

    def test_propagated_binding_has_labels(self, parse):
        """Binding propagated via NEXT and used in a labeled pattern should get labels."""
        ast = parse("MATCH (n:Person) RETURN n NEXT MATCH (n:Employee)-[r]->(m) RETURN m")
        result = LineageAnalyzer().analyze(ast)
        g = result

        # Find the n binding in pat_1
        pat_1 = g.patterns.get("pat_1")
        assert pat_1 is not None

        n_in_pat1 = None
        for bid in g.sources(pat_1.id, LineageEdgeKind.IN_PATTERN):
            b = g.bindings[bid]
            if b.name == "n":
                n_in_pat1 = b
                break

        assert n_in_pat1 is not None

        # The propagated binding should have Employee label expression
        assert "Employee" in n_in_pat1.label_expression, (
            f"Expected propagated binding 'n' in pat_1 to have Employee label, "
            f"got label_expression={n_in_pat1.label_expression!r}"
        )


class TestPropertyRefNextPropagation:
    """Property-ref-based RETURN aliases should propagate correctly across NEXT."""

    def test_aliased_property_has_propagates_to(self, parse):
        """RETURN n.name AS name NEXT ... — name should have PROPAGATES_TO from n."""
        ast = parse("MATCH (n) RETURN n, n.name AS name NEXT MATCH (n) RETURN n")
        g = LineageAnalyzer().analyze(ast)

        # Find the 'name' binding (in the NEXT scope)
        name_bindings = find_all_bindings(g, "name")
        assert name_bindings, "Expected at least one 'name' binding"
        name_b = name_bindings[0]

        # It should have a PROPAGATES_TO source (i.e., inherited from a binding)
        sources = g.sources(name_b.id, LineageEdgeKind.PROPAGATES_TO)
        assert sources, (
            f"Expected 'name' binding to have a PROPAGATES_TO source, "
            f"got edges: {[e for e in g.edges if e.target_id == name_b.id]}"
        )
        # The source should be a binding named 'n'
        source_binding = g.bindings[sources[0]]
        assert source_binding.name == "n", (
            f"Expected PROPAGATES_TO source to be 'n', got {source_binding.name!r}"
        )

    def test_aliased_property_has_depends_on_property(self, parse):
        """RETURN n.name AS name NEXT ... — name should DEPENDS_ON n.name PropertyRef."""
        ast = parse("MATCH (n) RETURN n, n.name AS name NEXT MATCH (n) RETURN n")
        g = LineageAnalyzer().analyze(ast)

        name_bindings = find_all_bindings(g, "name")
        assert name_bindings
        name_b = name_bindings[0]

        # Should have a DEPENDS_ON edge to a PropertyRef with property_name="name"
        dep_targets = g.targets(name_b.id, LineageEdgeKind.DEPENDS_ON)
        prop_deps = [tid for tid in dep_targets if tid in g.property_refs]
        assert prop_deps, (
            f"Expected 'name' binding to DEPENDS_ON a PropertyRef, got dep targets: {dep_targets}"
        )
        prop = g.property_refs[prop_deps[0]]
        assert prop.property_name == "name", (
            f"Expected PropertyRef with property_name='name', got {prop.property_name!r}"
        )

    def test_aliased_property_no_belongs_to(self, parse):
        """RETURN n.name AS name NEXT ... — name should NOT have BELONGS_TO edges."""
        ast = parse("MATCH (n) RETURN n, n.name AS name NEXT MATCH (n) RETURN n")
        g = LineageAnalyzer().analyze(ast)

        name_bindings = find_all_bindings(g, "name")
        assert name_bindings
        name_b = name_bindings[0]

        belongs_to = g.targets(name_b.id, LineageEdgeKind.BELONGS_TO)
        assert not belongs_to, (
            f"Expected 'name' binding to have NO BELONGS_TO edges, got: {belongs_to}"
        )

    def test_filter_chain_through_alias(self, parse):
        """Property alias propagated via NEXT should be traceable through a filter."""
        ast = parse("MATCH (n) RETURN n, n.name AS name NEXT MATCH (n) WHERE n.abc = name RETURN n")
        g = LineageAnalyzer().analyze(ast)

        name_bindings = find_all_bindings(g, "name")
        assert name_bindings
        name_b = name_bindings[0]

        # Should have PROPAGATES_TO from n
        sources = g.sources(name_b.id, LineageEdgeKind.PROPAGATES_TO)
        assert sources, "Expected 'name' to have PROPAGATES_TO source"

        # Should have DEPENDS_ON to n.name PropertyRef
        dep_targets = g.targets(name_b.id, LineageEdgeKind.DEPENDS_ON)
        prop_deps = [tid for tid in dep_targets if tid in g.property_refs]
        assert prop_deps, "Expected 'name' to DEPENDS_ON a PropertyRef"

        # The filter should constrain name
        filters = list(g.filters.values())
        filter_constrained = set()
        for f in filters:
            for tid in g.targets(f.id, LineageEdgeKind.CONSTRAINS):
                if tid in g.bindings:
                    filter_constrained.add(g.bindings[tid].name)
        assert "name" in filter_constrained, (
            f"Expected filter to constrain 'name', constrained: {filter_constrained}"
        )
