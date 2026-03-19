"""Tests for binding extraction from patterns.

These tests verify that the lineage module correctly extracts bindings
(node, edge, path variables) from MATCH patterns with their kinds,
labels, types, and scope information.
"""

from __future__ import annotations

from graphglot.lineage import BindingKind, LineageAnalyzer, LineageEdgeKind


class TestBindingExtraction:
    """Test extraction of bindings from MATCH patterns."""

    def test_simple_node_binding(self, parse):
        """Extract a single node binding."""
        ast = parse("MATCH (n) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        assert len(result.bindings) == 1
        binding = next(iter(result.bindings.values()))
        assert binding.name == "n"
        assert binding.kind == BindingKind.NODE

    def test_node_with_label(self, parse):
        """Extract node binding with label constraint."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        binding = next(iter(result.bindings.values()))
        assert binding.name == "n"
        assert binding.kind == BindingKind.NODE
        assert "Person" in binding.label_expression

    def test_node_with_multiple_labels(self, parse):
        """Extract node binding with multiple labels."""
        ast = parse("MATCH (n:Person&Employee) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        binding = next(iter(result.bindings.values()))
        assert "Person" in binding.label_expression
        assert "Employee" in binding.label_expression

    def test_edge_binding(self, parse):
        """Extract edge binding from pattern."""
        ast = parse("MATCH (a)-[r]->(b) RETURN r")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        assert len(result.bindings) == 3
        edge_binding = next(b for b in result.bindings.values() if b.name == "r")
        assert edge_binding.kind == BindingKind.EDGE

    def test_edge_with_type(self, parse):
        """Extract edge binding with relationship type."""
        ast = parse("MATCH (a)-[r:KNOWS]->(b) RETURN r")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        edge_binding = next(b for b in result.bindings.values() if b.name == "r")
        assert "KNOWS" in edge_binding.label_expression

    def test_path_binding(self, parse):
        """Extract path variable binding."""
        ast = parse("MATCH p = (a)-[r]->(b) RETURN p")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        path_binding = next(b for b in result.bindings.values() if b.name == "p")
        assert path_binding.kind == BindingKind.PATH

    def test_anonymous_node(self, parse):
        """Anonymous nodes should create synthetic bindings with empty name."""
        ast = parse("MATCH (a)-[r]->() RETURN a")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        named = {b.name for b in result.bindings.values() if b.name}
        assert named == {"a", "r"}
        anon = [b for b in result.bindings.values() if not b.name]
        assert len(anon) == 1
        assert anon[0].kind == BindingKind.NODE

    def test_anonymous_edge(self, parse):
        """Anonymous edges should create synthetic bindings with empty name."""
        ast = parse("MATCH (a)-[]->(b) RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        named = {b.name for b in result.bindings.values() if b.name}
        assert named == {"a", "b"}
        anon = [b for b in result.bindings.values() if not b.name]
        assert len(anon) == 1
        assert anon[0].kind == BindingKind.EDGE

    def test_anonymous_edge_preserves_type(self, parse):
        """Anonymous edges should preserve relationship types on binding."""
        ast = parse("MATCH (a:User)-[:FOLLOWS]->(b:User) RETURN a, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        edge_bindings = [b for b in result.bindings.values() if b.kind == BindingKind.EDGE]
        assert len(edge_bindings) == 1
        assert edge_bindings[0].name is None
        assert edge_bindings[0].label_expression == "FOLLOWS"

    def test_multiple_anonymous_edges_preserve_types(self, parse):
        """Multiple anonymous edges should each preserve their label expressions."""
        ast = parse("MATCH (a:User)-[:KNOWS]->(b:User)-[:LIVES_IN]->(c:City) RETURN a, c")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        edge_bindings = [b for b in result.bindings.values() if b.kind == BindingKind.EDGE]
        assert len(edge_bindings) == 2
        edge_labels = {eb.label_expression for eb in edge_bindings if eb.label_expression}
        assert edge_labels == {"KNOWS", "LIVES_IN"}

    def test_multiple_patterns_same_variable(self, parse):
        """Same variable in multiple patterns should be one binding."""
        ast = parse("""
            MATCH (p:Person)-[:OWNS]->(car:Car),
                  (p)-[:LIVES_IN]->(city:City)
            RETURN p, car, city
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        p_bindings = [b for b in result.bindings.values() if b.name == "p"]
        assert len(p_bindings) == 1
        named = {b.name for b in result.bindings.values() if b.name}
        assert named == {"p", "car", "city"}
        # Anonymous edges [:OWNS] and [:LIVES_IN] should have bindings too
        edge_bindings = [b for b in result.bindings.values() if b.kind == BindingKind.EDGE]
        assert len(edge_bindings) == 2
        edge_labels = {eb.label_expression for eb in edge_bindings if eb.label_expression}
        assert edge_labels == {"OWNS", "LIVES_IN"}


class TestBindingScopes:
    """Test scope handling for bindings."""

    def test_yield_passes_bindings(self, parse):
        """YIELD clause passes specified bindings — output depends on n."""
        ast = parse("MATCH (n:Person) YIELD n RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # n should exist as a binding and the output should depend on it
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        assert n_binding is not None

        # Output should have a dependency edge back to n
        from graphglot.lineage import LineageEdgeKind

        output = next(iter(result.outputs.values()))
        dep_targets = result.targets(output.id, LineageEdgeKind.DEPENDS_ON)
        # Should transitively depend on n (via property ref)
        all_dep_ids = set(dep_targets)
        for tid in dep_targets:
            all_dep_ids.update(result.targets(tid, LineageEdgeKind.DEPENDS_ON))
        assert n_binding.id in all_dep_ids, "Output should depend on n binding"

    def test_next_creates_scope_boundary(self, parse):
        """NEXT statement creates a new scope boundary with different scope_ids."""
        ast = parse("""
            MATCH (n:Person) RETURN n
            NEXT
            MATCH (m:Company) RETURN m
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # n and m should be in different scopes
        n_binding = next(b for b in result.bindings.values() if b.name == "n")
        m_binding = next(b for b in result.bindings.values() if b.name == "m")
        assert n_binding.scope_id != m_binding.scope_id, (
            "NEXT should create a scope boundary between n and m"
        )

        # n should also be propagated into the NEXT scope
        from graphglot.lineage import LineageEdgeKind

        n_bindings = [b for b in result.bindings.values() if b.name == "n"]
        if len(n_bindings) >= 2:
            # There's a propagated n — check PROPAGATES_TO edge
            prop_edges = [e for e in result.edges if e.kind == LineageEdgeKind.PROPAGATES_TO]
            n_ids = {b.id for b in n_bindings}
            assert any(e.source_id in n_ids and e.target_id in n_ids for e in prop_edges)

    def test_let_introduces_binding(self, parse):
        """LET statement introduces a new binding."""
        ast = parse("LET x = 5 RETURN x")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        x_binding = next((b for b in result.bindings.values() if b.name == "x"), None)
        assert x_binding is not None
        assert x_binding.kind == BindingKind.VARIABLE

    def test_let_binding_tracks_value_dependencies(self, parse):
        """LET binding should depend on the expression that defines it."""
        ast = parse("MATCH (n:Person) LET x = n.name RETURN x")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        x_binding = next((b for b in result.bindings.values() if b.name == "x"), None)
        n_binding = next((b for b in result.bindings.values() if b.name == "n"), None)
        assert x_binding is not None
        assert n_binding is not None

        dep_targets = result.targets(x_binding.id, LineageEdgeKind.DEPENDS_ON)
        assert dep_targets, "Expected LET binding to have dependency edges"
        assert n_binding.id in result.binding_deps(x_binding.id)

        prop_names = {
            result.property_refs[tid].property_name
            for tid in dep_targets
            if tid in result.property_refs
        }
        assert "name" in prop_names

    def test_yield_selective_passthrough(self, parse):
        """YIELD only passes specified bindings — output depends only on yielded binding."""
        ast = parse("""
            MATCH (a:Person), (b:Company)
            YIELD a
            RETURN a.name
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # Output should depend on a (via property ref), not b
        from graphglot.lineage import LineageEdgeKind

        output = next(iter(result.outputs.values()))
        dep_targets = result.targets(output.id, LineageEdgeKind.DEPENDS_ON)
        all_dep_ids = set(dep_targets)
        for tid in dep_targets:
            all_dep_ids.update(result.targets(tid, LineageEdgeKind.DEPENDS_ON))

        a_binding = next(b for b in result.bindings.values() if b.name == "a")
        b_binding = next((b for b in result.bindings.values() if b.name == "b"), None)

        assert a_binding.id in all_dep_ids, "Output should depend on yielded binding 'a'"
        if b_binding:
            assert b_binding.id not in all_dep_ids, (
                "Output should not depend on non-yielded binding 'b'"
            )


class TestPatternEntities:
    """Test that Pattern entities are created and populated."""

    def test_single_pattern_created(self, parse):
        """A single MATCH produces one Pattern entity."""
        ast = parse("MATCH (n:Person) RETURN n")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        assert len(result.patterns) == 1
        pat = next(iter(result.patterns.values()))
        assert pat.id == "pat_0"
        assert pat.match_index == 0

    def test_pattern_binding_ids(self, parse):
        """Pattern entity should have IN_PATTERN edges from its bindings."""
        ast = parse("MATCH (a)-[r]->(b) RETURN a, r, b")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        assert len(result.patterns) == 1
        pat = next(iter(result.patterns.values()))
        binding_ids = result.sources(pat.id, LineageEdgeKind.IN_PATTERN)
        assert len(binding_ids) == 3

        # Binding IDs should correspond to actual bindings
        for bid in binding_ids:
            assert bid in result.bindings

    def test_pattern_source_text(self, parse):
        """Pattern entity should have source_text derived via graph helper."""
        query = "MATCH (p:Person)-[r:KNOWS]->(f:Person) RETURN p, f"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)

        pat = next(iter(result.patterns.values()))
        src = result.source_text(pat)
        assert src is not None
        assert src in query

    def test_multi_match_creates_multiple_patterns(self, parse):
        """Multiple MATCH clauses create distinct Pattern entities."""
        ast = parse("""
            MATCH (p:Person)-[r:KNOWS]->(f:Person)
            MATCH (p)-[w:WORKS_AT]->(c:Company)
            RETURN p, f, c
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        assert len(result.patterns) >= 2
        indices = sorted(p.match_index for p in result.patterns.values())
        assert indices[0] == 0
        assert indices[1] == 1

    def test_multi_pattern_same_match(self, parse):
        """Comma-separated patterns in one MATCH create distinct Pattern entities."""
        ast = parse("""
            MATCH (p:Person)-[:OWNS]->(car:Car),
                  (p)-[:LIVES_IN]->(city:City)
            RETURN p, car, city
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # Two path patterns in one MATCH → two Pattern entities, same match_index
        assert len(result.patterns) == 2
        match_indices = {p.match_index for p in result.patterns.values()}
        assert match_indices == {0}

    def test_pattern_has_span(self, parse):
        """Pattern should have span when query_text is provided."""
        query = "MATCH (n:Person) RETURN n"
        ast = parse(query)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast, query_text=query)

        pat = next(iter(result.patterns.values()))
        assert pat.span is not None

    def test_shared_binding_appears_in_first_pattern(self, parse):
        """A binding used in multiple patterns has IN_PATTERN edges."""
        ast = parse("""
            MATCH (p:Person)-[r:KNOWS]->(f:Person)
            MATCH (p)-[w:WORKS_AT]->(c:Company)
            RETURN p, f, c
        """)

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        # p should have IN_PATTERN edge to first pattern
        pats = sorted(result.patterns.values(), key=lambda x: x.id)
        p_binding = next(b for b in result.bindings.values() if b.name == "p")
        pat0_bindings = result.sources(pats[0].id, LineageEdgeKind.IN_PATTERN)
        assert p_binding.id in pat0_bindings


class TestOutputBindingDedup:
    """Test dedup of output→binding edges when binding is reachable via property refs."""

    def test_output_no_redundant_binding_edge(self, parse):
        """Output depending on n.name ORDER BY n.age should NOT have direct edge to n."""
        ast = parse("MATCH (n) RETURN n.name ORDER BY n.age")
        result = LineageAnalyzer().analyze(ast)
        graph = result

        output = next(iter(graph.outputs.values()))
        # Output should depend on property refs, not directly on the binding
        dep_targets = graph.targets(output.id, LineageEdgeKind.DEPENDS_ON)
        n_binding = next(b for b in graph.bindings.values() if b.name == "n")
        assert n_binding.id not in dep_targets, (
            "Output should not have direct DEPENDS_ON to binding when reachable via property refs"
        )

    def test_output_direct_binding_when_no_property(self, parse):
        """Output depending on bare binding n should have direct edge to n."""
        ast = parse("MATCH (n) RETURN n")
        result = LineageAnalyzer().analyze(ast)
        graph = result

        output = next(iter(graph.outputs.values()))
        dep_targets = graph.targets(output.id, LineageEdgeKind.DEPENDS_ON)
        n_binding = next(b for b in graph.bindings.values() if b.name == "n")
        assert n_binding.id in dep_targets, (
            "Output should have direct DEPENDS_ON to binding when no property refs"
        )
