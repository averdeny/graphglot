"""Tests for pretty-printing (clause-level line breaks) in the generator."""

import unittest

from graphglot.dialect import Dialect


def _generate(query: str, dialect_name: str = "", pretty: bool = False) -> str:
    """Parse a query via Dialect.validate and generate with the given pretty flag."""
    d = Dialect.get_or_raise(dialect_name or None)
    result = d.validate(query)
    assert result.success, f"Parse failed: {result.error}"
    return d.generate(result.expressions[0], copy=False, pretty=pretty)


def _roundtrip(query: str, dialect_name: str = ""):
    """Parse → generate(pretty=True) → reparse. Return (generated, ast1, ast2)."""
    d = Dialect.get_or_raise(dialect_name or None)

    result1 = d.validate(query)
    assert result1.success, f"Parse failed: {result1.error}"
    ast1 = result1.expressions[0]

    generated = d.generate(ast1, copy=True, pretty=True)

    result2 = d.validate(generated)
    assert result2.success, f"Reparse failed: {result2.error}\nGenerated: {generated!r}"
    ast2 = result2.expressions[0]

    return generated, ast1, ast2


class TestPrettyPrint(unittest.TestCase):
    """Test pretty-printing of generated GQL/Cypher."""

    def test_compact_unchanged(self):
        """Default output has no newlines."""
        result = _generate("MATCH (n) RETURN n")
        self.assertNotIn("\n", result)
        self.assertEqual(result, "MATCH (n) RETURN n")

    def test_match_return(self):
        """MATCH and RETURN on separate lines."""
        result = _generate("MATCH (n) RETURN n", pretty=True)
        lines = result.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "MATCH (n)")
        self.assertEqual(lines[1], "RETURN n")

    def test_match_where_return(self):
        """MATCH, WHERE, RETURN each on own line."""
        result = _generate("MATCH (n) WHERE n.age > 30 RETURN n.name", pretty=True)
        lines = result.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("MATCH", lines[0])
        self.assertIn("WHERE", lines[1])
        self.assertIn("RETURN", lines[2])

    def test_order_by_limit(self):
        """ORDER BY and LIMIT on separate lines."""
        result = _generate("MATCH (n) RETURN n ORDER BY n.name LIMIT 10", pretty=True)
        lines = result.split("\n")
        self.assertGreaterEqual(len(lines), 4)
        self.assertTrue(any("ORDER BY" in line for line in lines))
        self.assertTrue(any("LIMIT" in line for line in lines))

    def test_union(self):
        """UNION branches on separate lines."""
        result = _generate("MATCH (a) RETURN a UNION MATCH (b) RETURN b", pretty=True)
        lines = result.split("\n")
        self.assertGreater(len(lines), 1)
        self.assertTrue(any("UNION" in line for line in lines))

    def test_next_statement(self):
        """NEXT-composed statements on separate lines."""
        result = _generate("MATCH (a) RETURN a NEXT MATCH (b) RETURN b", pretty=True)
        lines = result.split("\n")
        self.assertGreater(len(lines), 1)
        self.assertTrue(any("NEXT" in line for line in lines))

    def test_cypher_with_clause(self):
        """Cypher WITH gets its own line."""
        result = _generate("MATCH (n) WITH n RETURN n", dialect_name="neo4j", pretty=True)
        lines = result.split("\n")
        self.assertGreaterEqual(len(lines), 3)
        self.assertTrue(any("WITH" in line for line in lines))
        self.assertTrue(any("RETURN" in line for line in lines))

    def test_pretty_roundtrip(self):
        """Pretty output re-parses to equivalent AST."""
        queries = [
            ("MATCH (n) RETURN n", ""),
            ("MATCH (n) WHERE n.age > 30 RETURN n.name", ""),
            ("MATCH (n) RETURN n ORDER BY n.name LIMIT 10", ""),
            ("MATCH (a) RETURN a UNION MATCH (b) RETURN b", ""),
            ("MATCH (n) WITH n RETURN n", "neo4j"),
        ]
        for query, dialect_name in queries:
            with self.subTest(query=query, dialect=dialect_name):
                generated, ast1, ast2 = _roundtrip(query, dialect_name=dialect_name)
                self.assertEqual(
                    ast1,
                    ast2,
                    f"AST mismatch for pretty output:\n"
                    f"  Input:     {query}\n"
                    f"  Generated: {generated!r}",
                )


class TestPrettyPrintIndentation(unittest.TestCase):
    """Test indentation of nested blocks in pretty mode."""

    def test_call_subquery_indented(self):
        """CALL { ... } body is indented by 2 spaces."""
        result = _generate(
            "MATCH (a) CALL { MATCH (n) RETURN n } RETURN a, n",
            dialect_name="neo4j",
            pretty=True,
        )
        lines = result.split("\n")
        self.assertEqual(lines[0], "MATCH (a)")
        self.assertEqual(lines[1], "CALL {")
        self.assertEqual(lines[2], "  MATCH (n)")
        self.assertEqual(lines[3], "  RETURN n")
        self.assertEqual(lines[4], "}")
        self.assertEqual(lines[5], "RETURN a, n")

    def test_nested_call_double_indent(self):
        """Nested CALL blocks get cumulative indentation."""
        result = _generate(
            "MATCH (a) CALL { MATCH (b) CALL { MATCH (c) RETURN c } RETURN b, c } RETURN a",
            dialect_name="neo4j",
            pretty=True,
        )
        lines = result.split("\n")
        # Outer CALL body at 2-space indent
        self.assertEqual(lines[2], "  MATCH (b)")
        # Inner CALL block
        self.assertEqual(lines[3], "  CALL {")
        self.assertEqual(lines[4], "    MATCH (c)")
        self.assertEqual(lines[5], "    RETURN c")
        self.assertEqual(lines[6], "  }")
        self.assertEqual(lines[7], "  RETURN b, c")

    def test_exists_predicate_indented(self):
        """EXISTS { multi-clause } body is indented."""
        result = _generate(
            "MATCH (n) WHERE EXISTS { MATCH (n)-[r]->(m) RETURN m } RETURN n",
            dialect_name="neo4j",
            pretty=True,
        )
        # The EXISTS block content should be indented if it has newlines
        self.assertIn("EXISTS {", result)
        # Check indentation within the EXISTS block
        lines = result.split("\n")
        exists_idx = next(i for i, line in enumerate(lines) if "EXISTS {" in line)
        # Lines inside the block should be indented relative to EXISTS
        inner_line = lines[exists_idx + 1]
        self.assertTrue(inner_line.startswith("  "), f"Expected indented line, got: {inner_line!r}")

    def test_inline_braces_not_indented(self):
        """Map literal {name: 'John'} stays inline (no newlines)."""
        result = _generate("RETURN {name: 'John'}", dialect_name="neo4j", pretty=True)
        # Should be single-line braces, no indentation
        self.assertIn("{name : 'John'}", result)
        self.assertNotIn("\n  ", result)  # No indented lines

    def test_node_properties_not_indented(self):
        """Node properties {name: 'John'} stay inline."""
        result = _generate("MATCH (n {name: 'John'}) RETURN n", dialect_name="neo4j", pretty=True)
        # Properties braces should be inline
        self.assertIn("{name : 'John'}", result)

    def test_indented_roundtrip(self):
        """Indented pretty output re-parses to equivalent AST."""
        queries = [
            "MATCH (a) CALL { MATCH (n) RETURN n } RETURN a, n",
            "MATCH (a) CALL { MATCH (b) CALL { MATCH (c) RETURN c } RETURN b, c } RETURN a",
        ]
        for query in queries:
            with self.subTest(query=query):
                generated, ast1, ast2 = _roundtrip(query, dialect_name="neo4j")
                self.assertEqual(
                    ast1,
                    ast2,
                    f"AST mismatch for indented pretty output:\n"
                    f"  Input:     {query}\n"
                    f"  Generated: {generated!r}",
                )
