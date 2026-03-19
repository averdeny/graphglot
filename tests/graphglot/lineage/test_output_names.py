"""Tests for ImpactAnalyzer.output_names()."""

from __future__ import annotations

from graphglot.lineage import ImpactAnalyzer, LineageAnalyzer


def _output_names(parse, query: str) -> list[str]:
    """Parse query, run lineage analysis, return output_names()."""
    ast = parse(query)
    result = LineageAnalyzer().analyze(ast, query_text=query)
    return ImpactAnalyzer(result).output_names()


class TestOutputNamesSimple:
    """Simple single-RETURN queries."""

    def test_single_variable(self, parse):
        names = _output_names(parse, "MATCH (n:Person) RETURN n")
        assert names == ["n"]

    def test_single_property(self, parse):
        names = _output_names(parse, "MATCH (n:Person) RETURN n.name")
        assert names == ["n.name"]

    def test_aliased_output(self, parse):
        names = _output_names(parse, "MATCH (n:Person) RETURN n.name AS fullName")
        assert names == ["fullName"]

    def test_multiple_outputs(self, parse):
        names = _output_names(parse, "MATCH (n:Person) RETURN n.name, n.age, n.city")
        assert names == ["n.name", "n.age", "n.city"]

    def test_mixed_aliased_and_bare(self, parse):
        names = _output_names(parse, "MATCH (n:Person) RETURN n.name AS name, n.age")
        assert names == ["name", "n.age"]

    def test_aggregation_with_alias(self, parse):
        names = _output_names(parse, "MATCH (n:Person) RETURN count(n) AS total")
        assert names == ["total"]

    def test_expression_output(self, parse):
        names = _output_names(parse, "MATCH (n:Person) RETURN n.age + 1 AS next_age")
        assert names == ["next_age"]


class TestOutputNamesNext:
    """Queries with NEXT — only the last RETURN matters."""

    def test_next_takes_last_return(self, parse):
        """NEXT chain: output_names() returns last scope's outputs."""
        names = _output_names(
            parse,
            "MATCH (n:Person) RETURN n.name AS name, n.age AS age "
            "NEXT MATCH (x) RETURN x.name AS final_name",
        )
        assert names == ["final_name"]

    def test_next_chain_multiple_outputs(self, parse):
        names = _output_names(
            parse,
            "MATCH (n:Person) RETURN n AS p NEXT MATCH (p) RETURN p.name, p.age",
        )
        assert names == ["p.name", "p.age"]

    def test_double_next(self, parse):
        """Two NEXT hops — only the very last RETURN counts."""
        names = _output_names(
            parse,
            "MATCH (a:Person) RETURN a AS x "
            "NEXT MATCH (x) RETURN x AS y "
            "NEXT MATCH (y) RETURN y.name AS result",
        )
        assert names == ["result"]

    def test_many_next_scopes_use_final_scope_not_lexicographic_max(self, parse):
        """Long NEXT chains should still pick the true final scope."""
        query = "MATCH (n:Person) RETURN n AS s0"
        for i in range(10):
            query += f" NEXT RETURN s{i} AS s{i + 1}"
        query += " NEXT RETURN s10 AS final_name"

        names = _output_names(parse, query)
        assert names == ["final_name"]


class TestOutputNamesOtherwise:
    """Queries with OTHERWISE — both branches produce outputs."""

    def test_otherwise_returns_main_branch(self, parse):
        """OTHERWISE: output_names() returns the main branch outputs."""
        names = _output_names(
            parse,
            "MATCH (n:Person) RETURN n.name AS name OTHERWISE RETURN 'unknown' AS name",
        )
        # Both branches have outputs; last scope is OTHERWISE but main
        # branch outputs are what the query ultimately produces
        assert "name" in names

    def test_next_then_otherwise(self, parse):
        """NEXT followed by OTHERWISE — last RETURN is in the NEXT scope."""
        names = _output_names(
            parse,
            "MATCH (n:Person) RETURN n AS p "
            "NEXT MATCH (p) RETURN p.name AS result "
            "OTHERWISE RETURN 'fallback' AS result",
        )
        assert "result" in names


class TestOutputNamesWithoutQueryText:
    """output_names() without query_text — falls back to reconstruction from deps."""

    def _output_names_no_text(self, parse, query: str) -> list[str]:
        """Analyze without query_text so source_text() returns None."""
        ast_tree = parse(query)
        result = LineageAnalyzer().analyze(ast_tree)  # no query_text
        return ImpactAnalyzer(result).output_names()

    def test_alias_still_works(self, parse):
        """Alias is first choice — works without query_text."""
        names = self._output_names_no_text(parse, "MATCH (n:Person) RETURN n AS p")
        assert names == ["p"]

    def test_bare_variable_reconstructed(self, parse):
        """Bare variable name reconstructed from binding dependency."""
        names = self._output_names_no_text(parse, "MATCH (n:Person) RETURN n")
        assert names == ["n"]

    def test_property_access_reconstructed(self, parse):
        """Property access reconstructed from binding + property deps."""
        names = self._output_names_no_text(parse, "MATCH (n:Person) RETURN n.name")
        assert names == ["n.name"]

    def test_multiple_outputs_reconstructed(self, parse):
        """Multiple outputs reconstructed without query_text."""
        names = self._output_names_no_text(parse, "MATCH (n:Person) RETURN n.name, n.age")
        assert names == ["n.name", "n.age"]


class TestOutputNamesEdgeCases:
    """Edge cases and special queries."""

    def test_return_literal(self, parse):
        names = _output_names(parse, "RETURN 1 AS one, 'hello' AS greeting")
        assert names == ["one", "greeting"]

    def test_no_alias_property_access(self, parse):
        """Without alias, source_text is used."""
        names = _output_names(parse, "MATCH (a)-[r]->(b) RETURN a, b")
        assert names == ["a", "b"]
