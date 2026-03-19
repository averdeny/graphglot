"""Tests for literal output handling and intermediate RETURN suppression."""

from graphglot.lineage import LineageAnalyzer, LineageEdgeKind


def _analyze(parse, query: str):
    ast = parse(query)
    analyzer = LineageAnalyzer()
    return analyzer.analyze(ast, query_text=query)


class TestLiteralOutputEdges:
    """Literal outputs should not get spurious BELONGS_TO edges."""

    def test_literal_without_use_no_belongs_to(self, parse):
        """Literal in default-graph context gets no edges at all."""
        result = _analyze(parse, 'MATCH (n:Person) RETURN n, "hello" AS greeting')
        greeting = next(o for o in result.outputs.values() if o.alias == "greeting")
        belongs = result.targets(greeting.id, LineageEdgeKind.BELONGS_TO)
        depends = result.targets(greeting.id, LineageEdgeKind.DEPENDS_ON)
        assert len(belongs) == 0, "Literal output should not BELONGS_TO default graph"
        assert len(depends) == 0

    def test_literal_with_explicit_use_has_belongs_to(self, parse):
        """USE g RETURN 1 — literal output BELONGS_TO the explicit graph."""
        result = _analyze(parse, "USE g RETURN 1 AS one")
        one = next(o for o in result.outputs.values() if o.alias == "one")
        belongs = result.targets(one.id, LineageEdgeKind.BELONGS_TO)
        assert len(belongs) == 1, "Literal in USE scope should BELONGS_TO the graph"

    def test_literal_is_standalone_node(self, parse):
        """Literal output with no deps has zero outgoing edges."""
        result = _analyze(parse, 'MATCH (n) RETURN "constant" AS c')
        c = next(o for o in result.outputs.values() if o.alias == "c")
        all_outgoing = [e for e in result.edges if e.source_id == c.id]
        assert len(all_outgoing) == 0


class TestIntermediateOutputSuppression:
    """Intermediate RETURN (before NEXT) should not create output entities."""

    def test_intermediate_return_creates_no_outputs(self, parse):
        """RETURN n NEXT RETURN n.name — only the final RETURN creates outputs."""
        result = _analyze(parse, "MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n.name")
        outputs = list(result.outputs.values())
        assert len(outputs) == 1, f"Expected 1 final output, got {len(outputs)}"

    def test_final_return_has_correct_output(self, parse):
        """The single output from NEXT chain is the final RETURN's item."""
        result = _analyze(parse, "MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n.name")
        output = next(iter(result.outputs.values()))
        # Should depend on a property ref for n.name
        deps = result.targets(output.id, LineageEdgeKind.DEPENDS_ON)
        assert len(deps) >= 1

    def test_propagation_still_works(self, parse):
        """PROPAGATES_TO edges survive intermediate output removal."""
        result = _analyze(parse, "MATCH (n:Person) RETURN n NEXT MATCH (n) RETURN n.name")
        # n in scope 1 should propagate to n in scope 2
        propagations = [e for e in result.edges if e.kind == LineageEdgeKind.PROPAGATES_TO]
        assert len(propagations) >= 1

    def test_otherwise_both_branches_have_outputs(self, parse):
        """OTHERWISE branches are final — both create output entities."""
        query = (
            "MATCH (n:Person) RETURN n "
            "NEXT "
            "MATCH (n) RETURN n.name "
            "OTHERWISE "
            "MATCH (n) RETURN n.age"
        )
        result = _analyze(parse, query)
        outputs = list(result.outputs.values())
        # Two final outputs: n.name (branch 1) and n.age (branch 2)
        # The intermediate RETURN n (before NEXT) should NOT be here
        assert len(outputs) == 2, f"Expected 2 final outputs, got {len(outputs)}"

    def test_double_next_only_final_outputs(self, parse):
        """A NEXT B NEXT C — only C's outputs survive."""
        query = (
            "MATCH (a:Person) RETURN a NEXT MATCH (a) RETURN a AS b NEXT MATCH (b) RETURN b.name"
        )
        result = _analyze(parse, query)
        outputs = list(result.outputs.values())
        assert len(outputs) == 1, f"Expected 1 final output, got {len(outputs)}"
