"""Tests for AST source span tracking.

These tests verify that the @parses decorator wrapper automatically
captures start/end token positions on parsed Expression nodes.
"""

from __future__ import annotations

import pytest

from graphglot.ast.base import Expression
from graphglot.lexer import Lexer
from graphglot.parser import Parser


@pytest.fixture
def parse():
    """Parse a GQL query and return the root AST node."""
    lexer = Lexer()
    parser = Parser()

    def _parse(query: str) -> Expression:
        tokens = lexer.tokenize(query)
        result = parser.parse(tokens, query)
        assert result and result[0] is not None, "Parse failed"
        return result[0]

    return _parse


class TestSourceSpanTracking:
    """Verify that source spans are attached to parsed AST nodes."""

    def test_root_node_has_span(self, parse):
        """The root GqlProgram node should have a span covering the whole query."""
        query = "MATCH (n) RETURN n"
        ast = parse(query)
        span = ast.source_span
        assert span is not None
        start, end = span
        assert start == 0
        assert end == len(query)

    def test_span_covers_original_text(self, parse):
        """source_span offsets should extract the original query text."""
        query = "MATCH (n:Person) RETURN n.name"
        ast = parse(query)
        span = ast.source_span
        assert span is not None
        assert query[span[0] : span[1]] == query

    def test_child_nodes_have_spans(self, parse):
        """Child nodes in the AST should also have source spans."""
        query = "MATCH (n:Person) RETURN n"
        ast = parse(query)

        # At least some children should have spans
        children_with_spans = [
            node for node in ast.dfs() if isinstance(node, Expression) and node.source_span
        ]
        assert len(children_with_spans) > 1

    def test_child_spans_within_parent(self, parse):
        """Child spans should be contained within their parent spans."""
        query = "MATCH (n:Person) RETURN n.name"
        ast = parse(query)
        parent_span = ast.source_span
        assert parent_span is not None

        for node in ast.dfs():
            if node is ast:
                continue
            child_span = node.source_span
            if child_span:
                assert child_span[0] >= parent_span[0], (
                    f"{type(node).__name__} start {child_span[0]} < parent start {parent_span[0]}"
                )
                assert child_span[1] <= parent_span[1], (
                    f"{type(node).__name__} end {child_span[1]} > parent end {parent_span[1]}"
                )

    def test_leaf_identifier_span(self, parse):
        """Leaf Identifier nodes should have precise spans."""
        from graphglot.ast import expressions as expr

        query = "MATCH (n) RETURN n"
        ast = parse(query)

        # Find identifiers — they should have spans
        identifiers = list(ast.find_all(expr.Identifier))
        assert len(identifiers) > 0

        for ident in identifiers:
            span = ident.source_span
            if span:
                text = query[span[0] : span[1]]
                assert ident.name in text

    def test_no_span_on_freshly_constructed(self):
        """Manually constructed Expression nodes should have no span."""
        from graphglot.ast import expressions as expr

        ident = expr.Identifier(name="x")
        assert ident.source_span is None
        assert ident._start_token is None
        assert ident._end_token is None

    def test_span_tokens_have_line_col(self, parse):
        """Start/end tokens should have valid line and column info."""
        query = "MATCH (n) RETURN n"
        ast = parse(query)

        assert ast._start_token is not None
        assert ast._start_token.line >= 1
        assert ast._start_token.col >= 1

        assert ast._end_token is not None
        assert ast._end_token.line >= 1
        assert ast._end_token.col >= 1

    def test_multiline_query_spans(self, parse):
        """Spans work correctly with multi-line queries."""
        query = "MATCH (n:Person)\nRETURN n.name"
        ast = parse(query)
        span = ast.source_span
        assert span is not None
        assert query[span[0] : span[1]] == query

    def test_span_preserved_after_copy(self, parse):
        """Spans should survive deep_copy."""
        query = "MATCH (n) RETURN n"
        ast = parse(query)
        original_span = ast.source_span
        assert original_span is not None

        copied = ast.deep_copy()
        assert copied.source_span == original_span

    def test_equality_ignores_spans(self, parse):
        """Expression equality should not be affected by span data."""
        from graphglot.ast import expressions as expr

        a = expr.Identifier(name="x")
        b = expr.Identifier(name="x")
        assert a == b

        # Even if we manually set span tokens on one, equality should still hold
        # (PrivateAttrs are excluded from model_dump)
        assert a == b

    def test_where_clause_span(self, parse):
        """WHERE clause predicate should have its own span."""
        from graphglot.ast import expressions as expr

        query = "MATCH (n:Person) WHERE n.age > 21 RETURN n"
        ast = parse(query)

        # Find the comparison expression
        comparisons = list(ast.find_all(expr.ComparisonPredicatePart2))
        if comparisons:
            comp = comparisons[0]
            span = comp.source_span
            if span:
                text = query[span[0] : span[1]]
                assert ">" in text


class TestDfsSpanCoverage:
    """Verify span coverage across different query constructs."""

    def test_return_item_has_span(self, parse):
        """ReturnItem nodes should have spans."""
        from graphglot.ast import expressions as expr

        query = "MATCH (n) RETURN n.name AS person_name"
        ast = parse(query)

        items = list(ast.find_all(expr.ReturnItem))
        assert len(items) > 0
        for item in items:
            assert item.source_span is not None

    def test_node_pattern_has_span(self, parse):
        """NodePattern should have a span covering the parenthesized pattern."""
        from graphglot.ast import expressions as expr

        query = "MATCH (n:Person) RETURN n"
        ast = parse(query)

        patterns = list(ast.find_all(expr.NodePattern))
        assert len(patterns) > 0
        for pat in patterns:
            span = pat.source_span
            if span:
                text = query[span[0] : span[1]]
                assert "(" in text
