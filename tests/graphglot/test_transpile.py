"""Tests for the transpile CLI command and Dialect.transpile() method."""

from __future__ import annotations

import json
import unittest

from click.testing import CliRunner

from graphglot.cli import cli
from graphglot.dialect import Dialect
from graphglot.error import FeatureError, GraphGlotError


class TestDialectTranspile(unittest.TestCase):
    """Tests for the Dialect.transpile() instance method."""

    def test_same_dialect_roundtrip(self):
        """Base dialect roundtrip preserves query."""
        dialect = Dialect.get_or_raise("fullgql")
        result = dialect.transpile("MATCH (n) RETURN n")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("MATCH", result[0])
        self.assertIn("RETURN", result[0])

    def test_neo4j_roundtrip(self):
        """Neo4j roundtrip applies dialect transforms (WITH -> NEXT)."""
        dialect = Dialect.get_or_raise("neo4j")
        result = dialect.transpile("MATCH (n) WITH n RETURN n")
        self.assertEqual(len(result), 1)
        # Neo4j's transform rewrites WITH to RETURN...NEXT
        self.assertIn("NEXT", result[0])

    def test_returns_list(self):
        """transpile() always returns a list."""
        dialect = Dialect.get_or_raise("fullgql")
        result = dialect.transpile("MATCH (n) RETURN n")
        self.assertIsInstance(result, list)


class TestTranspileCLI(unittest.TestCase):
    """Tests for the `gg transpile` CLI command."""

    def setUp(self):
        self.runner = CliRunner()

    def test_same_dialect_roundtrip(self):
        """Default roundtrip with no --write uses --read dialect."""
        result = self.runner.invoke(cli, ["transpile", "-r", "neo4j", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MATCH", result.output)
        self.assertIn("RETURN", result.output)

    def test_cross_dialect_neo4j_to_fullgql(self):
        """Neo4j WITH is rewritten to RETURN...NEXT in FullGQL."""
        result = self.runner.invoke(
            cli,
            ["transpile", "-r", "neo4j", "-w", "fullgql", "MATCH (n) WITH n RETURN n"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("NEXT", result.output)

    def test_neo4j_to_coregql(self):
        """Transpile from Neo4j to CoreGQL."""
        result = self.runner.invoke(
            cli,
            ["transpile", "-r", "neo4j", "-w", "coregql", "MATCH (n) RETURN n"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MATCH", result.output)
        self.assertIn("RETURN", result.output)

    def test_transform_applied(self):
        """Neo4j->FullGQL: WITH is rewritten to NEXT (transform fires)."""
        result = self.runner.invoke(
            cli,
            ["transpile", "-r", "neo4j", "-w", "fullgql", "MATCH (n) WITH n RETURN n"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("NEXT", result.output)
        self.assertNotIn("WITH", result.output)

    def test_gql_to_neo4j(self):
        """FullGQL->Neo4j: standard GQL generates valid Cypher output."""
        result = self.runner.invoke(
            cli,
            ["transpile", "-r", "fullgql", "-w", "neo4j", "MATCH (n) RETURN n"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MATCH", result.output)
        self.assertIn("RETURN", result.output)

    def test_default_dialect(self):
        """When no --read or --write, uses base GQL dialect."""
        result = self.runner.invoke(cli, ["transpile", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MATCH", result.output)
        self.assertIn("RETURN", result.output)

    def test_json_output(self):
        """JSON output returns a list of strings."""
        result = self.runner.invoke(
            cli,
            ["transpile", "-r", "fullgql", "-o", "json", "MATCH (n) RETURN n"],
        )
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn("MATCH", data[0])

    def test_multiple_statements(self):
        """Semicolon-separated input produces multiple output lines."""
        result = self.runner.invoke(
            cli,
            ["transpile", "-r", "fullgql", "-o", "json", "MATCH (n) RETURN n ; MATCH (m) RETURN m"],
        )
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(len(data), 2)

    def test_short_alias(self):
        """The `tp` alias works."""
        result = self.runner.invoke(cli, ["tp", "-r", "fullgql", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MATCH", result.output)

    def test_stdin_input(self):
        """Query can be read from stdin."""
        result = self.runner.invoke(cli, ["transpile", "-r", "fullgql"], input="MATCH (n) RETURN n")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MATCH", result.output)


class TestTranspileFeatureValidation(unittest.TestCase):
    """Tests that transpilation fails when the target dialect lacks required features."""

    # -- Dialect.transpile() method --

    def test_optional_feature_rejected_by_coregql(self):
        """LIMIT (GQ13) is optional and not supported by CoreGQL."""
        coregql = Dialect.get_or_raise("coregql")
        with self.assertRaises(FeatureError) as ctx:
            coregql.transpile("MATCH (n) RETURN n LIMIT 10")
        self.assertIn("GQ13", str(ctx.exception))

    def test_optional_feature_accepted_by_fullgql(self):
        """LIMIT (GQ13) is supported by FullGQL — no error."""
        fullgql = Dialect.get_or_raise("fullgql")
        result = fullgql.transpile("MATCH (n) RETURN n LIMIT 10")
        self.assertEqual(len(result), 1)
        self.assertIn("LIMIT", result[0])

    def test_cypher_feature_accepted_by_neo4j(self):
        """STARTS WITH (CY:OP01) is supported by Neo4j — transpiles to LEFT()."""
        neo4j = Dialect.get_or_raise("neo4j")
        result = neo4j.transpile('MATCH (n) WHERE n.name STARTS WITH "A" RETURN n')
        self.assertEqual(len(result), 1)
        # Transform rewrites STARTS WITH → LEFT(...) = ...
        self.assertIn("LEFT(", result[0])

    def test_path_search_rejected_by_coregql(self):
        """ANY SHORTEST (G005+G018) is optional and not supported by CoreGQL."""
        coregql = Dialect.get_or_raise("coregql")
        with self.assertRaises(FeatureError) as ctx:
            coregql.transpile("MATCH ANY SHORTEST (n)-[r]->(m) RETURN n")
        # At least one of the path-search features should appear
        msg = str(ctx.exception)
        self.assertTrue("G005" in msg or "G018" in msg)

    # -- CLI command --

    def test_cli_cypher_to_fullgql_starts_with(self):
        """CLI: Neo4j STARTS WITH → FullGQL succeeds (rewritten to LEFT)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "transpile",
                "-r",
                "neo4j",
                "-w",
                "fullgql",
                'MATCH (n) WHERE n.name STARTS WITH "A" RETURN n',
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("LEFT(", result.output)

    def test_cli_optional_to_coregql_unsupported(self):
        """CLI: LIMIT → CoreGQL fails with non-zero exit."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["transpile", "-r", "fullgql", "-w", "coregql", "MATCH (n) RETURN n LIMIT 10"],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("GQ13", result.output)

    def test_cli_supported_feature_succeeds(self):
        """CLI: Compatible query transpiles without error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["transpile", "-r", "fullgql", "-w", "neo4j", "MATCH (n) RETURN n"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MATCH", result.output)

    # -- Semantic analysis (read side) --

    def test_read_semantic_analysis_rejects_path_comparison(self):
        """Read-side validate() catches GA09 (path comparison) on Neo4j."""
        neo4j = Dialect.get_or_raise("neo4j")
        with self.assertRaises(GraphGlotError) as ctx:
            neo4j.transpile("MATCH p = (a)-[r]->(b), q = (c)-[s]->(d) WHERE p = q RETURN p")
        self.assertIn("GA09", str(ctx.exception))

    def test_cli_read_semantic_analysis_rejects(self):
        """CLI: Read-side semantic analysis catches GA09 on Neo4j."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "transpile",
                "-r",
                "neo4j",
                "MATCH p = (a)-[r]->(b), q = (c)-[s]->(d) WHERE p = q RETURN p",
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("GA09", result.output)

    # -- Semantic analysis (write side) --

    def test_write_semantic_analysis_rejects_path_comparison(self):
        """Write-side analysis catches GA09 when transpiling FullGQL → Neo4j."""
        # FullGQL supports GA09 (read passes), Neo4j doesn't (write fails)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "transpile",
                "-r",
                "fullgql",
                "-w",
                "neo4j",
                "MATCH p = (a)-[r]->(b), q = (c)-[s]->(d) WHERE p = q RETURN p",
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("GA09", result.output)

    def test_write_semantic_analysis_passes_when_supported(self):
        """Write-side analysis passes when FullGQL → FullGQL (GA09 supported)."""
        fullgql = Dialect.get_or_raise("fullgql")
        result = fullgql.transpile("MATCH p = (a)-[r]->(b), q = (c)-[s]->(d) WHERE p = q RETURN p")
        self.assertEqual(len(result), 1)
        self.assertIn("MATCH", result[0])
