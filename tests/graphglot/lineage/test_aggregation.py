"""Tests for aggregation analysis.

These tests verify that the lineage module correctly identifies:
- Aggregated vs non-aggregated outputs
- Aggregation edges (AGGREGATES)
"""

from __future__ import annotations

from graphglot.lineage import LineageAnalyzer, LineageEdgeKind


class TestAggregationDetection:
    """Test detection of aggregation in expressions."""

    def test_count_is_aggregated(self, parse):
        """count() function marks output as aggregated."""
        ast = parse("MATCH (n:Person) RETURN count(n)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        assert output.is_aggregated is True
        assert output.aggregate_function == "count"

    def test_count_star_is_aggregated(self, parse):
        """count(*) is aggregated."""
        ast = parse("MATCH (n:Person) RETURN count(*)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        assert output.is_aggregated is True

    def test_sum_is_aggregated(self, parse):
        """sum() function marks output as aggregated."""
        ast = parse("MATCH (o:`Order`) RETURN SUM(o.amount)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        assert output.is_aggregated is True
        assert output.aggregate_function == "sum"

    def test_avg_is_aggregated(self, parse):
        """avg() function marks output as aggregated."""
        ast = parse("MATCH (p:Person) RETURN avg(p.age)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        assert output.is_aggregated is True
        assert output.aggregate_function == "avg"

    def test_min_max_are_aggregated(self, parse):
        """min() and max() are aggregated."""
        ast = parse("MATCH (p:Person) RETURN min(p.age), max(p.age)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        outputs = list(result.outputs.values())
        assert len(outputs) == 2
        assert all(o.is_aggregated for o in outputs)

    def test_collect_is_aggregated(self, cypher_parse):
        """collect() function marks output as aggregated."""
        ast = cypher_parse("MATCH (n:Person) RETURN collect(n.name)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        assert output.is_aggregated is True
        assert output.aggregate_function == "collect"

    def test_non_aggregated_property(self, parse):
        """Simple property access is not aggregated."""
        ast = parse("MATCH (n:Person) RETURN n.name")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        assert output.is_aggregated is False

    def test_non_aggregated_expression(self, parse):
        """Expression without aggregation is not aggregated."""
        ast = parse("MATCH (n:Person) RETURN n.age + 1")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        assert output.is_aggregated is False


class TestDistinctDetection:
    """Test detection of DISTINCT on output fields."""

    def test_return_distinct_marks_outputs(self, parse):
        """RETURN DISTINCT sets is_distinct on all output fields."""
        ast = parse("MATCH (n:Person) RETURN DISTINCT n.name, n.age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        outputs = list(result.outputs.values())
        assert len(outputs) == 2
        assert all(o.is_distinct for o in outputs)

    def test_return_without_distinct(self, parse):
        """Plain RETURN does not set is_distinct."""
        ast = parse("MATCH (n:Person) RETURN n.name, n.age")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        outputs = list(result.outputs.values())
        assert len(outputs) == 2
        assert not any(o.is_distinct for o in outputs)


class TestAggregationEdges:
    """Test lineage graph edges for aggregation."""

    def test_aggregates_edge(self, parse):
        """Aggregated output has AGGREGATES edge to source binding."""
        ast = parse("MATCH (n:Person) RETURN count(n)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        output = next(iter(result.outputs.values()))
        n_binding = next(b for b in result.bindings.values() if b.name == "n")

        agg_edges = [
            e
            for e in result.edges
            if e.source_id == output.id
            and e.target_id == n_binding.id
            and e.kind == LineageEdgeKind.AGGREGATES
        ]
        assert len(agg_edges) == 1

    def test_aggregated_output_detected(self, parse):
        """Aggregated output is detected and marked."""
        ast = parse("MATCH (p:Person) RETURN p.country, count(p)")

        analyzer = LineageAnalyzer()
        result = analyzer.analyze(ast)

        agg_output = next((o for o in result.outputs.values() if o.is_aggregated), None)
        assert agg_output is not None
        assert agg_output.aggregate_function is not None
